"""Config Flow für Hausmeister."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_WATCHED_SENSORS,
    CONF_SENSITIVITY,
    DEFAULT_SENSITIVITY,
)


class HausmeisterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Behandelt den Config Flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Erster Schritt: Sensoren auswählen."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_WATCHED_SENSORS):
                errors["base"] = "no_sensors"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Hausmeister",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WATCHED_SENSORS, default=[]): selector.EntitySelector(
                        selector.EntitySelectorConfig(multiple=True)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HausmeisterOptionsFlow(config_entry)


class HausmeisterOptionsFlow(config_entries.OptionsFlow):
    """Optionen bearbeiten (Empfindlichkeit etc.)."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SENSITIVITY,
                        default=self.config_entry.options.get(
                            CONF_SENSITIVITY, DEFAULT_SENSITIVITY
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1.0, max=4.0, step=0.1, mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                }
            ),
        )
