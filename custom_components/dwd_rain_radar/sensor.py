"""Sensor entities for the DWD Rain Radar integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from operator import attrgetter

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfPrecipitationDepth
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)

from .const import DOMAIN
from .coordinator import DwdRainRadarUpdateCoordinator, PrecipitationForecast
from .entity import DwdCoordinatorEntity


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PrecipitationSensorEntityDescription(SensorEntityDescription):
    """Provide a description for a precipitation sensor."""

    value_fn: Callable[[PrecipitationForecast], float | None]
    exists_fn: Callable[[dict], bool] = lambda _: True


PRECIPTITATION_SENSORS = [
    PrecipitationSensorEntityDescription(
        key="precipitation",
        name="Precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda forecast: forecast.precipitation,
    )
]


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PrecipitationSensorEntity(coordinator, description)
        for description in PRECIPTITATION_SENSORS
        if description.exists_fn(entry)
    )


class PrecipitationSensorEntity(DwdCoordinatorEntity, SensorEntity):
    """Implementation of a precipitation sensor."""

    def __init__(
            self,
            coordinator: DwdRainRadarUpdateCoordinator,
            description: PrecipitationSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, description)

        self._attr_unique_id = (
            f"{self.coordinator.config_entry.entry_id}"
            + f"_{self.entity_description.key}"
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        forecasts = self.coordinator.data
        assert forecasts[0] is not None

        return self.entity_description.value_fn(forecasts[0])
