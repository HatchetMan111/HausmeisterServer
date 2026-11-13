"""Hausmeister-Integration für Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import HausmeisterCoordinator

_LOGGER = logging.getLogger(__name__)

HausmeisterConfigEntry = ConfigEntry[HausmeisterCoordinator]

CARD_FILENAME = "hausmeister-card.js"
URL_BASE = "/hausmeister"


def _card_url() -> str:
    return f"{URL_BASE}/{CARD_FILENAME}"


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Statische Auslieferung der gebündelten Dashboard-Card registrieren."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                _card_url(),
                str(Path(__file__).parent / CARD_FILENAME),
                cache_headers=False,  # Updates der Card sofort übernehmen
            )
        ]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HausmeisterConfigEntry) -> bool:
    """Einrichtung der Integration."""
    coordinator = HausmeisterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await _async_ensure_lovelace_resource(hass)
    return True


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Card als Lovelace-Ressource registrieren — Plug & Play, idempotent."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.warning(
            "Hausmeister-Card: Lovelace ist nicht geladen — Card nicht "
            "automatisch registriert. Ressource manuell hinzufügen: %s",
            _card_url(),
        )
        return

    url = _card_url()
    mode = getattr(lovelace, "mode", None)
    mode_value = getattr(mode, "value", mode)

    if mode_value == "yaml":
        _LOGGER.warning(
            "Hausmeister-Card: Lovelace läuft im YAML-Modus — automatische "
            "Registrierung nicht möglich. In lovelace/resources.yaml ergänzen: "
            '- res_type: module\n  url: %s',
            url,
        )
        return

    try:
        resources = lovelace.resources
        if not getattr(resources, "loaded", True):
            await resources.async_load()
        if any(item.get("url") == url for item in resources.async_items()):
            return  # schon registriert (HACS-Update oder Neustart)

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info(
            "Hausmeister-Card automatisch als Lovelace-Ressource registriert: %s", url
        )
    except Exception:  # noqa: BLE001 — Registrierung darf die Integration nie blockieren
        _LOGGER.warning(
            "Hausmeister-Card konnte nicht automatisch registriert werden. "
            "Ressource manuell hinzufügen (JavaScript-Modul): %s",
            url,
            exc_info=True,
        )


async def async_unload_entry(hass: HomeAssistant, entry: HausmeisterConfigEntry) -> bool:
    """Entladen der Integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _update_listener(hass: HomeAssistant, entry: HausmeisterConfigEntry) -> None:
    """Optionsänderungen live übernehmen statt neu zu laden (Baseline bleibt)."""
    coordinator: HausmeisterCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_apply_options(entry)
