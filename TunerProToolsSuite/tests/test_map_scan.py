import random

from tunerpro_tools.map_scan import (
    ProbableType,
    find_axis_candidates,
    scan_table_candidates,
    score_table_candidate,
)


def test_finds_increasing_axis_embedded_in_noise():
    rng = random.Random(1)
    noise_before = bytes(rng.randrange(256) for _ in range(20))
    axis = bytes(range(10, 10 + 16))  # strictly increasing run of 16
    noise_after = bytes(rng.randrange(256) for _ in range(20))
    data = noise_before + axis + noise_after

    candidates = find_axis_candidates(data, cell_sizes=(1,))
    matches = [c for c in candidates if c.offset == len(noise_before) and c.length == 16]
    assert matches, "expected the embedded increasing run to be found"
    assert matches[0].probable_type == ProbableType.AXIS_INCREASING
    assert matches[0].confidence == 1.0


def test_finds_decreasing_axis():
    data = bytes([200, 190, 180, 170, 160, 150, 140, 130])
    candidates = find_axis_candidates(data, cell_sizes=(1,))
    assert any(c.probable_type == ProbableType.AXIS_DECREASING for c in candidates)


def test_plateaus_do_not_break_a_run():
    # a real axis can repeat a value (e.g. clamped at a limit) without
    # stopping being "the same axis" - flat steps must not split the run.
    data = bytes([10, 20, 20, 20, 30, 40, 50, 60])
    candidates = find_axis_candidates(data, cell_sizes=(1,))
    full_run = [c for c in candidates if c.length == 8]
    assert full_run, "plateau in the middle should not have split the run"


def test_pure_noise_rarely_produces_high_confidence_long_runs():
    rng = random.Random(42)
    data = bytes(rng.randrange(256) for _ in range(2000))
    candidates = find_axis_candidates(data, cell_sizes=(1,), min_run_length=10)
    # random bytes essentially never form a 10+ long monotonic run
    assert candidates == []


def test_score_table_candidate_high_for_smooth_surface():
    rows, columns = 8, 8
    grid_bytes = bytearray(rows * columns)
    for r in range(rows):
        for c in range(columns):
            grid_bytes[r * columns + c] = (r * 10 + c * 3) % 256  # smooth gradient
    score = score_table_candidate(bytes(grid_bytes), 0, rows, columns, 1, "little", False)
    assert score > 0.7


def test_score_table_candidate_low_for_random_noise():
    rng = random.Random(7)
    rows, columns = 8, 8
    data = bytes(rng.randrange(256) for _ in range(rows * columns))
    score = score_table_candidate(data, 0, rows, columns, 1, "little", False)
    assert score < 0.5


def test_score_table_candidate_zero_for_flat_region():
    data = bytes([42] * 64)
    score = score_table_candidate(data, 0, 8, 8, 1, "little", False)
    assert score == 0.0


def test_score_table_candidate_zero_out_of_range():
    data = bytes(10)
    assert score_table_candidate(data, 0, 8, 8, 1, "little", False) == 0.0


def test_scan_table_candidates_finds_embedded_smooth_table():
    rng = random.Random(3)
    noise = bytes(rng.randrange(256) for _ in range(64))
    rows, columns = 8, 8
    table = bytearray(rows * columns)
    for r in range(rows):
        for c in range(columns):
            table[r * columns + c] = (r * 8 + c * 2) % 256
    data = noise + bytes(table) + noise

    results = scan_table_candidates(data, dim_options=(8,), stride=8, min_confidence=0.6)
    assert any(
        c.offset == len(noise) and c.rows == 8 and c.columns == 8 for c in results
    ), f"expected to find the embedded table, got {results}"


def test_scan_table_candidates_deduplicates_overlaps():
    rows, columns = 8, 8
    table = bytearray(rows * columns)
    for r in range(rows):
        for c in range(columns):
            table[r * columns + c] = (r * 8 + c * 2) % 256
    results = scan_table_candidates(bytes(table), dim_options=(4, 8), stride=4, min_confidence=0.5)
    # every result's byte range must be disjoint from every other's
    for i, a in enumerate(results):
        for b in results[i + 1:]:
            overlap = a.offset < b.offset + b.byte_length and b.offset < a.offset + a.byte_length
            assert not overlap
