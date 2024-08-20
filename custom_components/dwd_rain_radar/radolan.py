# -*- coding: utf-8 -*-
import asyncio
import tarfile
import logging
from io import BytesIO

import httpx

from datetime import datetime, timedelta, timezone

from pyproj import Transformer

from .const import DWD_RADAR_COMPOSITE_RV_URL

_LOGGER = logging.getLogger(__name__)


class Radolan:
    """Radolan class."""

    def __init__(
            self,
            latitude: float,
            longitude: float,
            async_client: httpx.AsyncClient
    ):
        """Initialize instance."""
        self._async_client = async_client
        self._lat = latitude
        self._lon = longitude
        self._last_etag = None

        self._radolan_coord = None
        self.curr_value = None

    async def update(self):
        """Update DWD Radar data."""
        url = self._get_url()
        headers = {}
        if self._last_etag is not None:
            headers["If-None-Match"] = self._last_etag

        resp = await self._async_client.get(url, headers=headers)

        _LOGGER.debug(f"Response {resp.status_code} (Headers: {resp.headers}) from {url}")

        if resp.status_code == 304:
            return self.curr_value

        if resp.status_code != httpx.codes.OK:
            resp.raise_for_status()

        loop = asyncio.get_running_loop()

        self.curr_value = await loop.run_in_executor(None, self._parse, resp.read())

        self._last_etag = resp.headers["ETag"]

        return self.curr_value

    def _get_url(self) -> str:
        """Return the url."""
        return DWD_RADAR_COMPOSITE_RV_URL

    def _parse(self, response):
        """Parse the response."""

        tar = tarfile.open(fileobj=BytesIO(response), mode="r:bz2")
        result = []

        for tarinfo in tar:

            if not tarinfo.isreg():
                continue

            # Read the file
            f = tar.extractfile(tarinfo)
            header = self._read_header(f)
            # coord = self._get_closest_grid_indices(header['dimension'])
            coord = self._get_radolan_rv_coord()
            value = self._read_values(header, f, coord)

            result.append({
                'timestamp': header['timestamp'],
                'value': value,
            })

        return result

    def _read_header(self, stream):
        """Read the header information from the Radolan file."""
        headerBytes = stream.read(91)
        assert len(headerBytes) == 91, 'file too short'
        msLen = int(headerBytes[88:91])
        stream.read(msLen)
        assert stream.read(1) == b'\x03', '\\x03 at the end of header is missing -> wrong file format'
        dimension = headerBytes[60:69]
        [size_y, size_x] = map(lambda val: int(val), dimension.split(b'x', 2))
        DDhhmm = headerBytes[2:8]
        MMYY = headerBytes[13:17]
        timestamp = self._convert_to_timestamp(DDhhmm.decode(), MMYY.decode())
        precisionStr = headerBytes[47:51]
        precision = self._decode_precision(precisionStr.decode())
        forecast = headerBytes[72:75]

        return {
            'dimension': {'x': size_x, 'y': size_y},
            'precision': precision,
            'timestamp': timestamp + timedelta(minutes=int(forecast)),
        }

    def _decode_precision(self, precision):
        return pow(10, int(precision[1:4]))

    def _convert_to_timestamp(self, DDhhmm, MMYY):
        return datetime(int('20' + MMYY[2:4]), int(MMYY[0:2]), int(DDhhmm[0:2]),
                        int(DDhhmm[2:4]), int(DDhhmm[4:6]), 0, tzinfo=timezone.utc)

    def _read_values(self, header, stream, coord):
        """Read the data values from the Radolan file."""
        header_x = header['dimension']['x']
        header_y = header['dimension']['y']

        assert coord[0] <= header_x, f"x ({coord[0]}) shall be lesser than {header_x}"
        assert coord[1] <= header_y, f"y ({coord[1]}) shall be lesser than {header_y}"

        dataRow = bytearray(header_x * 2)

        for curY in range(header_y):
            assert stream.readinto(dataRow) == len(dataRow), 'file too short'
            if curY == coord[1]:
                valBytes = dataRow[coord[0] * 2: coord[0] * 2 + 2]
                if valBytes == b'\xc4\x29':  # Special value indicating missing data
                    return None
                else:
                    return float(int.from_bytes(valBytes, 'little')) * header['precision']

    def _get_radolan_grid(self, ds):
        """Create the Radolan latitude and longitude grid."""
        grid_age = datetime.now(timezone.utc) - self._last_grid_update
        to_refresh = grid_age > timedelta(hours=24)
        if to_refresh or self._radolan_grid is None:
            # Create the grid here; replace the wradlib logic with a custom calculation if needed
            self._radolan_grid = self._generate_radolan_grid(nrows=ds['dimension']['y'], ncols=ds['dimension']['x'])

        return self._radolan_grid

    def _get_radolan_rv_coord(self):
        """see https://www.dwd.de/DE/leistungen/radarprodukte/formatbeschreibung_rv.pdf"""
        if self._radolan_coord is None:
            transformer = Transformer.from_proj("EPSG:4326",
                                                "+proj=stere +lat_0=90 +lat_ts=60 +lon_0=10 +a=6378137 +b=6356752.3142451802 +no_defs +x_0=543696.83521776402 +y_0=3622088.8619310018")
            (x, y) = transformer.transform(self._lat, self._lon)
            self._radolan_coord = ((int(round(x / 1000, 0)), int(round(y / 1000 + 1200, 0))))
        return self._radolan_coord
