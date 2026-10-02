"""One gentle move: send the planned steps, and step aside for people.

A move owns its timeline and nothing else. It stops itself the moment
someone else commands one of its curtains through Home Assistant (the
interface, HomeKit, another automation), and when a curtain settles well away
from where it was sent (its own button, the vendor app) — fighting a person
over the curtains is worse than not finishing.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_SET_COVER_POSITION,
    CoverState,
)
from homeassistant.const import ATTR_ENTITY_ID, EVENT_CALL_SERVICE
from homeassistant.core import CALLBACK_TYPE, Context, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.util import dt as dt_util

from .const import SETTLE_GRACE_S, SETTLE_TOLERANCE
from .curve import Curve
from .planner import off_course, plan

_LOGGER = logging.getLogger(__name__)


def member_position(hass: HomeAssistant, entity_id: str) -> float | None:
    """A real curtain's reported position, or None when it has none."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    position = state.attributes.get(ATTR_CURRENT_POSITION)
    return float(position) if isinstance(position, (int, float)) else None


def _call_targets(hass: HomeAssistant, service_data: dict) -> set[str] | None:
    """The entities a service call reaches, or None for "all of them".

    The event carries the call's raw data, so a person saying "close the
    bedroom curtains" arrives as an area, not as our curtains' entity ids.
    """
    entity_ids = service_data.get(ATTR_ENTITY_ID)
    if entity_ids == "all":
        return None
    data = dict(service_data)
    if isinstance(entity_ids, str):
        data[ATTR_ENTITY_ID] = [part.strip() for part in entity_ids.split(",") if part.strip()]
    selected = async_extract_referenced_entity_ids(hass, TargetSelection(data))
    return selected.referenced | selected.indirectly_referenced


class GentleMove:
    def __init__(
        self,
        hass: HomeAssistant,
        covers: list[str],
        target: int,
        curve: Curve,
        duration_s: float,
        min_step: float,
        interval_s: float,
        on_end: Callable[[GentleMove, str], None],
    ) -> None:
        self._hass = hass
        self._covers = covers
        self.target = target
        self._curve = curve
        self._duration_s = duration_s
        self._min_step = min_step
        self._interval_s = interval_s
        self._on_end = on_end
        self.ends_at: datetime | None = None
        # Every command we send carries a context of ours, so our own
        # call_service events are told apart from a person's.
        self._contexts: set[str] = set()
        # Per curtain: the position we last sent it, where it was then, and
        # when.
        self._sent: dict[str, tuple[int, float | None, float]] = {}
        self._timeline: list[tuple[float, dict[int, list[str]]]] = []
        self._task: asyncio.Task | None = None
        self._unsubs: list[CALLBACK_TYPE] = []
        self._ended = False

    def start(self) -> bool:
        """Plan every curtain from where it is now, all on one timeline."""
        timeline: dict[float, dict[int, list[str]]] = {}
        for entity_id in self._covers:
            start = member_position(self._hass, entity_id)
            if start is None:
                # A curtain that cannot say where it is cannot be planned;
                # the others still move.
                continue
            for at, position in plan(
                start, self.target, self._curve, self._duration_s,
                self._min_step, self._interval_s,
            ).steps:
                timeline.setdefault(at, {}).setdefault(position, []).append(entity_id)
        if not timeline:
            return False
        self._timeline = sorted(timeline.items())
        self.ends_at = dt_util.utcnow() + timedelta(seconds=self._timeline[-1][0])
        self._unsubs.append(
            self._hass.bus.async_listen(EVENT_CALL_SERVICE, self._on_call_service)
        )
        self._unsubs.append(
            async_track_state_change_event(
                self._hass, self._covers, self._on_member_state
            )
        )
        # Not eager: an eager task would send the first step inside start(),
        # and a step that fails at once would report the end before the
        # owner has even stored the move.
        self._task = self._hass.async_create_background_task(
            self._run(), name=f"gentle_cover move to {self.target}", eager_start=False
        )
        return True

    def cancel(self) -> None:
        """Stop without reporting: the caller already knows why."""
        self._stop(None)

    async def _run(self) -> None:
        began = time.monotonic()
        try:
            for at, groups in self._timeline:
                wait = at - (time.monotonic() - began)
                if wait > 0:
                    await asyncio.sleep(wait)
                for position, entity_ids in groups.items():
                    context = Context()
                    self._contexts.add(context.id)
                    now = time.monotonic()
                    for entity_id in entity_ids:
                        self._sent[entity_id] = (
                            position, member_position(self._hass, entity_id), now
                        )
                    # One call per position, so curtains that share a step
                    # get it in the same command and stay together.
                    await self._hass.services.async_call(
                        COVER_DOMAIN,
                        SERVICE_SET_COVER_POSITION,
                        {ATTR_ENTITY_ID: entity_ids, ATTR_POSITION: position},
                        blocking=True,
                        context=context,
                    )
        except asyncio.CancelledError:
            raise
        except HomeAssistantError as err:
            _LOGGER.warning("Gentle move to %s failed: %s", self.target, err)
            self._stop("failed")
            return
        except Exception:
            # Anything else would leave the listeners behind and the room
            # "opening" forever; end the move the same way, loudly.
            _LOGGER.exception("Gentle move to %s failed", self.target)
            self._stop("failed")
            return
        self._stop("done")

    @callback
    def _on_call_service(self, event: Event) -> None:
        if event.data.get("domain") != COVER_DOMAIN:
            return
        if event.context.id in self._contexts:
            return
        targets = _call_targets(self._hass, event.data.get("service_data") or {})
        if targets is None or not targets.isdisjoint(self._covers):
            _LOGGER.debug("Gentle move to %s: a curtain was commanded elsewhere", self.target)
            self._stop("interrupted")

    @callback
    def _on_member_state(self, event: Event) -> None:
        entity_id = event.data["entity_id"]
        new_state = event.data["new_state"]
        if new_state is None or entity_id not in self._sent:
            return
        if new_state.state in (CoverState.OPENING, CoverState.CLOSING):
            return
        position = new_state.attributes.get(ATTR_CURRENT_POSITION)
        if not isinstance(position, (int, float)):
            return
        sent_position, origin, sent_at = self._sent[entity_id]
        if time.monotonic() - sent_at < SETTLE_GRACE_S:
            return
        # These curtains report late and rarely say "opening", so a report is
        # only a person's doing when it is off the path we sent it along.
        if off_course(origin, sent_position, position, SETTLE_TOLERANCE):
            _LOGGER.debug(
                "Gentle move to %s: %s settled at %s, sent %s",
                self.target, entity_id, position, sent_position,
            )
            self._stop("interrupted")

    @callback
    def _stop(self, reason: str | None) -> None:
        if self._ended:
            return
        self._ended = True
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        task = self._task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        if reason is not None:
            self._on_end(self, reason)
