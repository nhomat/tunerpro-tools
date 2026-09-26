import math

import pytest

from tunerpro_tools.transmission_model import (
    Gear,
    TransmissionSpec,
    engine_rpm_for_speed,
    speed_for_engine_rpm,
    traction_force_n,
    wheel_torque_nm,
)


def _spec() -> TransmissionSpec:
    return TransmissionSpec(
        gears=[Gear(ratio=3.5, efficiency=0.95), Gear(ratio=2.1, efficiency=0.95)],
        final_drive_ratio=3.9,
        wheel_radius_m=0.3,
    )


def test_speed_and_rpm_are_exact_inverses():
    transmission = _spec()
    rpm = 4000
    speed = speed_for_engine_rpm(rpm, 0, transmission)
    rpm_back = engine_rpm_for_speed(speed, 0, transmission)
    assert rpm_back == pytest.approx(rpm, rel=1e-9)


def test_higher_gear_ratio_means_lower_speed_at_same_rpm():
    transmission = _spec()
    speed_gear0 = speed_for_engine_rpm(4000, 0, transmission)  # ratio 3.5 (lower gear)
    speed_gear1 = speed_for_engine_rpm(4000, 1, transmission)  # ratio 2.1 (higher gear)
    assert speed_gear1 > speed_gear0


def test_wheel_torque_multiplies_by_gear_and_final_drive_and_efficiency():
    transmission = TransmissionSpec(
        gears=[Gear(ratio=3.0, efficiency=0.9)], final_drive_ratio=4.0, wheel_radius_m=0.3
    )
    torque = wheel_torque_nm(100.0, 0, transmission)
    assert torque == pytest.approx(100.0 * 3.0 * 4.0 * 0.9)


def test_traction_force_is_torque_over_radius():
    transmission = _spec()
    force = traction_force_n(300.0, 0, transmission)
    assert force == pytest.approx(300.0 / 0.3)


def test_per_gear_wheel_radius_override():
    transmission = TransmissionSpec(
        gears=[Gear(ratio=3.0, wheel_radius_m=0.35)], final_drive_ratio=4.0, wheel_radius_m=0.3
    )
    assert transmission.wheel_radius_for(0) == 0.35


def test_rejects_invalid_gear_ratio():
    with pytest.raises(ValueError):
        Gear(ratio=0)


def test_rejects_invalid_efficiency():
    with pytest.raises(ValueError):
        Gear(ratio=3.0, efficiency=1.5)


def test_rejects_empty_gear_list():
    with pytest.raises(ValueError):
        TransmissionSpec(gears=[], final_drive_ratio=4.0, wheel_radius_m=0.3)
