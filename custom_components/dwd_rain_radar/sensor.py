"""Sensor entities for the DWD Rain Radar integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
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

from .const import DOMAIN, ATTRIBUTION, FORECAST_MINUTES
from homeassistant.const import (
    ATTR_ATTRIBUTION
)
from .coordinator import DwdRainRadarUpdateCoordinator, PrecipitationForecast
from .entity import DwdCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PrecipitationSensorEntityDescription(SensorEntityDescription):
    """Provide a description for a precipitation sensor."""

    value_fn: Callable[[PrecipitationForecast]]
    extra_state_attributes_fn: Callable[[PrecipitationForecast], dict] = lambda _: {}
    exists_fn: Callable[[dict], bool] = lambda _: True


PRECIPTITATION_SENSORS = [
    PrecipitationSensorEntityDescription(
        key="precipitation",
        name="Precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda forecasts: next(
            (forecast.precipitation for forecast in forecasts if
             forecast.prediction_time > datetime.now().astimezone() - timedelta(minutes=5)),
            None
        ),
        extra_state_attributes_fn=lambda forecasts: {
            'prediction_time': next(
                (forecast.prediction_time for forecast in forecasts if
                 forecast.prediction_time > datetime.now().astimezone() - timedelta(minutes=5)),
                None
            )
        },
    ),
    *(PrecipitationSensorEntityDescription(
        key=f"precipitation_in_{forecast_in}_minutes",
        name=f"Precipitation In {forecast_in} Minutes",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda forecasts, forecast_in=forecast_in: next(
            (forecast.precipitation for forecast in forecasts if
             forecast.prediction_time > datetime.now().astimezone() + timedelta(minutes=forecast_in - 5)),
            None
        ),
        extra_state_attributes_fn=lambda forecasts, forecast_in=forecast_in: {
            'prediction_time': next(
                (forecast.prediction_time for forecast in forecasts if
                 forecast.prediction_time > datetime.now().astimezone() + timedelta(minutes=forecast_in - 5)),
                None
            )
        },
    ) for forecast_in in FORECAST_MINUTES),
    PrecipitationSensorEntityDescription(
        key="rain_expected_at",
        name="Rain Expected At",
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda forecasts: next(
            (forecast.prediction_time for forecast in forecasts if
             forecast.precipitation > 0 and forecast.prediction_time > datetime.now().astimezone()),
            None
        ),
        extra_state_attributes_fn=lambda forecasts: {
            'precipitation': next(
                (forecast.precipitation for forecast in forecasts if
                 forecast.precipitation > 0 and forecast.prediction_time > datetime.now().astimezone()),
                None
            )
        },
    ),
    PrecipitationSensorEntityDescription(
        key="rain_expected_in_minutes",
        name="Rain Expected In Minutes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda forecasts: next(
            (int((forecast.prediction_time - datetime.now().astimezone()).total_seconds() // 60) for forecast in
             forecasts if forecast.precipitation > 0 and forecast.prediction_time > datetime.now().astimezone()),
            None
        ),
        extra_state_attributes_fn=lambda forecasts: {
            'precipitation': next(
                (forecast.precipitation for forecast in forecasts if
                 forecast.precipitation > 0 and forecast.prediction_time > datetime.now().astimezone()),
                None
            )
        },
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
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        attributes = self.entity_description.extra_state_attributes_fn(self.coordinator.data)

        attributes['latest_update'] = self.coordinator.latest_update
        attributes[ATTR_ATTRIBUTION] = ATTRIBUTION

        return attributes
