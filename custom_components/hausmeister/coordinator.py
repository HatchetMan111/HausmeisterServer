"""DataUpdateCoordinator für Hausmeister."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_WATCHED_SENSORS, CONF_SENSITIVITY, DEFAULT_SENSITIVITY
from .engine import HausmeisterEngine, Insight

_LOGGER = logging.getLogger(__name__)


class HausmeisterCoordinator(DataUpdateCoordinator[dict[str, Insight]]):
    """Koordiniert die Analyse aller überwachten Sensoren."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.engine = HausmeisterEngine(
            sensitivity=entry.options.get(CONF_SENSITIVITY, DEFAULT_SENSITIVITY)
        )
        self.watched: list[str] = entry.data.get(CONF_WATCHED_SENSORS, [])

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get("update_interval", 300)),
        )

    async def _async_update_data(self) -> dict[str, Insight]:
        """Alle überwachten Sensoren lesen und analysieren."""
        insights: dict[str, Insight] = {}

        for entity_id in self.watched:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                continue
            try:
                value = float(state.state)
            except (ValueError, TypeError):
                continue

            insights[entity_id] = await self.hass.async_add_executor_job(
                self.engine.analyze,
                entity_id,
                value,
                state.last_updated,
                state.attributes.get("friendly_name", entity_id),
                state.attributes.get("unit_of_measurement", ""),
            )

        return insights
