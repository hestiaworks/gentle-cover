"""Where the curtains should be, and when, during one gentle move.

Pure arithmetic with nothing from Home Assistant, so it is tested on its own.
The whole plan is made before the first command and never revised: the
curtain controller reports its position late and loosely around a move, and
re-planning from those reports is what made the old blueprint overshoot and
twitch back.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple


class Plan(NamedTuple):
    steps: list[tuple[float, int]]
    t_start: float
    t_end: float
    span_s: float


def plan(
    start: float,
    target: float,
    curve: Any,
    duration_s: float,
    min_step: float,
    interval_s: float = 150.0,
) -> Plan:
    """The commands for a move from start to target along the curve.

    The curve is one full opening or closing over duration_s. A move picks
    up where the curve last is at start (skipping a hold it is already in)
    and stops where the curve first reaches target. A step smaller than
    min_step merges with the ones after it — tiny moves are what this motor
    does worst. Each command is sent when the curve reaches its position, so
    a hold keeps its length and the last command lands exactly on target at
    the end of the span; only the first is sent at once, so the move visibly
    starts.
    """
    start = round(start)
    target = round(target)
    if start == target:
        return Plan([], 0.0, 0.0, 0.0)
    t_start = curve.last_time_at(start)
    t_end = max(t_start, curve.first_time_reaching(target))
    span = (t_end - t_start) * duration_s
    count = max(1, math.ceil(span / interval_s))
    low, high = sorted((start, target))
    steps: list[tuple[float, int]] = []
    last = start
    for i in range(1, count + 1):
        # Sent when the curve gets there, never before: a command early by
        # one interval would cut a hold short by as much.
        at = i * span / count
        if i == count:
            position = target
        else:
            position = round(curve.at(t_start + (t_end - t_start) * i / count))
            position = min(high, max(low, position))
            if abs(position - last) < min_step:
                continue
        # Except the first, which goes out at once so the move visibly starts.
        steps.append((0.0 if not steps else round(at, 1), position))
        last = position
    return Plan(steps, t_start, t_end, span)


def preview(
    curve: Any, duration_s: float, min_step: float, interval_s: float
) -> dict[str, Any]:
    """What a full opening or closing along this curve sends, for the page."""
    start, target = (0, 100) if curve.direction == "open" else (100, 0)
    result = plan(start, target, curve, duration_s, min_step, interval_s)
    return {
        "steps": [[at, position] for at, position in result.steps],
        "samples": [[i / 100, round(curve.at(i / 100), 2)] for i in range(101)],
        "span_s": round(result.span_s, 1),
        "t_start": round(result.t_start, 4),
    }


def off_course(
    origin: float | None, sent: float, reported: float, tolerance: float
) -> bool:
    """Whether a curtain that reported this position was moved by a person.

    Anywhere between where it was when we sent the step and where we sent
    it, give or take the tolerance, is ours: still on its way, arrived, or a
    late report of where it used to be. Beyond that, someone else moved it.
    """
    if origin is None:
        return abs(reported - sent) > tolerance
    low, high = sorted((origin, sent))
    return reported < low - tolerance or reported > high + tolerance
