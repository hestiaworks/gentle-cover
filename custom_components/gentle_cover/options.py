"""A room's settings: their defaults, how older rooms are brought up to date,
and the checks a save from the page must pass."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .const import (
    CONF_CLOSE_CURVE,
    CONF_CLOSE_DURATION,
    CONF_GENTLE_COVERS,
    CONF_GENTLE_ENABLED,
    CONF_GENTLE_NAME,
    CONF_INDIVIDUAL,
    CONF_MIN_STEP,
    CONF_NORMAL_COVERS,
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


def defaults(title: str, covers: list[str]) -> dict[str, Any]:
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
            CONF_NORMAL_COVERS: list(covers),
            CONF_GENTLE_COVERS: list(covers),
            CONF_INDIVIDUAL: {},
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


def migrate_room_covers(options: dict[str, Any], covers: list[str]) -> dict[str, Any]:
    """A room from before curtains were chosen: both move all of them, and
    none is offered on its own — exactly as it behaved."""
    new = copy.deepcopy(options)
    new.setdefault(CONF_NORMAL_COVERS, list(covers))
    new.setdefault(CONF_GENTLE_COVERS, list(covers))
    new.setdefault(CONF_INDIVIDUAL, {})
    return new


def migrate_entry_options(
    minor_version: int, options: dict[str, Any], title: str, covers: list[str]
) -> dict[str, Any]:
    """Bring a room's options from any earlier minor version to the current
    one, each step only where it is needed."""
    if minor_version >= 4:
        return options
    if minor_version < 2:
        options = migrate_options(options)
    if minor_version < 3:
        options = migrate_room_settings(options, title)
    return migrate_room_covers(options, covers)


def own_curtains_wanted(covers: list[str], individual: dict[str, Any]) -> list[str]:
    """The room's real curtains that are switched on as curtains of their own,
    in the room's order; one that has left the room is not."""
    return [
        entity_id
        for entity_id in covers
        if isinstance(individual.get(entity_id), dict) and individual[entity_id].get("enabled")
    ]


def default_own_name(curtain_name: str, room_title: str) -> str:
    """A real curtain's name without the room's name in front.

    Names follow the room's name when shown, so "Bedroom Curtains Right" in
    the Bedroom becomes "Curtains Right", shown as "Bedroom Curtains Right".
    """
    name = curtain_name.strip()
    title = room_title.strip()
    if title and name.casefold().startswith(title.casefold()):
        rest = name[len(title):].strip()
        if rest:
            return rest
    return name


def _subset(value: Any, covers: list[str], what: str, required: bool) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(c, str) for c in value):
        raise ValueError(f"{what}: curtains must be a list of entity ids")
    if len(set(value)) != len(value):
        raise ValueError(f"{what}: a curtain is listed twice")
    for entity_id in value:
        if entity_id not in covers:
            raise ValueError(f"{what}: {entity_id} is not one of the room's curtains")
    if required and not value:
        raise ValueError(f"{what} needs at least one curtain to move")
    # In the room's order, so saving the same choice twice stores the same list.
    return [entity_id for entity_id in covers if entity_id in value]


def _name(value: Any, what: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{what}: the name must be text")
    name = value.strip()
    if required and not name:
        raise ValueError(f"{what} needs a name")
    if len(name) > NAME_MAX:
        raise ValueError(f"{what}: a name is at most {NAME_MAX} characters")
    return name


def validate_options(data: dict[str, Any], covers: list[str]) -> dict[str, Any]:
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
    result[CONF_NORMAL_NAME] = _name(data.get(CONF_NORMAL_NAME), "The normal curtain", required=False)
    result[CONF_GENTLE_NAME] = _name(data.get(CONF_GENTLE_NAME), "The gentle curtain", required=False)
    result[CONF_NORMAL_COVERS] = _subset(
        data.get(CONF_NORMAL_COVERS), covers, "The normal curtain", result[CONF_NORMAL_ENABLED]
    )
    result[CONF_GENTLE_COVERS] = _subset(
        data.get(CONF_GENTLE_COVERS), covers, "The gentle curtain", result[CONF_GENTLE_ENABLED]
    )
    individual = data.get(CONF_INDIVIDUAL, {})
    if not isinstance(individual, dict):
        raise ValueError("own curtains must be a mapping of curtain to settings")
    result[CONF_INDIVIDUAL] = {}
    for entity_id, own in individual.items():
        if entity_id not in covers:
            raise ValueError(f"{entity_id} is not one of the room's curtains")
        if not isinstance(own, dict) or not isinstance(own.get("enabled"), bool):
            raise ValueError(f"{entity_id}: on its own must be on or off")
        result[CONF_INDIVIDUAL][entity_id] = {
            "enabled": own["enabled"],
            "name": _name(own.get("name", ""), entity_id, required=False),
        }
    enabled_names = [
        name
        for on, name in (
            (result[CONF_NORMAL_ENABLED], result[CONF_NORMAL_NAME]),
            (result[CONF_GENTLE_ENABLED], result[CONF_GENTLE_NAME]),
            *((own["enabled"], own["name"]) for own in result[CONF_INDIVIDUAL].values()),
        )
        if on
    ]
    if not enabled_names:
        raise ValueError("a room needs at least one curtain")
    folded = [name.casefold() for name in enabled_names]
    if len(set(folded)) != len(folded):
        # Two would show as the same thing in Home Assistant and HomeKit.
        raise ValueError("every curtain in a room needs a different name")
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
