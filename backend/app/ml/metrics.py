"""Evaluation metrics behind P1's headline numbers (annotation protocol, model card).

Plain Python so the formulas stay readable; tests pin them to scikit-learn and SciPy values.
"""

from collections.abc import Sequence

LEVELS = (1, 2, 3, 4, 5)


def weighted_kappa(a: Sequence[int], b: Sequence[int]) -> float:
    """Quadratic weighted Cohen's κ for two raters on a 1-5 scale.

    κ = 1 - Σ w·observed / Σ w·expected, where w = (i - j)² / (k - 1)²: big disagreements cost
    more, and "expected" is what two raters with these rating habits would agree on by chance.
    """
    if len(a) != len(b) or not a:
        raise ValueError("need two equally long, non-empty rating lists")
    k, n = len(LEVELS), len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        if x not in LEVELS or y not in LEVELS:
            raise ValueError(f"ratings must be 1-5, got {x} and {y}")
        observed[x - 1][y - 1] += 1 / n
    row = [sum(r) for r in observed]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * observed[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * row[i] * col[j] for i in range(k) for j in range(k))
    return 1.0 if den == 0 else 1 - num / den


def ranks(values: Sequence[float]) -> list[float]:
    """Rank values from 1, giving tied values the average of their ranks."""
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for m in range(i, j + 1):
            result[order[m]] = (i + j) / 2 + 1
        i = j + 1
    return result


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman ρ: the Pearson correlation of the ranks (handles ties); 0 if either is constant."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((p - mx) * (q - my) for p, q in zip(rx, ry, strict=True))
    vx = sum((p - mx) ** 2 for p in rx)
    vy = sum((q - my) ** 2 for q in ry)
    return cov / (vx * vy) ** 0.5 if vx and vy else 0.0
