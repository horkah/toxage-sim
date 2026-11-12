"""Performance measures for risk scores. Standard library only."""
import math

import glm


def auc(risks, outcomes):
    """Area under the ROC curve (c-statistic), with ties counted as one half."""
    pairs = sorted(zip(risks, outcomes))
    n_pos = sum(outcomes)
    n_neg = len(outcomes) - n_pos
    if not n_pos or not n_neg:
        return None
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        mid_rank = (i + 1 + j) / 2
        rank_sum += mid_rank * sum(y for _, y in pairs[i:j])
        i = j
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def brier(risks, outcomes):
    return sum((p - y) ** 2 for p, y in zip(risks, outcomes)) / len(risks)


def calibration_slope(risks, outcomes):
    """Slope of a logistic regression of the outcome on the logit of the risk.
    1 means the spread of the risks is right, below 1 means too extreme."""
    if not 0 < sum(outcomes) < len(outcomes):
        return None
    x = [[1.0, math.log(p / (1 - p))] for p in (min(max(r, 1e-9), 1 - 1e-9) for r in risks)]
    return glm.fit(x, list(outcomes))["coefficients"][1]


def calibration_groups(risks, outcomes, groups=10):
    """Mean predicted risk and observed rate in groups of equal size,
    ordered by predicted risk. Returns rows (n, mean risk, observed rate)."""
    pairs = sorted(zip(risks, outcomes))
    rows = []
    for g in range(groups):
        part = pairs[len(pairs) * g // groups: len(pairs) * (g + 1) // groups]
        if part:
            rows.append((
                len(part),
                sum(p for p, _ in part) / len(part),
                sum(y for _, y in part) / len(part),
            ))
    return rows


def summary(risks, outcomes):
    outcomes = [int(y) for y in outcomes]
    observed = sum(outcomes) / len(outcomes)
    expected = sum(risks) / len(risks)
    return {
        "n": len(outcomes),
        "events": sum(outcomes),
        "observed_rate": observed,
        "mean_risk": expected,
        "observed_to_expected": observed / expected if expected else None,
        "auc": auc(risks, outcomes),
        "brier": brier(risks, outcomes),
        "calibration_slope": calibration_slope(risks, outcomes),
    }
