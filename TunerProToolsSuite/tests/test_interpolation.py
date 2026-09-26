import pytest

from tunerpro_tools.interpolation import build_monotone_cubic_spline


def test_passes_exactly_through_given_points():
    points = [(0, 10), (1000, 200), (3000, 350), (6000, 180)]
    spline = build_monotone_cubic_spline(points)
    for x, y in points:
        assert spline(x) == pytest.approx(y, abs=1e-9)


def test_monotonic_input_stays_monotonic_between_knots():
    points = [(0, 0), (10, 5), (20, 30), (30, 32), (40, 100)]
    spline = build_monotone_cubic_spline(points)
    samples = spline.sample(200)
    values = [y for _, y in samples]
    assert all(b >= a - 1e-9 for a, b in zip(values, values[1:]))


def test_hump_shape_never_overshoots_past_neighboring_knots():
    # a torque-curve-like shape: rises, peaks, falls
    points = [(800, 50), (2000, 300), (4000, 350), (5500, 340), (7000, 200)]
    spline = build_monotone_cubic_spline(points)
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        lower, upper = min(y0, y1), max(y0, y1)
        step = (x1 - x0) / 20
        x = x0
        while x <= x1:
            y = spline(x)
            assert lower - 1e-6 <= y <= upper + 1e-6, f"overshoot at x={x}: y={y} not in [{lower},{upper}]"
            x += step


def test_extrapolation_is_linear_beyond_the_endpoints():
    points = [(0, 0), (10, 100)]
    spline = build_monotone_cubic_spline(points)
    # with 2 points the spline is exactly the line y = 10x
    assert spline(20) == pytest.approx(200, rel=1e-6)
    assert spline(-10) == pytest.approx(-100, rel=1e-6)


def test_requires_at_least_two_points():
    with pytest.raises(ValueError):
        build_monotone_cubic_spline([(0, 0)])


def test_rejects_duplicate_x_values():
    with pytest.raises(ValueError):
        build_monotone_cubic_spline([(0, 0), (0, 5), (10, 10)])


def test_sample_requires_at_least_two_points_count():
    spline = build_monotone_cubic_spline([(0, 0), (10, 10)])
    with pytest.raises(ValueError):
        spline.sample(1)


def test_sample_endpoints_match_knot_endpoints():
    points = [(0, 5), (10, 50), (20, 30)]
    spline = build_monotone_cubic_spline(points)
    samples = spline.sample(50)
    assert samples[0] == pytest.approx((0, 5))
    assert samples[-1][0] == pytest.approx(20)
    assert samples[-1][1] == pytest.approx(30)
