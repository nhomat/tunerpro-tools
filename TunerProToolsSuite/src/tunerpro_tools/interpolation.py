"""Monotone cubic (Fritsch-Carlson) interpolation.

Used to build a smooth curve (e.g. torque vs RPM) through a handful of
known/disclosed points (idle, peak torque, peak power, redline) without
inventing a shape: the classic Fritsch & Carlson (1980) construction
guarantees the interpolant never overshoots past its neighboring knot
values within any interval, so a "rise then fall" shape (like a real
torque curve) stays physically sane between the disclosed points instead
of oscillating or diving negative. This is the same construction behind
SciPy's PCHIP - reimplemented here in pure Python since the project has
no numpy/scipy dependency.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True)
class MonotoneCubicSpline:
    """A callable piecewise-cubic Hermite spline through `xs`/`ys`.

    Evaluating outside [xs[0], xs[-1]] clamps to the nearest end slope
    (linear extrapolation) rather than producing an unbounded cubic.
    """

    xs: tuple[float, ...]
    ys: tuple[float, ...]
    tangents: tuple[float, ...]

    def __call__(self, x: float) -> float:
        xs, ys, m = self.xs, self.ys, self.tangents
        n = len(xs)
        if x <= xs[0]:
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])

        i = bisect_right(xs, x) - 1
        i = min(i, n - 2)
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h

        h00 = 2 * t**3 - 3 * t**2 + 1
        h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2
        h11 = t**3 - t**2

        return h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]

    def sample(self, count: int) -> list[tuple[float, float]]:
        """Evenly spaced (x, y) pairs across [xs[0], xs[-1]], `count` points."""
        if count < 2:
            raise ValueError("count must be at least 2")
        x0, x1 = self.xs[0], self.xs[-1]
        step = (x1 - x0) / (count - 1)
        return [(x0 + i * step, self(x0 + i * step)) for i in range(count)]


def build_monotone_cubic_spline(points: list[tuple[float, float]]) -> MonotoneCubicSpline:
    """Build a Fritsch-Carlson monotone cubic Hermite spline through `points`.

    `points` must have at least 2 entries with strictly increasing x
    values (e.g. RPM). Each resulting interval is monotonic on its own -
    it never over/undershoots past either of its two endpoint y-values,
    even when the overall curve rises then falls (a real torque curve's
    shape) across multiple intervals.
    """
    if len(points) < 2:
        raise ValueError("At least 2 points are required to build a spline")
    ordered = sorted(points, key=lambda p: p[0])
    xs = tuple(p[0] for p in ordered)
    ys = tuple(p[1] for p in ordered)
    if len(set(xs)) != len(xs):
        raise ValueError("x values must be strictly increasing (no duplicates)")

    n = len(xs)
    secants = [(ys[k + 1] - ys[k]) / (xs[k + 1] - xs[k]) for k in range(n - 1)]

    tangents = [0.0] * n
    tangents[0] = secants[0]
    tangents[-1] = secants[-1]
    for k in range(1, n - 1):
        if secants[k - 1] == 0 or secants[k] == 0 or (secants[k - 1] > 0) != (secants[k] > 0):
            tangents[k] = 0.0
        else:
            # weighted harmonic mean of the two adjacent secants
            w1 = 2 * (xs[k + 1] - xs[k]) + (xs[k] - xs[k - 1])
            w2 = (xs[k + 1] - xs[k]) + 2 * (xs[k] - xs[k - 1])
            tangents[k] = (w1 + w2) / (w1 / secants[k - 1] + w2 / secants[k])

    # Fritsch-Carlson limiter: clamp each interval's tangent pair so the
    # interpolant cannot overshoot beyond [min(y_k, y_k+1), max(y_k, y_k+1)].
    for k in range(n - 1):
        if secants[k] == 0:
            tangents[k] = 0.0
            tangents[k + 1] = 0.0
            continue
        alpha = tangents[k] / secants[k]
        beta = tangents[k + 1] / secants[k]
        if alpha < 0:
            tangents[k] = 0.0
            alpha = 0.0
        if beta < 0:
            tangents[k + 1] = 0.0
            beta = 0.0
        norm = alpha * alpha + beta * beta
        if norm > 9:
            tau = 3 / (norm ** 0.5)
            tangents[k] = tau * alpha * secants[k]
            tangents[k + 1] = tau * beta * secants[k]

    return MonotoneCubicSpline(xs=xs, ys=ys, tangents=tuple(tangents))
