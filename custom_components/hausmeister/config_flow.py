"""Config Flow für Hausmeister."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BASELINE_DAYS,
    CONF_SENSITIVITY,
    CONF_UPDATE_INTERVAL,
    CONF_WATCHED_SENSORS,
    DEFAULT_BASELINE_DAYS,
    DEFAULT_SENSITIVITY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)


def _current(entry: ConfigEntry, key: str, default):
    return entry.options.get(key, entry.data.get(key, default))


class HausmeisterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Behandelt den Config Flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                        selector.EntitySelectorConfig(domain="sensor", multiple=True)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HausmeisterOptionsFlow()


class HausmeisterOptionsFlow(OptionsFlow):
    """Optionen: Sensoren, Empfindlichkeit, Baseline und Intervall."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_WATCHED_SENSORS,
                        default=list(_current(entry, CONF_WATCHED_SENSORS, [])),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor", multiple=True)
                    ),
                    vol.Required(
                        CONF_SENSITIVITY,
                        default=_current(entry, CONF_SENSITIVITY, DEFAULT_SENSITIVITY),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1.0, max=4.0, step=0.1,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                    vol.Required(
                        CONF_BASELINE_DAYS,
                        default=_current(entry, CONF_BASELINE_DAYS, DEFAULT_BASELINE_DAYS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=30, step=1)
                    ),
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=_current(entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=MAX_UPDATE_INTERVAL,
                            step=30,
                            mode=selector.NumberSelectorMode.SLIDER,
                        )
                    ),
                }
            ),
        )
