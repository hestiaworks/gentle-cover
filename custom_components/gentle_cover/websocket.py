"""The commands the Gentle Cover page calls.

The page draws and edits; every rule lives here. A preview runs the same
planner a real move runs, so the dots on the chart are the commands the
curtains will get, and a save passes the same checks the options are held to.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_COVERS, DOMAIN
from .curve import CLOSE, OPEN, PRESETS, Curve
from .options import validate_options
from .planner import preview


def _room(hass: HomeAssistant, entry: Any) -> dict[str, Any]:
    entity_id = er.async_get(hass).async_get_entity_id("cover", DOMAIN, entry.entry_id)
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "entity_id": entity_id,
        "covers": list(entry.data.get(CONF_COVERS, [])),
        "options": dict(entry.options),
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "gentle_cover/rooms"})
@callback
def ws_rooms(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    rooms = [_room(hass, entry) for entry in hass.config_entries.async_entries(DOMAIN)]
    # The presets come from here so the page and the migration share them.
    connection.send_result(msg["id"], {"rooms": rooms, "presets": PRESETS})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gentle_cover/preview",
        vol.Required("direction"): vol.In([OPEN, CLOSE]),
        vol.Required("curve"): list,
        vol.Required("duration"): vol.Coerce(float),
        vol.Required("step_interval"): vol.Coerce(float),
        vol.Required("min_step"): vol.Coerce(float),
    }
)
@callback
def ws_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    try:
        curve = Curve(msg["curve"], msg["direction"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_curve", str(err))
        return
    # Out-of-range numbers are previewed clamped; the save rejects them.
    duration_s = min(120.0, max(1.0, msg["duration"])) * 60
    interval_s = min(600.0, max(30.0, msg["step_interval"]))
    min_step = min(50.0, max(1.0, msg["min_step"]))
    connection.send_result(msg["id"], preview(curve, duration_s, min_step, interval_s))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gentle_cover/save",
        vol.Required("entry_id"): str,
        vol.Required("options"): dict,
    }
)
@callback
def ws_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "No such room")
        return
    try:
        options = validate_options(msg["options"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_options", str(err))
        return
    # Saving reloads the room (its update listener), which also drops a move
    # planned under the old settings.
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"options": options})


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_rooms, ws_preview, ws_save):
        websocket_api.async_register_command(hass, command)
