"""Map Optimizer Assistant - core logic.

SCOPE AND LIMITS (read before touching this file):

This module offers two independent tools over a numeric grid, both of
which are pure geometry/statistics - neither ever reasons about engine
physics:

1. ``smooth_grid`` / ``detect_outliers`` (the "Lissage" function) -
   data-quality operations. Smoothing blends each cell toward its local
   neighborhood average to reduce abrupt cell-to-cell discontinuities;
   outlier detection flags a cell that jars against its neighbors
   (typically a typo or transfer error). Neither "fixes" anything.
2. ``interpolate_from_targets`` / ``generate_tuning_suggestion`` (the
   "Tuning" function) - fills an entire table from a sparse set of
   anchor points the *user* supplies (their own dyno data, reference
   calibration, manufacturer spec). It only interpolates between values
   a human already decided on; it never decides a target value itself.

Neither function:
- estimates horsepower/torque, air-fuel ratio quality, knock margin, or
  any other engine-physics quantity - there is no sensor data (wideband
  O2, knock, EGT, dyno load) available from a static file to base such
  a judgment on;
- chooses, on its own, that a cell should be leaner/richer or have more/
  less advance "for more power" - every number this module ever outputs
  either comes from smoothing existing data or from interpolating
  values the user typed in themselves;
- writes anything back into a BIN file. Every function here returns new
  Python data structures; ``patch.py`` is the only place that ever turns
  a suggestion into bytes, and only into a copy the caller explicitly
  chooses (see its own module docstring).

Every suggestion this module produces still needs a human familiar with
the engine to review it before it is used for anything real.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class OutlierFlag:
    row: int
    column: int
    value: float
    neighbor_mean: float
    neighbor_std: float
    z_score: float

    @property
    def note(self) -> str:
        return "Ecart isole par rapport aux cellules voisines - verification manuelle recommandee."


@dataclass(frozen=True)
class OptimizationSuggestion:
    original: list[list[float]]
    smoothed: list[list[float]]
    outliers: tuple[OutlierFlag, ...]

    @property
    def delta(self) -> list[list[float]]:
        return [
            [s - o for s, o in zip(srow, orow)]
            for srow, orow in zip(self.smoothed, self.original)
        ]

    @property
    def changed_cell_count(self) -> int:
        return sum(1 for row in self.delta for value in row if abs(value) > 1e-9)


def _neighbors(grid: list[list[float]], row: int, column: int, radius: int = 1) -> list[float]:
    rows, columns = len(grid), len(grid[0])
    values = []
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dr == 0 and dc == 0:
                continue
            r, c = row + dr, column + dc
            if 0 <= r < rows and 0 <= c < columns:
                values.append(grid[r][c])
    return values


def smooth_grid(grid: list[list[float]], strength: float = 0.5, radius: int = 1) -> list[list[float]]:
    """Blend each cell toward its neighborhood average.

    ``strength`` is clamped to [0, 1]: 0 returns the grid unchanged, 1
    replaces each cell fully with its neighbor average. This is a
    smoothing/de-noising operation only - it has no notion of "better"
    engine behavior, only of "less abrupt" numbers.
    """
    if not grid or not grid[0]:
        return [row[:] for row in grid]
    strength = max(0.0, min(1.0, strength))

    result = []
    for r, row in enumerate(grid):
        new_row = []
        for c, value in enumerate(row):
            neighbors = _neighbors(grid, r, c, radius=radius)
            if not neighbors:
                new_row.append(value)
                continue
            neighbor_mean = sum(neighbors) / len(neighbors)
            new_row.append(value * (1 - strength) + neighbor_mean * strength)
        result.append(new_row)
    return result


def detect_outliers(grid: list[list[float]], z_threshold: float = 2.5, radius: int = 1) -> list[OutlierFlag]:
    """Flag cells that deviate sharply from their local neighborhood.

    A cell is flagged when ``|value - neighbor_mean| / neighbor_std``
    exceeds ``z_threshold``. When the neighborhood has zero variance
    (all neighbors identical), any nonzero deviation is flagged outright
    - a lone spike surrounded by perfectly uniform values is exactly the
    case this function exists to catch, and there is no valid z-score to
    fall back on there (division by zero), so its z_score is reported as
    infinite rather than the cell being silently skipped.
    """
    flags = []
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            neighbors = _neighbors(grid, r, c, radius=radius)
            if len(neighbors) < 2:
                continue
            neighbor_mean = statistics.mean(neighbors)
            neighbor_std = statistics.pstdev(neighbors)
            if neighbor_std == 0:
                if abs(value - neighbor_mean) > 1e-9:
                    flags.append(OutlierFlag(r, c, value, neighbor_mean, neighbor_std, math.inf))
                continue
            z_score = abs(value - neighbor_mean) / neighbor_std
            if z_score >= z_threshold:
                flags.append(OutlierFlag(r, c, value, neighbor_mean, neighbor_std, z_score))
    return flags


def generate_suggestions(
    grid: list[list[float]], *, smoothing_strength: float = 0.3, z_threshold: float = 2.5
) -> OptimizationSuggestion:
    """Compute the full suggestion set (smoothed grid + outlier flags) for `grid`."""
    outliers = detect_outliers(grid, z_threshold=z_threshold)
    smoothed = smooth_grid(grid, strength=smoothing_strength)
    return OptimizationSuggestion(original=[row[:] for row in grid], smoothed=smoothed, outliers=tuple(outliers))


@dataclass(frozen=True)
class TuningTarget:
    """One user-supplied anchor point: 'at this cell, I want this value.'

    The value always comes from the person using the tool (their own
    dyno data, reference calibration, manufacturer spec, experience) -
    this module never invents one.
    """

    row: int
    column: int
    value: float


@dataclass(frozen=True)
class TuningSuggestion:
    original: list[list[float]]
    tuned: list[list[float]]
    targets: tuple[TuningTarget, ...]

    @property
    def delta(self) -> list[list[float]]:
        return [
            [t - o for t, o in zip(trow, orow)]
            for trow, orow in zip(self.tuned, self.original)
        ]


def interpolate_from_targets(
    rows: int, columns: int, targets: list[TuningTarget], *, power: float = 2.0
) -> list[list[float]]:
    """Fill an entire grid from a sparse set of user-supplied anchor points.

    Uses inverse-distance weighting (IDW): every cell's value is a
    distance-weighted average of every target's value, so the result
    passes exactly through each target and blends smoothly between them.
    This is the same idea a mapper applies by hand when they set a few
    known-good breakpoints in a table and interpolate the rest - it is
    pure geometry, not an engine model, and never runs unless the caller
    supplies at least one target value themselves.
    """
    if not targets:
        raise ValueError("At least one TuningTarget is required")
    if rows <= 0 or columns <= 0:
        raise ValueError("rows and columns must be positive")

    target_by_position = {(t.row, t.column): t.value for t in targets}

    grid = []
    for r in range(rows):
        row_values = []
        for c in range(columns):
            if (r, c) in target_by_position:
                row_values.append(target_by_position[(r, c)])
                continue
            weight_sum = 0.0
            weighted_value_sum = 0.0
            for target in targets:
                distance = math.hypot(r - target.row, c - target.column)
                weight = 1.0 / (distance ** power)
                weight_sum += weight
                weighted_value_sum += weight * target.value
            row_values.append(weighted_value_sum / weight_sum)
        grid.append(row_values)
    return grid


def generate_tuning_suggestion(
    grid: list[list[float]], targets: list[TuningTarget], *, power: float = 2.0
) -> TuningSuggestion:
    """Interpolate `targets` across a grid the same shape as `grid`."""
    rows, columns = len(grid), len(grid[0]) if grid else 0
    tuned = interpolate_from_targets(rows, columns, targets, power=power)
    return TuningSuggestion(original=[row[:] for row in grid], tuned=tuned, targets=tuple(targets))
