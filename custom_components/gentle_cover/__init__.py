"""Gentle Cover: a curtain per room that opens and closes in slow, eased steps.

The real curtains have one motor speed, so "slowly" can only mean a few short
moves with pauses between them. Each room gets a cover entity that drives its
real curtains that way, for wake-ups that do not go from dark to dazzling.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .const import DOMAIN
from .options import migrate_options, migrate_room_settings
from .page import async_setup_page

PLATFORMS = [Platform.COVER]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The page and its commands exist once, whatever the number of rooms."""
    websocket.async_register(hass)
    await async_setup_page(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # The options are read when a move is planned; rebuilding the entity is
    # the simplest way to drop any move planned under the old ones.
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Easings became curves in minor version 2; rooms got two named
    curtains and a scale in 3."""
    if entry.version != 1:
        return False
    if entry.minor_version >= 3:
        return True
    options = dict(entry.options)
    if entry.minor_version < 2:
        options = migrate_options(options)
    options = migrate_room_settings(options, entry.title)
    hass.config_entries.async_update_entry(entry, options=options, minor_version=3)
    return True
