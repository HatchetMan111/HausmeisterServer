"""DataUpdateCoordinator für Hausmeister."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BASELINE_DAYS,
    CONF_SENSITIVITY,
    CONF_UPDATE_INTERVAL,
    CONF_WATCHED_SENSORS,
    DEFAULT_BASELINE_DAYS,
    DEFAULT_SENSITIVITY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    STORE_VERSION,
)
from .engine import HausmeisterEngine, Insight

_LOGGER = logging.getLogger(__name__)

SAVE_DEBOUNCE_SECONDS = 30


def _setting(entry: ConfigEntry, key: str, default):
    """Optionen schlagen Konfiguration — Optionen lassen sich live ändern."""
    return entry.options.get(key, entry.data.get(key, default))


def _caps(interval_seconds: int, baseline_days: int) -> tuple[int, int]:
    """Kapazitäten für Baseline- und Trend-Speicher ableiten."""
    per_hour = max(1, 3600 // max(1, interval_seconds))
    return max(8, per_hour * baseline_days), max(48, (7 * 86400) // interval_seconds)


class HausmeisterCoordinator(DataUpdateCoordinator[dict[str, Insight]]):
    """Koordiniert die Analyse aller überwachten Sensoren."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.watched: list[str] = list(_setting(entry, CONF_WATCHED_SENSORS, []))
        interval_seconds = max(
            5, int(_setting(entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        )
        baseline_days = _setting(entry, CONF_BASELINE_DAYS, DEFAULT_BASELINE_DAYS)
        max_baseline, trend = _caps(interval_seconds, baseline_days)
        self.engine = HausmeisterEngine(
            sensitivity=_setting(entry, CONF_SENSITIVITY, DEFAULT_SENSITIVITY),
            baseline_days=baseline_days,
            max_baseline_samples=max_baseline,
            trend_samples=trend,
        )
        self._store = Store(hass, STORE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        self._store_task: asyncio.Task | None = None
        self._memory_loaded = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval_seconds),
        )

    async def _async_update_data(self) -> dict[str, Insight]:
        """Alle überwachten Sensoren lesen und analysieren."""
        if not self._memory_loaded:
            await self._async_load_memory()

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

        self._schedule_store_save()
        return insights

    async def async_apply_options(self, entry: ConfigEntry) -> None:
        """Optionsänderungen live übernehmen, ohne die Baseline zu verlieren."""
        self.entry = entry
        self.watched = list(_setting(entry, CONF_WATCHED_SENSORS, []))
        self.engine.sensitivity = _setting(entry, CONF_SENSITIVITY, DEFAULT_SENSITIVITY)
        interval_seconds = max(
            5, int(_setting(entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        )
        self.update_interval = timedelta(seconds=interval_seconds)

        baseline_days = _setting(entry, CONF_BASELINE_DAYS, DEFAULT_BASELINE_DAYS)
        if baseline_days != self.engine.baseline_days:
            self.engine.baseline_days = baseline_days
            max_baseline, _ = _caps(interval_seconds, baseline_days)
            self.engine.max_baseline_samples = max_baseline
            for mem in self.engine.memory.values():
                mem.baseline_by_hour = {
                    h: deque(b, maxlen=max_baseline)
                    for h, b in mem.baseline_by_hour.items()
                }

        self.hass.async_create_task(self.async_request_refresh())

    # ------------------------------------------------------------------
    # Persistenz über HA-Neustarts (Baseline + Anomalie-Streaks)
    # ------------------------------------------------------------------

    async def _async_load_memory(self) -> None:
        self._memory_loaded = True
        try:
            data = await self._store.async_load()
        except Exception:  # noqa: BLE001 — kaputter Store darf die Integration nicht blockieren
            _LOGGER.exception("Hausmeister-Baseline konnte nicht geladen werden")
            return
        if data:
            self.engine.import_memory(data)

    def _schedule_store_save(self) -> None:
        if self._store_task:
            self._store_task.cancel()
        self._store_task = self.hass.async_create_task(self._async_store_save())

    async def _async_store_save(self) -> None:
        try:
            await asyncio.sleep(SAVE_DEBOUNCE_SECONDS)
            await self._store.async_save(self.engine.export_memory())
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Hausmeister-Baseline konnte nicht gespeichert werden")
