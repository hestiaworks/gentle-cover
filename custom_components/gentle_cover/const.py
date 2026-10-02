"""Names and defaults shared across the integration."""

from __future__ import annotations

from .curve import CLOSE, OPEN, PRESETS

DOMAIN = "gentle_cover"
MINOR_VERSION = 2

CONF_COVERS = "covers"
CONF_OPEN_DURATION = "open_duration"
CONF_CLOSE_DURATION = "close_duration"
CONF_OPEN_CURVE = "open_curve"
CONF_CLOSE_CURVE = "close_curve"
CONF_STEP_INTERVAL = "step_interval"
CONF_MIN_STEP = "min_step"

# Durations are minutes for a full 0-100 travel. Opening is the wake-up and
# gets the long, slow-starting curve; closing has no one to dazzle. A command
# every two and a half minutes reads as "the curtains open a bit now and
# then", not as a motor that cannot make up its mind.
DEFAULT_OPTIONS: dict[str, object] = {
    CONF_OPEN_DURATION: 20,
    CONF_CLOSE_DURATION: 10,
    CONF_OPEN_CURVE: PRESETS[OPEN]["slow_start"],
    CONF_CLOSE_CURVE: PRESETS[CLOSE]["even"],
    CONF_STEP_INTERVAL: 150,
    CONF_MIN_STEP: 5,
}

# How far from the position we sent a curtain may settle before we decide a
# person moved it, and how long after our command before we start judging:
# the controller reports its position late.
SETTLE_TOLERANCE = 10
SETTLE_GRACE_S = 30.0

SERVICE_MOVE = "move"
ATTR_DURATION = "duration"
