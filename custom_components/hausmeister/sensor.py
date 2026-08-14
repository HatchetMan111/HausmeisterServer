"""Sensor-Plattform für Hausmeister-Insights."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HausmeisterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HausmeisterCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for entity_id in coordinator.watched:
        entities.extend(
            [
                HausmeisterInsightSensor(coordinator, entity_id, "insight"),
                HausmeisterDeviationSensor(coordinator, entity_id, "abweichung"),
                HausmeisterTrendSensor(coordinator, entity_id, "trend"),
            ]
        )
    async_add_entities(entities)


class HausmeisterBaseSensor(CoordinatorEntity[HausmeisterCoordinator], SensorEntity):
    """Basis für alle Hausmeister-Sensoren."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, source_entity: str, suffix: str):
        super().__init__(coordinator)
        self.source_entity = source_entity
        self._attr_unique_id = f"{DOMAIN}_{source_entity}_{suffix}"
        short = source_entity.split(".")[-1]
        self._attr_name = f"Hausmeister {short} {suffix}"

    @property
    def insight(self):
        return self.coordinator.data.get(self.source_entity)


class HausmeisterInsightSensor(HausmeisterBaseSensor):
    """Der Haupt-Insight: Status + menschenlesbarer Text."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["normal", "warnung", "kritisch"]

    @property
    def native_value(self):
        return self.insight.state if self.insight else "normal"

    @property
    def extra_state_attributes(self):
        if not self.insight:
            return {}
        return {
            "nachricht": self.insight.message,
            "abweichung_prozent": self.insight.deviation_pct,
            "z_score": self.insight.z_score,
            "anomalie_seit": self.insight.anomaly_since,
        }


class HausmeisterDeviationSensor(HausmeisterBaseSensor):
    """Abweichung von der Baseline in %."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.insight.deviation_pct if self.insight else 0


class HausmeisterTrendSensor(HausmeisterBaseSensor):
    """Trend in % pro Tag."""

    _attr_native_unit_of_measurement = "%/Tag"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.insight.trend_pct_per_day if self.insight else 0
