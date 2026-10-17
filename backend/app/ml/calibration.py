"""Turn the raw TF-IDF similarity into an estimated fit from 0 to 100% (J2 ratings).

A raw cosine like 0.043 means little to a reader. We map it to **how we'd likely rate the pair**:
a logistic curve in log(score), fitted by least squares to our mean ratings rescaled to 0–1
(rating 1 → 0%, rating 5 → 100%):

    fit(score) = 1 / (1 + exp(-(a + b · ln score)))

The curve is strictly increasing (b > 0), so pairs keep their order and Spearman ρ is unchanged:
it changes how the score reads, not how well it ranks. It is fitted on the dev pairs only, and the
test pairs check how far its estimates land from our ratings.

Plain Python, so `scripts/j2-pairs/evaluate.py` can use it without dependencies; tests pin the fit
to values computed with SciPy's `least_squares`.
"""

import math
from collections.abc import Sequence

MIN_SCORE = 1e-6  # log(0) is undefined; a zero similarity reads as the lowest fit


def fit_percent(score: float, a: float, b: float) -> float:
    """The estimated fit, from 0 to 1, of a raw similarity under the curve (a, b)."""
    z = a + b * math.log(max(score, MIN_SCORE))
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def fit_logistic(
    scores: Sequence[float], targets: Sequence[float], iterations: int = 200
) -> tuple[float, float]:
    """Least-squares (a, b) for `fit_percent` against targets in [0, 1] (Levenberg–Marquardt)."""
    if len(scores) != len(targets) or len(scores) < 3:
        raise ValueError("need at least 3 (score, target) pairs of equal length")
    xs = [math.log(max(s, MIN_SCORE)) for s in scores]

    def loss(a: float, b: float) -> float:
        return sum(
            (fit_percent(math.exp(x), a, b) - t) ** 2 for x, t in zip(xs, targets, strict=True)
        )

    a, b, damping = 0.0, 1.0, 1e-3
    current = loss(a, b)
    for _ in range(iterations):
        # Normal equations of the linearised problem: J^T J and J^T r for the residuals r.
        jaa = jab = jbb = ga = gb = 0.0
        for x, t in zip(xs, targets, strict=True):
            p = fit_percent(math.exp(x), a, b)
            d = p * (1 - p)  # derivative of the logistic
            r = p - t
            jaa += d * d
            jab += d * d * x
            jbb += d * d * x * x
            ga += d * r
            gb += d * r * x
        # Damping keeps the system solvable: by Cauchy–Schwarz jab² ≤ jaa·jbb, so det > 0.
        m_aa, m_bb = jaa * (1 + damping), jbb * (1 + damping)
        det = m_aa * m_bb - jab * jab
        step_a = (m_bb * ga - jab * gb) / det
        step_b = (m_aa * gb - jab * ga) / det
        trial = loss(a - step_a, b - step_b)
        if trial <= current:
            a, b, current, damping = a - step_a, b - step_b, trial, damping / 10
            if abs(step_a) < 1e-12 and abs(step_b) < 1e-12:
                break
        else:
            damping *= 10  # the step overshot: lean towards gradient descent
    return a, b
