import math

from tunerpro_tools.lambda_afr import (
    FUEL_PROFILES,
    afr_to_lambda,
    common_conversion_table,
    lambda_to_afr,
)


def test_gasoline_stoichiometric_roundtrip():
    afr = lambda_to_afr(1.0, "gasoline")
    assert math.isclose(afr, 14.7)
    assert math.isclose(afr_to_lambda(afr, "gasoline"), 1.0)


def test_e85_stoichiometric_afr():
    assert math.isclose(lambda_to_afr(1.0, "e85"), 9.8)


def test_all_fuel_profiles_roundtrip():
    for key in FUEL_PROFILES:
        lam = afr_to_lambda(lambda_to_afr(1.1, key), key)
        assert math.isclose(lam, 1.1, rel_tol=1e-9)


def test_common_conversion_table_has_stoichiometric_row():
    table = common_conversion_table("gasoline")
    lambdas = [row[0] for row in table]
    assert 1.00 in lambdas
