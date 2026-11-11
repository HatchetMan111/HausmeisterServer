"""Konstanten für die Hausmeister-Integration."""
from homeassistant.const import Platform

DOMAIN = "hausmeister"
PLATFORMS: list[Platform] = [Platform.SENSOR]
VERSION = "0.2.0"

# Config-Optionen
CONF_WATCHED_SENSORS = "watched_sensors"
CONF_SENSITIVITY = "sensitivity"          # Z-Score-Schwelle (Standard: 2.0)
CONF_BASELINE_DAYS = "baseline_days"      # Tage für Baseline (Standard: 14)
CONF_UPDATE_INTERVAL = "update_interval"  # Sekunden (Standard: 300)

DEFAULT_SENSITIVITY = 2.0
DEFAULT_BASELINE_DAYS = 14
DEFAULT_UPDATE_INTERVAL = 300
MIN_UPDATE_INTERVAL = 30
MAX_UPDATE_INTERVAL = 3600

# Zustände
STATE_NORMAL = "normal"
STATE_WARNING = "warnung"
STATE_CRITICAL = "kritisch"
INSIGHT_STATES = [STATE_NORMAL, STATE_WARNING, STATE_CRITICAL]

# Persistenz (Store-Version)
STORE_VERSION = 1
