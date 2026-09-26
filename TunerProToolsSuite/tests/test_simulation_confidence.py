from tunerpro_tools.data_provenance import DataSource
from tunerpro_tools.simulation_confidence import REQUIRED_FIELDS, compute_confidence_report


def test_all_fields_known_gives_full_confidence():
    sources = {name: DataSource.USER for name in REQUIRED_FIELDS}
    report = compute_confidence_report(sources)
    assert report.confidence == 1.0
    assert report.confidence_percent == 100.0
    assert report.limitations == ()


def test_all_fields_unknown_gives_zero_confidence():
    report = compute_confidence_report({})
    assert report.confidence == 0.0
    assert len(report.limitations) == len(REQUIRED_FIELDS)


def test_missing_field_is_treated_as_unknown_not_silently_fine():
    sources = {name: DataSource.USER for name in REQUIRED_FIELDS}
    del sources["vehicle.mass_kg"]
    report = compute_confidence_report(sources)
    assert report.confidence < 1.0
    assert any("vehicle.mass_kg" in note for note in report.limitations)


def test_estimated_fields_reduce_confidence_but_less_than_unknown():
    sources_estimated = {name: DataSource.USER for name in REQUIRED_FIELDS}
    sources_estimated["vehicle.rolling_resistance_coefficient"] = DataSource.ESTIMATED

    sources_unknown = {name: DataSource.USER for name in REQUIRED_FIELDS}
    del sources_unknown["vehicle.rolling_resistance_coefficient"]

    report_estimated = compute_confidence_report(sources_estimated)
    report_unknown = compute_confidence_report(sources_unknown)
    assert report_estimated.confidence > report_unknown.confidence
    assert report_estimated.confidence < 1.0


def test_limitations_text_names_the_concrete_impact():
    sources = {name: DataSource.USER for name in REQUIRED_FIELDS}
    sources["engine.peak_power_kw"] = DataSource.UNKNOWN
    report = compute_confidence_report(sources)
    matching = [note for note in report.limitations if "engine.peak_power_kw" in note]
    assert matching
    assert "puissance" in matching[0].lower()


def test_confidence_never_exceeds_bounds():
    sources = {name: DataSource.BIN for name in REQUIRED_FIELDS}
    report = compute_confidence_report(sources)
    assert 0.0 <= report.confidence <= 1.0
