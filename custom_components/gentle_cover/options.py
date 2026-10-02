"""A room's settings: their defaults, the move from easings to curves, and
the checks a save from the page must pass."""

from __future__ import annotations

import copy
from typing import Any

from .const import (
    CONF_CLOSE_CURVE,
    CONF_CLOSE_DURATION,
    CONF_MIN_STEP,
    CONF_OPEN_CURVE,
    CONF_OPEN_DURATION,
    CONF_STEP_INTERVAL,
    DEFAULT_OPTIONS,
)
from .curve import CLOSE, OPEN, PRESETS, validate_curve

# Ranges shared with the page's fields.
RANGES = {
    CONF_OPEN_DURATION: (1, 120),
    CONF_CLOSE_DURATION: (1, 120),
    CONF_STEP_INTERVAL: (30, 600),
    CONF_MIN_STEP: (1, 50),
}


def defaults() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_OPTIONS)


def migrate_options(old: dict[str, Any]) -> dict[str, Any]:
    """Options from before curves: each easing becomes its preset curve."""
    new = defaults()
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
    return result
