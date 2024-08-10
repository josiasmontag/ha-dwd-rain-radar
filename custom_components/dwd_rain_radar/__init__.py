"""DWD Rain Radar integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.core import HomeAssistant

from .coordinator import DwdRainRadarUpdateCoordinator
from .const import (
    DOMAIN, PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DWD Rain Radar from a config entry."""
    coordinator = DwdRainRadarUpdateCoordinator(hass, entry, get_async_client(hass))

    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle config_entry updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entries."""
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload

