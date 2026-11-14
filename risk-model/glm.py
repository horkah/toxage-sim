"""Binomial regression for refitting the models on data.

Fisher scoring (iteratively reweighted least squares) with a logit or a
complementary log-log link. The complementary log-log link gives the
proportional hazards form 1 - (1 - r0)^HR of candidate 2, with
coefficients equal to log hazard ratios. Standard library only.
"""
import math

_EPS = 1e-10


def _inverse_link(eta, link):
    """Return mean and its derivative by eta."""
    if link == "logit":
        eta = max(min(eta, 35), -35)
        mu = 1 / (1 + math.exp(-eta))
        return mu, mu * (1 - mu)
    if link == "cloglog":
        eta = min(eta, 3.5)
        e = math.exp(eta)
        return 1 - math.exp(-e), e * math.exp(-e)
    raise ValueError(f"unknown link: {link}")


def solve(a, b):
    """Solve a x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            raise ValueError("singular matrix: a predictor has no variation in the data")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def inverse(a):
    """Inverse of a square matrix, column by column with solve()."""
    n = len(a)
    columns = [solve(a, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[columns[j][i] for j in range(n)] for i in range(n)]


def fit(x, y, link="logit", offset=None, start=None, max_iter=50, tol=1e-9):
    """Fit a binomial regression.

    x: rows of predictor values (include a column of ones for an intercept).
    y: outcomes, 0 or 1.
    start: starting coefficients, zero by default.
    Returns dict with coefficients, standard errors, the number of iterations
    and whether the fit converged within max_iter rounds.
    """
    n, k = len(x), len(x[0])
    offset = offset or [0.0] * n
    beta = list(start) if start else [0.0] * k
    converged = False
    for iteration in range(1, max_iter + 1):
        xtwx = [[0.0] * k for _ in range(k)]
        xtwz = [0.0] * k
        for row, yi, oi in zip(x, y, offset):
            eta = sum(b * v for b, v in zip(beta, row)) + oi
            mu, d = _inverse_link(eta, link)
            mu = min(max(mu, _EPS), 1 - _EPS)
            d = max(d, _EPS)
            # Weight and working response of iteratively reweighted least squares.
            w = d * d / (mu * (1 - mu))
            z = eta - oi + (yi - mu) / d
            for i in range(k):
                if row[i]:
                    wi = w * row[i]
                    xtwz[i] += wi * z
                    xi = xtwx[i]
                    for j in range(i, k):
                        if row[j]:
                            xi[j] += wi * row[j]
        for i in range(k):
            for j in range(i):
                xtwx[i][j] = xtwx[j][i]
        new = solve(xtwx, xtwz)
        change = max(abs(a - b) for a, b in zip(new, beta))
        beta = new
        if change < tol:
            converged = True
            break
    cov = inverse(xtwx)
    return {
        "coefficients": beta,
        "standard_errors": [math.sqrt(max(cov[i][i], 0.0)) for i in range(k)],
        "iterations": iteration,
        "converged": converged,     # False: the coefficients are those of the last round
    }
