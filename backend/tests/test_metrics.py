import pytest

from app.ml.metrics import ranks, spearman, weighted_kappa

# Reference values from scikit-learn 1.x `cohen_kappa_score(a, b, weights="quadratic",
# labels=[1, 2, 3, 4, 5])` and SciPy `spearmanr(x, y).statistic` on the same inputs.
A = [1, 2, 3, 4, 5, 3, 2, 4, 5, 1, 3, 4]
B = [1, 3, 3, 5, 4, 2, 2, 4, 5, 2, 3, 3]
X = [0.12, 0.40, 0.33, 0.90, 0.75, 0.05, 0.61, 0.40]
Y = [1, 3, 2.5, 5, 4, 1, 3.5, 2.5]


def test_weighted_kappa_matches_scikit_learn() -> None:
    assert weighted_kappa(A, B) == pytest.approx(0.8414096916299559, abs=1e-12)


def test_weighted_kappa_is_one_for_perfect_agreement() -> None:
    assert weighted_kappa(A, A) == pytest.approx(1.0)


def test_weighted_kappa_punishes_big_disagreements_more() -> None:
    small = weighted_kappa([1, 3, 5, 2, 4], [2, 3, 4, 2, 4])  # off by one twice
    big = weighted_kappa([1, 3, 5, 2, 4], [5, 3, 1, 2, 4])  # off by four twice
    assert small > big


def test_weighted_kappa_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        weighted_kappa([1, 2], [1])
    with pytest.raises(ValueError):
        weighted_kappa([], [])
    with pytest.raises(ValueError):
        weighted_kappa([0, 6], [1, 2])


def test_weighted_kappa_when_both_raters_give_one_constant_rating() -> None:
    assert weighted_kappa([3, 3, 3], [3, 3, 3]) == 1.0


def test_ranks_average_ties() -> None:
    assert ranks([10, 20, 20, 5]) == [2.0, 3.5, 3.5, 1.0]


def test_spearman_matches_scipy_with_ties() -> None:
    assert spearman(X, Y) == pytest.approx(0.9757754965005869, abs=1e-12)


def test_spearman_only_depends_on_order() -> None:
    assert spearman([1, 2, 3, 4], [10, 20, 30, 1000]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_of_a_constant_is_zero() -> None:
    assert spearman([1, 1, 1], [1, 2, 3]) == 0.0


def test_spearman_rejects_different_lengths() -> None:
    with pytest.raises(ValueError):
        spearman([1, 2], [1, 2, 3])
