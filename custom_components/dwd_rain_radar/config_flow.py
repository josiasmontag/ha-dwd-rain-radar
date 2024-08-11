"""Config flow for DWD Rain Radar integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_COORDINATES,
)

_LOGGER = logging.getLogger(__name__)


class DwdRainRadarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the DWD Rain Radar coordinator."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        pass

    async def async_step_user(self, user_input=None):
        """Handle the user step.

        Allows the user to specify a name.

        """

        _LOGGER.debug("User:user_input: {}".format(user_input))

        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:

            if (CONF_COORDINATES not in user_input
                    or "latitude" not in user_input[CONF_COORDINATES]
                    or "longitude" not in user_input[CONF_COORDINATES]):
                errors["base"] = "Invalid location"

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="DWD Rain Radar", description="Name"): str,
                vol.Optional(CONF_COORDINATES, description="Location"): selector.LocationSelector(
                    selector.LocationSelectorConfig()
                )
            }),
            description_placeholders=placeholders,
            errors=errors,
        )
