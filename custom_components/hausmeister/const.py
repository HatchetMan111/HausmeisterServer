"""Konstanten für die Hausmeister-Integration."""
from homeassistant.const import Platform

DOMAIN = "hausmeister"
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Config-Optionen
CONF_WATCHED_SENSORS = "watched_sensors"
CONF_SENSITIVITY = "sensitivity"          # Z-Score-Schwelle (Standard: 2.0)
CONF_BASELINE_DAYS = "baseline_days"      # Tage für Baseline (Standard: 14)
CONF_UPDATE_INTERVAL = "update_interval"  # Sekunden (Standard: 300)

# Profile: welche Logik für welchen Sensortyp
PROFILE_GENERIC = "generic"
PROFILE_HUMIDITY = "humidity"
PROFILE_POWER_APPLIANCE = "power_appliance"   # Waschmaschine, Kühlschrank
PROFILE_HEATING = "heating"
PROFILE_PRESENCE = "presence"                 # Fenster, Türen

DEFAULT_SENSITIVITY = 2.0
DEFAULT_BASELINE_DAYS = 14
DEFAULT_UPDATE_INTERVAL = 300

# Zustände
STATE_NORMAL = "normal"
STATE_WARNING = "warnung"
STATE_CRITICAL = "kritisch"
