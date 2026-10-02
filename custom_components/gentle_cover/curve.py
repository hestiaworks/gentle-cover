"""Position-over-time curves for a gentle move.

A curve says how open the curtains are at each moment of a full opening or
closing. Between its points it is a monotone cubic (Fritsch–Carlson): smooth
like a drawn curve, but it never bulges past a point. A bulge would be real
movement — curtains dipping during a hold and backing up after it.
"""

from __future__ import annotations

import math

OPEN = "open"
CLOSE = "close"

PRESETS: dict[str, dict[str, list[list[float]]]] = {
    OPEN: {
        "slow_start": [[0, 0], [0.25, 6], [0.5, 25], [0.75, 56], [1, 100]],
        "even": [[0, 0], [1, 100]],
        "hold_then_open": [[0, 0], [0.1, 10], [0.4, 10], [1, 100]],
    },
    CLOSE: {
        "slow_start": [[0, 100], [0.25, 94], [0.5, 75], [0.75, 44], [1, 0]],
        "even": [[0, 100], [1, 0]],
    },
}


def validate_curve(points: object, direction: str) -> list[list[float]]:
    """The curve as floats, or ValueError saying what is wrong with it."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("a curve needs at least two points")
    cleaned: list[list[float]] = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("each point is [time, position]")
        t, position = float(point[0]), float(point[1])
        if not (0 <= t <= 1 and 0 <= position <= 100):
            raise ValueError("time is 0..1 and position 0..100")
        cleaned.append([t, position])
    start, end = (0.0, 100.0) if direction == OPEN else (100.0, 0.0)
    if cleaned[0] != [0.0, start] or cleaned[-1] != [1.0, end]:
        raise ValueError(f"the curve runs from {start:g} % to {end:g} %")
    sign = 1 if direction == OPEN else -1
    for a, b in zip(cleaned, cleaned[1:]):
        if b[0] <= a[0]:
            raise ValueError("points must be in time order")
        if sign * (b[1] - a[1]) < 0:
            raise ValueError("the curve cannot go backwards")
    return cleaned


class Curve:
    def __init__(self, points: object, direction: str) -> None:
        self.points = validate_curve(points, direction)
        self.direction = direction
        self._sign = 1 if direction == OPEN else -1
        x = [p[0] for p in self.points]
        y = [p[1] for p in self.points]
        n = len(x)
        secants = [(y[k + 1] - y[k]) / (x[k + 1] - x[k]) for k in range(n - 1)]
        tangents = [0.0] * n
        tangents[0], tangents[-1] = secants[0], secants[-1]
        for k in range(1, n - 1):
            same_way = secants[k - 1] * secants[k] > 0
            tangents[k] = (secants[k - 1] + secants[k]) / 2 if same_way else 0.0
        for k in range(n - 1):
            if secants[k] == 0:
                # A hold: flat at both ends, so it stays exactly level.
                tangents[k] = tangents[k + 1] = 0.0
                continue
            a = tangents[k] / secants[k]
            b = tangents[k + 1] / secants[k]
            if a * a + b * b > 9:
                tau = 3 / math.sqrt(a * a + b * b)
                tangents[k] = tau * a * secants[k]
                tangents[k + 1] = tau * b * secants[k]
        self._x, self._y, self._m = x, y, tangents

    def at(self, t: float) -> float:
        """Position at time share t."""
        x, y, m = self._x, self._y, self._m
        t = min(1.0, max(0.0, t))
        k = 0
        while k < len(x) - 2 and t > x[k + 1]:
            k += 1
        h = x[k + 1] - x[k]
        u = (t - x[k]) / h
        return (
            (2 * u**3 - 3 * u**2 + 1) * y[k]
            + (u**3 - 2 * u**2 + u) * h * m[k]
            + (-2 * u**3 + 3 * u**2) * y[k + 1]
            + (u**3 - u**2) * h * m[k + 1]
        )

    def _progress(self, t: float) -> float:
        # Opening and closing both become "never decreasing" for the searches.
        return self._sign * self.at(t)

    def last_time_at(self, position: float) -> float:
        """The last moment the curve is at (or before) this position.

        A move from here starts at that moment, so a hold at this position
        is skipped rather than waited out.
        """
        goal = self._sign * position
        if self._progress(1.0) <= goal:
            return 1.0
        low, high = 0.0, 1.0
        for _ in range(60):
            mid = (low + high) / 2
            if self._progress(mid) <= goal + 1e-9:
                low = mid
            else:
                high = mid
        return low

    def first_time_reaching(self, position: float) -> float:
        """The first moment the curve reaches this position."""
        goal = self._sign * position
        if self._progress(0.0) >= goal:
            return 0.0
        low, high = 0.0, 1.0
        for _ in range(60):
            mid = (low + high) / 2
            if self._progress(mid) >= goal - 1e-9:
                high = mid
            else:
                low = mid
        return high
