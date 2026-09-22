"""Byte-level diffing shared by BIN Compare and Calibration Diff.

Comparison is strictly read-only: both files are loaded, never modified.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ByteDifference:
    offset: int
    original: int
    modified: int

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:X}"

    @property
    def delta(self) -> int:
        return self.modified - self.original

    @property
    def percent_change(self) -> float | None:
        if self.original == 0:
            return None
        return (self.delta / self.original) * 100.0


class VariationLevel(str, Enum):
    """Neutral variation labels - never "safe"/"dangerous"/"good"/"bad"."""

    LOW = "faible variation"
    MODERATE = "variation moderee"
    HIGH = "variation importante"


def classify_variation(percent_change: float | None, *, absolute_delta: int = 0) -> VariationLevel:
    """Classify a change using percentage when available, else absolute delta.

    Thresholds are intentionally simple and neutral: they describe the
    *size* of a change, never its safety or correctness.
    """
    magnitude = abs(percent_change) if percent_change is not None else abs(absolute_delta)
    reference = 100.0 if percent_change is not None else 32.0
    ratio = magnitude / reference
    if ratio < 0.15:
        return VariationLevel.LOW
    if ratio < 0.5:
        return VariationLevel.MODERATE
    return VariationLevel.HIGH


@dataclass(frozen=True)
class CompareSummary:
    original_size: int
    modified_size: int
    differences: tuple[ByteDifference, ...]

    @property
    def difference_count(self) -> int:
        return len(self.differences)

    @property
    def size_matches(self) -> bool:
        return self.original_size == self.modified_size


def compare_bytes(original: bytes, modified: bytes) -> CompareSummary:
    """Byte-by-byte diff over the overlapping length of both buffers."""
    shortest = min(len(original), len(modified))
    differences = [
        ByteDifference(offset=i, original=original[i], modified=modified[i])
        for i in range(shortest)
        if original[i] != modified[i]
    ]
    return CompareSummary(
        original_size=len(original),
        modified_size=len(modified),
        differences=tuple(differences),
    )


def filter_differences(
    differences: tuple[ByteDifference, ...],
    *,
    min_offset: int | None = None,
    max_offset: int | None = None,
    min_abs_delta: int | None = None,
) -> list[ByteDifference]:
    result = list(differences)
    if min_offset is not None:
        result = [d for d in result if d.offset >= min_offset]
    if max_offset is not None:
        result = [d for d in result if d.offset <= max_offset]
    if min_abs_delta is not None:
        result = [d for d in result if abs(d.delta) >= min_abs_delta]
    return result


def differences_to_csv(differences: tuple[ByteDifference, ...]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Offset", "Original", "Modified", "Difference", "PercentChange"])
    for diff in differences:
        percent = "" if diff.percent_change is None else f"{diff.percent_change:.2f}"
        writer.writerow([diff.offset_hex, diff.original, diff.modified, diff.delta, percent])
    return buffer.getvalue()


def differences_to_html(differences: tuple[ByteDifference, ...], *, title: str = "BIN Compare Report") -> str:
    rows = []
    for diff in differences:
        percent = "-" if diff.percent_change is None else f"{diff.percent_change:+.2f}%"
        sign = "+" if diff.delta >= 0 else ""
        rows.append(
            f"<tr><td>{diff.offset_hex}</td><td>{diff.original}</td>"
            f"<td>{diff.modified}</td><td>{sign}{diff.delta}</td><td>{percent}</td></tr>"
        )
    rows_html = "\n".join(rows) if rows else "<tr><td colspan='5'>Aucune difference</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; background: #1e1e1e; color: #ddd; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #444; padding: 6px 10px; text-align: right; }}
th {{ background: #2d2d2d; text-align: center; }}
td:first-child, th:first-child {{ text-align: left; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>{len(differences)} difference(s) detectee(s).</p>
<table>
<tr><th>Offset</th><th>Original</th><th>Modified</th><th>Difference</th><th>% variation</th></tr>
{rows_html}
</table>
</body>
</html>
"""


@dataclass(frozen=True)
class CalibrationDiffStats:
    modified_cell_count: int
    mean_variation: float
    max_variation: float
    min_variation: float


def calibration_diff_stats(differences: tuple[ByteDifference, ...]) -> CalibrationDiffStats:
    """Aggregate statistics over a set of differences for Calibration Diff.

    Variation here is the raw byte delta; when a MapDefinition scaling
    factor is available, callers should convert deltas to engineering
    units before calling this (see map_model.scale_value).
    """
    if not differences:
        return CalibrationDiffStats(0, 0.0, 0.0, 0.0)
    deltas = [d.delta for d in differences]
    return CalibrationDiffStats(
        modified_cell_count=len(differences),
        mean_variation=sum(deltas) / len(deltas),
        max_variation=max(deltas),
        min_variation=min(deltas),
    )
