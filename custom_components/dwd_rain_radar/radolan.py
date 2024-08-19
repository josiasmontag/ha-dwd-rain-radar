# -*- coding: utf-8 -*-
import asyncio
import tarfile
import logging
from io import BytesIO

import wradlib as wrl

import httpx
import numpy as np

from datetime import datetime, timedelta, timezone

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

        self._radolan_grid_ll = None
        self._last_grid_update = datetime.now(timezone.utc)
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

            # read the file
            f = tar.extractfile(tarinfo)
            ds = wrl.io.open_radolan_dataset(f)

            radolan_grid_ll = self._get_radolan_grid(ds)

            ds = ds.assign_coords({
                "lon": (["y", "x"], radolan_grid_ll[..., 0]),
                "lat": (["y", "x"], radolan_grid_ll[..., 1])
            })

            abslat = np.abs(ds.lat - self._lat)
            abslon = np.abs(ds.lon - self._lon)
            c = np.maximum(abslon, abslat)

            # Attention: y/lat is first dim, get
            ([yidx], [xidx]) = np.where(c == np.min(c))

            # Select index location at the x/y dimension
            # use isel as we select with index
            point_ds = ds.isel(x=xidx, y=yidx)

            result.append(point_ds)

        return result

    def _get_radolan_grid(self, ds):
        """Return the radolan lat, lon grid."""
        grid_age = datetime.now(timezone.utc) - self._last_grid_update
        to_refresh = grid_age > timedelta(hours=24)
        if to_refresh or self._radolan_grid_ll is None:
            self._radolan_grid_ll = wrl.georef.get_radolan_grid(
                nrows=ds.sizes["y"],
                ncols=ds.sizes["x"],
                wgs84=True,
                mode="radolan",
                # proj=proj_stereo
            )

        return self._radolan_grid_ll
