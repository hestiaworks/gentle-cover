"""A stand-in for the few Home Assistant pieces mover.py touches.

Home Assistant cannot be imported here (it needs a newer Python), so the move
runner is tested against this: states, the event bus, service calls that fire
call_service events with their context like the real registry does, area
targets, and HA's eager task start.
"""

from __future__ import annotations

import asyncio
import enum
import sys
import types
import uuid
from datetime import datetime, timezone

class HomeAssistantError(Exception):
    pass


class CoverState(enum.StrEnum):
    OPEN = "open"
    OPENING = "opening"
    CLOSED = "closed"
    CLOSING = "closing"


class Context:
    def __init__(self) -> None:
        self.id = uuid.uuid4().hex


class Event:
    def __init__(self, data: dict, context: Context | None = None) -> None:
        self.data = data
        self.context = context or Context()


class State:
    def __init__(self, state: str, attributes: dict) -> None:
        self.state = state
        self.attributes = attributes


class TargetSelection:
    def __init__(self, config: dict) -> None:
        def ids(key: str) -> set[str]:
            value = config.get(key)
            if value in (None, "all", "none"):
                return set()
            return set(value if isinstance(value, list) else [value])

        self.entity_ids = ids("entity_id")
        self.area_ids = ids("area_id")


class SelectedEntities:
    def __init__(self) -> None:
        self.referenced: set[str] = set()
        self.indirectly_referenced: set[str] = set()


def async_extract_referenced_entity_ids(hass, selection, expand_group=True):
    selected = SelectedEntities()
    selected.referenced |= selection.entity_ids
    for area in selection.area_ids:
        selected.indirectly_referenced |= set(hass.areas.get(area, []))
    return selected


def async_track_state_change_event(hass, entity_ids, action):
    entry = (set(entity_ids), action)
    hass.state_listeners.append(entry)
    return lambda: hass.state_listeners.remove(entry)


class FakeServices:
    def __init__(self, hass: "FakeHass") -> None:
        self._hass = hass
        self.calls: list[tuple[str, str, dict]] = []
        self.raises: Exception | None = None

    async def async_call(self, domain, service, data, blocking=False, context=None):
        context = context or Context()
        # Like the real registry: the event fires, with the caller's context,
        # before the service runs.
        self._hass.bus.fire(
            "call_service",
            {"domain": domain, "service": service, "service_data": dict(data)},
            context,
        )
        if self.raises is not None:
            raise self.raises
        self.calls.append((domain, service, dict(data)))


class FakeBus:
    def __init__(self) -> None:
        self.listeners: list[tuple[str, object]] = []

    def async_listen(self, event_type, action):
        entry = (event_type, action)
        self.listeners.append(entry)
        return lambda: self.listeners.remove(entry)

    def fire(self, event_type, data, context=None):
        for listened, action in list(self.listeners):
            if listened == event_type:
                action(Event(data, context))


class FakeStates:
    def __init__(self) -> None:
        self._states: dict[str, State] = {}

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeHass:
    def __init__(self, positions: dict[str, float | None]) -> None:
        self.states = FakeStates()
        self.bus = FakeBus()
        self.services = FakeServices(self)
        self.state_listeners: list[tuple[set[str], object]] = []
        self.areas: dict[str, list[str]] = {}
        self.tasks: list[asyncio.Task] = []
        for entity_id, position in positions.items():
            self.set_position(entity_id, position, notify=False)

    def set_position(self, entity_id, position, state="open", notify=True):
        attributes = {} if position is None else {"current_position": position}
        new = State(state, attributes)
        self.states._states[entity_id] = new
        if notify:
            for entity_ids, action in list(self.state_listeners):
                if entity_id in entity_ids:
                    action(Event({"entity_id": entity_id, "new_state": new}))

    def async_create_background_task(self, coro, name, eager_start=True):
        if eager_start:
            # HA runs an eager task synchronously up to its first suspension.
            # Only the case the tests need is emulated: a coroutine that
            # finishes without suspending.
            try:
                coro.send(None)
            except StopIteration:
                future = asyncio.get_running_loop().create_future()
                future.set_result(None)
                return future
            raise AssertionError("eager start with suspension is not emulated")
        task = asyncio.get_running_loop().create_task(coro)
        self.tasks.append(task)
        return task


def _module(name: str, **attributes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module
    return module


def load_mover():
    """Install the stand-in and import mover.py without the package __init__."""
    _module("homeassistant")
    _module("homeassistant.components")
    _module(
        "homeassistant.components.cover",
        ATTR_CURRENT_POSITION="current_position",
        ATTR_POSITION="position",
        DOMAIN="cover",
        SERVICE_SET_COVER_POSITION="set_cover_position",
        CoverState=CoverState,
    )
    _module("homeassistant.const", ATTR_ENTITY_ID="entity_id", EVENT_CALL_SERVICE="call_service")
    _module(
        "homeassistant.core",
        CALLBACK_TYPE=object,
        Context=Context,
        Event=Event,
        HomeAssistant=object,
        callback=lambda func: func,
    )
    _module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
    _module("homeassistant.helpers")
    _module(
        "homeassistant.helpers.event",
        async_track_state_change_event=async_track_state_change_event,
    )
    _module(
        "homeassistant.helpers.target",
        TargetSelection=TargetSelection,
        async_extract_referenced_entity_ids=async_extract_referenced_entity_ids,
    )
    _module("homeassistant.util")
    _module(
        "homeassistant.util.dt",
        utcnow=lambda: datetime.now(timezone.utc),
    )
    sys.modules["homeassistant.util"].dt = sys.modules["homeassistant.util.dt"]
    from pkg import load

    return load("mover")
