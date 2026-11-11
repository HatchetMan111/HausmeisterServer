"""Sensor-Plattform für Hausmeister-Insights."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INSIGHT_STATES, VERSION
from .coordinator import HausmeisterCoordinator

SUFFIX_LABELS = {"insight": "Status", "abweichung": "Abweichung", "trend": "Trend"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HausmeisterCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for entity_id in coordinator.watched:
        for suffix, cls in SENSOR_CLASSES.items():
            entities.append(cls(coordinator, entry, entity_id, suffix))
    async_add_entities(entities)


class HausmeisterBaseSensor(CoordinatorEntity[HausmeisterCoordinator], SensorEntity):
    """Basis für alle Hausmeister-Sensoren."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HausmeisterCoordinator,
        entry: ConfigEntry,
        source_entity: str,
        suffix: str,
    ):
        super().__init__(coordinator)
        self.source_entity = source_entity
        self._attr_unique_id = f"{entry.entry_id}_{source_entity}_{suffix}"

        friendly = source_entity.split(".")[-1].replace("_", " ")
        state = coordinator.hass.states.get(source_entity)
        if state and state.attributes.get("friendly_name"):
            friendly = state.attributes["friendly_name"]
        self._attr_name = f"Hausmeister {friendly} {SUFFIX_LABELS[suffix]}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Hausmeister",
            manufacturer="HatchetMan111",
            model="Predictive-Maintenance-Engine",
            sw_version=VERSION,
        )

    @property
    def insight(self):
        return self.coordinator.data.get(self.source_entity)


class HausmeisterInsightSensor(HausmeisterBaseSensor):
    """Der Haupt-Insight: Status + menschenlesbarer Text."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = INSIGHT_STATES

    @property
    def native_value(self):
        return self.insight.state if self.insight else None

    @property
    def extra_state_attributes(self):
        if not self.insight:
            return {}
        return {
            "nachricht": self.insight.message,
            "abweichung_prozent": self.insight.deviation_pct,
            "z_score": self.insight.z_score,
            "anomalie_seit": (
                self.insight.anomaly_since.isoformat()
                if self.insight.anomaly_since
                else None
            ),
        }


class HausmeisterDeviationSensor(HausmeisterBaseSensor):
    """Abweichung von der Baseline in %."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.insight.deviation_pct if self.insight else None


class HausmeisterTrendSensor(HausmeisterBaseSensor):
    """Trend in % pro Tag."""

    _attr_native_unit_of_measurement = "%/Tag"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.insight.trend_pct_per_day if self.insight else None


SENSOR_CLASSES = {
    "insight": HausmeisterInsightSensor,
    "abweichung": HausmeisterDeviationSensor,
    "trend": HausmeisterTrendSensor,
}
