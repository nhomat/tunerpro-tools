import math

import pytest

from tunerpro_tools.data_provenance import DataSource
from tunerpro_tools.engine_model import (
    EngineSpec,
    build_engine_curve,
    ch_to_kw,
    kw_to_ch,
    power_kw_from_torque_nm,
    torque_nm_from_power_kw,
)


def test_power_torque_relationship_is_physically_correct():
    # a well-known real reference point: 300 Nm @ 4000 rpm ~= 125.7 kW
    power = power_kw_from_torque_nm(300, 4000)
    assert power == pytest.approx(125.66, abs=0.05)


def test_torque_from_power_is_the_exact_inverse():
    torque = torque_nm_from_power_kw(150.0, 5500)
    power_back = power_kw_from_torque_nm(torque, 5500)
    assert power_back == pytest.approx(150.0, rel=1e-9)


def test_kw_ch_conversion_roundtrip():
    assert kw_to_ch(ch_to_kw(200.0)) == pytest.approx(200.0, rel=1e-9)
    assert kw_to_ch(100.0) == pytest.approx(135.962, rel=1e-4)


def test_build_engine_curve_requires_minimum_data():
    spec = EngineSpec(peak_torque_nm=300, peak_torque_rpm=4000)  # missing power fields
    with pytest.raises(ValueError, match="peak_power_kw"):
        build_engine_curve(spec)


def test_curve_passes_through_declared_peak_torque_point():
    spec = EngineSpec(
        peak_torque_nm=350.0, peak_torque_rpm=4000,
        peak_power_kw=180.0, peak_power_rpm=6000,
    )
    curve = build_engine_curve(spec)
    assert curve.torque_nm(4000) == pytest.approx(350.0, rel=1e-6)


def test_curve_is_consistent_with_declared_peak_power():
    spec = EngineSpec(
        peak_torque_nm=350.0, peak_torque_rpm=4000,
        peak_power_kw=180.0, peak_power_rpm=6000,
    )
    curve = build_engine_curve(spec)
    # at peak_power_rpm, power computed from the curve's torque must equal
    # the declared peak power exactly, since that point anchors the spline
    assert curve.power_kw(6000) == pytest.approx(180.0, rel=1e-6)


def test_confidence_is_lower_with_estimated_endpoints():
    base_spec = EngineSpec(
        peak_torque_nm=300, peak_torque_rpm=3500,
        peak_power_kw=150, peak_power_rpm=5500,
        sources={"peak_torque_nm": DataSource.USER, "peak_power_kw": DataSource.USER},
    )
    curve_minimal = build_engine_curve(base_spec)

    spec_with_estimates = EngineSpec(
        peak_torque_nm=300, peak_torque_rpm=3500,
        peak_power_kw=150, peak_power_rpm=5500,
        idle_rpm=800, redline_rpm=6500,
        sources={"peak_torque_nm": DataSource.USER, "peak_power_kw": DataSource.USER},
    )
    curve_with_estimates = build_engine_curve(spec_with_estimates)

    # adding idle/redline ESTIMATED points dilutes the average confidence
    assert curve_with_estimates.model_confidence < curve_minimal.model_confidence
    assert curve_minimal.model_confidence == 1.0  # both defining points are USER


def test_confidence_is_zero_with_no_source_declared():
    spec = EngineSpec(peak_torque_nm=300, peak_torque_rpm=3500, peak_power_kw=150, peak_power_rpm=5500)
    curve = build_engine_curve(spec)  # no `sources` given -> DataSource.UNKNOWN for both
    assert curve.model_confidence == 0.0


def test_power_curve_never_produces_nan_or_infinite_values():
    spec = EngineSpec(
        peak_torque_nm=400, peak_torque_rpm=3000,
        peak_power_kw=200, peak_power_rpm=6000,
        idle_rpm=750, redline_rpm=7000,
    )
    curve = build_engine_curve(spec)
    for rpm, torque, power in curve.sample(200):
        assert math.isfinite(torque)
        assert math.isfinite(power)


def test_peak_power_kw_reports_the_actual_curve_maximum():
    spec = EngineSpec(
        peak_torque_nm=400, peak_torque_rpm=3000,
        peak_power_kw=200, peak_power_rpm=6000,
        redline_rpm=6800,
    )
    curve = build_engine_curve(spec)
    rpm_at_peak, power_at_peak = curve.peak_power_kw()
    assert power_at_peak >= curve.power_kw(3000)
    assert power_at_peak >= curve.power_kw(6800)
