"""Data update coordinator for the DWD Rain Radar integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator
)

from .const import CONF_COORDINATES
from .radolan import Radolan

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=300)


@dataclass(slots=True)
class PrecipitationForecast:
    """Model for precipitation forecast."""
    precipitation: float
    prediction_time: datetime

    @classmethod
    def from_radolan_data(cls, data) -> PrecipitationForecast:
        """Return instance of Precipitation."""
        return cls(
            prediction_time=data.prediction_time.values[0],
            precipitation=data.RV.values.item()
        )


class DwdRainRadarUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator."""

    def __init__(
            self,
            hass: HomeAssistant,
            entry: ConfigEntry,
            async_client,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data[CONF_NAME],
            update_interval=UPDATE_INTERVAL,
        )
        self.config_entry = entry
        self.async_client = async_client
        self.coords = entry.data[CONF_COORDINATES]
        self.lat = self.coords["latitude"]
        self.lon = self.coords["longitude"]
        self.radolan = Radolan(self.lat, self.lon, self.async_client)

    async def _async_update_data(self) -> List[PrecipitationForecast]:
        """Update the data"""
        data = await self.radolan.update()

        forecasts = list(map(PrecipitationForecast.from_radolan_data, data))

        """Make sure closest predictions are first"""
        forecasts.sort(key=lambda forecast: forecast.prediction_time, reverse=False)

        _LOGGER.debug("Fetched forecasts: {}".format(forecasts))

        return forecasts
