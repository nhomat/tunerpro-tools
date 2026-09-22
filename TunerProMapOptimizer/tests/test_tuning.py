import pytest

from map_optimizer.optimizer import TuningTarget, generate_tuning_suggestion, interpolate_from_targets


def test_interpolate_passes_exactly_through_targets():
    targets = [TuningTarget(0, 0, 10.0), TuningTarget(3, 3, 40.0)]
    grid = interpolate_from_targets(4, 4, targets)
    assert grid[0][0] == 10.0
    assert grid[3][3] == 40.0


def test_interpolate_blends_between_two_targets_on_a_line():
    targets = [TuningTarget(0, 0, 0.0), TuningTarget(0, 4, 100.0)]
    grid = interpolate_from_targets(1, 5, targets)
    # midpoint should land between the two anchors
    assert 0.0 < grid[0][2] < 100.0
    # closer to the low anchor should be lower than closer to the high anchor
    assert grid[0][1] < grid[0][3]


def test_interpolate_requires_at_least_one_target():
    with pytest.raises(ValueError):
        interpolate_from_targets(4, 4, [])


def test_interpolate_requires_positive_dimensions():
    with pytest.raises(ValueError):
        interpolate_from_targets(0, 4, [TuningTarget(0, 0, 1.0)])


def test_single_target_fills_grid_uniformly():
    grid = interpolate_from_targets(3, 3, [TuningTarget(1, 1, 42.0)])
    assert all(value == 42.0 for row in grid for value in row)


def test_generate_tuning_suggestion_does_not_mutate_input_grid():
    grid = [[1.0, 2.0], [3.0, 4.0]]
    suggestion = generate_tuning_suggestion(grid, [TuningTarget(0, 0, 99.0)])
    assert grid == [[1.0, 2.0], [3.0, 4.0]]
    assert suggestion.tuned[0][0] == 99.0
    assert suggestion.delta[0][0] == pytest.approx(98.0)
