"""Heuristic structure scanner for BIN Analyzer's automatic analysis.

Honesty contract (this is the whole point of this module - read before
changing anything): nothing here can know that a given region is "the
ignition table" or "the fuel map". A raw calibration BIN carries no
type information; that mapping only exists in the ECU manufacturer's
own (usually proprietary) table definition (XDF/A2L). What this module
*can* determine from the bytes alone, honestly, is purely geometric/
statistical:

- ``find_axis_candidates`` - contiguous runs of monotonic integers,
  the same shape a real RPM/load/temperature axis has.
- ``score_table_candidate`` / ``scan_table_candidates`` - regions whose
  values change smoothly from one cell to its neighbors, the same shape
  a real 2D calibration surface has (as opposed to code, text, or
  padding, which score low).

Every result carries a numeric ``confidence`` computed from the data
itself (never a fixed/invented number), and every result's
``probable_type`` is one of the generic labels below - never an
automotive role. Anything not meeting the confidence threshold is
simply not reported, rather than guessed.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum


class ProbableType(str, Enum):
    AXIS_INCREASING = "axe probable (croissant)"
    AXIS_DECREASING = "axe probable (decroissant)"
    TABLE_2D = "table 2D probable (surface lisse)"
    UNKNOWN = "inconnu - validation manuelle necessaire"


@dataclass(frozen=True)
class AxisCandidate:
    offset: int
    length: int
    cell_size: int
    endianness: str
    signed: bool
    values: tuple[int, ...]
    confidence: float
    probable_type: ProbableType

    @property
    def byte_length(self) -> int:
        return self.length * self.cell_size


@dataclass(frozen=True)
class TableCandidate:
    offset: int
    rows: int
    columns: int
    cell_size: int
    endianness: str
    signed: bool
    confidence: float
    probable_type: ProbableType = field(default=ProbableType.TABLE_2D)

    @property
    def byte_length(self) -> int:
        return self.rows * self.columns * self.cell_size


MIN_AXIS_RUN_LENGTH = 6


def _decode_ints(data: bytes, cell_size: int, endianness: str, signed: bool) -> list[int]:
    count = len(data) // cell_size
    return [
        int.from_bytes(data[i * cell_size:(i + 1) * cell_size], byteorder=endianness, signed=signed)
        for i in range(count)
    ]


def find_axis_candidates(
    data: bytes,
    *,
    cell_sizes: tuple[int, ...] = (1, 2),
    min_run_length: int = MIN_AXIS_RUN_LENGTH,
) -> list[AxisCandidate]:
    """Find every maximal run of monotonic integers at least `min_run_length` long.

    Runs a single O(n) pass per (cell_size, endianness, signed) combination
    over the whole file - tractable even on a multi-megabyte BIN, since it
    never re-decodes overlapping windows.
    """
    candidates: list[AxisCandidate] = []
    for cell_size in cell_sizes:
        for endianness in ("little", "big"):
            for signed in (False, True):
                values = _decode_ints(data, cell_size, endianness, signed)
                candidates.extend(
                    _scan_monotonic_runs(values, cell_size, endianness, signed, min_run_length)
                )
    return candidates


def _scan_monotonic_runs(
    values: list[int], cell_size: int, endianness: str, signed: bool, min_run_length: int
) -> list[AxisCandidate]:
    results: list[AxisCandidate] = []
    if len(values) < min_run_length:
        return results

    run_start = 0
    # direction: 0 = undetermined/flat so far, 1 = increasing, -1 = decreasing
    direction = 0

    def flush(end_index: int, run_direction: int) -> None:
        length = end_index - run_start + 1
        if length < min_run_length or run_direction == 0:
            return
        run_values = values[run_start:end_index + 1]
        strict_steps = sum(
            1 for a, b in zip(run_values, run_values[1:])
            if (b - a) * run_direction > 0
        )
        confidence = strict_steps / (length - 1)
        if confidence <= 0:
            return
        probable_type = ProbableType.AXIS_INCREASING if run_direction > 0 else ProbableType.AXIS_DECREASING
        results.append(
            AxisCandidate(
                offset=run_start * cell_size,
                length=length,
                cell_size=cell_size,
                endianness=endianness,
                signed=signed,
                values=tuple(run_values),
                confidence=round(confidence, 4),
                probable_type=probable_type,
            )
        )

    for i in range(1, len(values)):
        step = values[i] - values[i - 1]
        step_direction = (step > 0) - (step < 0)  # -1, 0, or 1

        if step_direction == 0:
            continue  # a plateau doesn't break a run - real axes repeat values
        if direction == 0:
            direction = step_direction
        elif step_direction != direction:
            flush(i - 1, direction)
            run_start = i - 1
            direction = step_direction

    flush(len(values) - 1, direction)
    return results


def score_table_candidate(
    data: bytes, offset: int, rows: int, columns: int, cell_size: int, endianness: str, signed: bool
) -> float:
    """Score how much a region looks like a smooth 2D calibration surface.

    Returns 0.0 if the region is out of range or degenerate (constant).
    Otherwise returns a 0..1 smoothness confidence: for every interior
    cell, compare it to the average of its 4-neighbors; a real
    calibration surface changes gradually, so most cells should be close
    to that average relative to the region's overall value spread.
    """
    end = offset + rows * columns * cell_size
    if end > len(data) or rows < 2 or columns < 2:
        return 0.0

    grid = []
    cursor = offset
    for _ in range(rows):
        row = []
        for _ in range(columns):
            chunk = data[cursor:cursor + cell_size]
            row.append(int.from_bytes(chunk, byteorder=endianness, signed=signed))
            cursor += cell_size
        grid.append(row)

    flat = [v for row in grid for v in row]
    value_range = max(flat) - min(flat)
    if value_range == 0:
        return 0.0  # a flat region is not evidence of a calibration surface

    deviations = []
    for r in range(1, rows - 1):
        for c in range(1, columns - 1):
            neighbor_average = (grid[r - 1][c] + grid[r + 1][c] + grid[r][c - 1] + grid[r][c + 1]) / 4
            deviations.append(abs(grid[r][c] - neighbor_average) / value_range)

    if not deviations:
        return 0.0
    mean_deviation = statistics.mean(deviations)
    return max(0.0, min(1.0, 1.0 - mean_deviation * 4))


def scan_table_candidates(
    data: bytes,
    *,
    cell_sizes: tuple[int, ...] = (1, 2),
    dim_options: tuple[int, ...] = (4, 8, 12, 16, 20, 24, 32),
    stride: int = 16,
    min_confidence: float = 0.6,
    max_results: int = 25,
) -> list[TableCandidate]:
    """Bounded brute-force search for smooth 2D regions.

    Complexity is offsets-scanned x dims-tried x cell_sizes x 2
    endiannesses, each an O(rows*columns) score. `stride` and
    `dim_options` bound this explicitly - on a multi-megabyte file,
    increase `stride` (or narrow `dim_options`) to keep this tractable;
    this function deliberately does not pretend to be an exhaustive,
    instant scan of an arbitrarily large file.
    """
    results: list[TableCandidate] = []
    for offset in range(0, len(data), stride):
        for cell_size in cell_sizes:
            for endianness in ("little", "big"):
                for rows in dim_options:
                    for columns in dim_options:
                        if offset + rows * columns * cell_size > len(data):
                            continue
                        confidence = score_table_candidate(
                            data, offset, rows, columns, cell_size, endianness, signed=False
                        )
                        if confidence >= min_confidence:
                            results.append(
                                TableCandidate(
                                    offset=offset,
                                    rows=rows,
                                    columns=columns,
                                    cell_size=cell_size,
                                    endianness=endianness,
                                    signed=False,
                                    confidence=round(confidence, 4),
                                )
                            )

    results.sort(key=lambda candidate: candidate.confidence, reverse=True)
    return _deduplicate_overlapping(results)[:max_results]


def _deduplicate_overlapping(candidates: list[TableCandidate]) -> list[TableCandidate]:
    """Keep the highest-confidence candidate among heavily overlapping ones.

    Without this, one real table gets reported dozens of times at every
    dim/offset that happens to also score well against the same bytes.
    """
    kept: list[TableCandidate] = []
    for candidate in candidates:
        overlaps_kept = any(
            candidate.offset < other.offset + other.byte_length
            and other.offset < candidate.offset + candidate.byte_length
            for other in kept
        )
        if not overlaps_kept:
            kept.append(candidate)
    return kept
