"""Test sensor for DWD rain radar integration."""
import os

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dwd_rain_radar.const import DOMAIN


# Example binary data to return
with open(os.path.dirname(__file__) + '/DE1200_RV_LATEST.tar.bz2', 'rb') as f:
    binary_data = f.read()

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_sensor(mock_get, hass, enable_custom_integrations):
    """Test sensor."""

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.read = AsyncMock(return_value=binary_data)  # Mock the read() method

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



    state = hass.states.get("sensor.mock_title_precipitation")

    assert state
    assert state.state == '0.839999973773956'
    assert state.attributes['unit_of_measurement'] == 'mm'
    assert state.attributes['device_class'] == 'precipitation'
