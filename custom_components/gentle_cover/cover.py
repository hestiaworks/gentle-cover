"""The gentle curtain of one room."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DURATION,
    CONF_CLOSE_CURVE,
    CONF_CLOSE_DURATION,
    CONF_COVERS,
    CONF_MIN_STEP,
    CONF_OPEN_CURVE,
    CONF_OPEN_DURATION,
    CONF_STEP_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
    SERVICE_MOVE,
)
from .curve import CLOSE, OPEN, Curve
from .mover import GentleMove, member_position
from .planner import Plan, plan

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([GentleCover(entry)])
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_MOVE,
        {
            vol.Required(ATTR_POSITION): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            vol.Optional(ATTR_DURATION): vol.All(vol.Coerce(float), vol.Range(min=1, max=240)),
        },
        "async_gentle_move",
    )


class GentleCover(CoverEntity):
    _attr_has_entity_name = True
    _attr_name = "Gentle"
    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._covers: list[str] = list(entry.data[CONF_COVERS])
        self._move: GentleMove | None = None
        self._direction = OPEN
        # What the card draws while a move runs: the room's own plan, from
        # the average position, and when it began.
        self._shown: Plan | None = None
        self._started_at: datetime | None = None
        self._attr_unique_id = entry.entry_id
        # A device per room, so the gentle curtain takes the room's name.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Gentle Cover",
        )

    def _option(self, key: str) -> Any:
        return self._entry.options.get(key, DEFAULT_OPTIONS[key])

    # --- what the room looks like -----------------------------------------

    def _positions(self) -> list[float]:
        return [
            position
            for entity_id in self._covers
            if (position := member_position(self.hass, entity_id)) is not None
        ]

    @property
    def available(self) -> bool:
        return bool(self._positions())

    @property
    def current_cover_position(self) -> int | None:
        positions = self._positions()
        if not positions:
            return None
        return round(sum(positions) / len(positions))

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    @property
    def is_opening(self) -> bool:
        return self._move is not None and self._direction == OPEN

    @property
    def is_closing(self) -> bool:
        return self._move is not None and self._direction == CLOSE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "covers": self._covers,
            "open_curve": self._option(CONF_OPEN_CURVE),
            "close_curve": self._option(CONF_CLOSE_CURVE),
            "open_duration": self._option(CONF_OPEN_DURATION),
            "close_duration": self._option(CONF_CLOSE_DURATION),
            "step_interval": self._option(CONF_STEP_INTERVAL),
            "min_step": self._option(CONF_MIN_STEP),
        }
        if self._move is not None:
            attributes["target_position"] = self._move.target
            attributes["move_direction"] = self._direction
            if self._move.ends_at is not None:
                attributes["move_ends_at"] = self._move.ends_at.isoformat()
            if self._shown is not None and self._started_at is not None:
                attributes["move_started_at"] = self._started_at.isoformat()
                attributes["move_span_s"] = round(self._shown.span_s, 1)
                attributes["move_curve_start"] = round(self._shown.t_start, 4)
                attributes["move_curve_end"] = round(self._shown.t_end, 4)
        return attributes

    async def async_added_to_hass(self) -> None:
        # Our position is the real curtains' position: follow them.
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._covers, self._on_member_changed
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_move()

    @callback
    def _on_member_changed(self, event: Event) -> None:
        self.async_write_ha_state()

    # --- commands -----------------------------------------------------------

    async def async_open_cover(self, **kwargs: Any) -> None:
        self._start(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        self._start(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        self._start(int(kwargs[ATTR_POSITION]))

    async def async_stop_cover(self, **kwargs: Any) -> None:
        # The curtains finish their current short run; nothing more is sent.
        self._cancel_move()
        self.async_write_ha_state()

    async def async_gentle_move(self, position: int, duration: float | None = None) -> None:
        self._start(position, duration)

    @callback
    def _start(self, target: int, duration: float | None = None) -> None:
        # A new command always replaces the running move, before planning, so
        # two moves never drive the same curtains.
        self._cancel_move()
        current = self.current_cover_position
        direction = OPEN if current is None or target >= current else CLOSE
        curve = Curve(
            self._option(CONF_OPEN_CURVE if direction == OPEN else CONF_CLOSE_CURVE),
            direction,
        )
        if duration is None:
            duration = self._option(
                CONF_OPEN_DURATION if direction == OPEN else CONF_CLOSE_DURATION
            )
        duration_s = float(duration) * 60
        min_step = float(self._option(CONF_MIN_STEP))
        interval_s = float(self._option(CONF_STEP_INTERVAL))
        move = GentleMove(
            self.hass,
            self._covers,
            target,
            curve,
            duration_s,
            min_step,
            interval_s,
            self._move_ended,
        )
        # Stored before start: a move reports its end through _move_ended,
        # which only listens to the move it holds.
        self._move = move
        self._direction = direction
        if move.start():
            start = current if current is not None else (0 if direction == OPEN else 100)
            self._shown = plan(start, target, curve, duration_s, min_step, interval_s)
            self._started_at = dt_util.utcnow()
        else:
            self._move = None
        self.async_write_ha_state()

    @callback
    def _cancel_move(self) -> None:
        if self._move is not None:
            self._move.cancel()
            self._move = None
        self._shown = None
        self._started_at = None

    @callback
    def _move_ended(self, move: GentleMove, reason: str) -> None:
        if move is not self._move:
            # A move already replaced or cancelled has nothing left to say.
            return
        _LOGGER.debug("%s: gentle move ended (%s)", self.entity_id, reason)
        self._move = None
        self._shown = None
        self._started_at = None
        self.async_write_ha_state()
