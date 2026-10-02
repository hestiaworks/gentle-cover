"""A room's settings: their defaults, how older rooms are brought up to date,
and the checks a save from the page must pass."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .const import (
    CONF_CLOSE_CURVE,
    CONF_CLOSE_DURATION,
    CONF_GENTLE_ENABLED,
    CONF_GENTLE_NAME,
    CONF_MIN_STEP,
    CONF_NORMAL_ENABLED,
    CONF_NORMAL_NAME,
    CONF_OPEN_CURVE,
    CONF_OPEN_DURATION,
    CONF_SCALE,
    CONF_STEP_INTERVAL,
    DEFAULT_OPTIONS,
    SCALE_CLOSED_IS_100,
    SCALE_OPEN_IS_100,
)
from .curve import CLOSE, OPEN, PRESETS, validate_curve

# Ranges shared with the page's fields.
RANGES = {
    CONF_OPEN_DURATION: (1, 120),
    CONF_CLOSE_DURATION: (1, 120),
    CONF_STEP_INTERVAL: (30, 600),
    CONF_MIN_STEP: (1, 50),
}
SCALES = (SCALE_OPEN_IS_100, SCALE_CLOSED_IS_100)
NAME_MAX = 64

# What a curtain may be, as the describer passed to validate_covers says it.
COVER_PROBLEMS = {
    "missing": "does not exist",
    "no_position": "cannot be set to a position",
    "ours": "is already a Gentle Cover curtain",
}


def defaults(title: str) -> dict[str, Any]:
    """A new room: both curtains.

    Curtain names follow the room's name, the way Home Assistant shows any
    entity of a device: "" is the room itself ("Bedroom"), "Sunrise" shows as
    "Bedroom Sunrise". Renaming the room renames its curtains with it.
    """
    options = copy.deepcopy(DEFAULT_OPTIONS)
    options.update(
        {
            CONF_NORMAL_ENABLED: True,
            CONF_NORMAL_NAME: "",
            CONF_GENTLE_ENABLED: True,
            CONF_GENTLE_NAME: "Sunrise",
            CONF_SCALE: SCALE_OPEN_IS_100,
        }
    )
    return options


def migrate_options(old: dict[str, Any]) -> dict[str, Any]:
    """Options from before curves: each easing becomes its preset curve."""
    new = copy.deepcopy(DEFAULT_OPTIONS)
    for key in (CONF_OPEN_DURATION, CONF_CLOSE_DURATION, CONF_MIN_STEP, CONF_STEP_INTERVAL):
        if key in old:
            new[key] = old[key]
    open_easing = old.get("open_easing", "slow_start")
    close_easing = old.get("close_easing", "even")
    new[CONF_OPEN_CURVE] = copy.deepcopy(
        PRESETS[OPEN].get(open_easing, PRESETS[OPEN]["slow_start"])
    )
    new[CONF_CLOSE_CURVE] = copy.deepcopy(
        PRESETS[CLOSE].get(close_easing, PRESETS[CLOSE]["even"])
    )
    return new


def migrate_room_settings(options: dict[str, Any], title: str) -> dict[str, Any]:
    """A room from before there were two curtains.

    Its gentle curtain stays as it was, name included, so dashboards,
    automations and HomeKit see no change; the normal one starts switched off.
    """
    new = copy.deepcopy(options)
    new.setdefault(CONF_NORMAL_ENABLED, False)
    new.setdefault(CONF_NORMAL_NAME, "")
    new.setdefault(CONF_GENTLE_ENABLED, True)
    # Shown as "<room> Gentle", which is what it was called before.
    new.setdefault(CONF_GENTLE_NAME, "Gentle")
    new.setdefault(CONF_SCALE, SCALE_OPEN_IS_100)
    return new


def _name(value: Any, what: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{what}: the name must be text")
    name = value.strip()
    if required and not name:
        raise ValueError(f"{what} needs a name")
    if len(name) > NAME_MAX:
        raise ValueError(f"{what}: a name is at most {NAME_MAX} characters")
    return name


def validate_options(data: dict[str, Any]) -> dict[str, Any]:
    """The options as stored, or ValueError naming the first problem."""
    result: dict[str, Any] = {}
    for key, (low, high) in RANGES.items():
        try:
            value = float(data[key])
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError(f"{key} must be a number") from err
        if not low <= value <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
        result[key] = value
    result[CONF_OPEN_CURVE] = validate_curve(data.get(CONF_OPEN_CURVE), OPEN)
    result[CONF_CLOSE_CURVE] = validate_curve(data.get(CONF_CLOSE_CURVE), CLOSE)
    for key in (CONF_NORMAL_ENABLED, CONF_GENTLE_ENABLED):
        if not isinstance(data.get(key), bool):
            raise ValueError(f"{key} must be on or off")
        result[key] = data[key]
    if not (result[CONF_NORMAL_ENABLED] or result[CONF_GENTLE_ENABLED]):
        raise ValueError("a room needs at least one curtain")
    result[CONF_NORMAL_NAME] = _name(data.get(CONF_NORMAL_NAME), "The normal curtain", required=False)
    result[CONF_GENTLE_NAME] = _name(data.get(CONF_GENTLE_NAME), "The gentle curtain", required=False)
    if result[CONF_NORMAL_NAME].casefold() == result[CONF_GENTLE_NAME].casefold():
        # Both would show as the same thing in Home Assistant and HomeKit.
        raise ValueError("the normal and the gentle curtain need different names")
    if data.get(CONF_SCALE) not in SCALES:
        raise ValueError("scale must be open_is_100 or closed_is_100")
    result[CONF_SCALE] = data[CONF_SCALE]
    return result


def validate_covers(covers: Any, describe: Callable[[str], str]) -> list[str]:
    """The room's real curtains, or ValueError naming the one that is wrong."""
    if not isinstance(covers, list) or not all(isinstance(c, str) for c in covers):
        raise ValueError("curtains must be a list of entity ids")
    if not covers:
        raise ValueError("a room needs at least one curtain")
    for entity_id in covers:
        kind = describe(entity_id)
        if kind != "ok":
            raise ValueError(f"{entity_id} {COVER_PROBLEMS.get(kind, 'cannot be used')}")
    return list(covers)


def validate_title(title: Any, taken: set[str]) -> str:
    """A room name not used by another room (compared without case)."""
    name = _name(title, "The room")
    if name.casefold() in {other.casefold() for other in taken}:
        raise ValueError(f"there is already a room called {name}")
    return name


def to_room_scale(position: float, scale: str) -> float:
    """Home Assistant's position (100 = open) in the room's scale."""
    return 100 - position if scale == SCALE_CLOSED_IS_100 else position


def from_room_scale(position: float, scale: str) -> float:
    """A position in the room's scale as Home Assistant's (100 = open)."""
    # The same flip both ways; two names so callers say which way they go.
    return to_room_scale(position, scale)
