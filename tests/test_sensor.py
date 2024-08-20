"""Test sensor for DWD rain radar integration."""
import os
import time

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from freezegun import freeze_time
from pytest_homeassistant_custom_component.common import MockConfigEntry
from typing_extensions import Generator

from custom_components.dwd_rain_radar.const import DOMAIN




@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Test fixture that ensures all entities are enabled in the registry."""
    with patch(
            "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
            return_value=True,
    ):
        yield

@pytest.fixture(autouse=True)
def set_timezone():
    os.environ['TZ'] = 'Europe/Berlin'  # Set to your desired timezone
    time.tzset()  # Apply the timezone setting

    yield  # Run the test

    # Cleanup after the test
    del os.environ['TZ']
    time.tzset()

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
@freeze_time("2024-08-08T15:47:00", tz_offset=2)
async def test_sensor(mock_get, hass, enable_custom_integrations, entity_registry_enabled_by_default):
    """Test sensor."""


    # Example binary data to return
    with open(os.path.dirname(__file__) + '/DE1200_RV_LATEST.tar.bz2', 'rb') as f:
        binary_data = f.read()

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.read = MagicMock(return_value=binary_data)  # Mock the read() method

    # Assign the mock response to the get request
    mock_get.return_value = mock_response

    entry = MockConfigEntry(domain=DOMAIN, data={
        "name": "test dwd",
        "coordinates": {
            "latitude": 48.07530,
            "longitude": 11.32589
        }
    })
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()



    precipitation = hass.states.get("sensor.mock_title_precipitation")

    assert precipitation
    assert precipitation.state == '0.84'
    assert precipitation.attributes['prediction_time'].isoformat() == '2024-08-08T17:50:00+02:00'
    assert precipitation.attributes['unit_of_measurement'] == 'mm'
    assert precipitation.attributes['device_class'] == 'precipitation'


    precipitation_10_minutes = hass.states.get("sensor.mock_title_precipitation_in_10_minutes")
    assert precipitation_10_minutes
    assert precipitation_10_minutes.state == '0.12'
    assert precipitation_10_minutes.attributes['prediction_time'].isoformat() == '2024-08-08T17:55:00+02:00'

    rain_expected_at = hass.states.get("sensor.mock_title_rain_expected_at")

    assert rain_expected_at
    assert rain_expected_at.state == '2024-08-08T17:50:00+02:00'


    rain_expected_in_minutes = hass.states.get("sensor.mock_title_rain_expected_in_minutes")

    assert rain_expected_in_minutes
    assert rain_expected_in_minutes.state == '3'