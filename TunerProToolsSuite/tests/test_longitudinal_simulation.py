import math

import pytest

from tunerpro_tools.engine_model import EngineSpec, build_engine_curve
from tunerpro_tools.longitudinal_simulation import simulate_acceleration, theoretical_top_speed_kmh
from tunerpro_tools.transmission_model import Gear, TransmissionSpec
from tunerpro_tools.vehicle_dynamics import VehicleSpec


def _engine(peak_power_kw: float = 110.0) -> "EngineCurve":
    spec = EngineSpec(
        peak_torque_nm=200.0, peak_torque_rpm=4000,
        peak_power_kw=peak_power_kw, peak_power_rpm=6000,
        idle_rpm=900, redline_rpm=6800,
    )
    return build_engine_curve(spec)


def _transmission() -> TransmissionSpec:
    return TransmissionSpec(
        gears=[
            Gear(ratio=3.5, efficiency=0.95),
            Gear(ratio=2.1, efficiency=0.96),
            Gear(ratio=1.4, efficiency=0.97),
            Gear(ratio=1.0, efficiency=0.97),
            Gear(ratio=0.8, efficiency=0.96),
        ],
        final_drive_ratio=4.1,
        wheel_radius_m=0.31,
    )


def _vehicle(mass_kg: float = 1300.0) -> VehicleSpec:
    return VehicleSpec(mass_kg=mass_kg, drag_coefficient=0.32, frontal_area_m2=2.2)


def test_simulation_never_produces_nan_or_infinite_values():
    result = simulate_acceleration(_engine(), _transmission(), _vehicle())
    for sample in result.samples:
        assert math.isfinite(sample.speed_ms)
        assert math.isfinite(sample.rpm)
        assert math.isfinite(sample.acceleration_ms2)
        assert math.isfinite(sample.engine_torque_nm)
        assert math.isfinite(sample.engine_power_kw)


def test_vehicle_accelerates_from_rest():
    result = simulate_acceleration(_engine(), _transmission(), _vehicle())
    assert len(result.samples) > 10
    assert result.samples[-1].speed_ms > result.samples[0].speed_ms


def test_gear_upshifts_occur_over_a_full_run():
    result = simulate_acceleration(_engine(), _transmission(), _vehicle(), max_time_s=30.0, max_speed_kmh=250)
    gears_used = {s.gear_index for s in result.samples}
    assert len(gears_used) > 1, "expected at least one upshift over a long run"
    # gear index must never decrease (no downshifts in this simple strategy)
    indices = [s.gear_index for s in result.samples]
    assert all(b >= a for a, b in zip(indices, indices[1:]))


def test_more_power_reaches_100kmh_faster_for_same_vehicle():
    transmission = _transmission()
    vehicle = _vehicle()
    slow = simulate_acceleration(_engine(peak_power_kw=90.0), transmission, vehicle, max_time_s=40.0)
    fast = simulate_acceleration(_engine(peak_power_kw=200.0), transmission, vehicle, max_time_s=40.0)

    t_slow = slow.time_to_speed_kmh(100.0)
    t_fast = fast.time_to_speed_kmh(100.0)
    assert t_slow is not None and t_fast is not None
    assert t_fast < t_slow


def test_more_mass_slows_acceleration_for_same_engine():
    engine = _engine()
    transmission = _transmission()
    light = simulate_acceleration(engine, transmission, _vehicle(mass_kg=1000.0), max_time_s=40.0)
    heavy = simulate_acceleration(engine, transmission, _vehicle(mass_kg=2200.0), max_time_s=40.0)

    t_light = light.time_to_speed_kmh(100.0)
    t_heavy = heavy.time_to_speed_kmh(100.0)
    assert t_light is not None and t_heavy is not None
    assert t_light < t_heavy


def test_time_to_speed_returns_none_when_never_reached():
    result = simulate_acceleration(_engine(peak_power_kw=110.0), _transmission(), _vehicle(), max_time_s=2.0)
    # 2 seconds is nowhere near enough to reach 300 km/h
    assert result.time_to_speed_kmh(300.0) is None


def test_time_between_speeds_is_consistent_with_individual_lookups():
    result = simulate_acceleration(_engine(), _transmission(), _vehicle(), max_time_s=40.0)
    t0 = result.time_to_speed_kmh(50.0)
    t1 = result.time_to_speed_kmh(100.0)
    interval = result.time_between_speeds_kmh(50.0, 100.0)
    assert interval == pytest.approx(t1 - t0)


def test_theoretical_top_speed_is_plausible_for_a_realistic_car():
    top_speed, note = theoretical_top_speed_kmh(_engine(), _transmission(), _vehicle())
    assert top_speed is not None
    assert 100.0 < top_speed < 280.0  # sanity bounds for a ~110kW small car
    assert isinstance(note, str) and note


def test_theoretical_top_speed_is_none_when_vehicle_cannot_move():
    # absurdly high drag / rolling resistance: no RPM in range beats resistance
    impossible_vehicle = VehicleSpec(
        mass_kg=1300, drag_coefficient=0.32, frontal_area_m2=2.2,
        rolling_resistance_coefficient=50.0,  # wildly unrealistic on purpose
    )
    top_speed, note = theoretical_top_speed_kmh(_engine(), _transmission(), impossible_vehicle)
    assert top_speed is None
    assert "indetermin" in note.lower()


def test_higher_power_increases_theoretical_top_speed():
    transmission = _transmission()
    vehicle = _vehicle()
    low_top, _ = theoretical_top_speed_kmh(_engine(peak_power_kw=90.0), transmission, vehicle)
    high_top, _ = theoretical_top_speed_kmh(_engine(peak_power_kw=250.0), transmission, vehicle)
    assert high_top > low_top


def test_rejects_non_positive_dt():
    with pytest.raises(ValueError):
        simulate_acceleration(_engine(), _transmission(), _vehicle(), dt_s=0)
