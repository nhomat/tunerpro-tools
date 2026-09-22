from map_optimizer.optimizer import detect_outliers, generate_suggestions, smooth_grid


def test_smooth_grid_zero_strength_is_noop():
    grid = [[1.0, 2.0], [3.0, 4.0]]
    assert smooth_grid(grid, strength=0.0) == grid


def test_smooth_grid_pulls_toward_neighbor_mean():
    grid = [[10.0, 10.0, 10.0], [10.0, 100.0, 10.0], [10.0, 10.0, 10.0]]
    smoothed = smooth_grid(grid, strength=1.0)
    # center cell should move fully to its neighbors' mean (10.0), away from 100
    assert smoothed[1][1] == 10.0


def test_smooth_grid_cell_far_from_spike_is_unaffected():
    # 5x5 flat grid with a single spike in the middle: a corner cell's
    # 3x3 neighborhood never reaches the spike, so it stays unchanged.
    grid = [[10.0] * 5 for _ in range(5)]
    grid[2][2] = 500.0
    smoothed = smooth_grid(grid, strength=1.0)
    assert smoothed[0][0] == 10.0


def test_smooth_grid_strength_clamped():
    grid = [[1.0, 2.0], [3.0, 4.0]]
    over = smooth_grid(grid, strength=5.0)
    under = smooth_grid(grid, strength=-5.0)
    assert over == smooth_grid(grid, strength=1.0)
    assert under == smooth_grid(grid, strength=0.0)


def test_detect_outliers_flags_spike():
    grid = [[10.0, 10.0, 10.0], [10.0, 500.0, 10.0], [10.0, 10.0, 10.0]]
    flags = detect_outliers(grid, z_threshold=2.0)
    positions = {(f.row, f.column) for f in flags}
    assert (1, 1) in positions
    assert (0, 0) not in positions


def test_detect_outliers_flat_grid_has_no_flags():
    grid = [[5.0] * 4 for _ in range(4)]
    assert detect_outliers(grid) == []


def test_generate_suggestions_never_mutates_original():
    grid = [[10.0, 10.0], [10.0, 90.0]]
    suggestion = generate_suggestions(grid, smoothing_strength=1.0)
    assert grid == [[10.0, 10.0], [10.0, 90.0]]  # caller's list untouched
    assert suggestion.original == [[10.0, 10.0], [10.0, 90.0]]
    assert suggestion.smoothed != suggestion.original


def test_optimization_suggestion_delta_and_changed_count():
    grid = [[10.0, 10.0], [10.0, 10.0]]
    suggestion = generate_suggestions(grid, smoothing_strength=0.0)
    assert suggestion.changed_cell_count == 0
    assert suggestion.delta == [[0.0, 0.0], [0.0, 0.0]]
