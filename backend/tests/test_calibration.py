import pytest

from app.ml.calibration import fit_logistic, fit_percent
from app.ml.metrics import spearman

# Synthetic scores and targets (mean rating rescaled to 0-1). Reference values from SciPy
# `least_squares` on 1 / (1 + exp(-(a + b ln s))) - t, started at (0, 1), tolerances 1e-15.
S = [
    0.004,
    0.011,
    0.015,
    0.019,
    0.024,
    0.028,
    0.033,
    0.041,
    0.047,
    0.052,
    0.061,
    0.073,
    0.088,
    0.104,
]
T = [0.0, 0.125, 0.0, 0.25, 0.125, 0.5, 0.25, 0.375, 0.75, 0.5, 0.625, 0.875, 0.75, 1.0]


def test_fit_matches_scipy_least_squares() -> None:
    a, b = fit_logistic(S, T)
    assert a == pytest.approx(6.9730654106450505, abs=1e-6)
    assert b == pytest.approx(2.19867915657627, abs=1e-6)


def test_fit_is_increasing_so_the_ranking_is_unchanged() -> None:
    a, b = fit_logistic(S, T)
    fitted = [fit_percent(s, a, b) for s in S]
    assert all(x < y for x, y in zip(fitted, fitted[1:], strict=False))
    assert spearman(fitted, T) == pytest.approx(spearman(S, T))


def test_fit_percent_stays_between_zero_and_one() -> None:
    assert fit_percent(0.0, 5.3, 1.7) == pytest.approx(0.0, abs=1e-6)
    assert fit_percent(1.0, 5.3, 1.7) == pytest.approx(0.995, abs=1e-3)
    assert fit_percent(1e9, 5.3, 1.7) == pytest.approx(1.0)
    assert fit_percent(0.04, 0.0, 0.0) == pytest.approx(0.5)


def test_fit_needs_enough_matching_data() -> None:
    with pytest.raises(ValueError):
        fit_logistic([0.1, 0.2], [0.5, 1.0])
    with pytest.raises(ValueError):
        fit_logistic([0.1, 0.2, 0.3], [0.5, 1.0])


def test_fit_stops_when_the_data_cannot_move_it() -> None:
    # Identical scores: the slope is unidentifiable, so the normal equations are singular.
    a, b = fit_logistic([0.05, 0.05, 0.05], [0.2, 0.5, 0.8])
    assert fit_percent(0.05, a, b) == pytest.approx(0.5, abs=1e-6)
