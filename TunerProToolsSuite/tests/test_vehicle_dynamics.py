import pytest

from tunerpro_tools.vehicle_dynamics import (
    VehicleSpec,
    acceleration_ms2,
    aerodynamic_drag_force_n,
    grade_force_n,
    rolling_resistance_force_n,
    total_resistance_force_n,
)


def _spec(**overrides) -> VehicleSpec:
    defaults = dict(mass_kg=1500, drag_coefficient=0.30, frontal_area_m2=2.2)
    defaults.update(overrides)
    return VehicleSpec(**defaults)


def test_drag_force_scales_with_velocity_squared():
    vehicle = _spec()
    f1 = aerodynamic_drag_force_n(10.0, vehicle)
    f2 = aerodynamic_drag_force_n(20.0, vehicle)
    assert f2 == pytest.approx(f1 * 4, rel=1e-9)


def test_drag_force_matches_known_formula():
    vehicle = _spec(drag_coefficient=0.3, frontal_area_m2=2.0, air_density_kg_m3=1.225)
    force = aerodynamic_drag_force_n(30.0, vehicle)  # ~108 km/h
    expected = 0.5 * 1.225 * 0.3 * 2.0 * 30.0 ** 2
    assert force == pytest.approx(expected)


def test_rolling_resistance_independent_of_speed():
    vehicle = _spec()
    assert rolling_resistance_force_n(vehicle) == pytest.approx(0.015 * 1500 * 9.81)


def test_grade_force_zero_on_flat_ground():
    vehicle = _spec()
    assert grade_force_n(vehicle, 0.0) == pytest.approx(0.0, abs=1e-9)


def test_grade_force_positive_uphill():
    vehicle = _spec()
    assert grade_force_n(vehicle, 10.0) > 0  # a 10% grade opposes forward motion


def test_total_resistance_is_the_sum_of_components():
    vehicle = _spec()
    speed = 25.0
    total = total_resistance_force_n(speed, vehicle, grade_percent=5.0)
    expected = (
        aerodynamic_drag_force_n(speed, vehicle)
        + rolling_resistance_force_n(vehicle)
        + grade_force_n(vehicle, 5.0)
    )
    assert total == pytest.approx(expected)


def test_acceleration_is_force_over_mass():
    vehicle = _spec(mass_kg=1000)
    assert acceleration_ms2(2000.0, vehicle) == pytest.approx(2.0)


def test_rejects_non_positive_mass():
    with pytest.raises(ValueError):
        _spec(mass_kg=0)


def test_rejects_non_positive_drag_coefficient():
    with pytest.raises(ValueError):
        _spec(drag_coefficient=0)
