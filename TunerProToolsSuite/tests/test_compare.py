from tunerpro_tools.compare import (
    VariationLevel,
    calibration_diff_stats,
    classify_variation,
    compare_bytes,
    differences_to_csv,
    differences_to_html,
    filter_differences,
)


def test_compare_bytes_finds_exact_differences():
    original = bytes([10, 20, 30, 40])
    modified = bytes([10, 25, 30, 45])
    summary = compare_bytes(original, modified)
    assert summary.difference_count == 2
    offsets = [d.offset for d in summary.differences]
    assert offsets == [1, 3]
    assert summary.differences[0].delta == 5
    assert summary.size_matches is True


def test_compare_bytes_no_differences():
    data = bytes([1, 2, 3])
    summary = compare_bytes(data, data)
    assert summary.difference_count == 0


def test_compare_bytes_different_sizes_only_compares_overlap():
    original = bytes([1, 2, 3])
    modified = bytes([1, 2, 3, 99])
    summary = compare_bytes(original, modified)
    assert summary.difference_count == 0
    assert summary.size_matches is False


def test_percent_change_handles_zero_original():
    original = bytes([0])
    modified = bytes([5])
    summary = compare_bytes(original, modified)
    assert summary.differences[0].percent_change is None


def test_filter_differences_by_offset_and_delta():
    original = bytes([0, 0, 0, 0])
    modified = bytes([1, 50, 1, 50])
    summary = compare_bytes(original, modified)
    filtered = filter_differences(summary.differences, min_abs_delta=10)
    assert [d.offset for d in filtered] == [1, 3]

    filtered_by_offset = filter_differences(summary.differences, min_offset=2)
    assert [d.offset for d in filtered_by_offset] == [2, 3]


def test_classify_variation_thresholds():
    assert classify_variation(5.0) == VariationLevel.LOW
    assert classify_variation(30.0) == VariationLevel.MODERATE
    assert classify_variation(80.0) == VariationLevel.HIGH


def test_classify_variation_never_uses_safety_language():
    for level in VariationLevel:
        text = level.value.lower()
        for forbidden in ("sur", "danger", "safe", "bon", "mauvais"):
            assert forbidden not in text


def test_export_csv_and_html_contain_all_differences():
    original = bytes([0, 0])
    modified = bytes([1, 2])
    summary = compare_bytes(original, modified)
    csv_text = differences_to_csv(summary.differences)
    assert csv_text.count("\n") == 3  # header + 2 rows (+ trailing newline)
    html_text = differences_to_html(summary.differences)
    assert "0x0" in html_text.upper() or "0X0" in html_text.upper()


def test_calibration_diff_stats():
    original = bytes([100, 100, 100])
    modified = bytes([110, 90, 100])
    summary = compare_bytes(original, modified)
    stats = calibration_diff_stats(summary.differences)
    assert stats.modified_cell_count == 2
    assert stats.max_variation == 10
    assert stats.min_variation == -10


def test_calibration_diff_stats_empty():
    stats = calibration_diff_stats(())
    assert stats.modified_cell_count == 0
