"""Bayesian online changepoint detection (Adams and MacKay 2007) with a normal-gamma prior.

Pure numpy, no data access. Specification: docs/steg2/c4_spec.md section 4 (register G-D, F-D4, F-D5).

Within a segment x ~ N(mu, 1/tau) with (mu, tau) ~ NormalGamma(mu0, kappa0, alpha0, beta0) (beta as rate). Constant
hazard H per period. Run length r_t = number of periods of the current segment before period t (r_t = 0: the
segment starts at t; the first period has r = 0):

    P(r_t = 0, x_1:t)     = H * sum_r P(r_{t-1} = r, x_1:t-1) * pi_prior(x_t)
    P(r_t = r + 1, x_1:t) = (1 - H) * P(r_{t-1} = r, x_1:t-1) * pi(x_t | the segment's earlier values)

A missing value (NaN) inside the series applies only the hazard step (no likelihood, statistics unchanged), so run
lengths count the series' own periods. No truncation of the run length.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import gammaln

HAZARD = {"M": 1 / 36, "Q": 1 / 12, "A": 1 / 3}  # F-D4, per period of the measure's frequency
PRIOR = (0.0, 1.0, 1.0, 1.0)  # mu0, kappa0, alpha0, beta0 (F-D5)
RECENT = 2  # P(r_T <= RECENT)
THRESHOLD = 0.8
QUIET = 3  # no new break for the same series within this many periods of a reported one


def _log_t(x: float, mu, kappa, alpha, beta) -> np.ndarray:
    nu = 2 * alpha
    scale2 = beta * (kappa + 1) / (alpha * kappa)
    return (gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(nu * math.pi * scale2)
            - (nu + 1) / 2 * np.log1p((x - mu) ** 2 / (nu * scale2)))


def run_length_posterior(x, hazard: float, prior=PRIOR) -> np.ndarray:
    """P(r_T = r | x_1..x_T) for r = 0..T-1 at the last period T. x[0] must be finite."""
    x = np.asarray(x, float)
    if len(x) == 0 or not np.isfinite(x[0]):
        raise ValueError("BOCPD needs a finite first value")
    m0, k0, a0, b0 = map(float, prior)
    lh, l1h = math.log(hazard), math.log1p(-hazard)

    def update(mu, kappa, alpha, beta, v):
        return ((kappa * mu + v) / (kappa + 1), kappa + 1, alpha + 0.5, beta + kappa * (v - mu) ** 2 / (2 * (kappa + 1)))

    # t = 1: r = 0 with probability 1; posterior parameters after x_1
    logp = np.array([0.0])
    mu, kappa, alpha, beta = (np.array([v]) for v in update(m0, k0, a0, b0, x[0]))
    for v in x[1:]:
        if np.isfinite(v):
            pred = _log_t(v, mu, kappa, alpha, beta)
            prior_pred = float(_log_t(v, m0, k0, a0, b0))
            grow = logp + l1h + pred
            cp = np.logaddexp.reduce(logp) + lh + prior_pred
            logp = np.concatenate([[cp], grow])
            mu_n, ka_n, al_n, be_n = update(mu, kappa, alpha, beta, v)
            n0 = update(m0, k0, a0, b0, v)
        else:  # missing: hazard step only
            grow = logp + l1h
            cp = np.logaddexp.reduce(logp) + lh
            logp = np.concatenate([[cp], grow])
            mu_n, ka_n, al_n, be_n = mu, kappa, alpha, beta
            n0 = (m0, k0, a0, b0)
        mu, kappa = np.concatenate([[n0[0]], mu_n]), np.concatenate([[n0[1]], ka_n])
        alpha, beta = np.concatenate([[n0[2]], al_n]), np.concatenate([[n0[3]], be_n])
        logp = logp - np.logaddexp.reduce(logp)
    return np.exp(logp)


def p_recent(x, hazard: float, prior=PRIOR, recent: int = RECENT) -> float:
    """P(r_T <= recent | x_1..x_T): the current segment began in one of the last recent + 1 periods."""
    return float(run_length_posterior(x, hazard, prior)[: recent + 1].sum())


def standardize(pace) -> np.ndarray | None:
    """(pace - mean) / SD (ddof = 1) over the finite values of the path; None with < 2 values or SD = 0."""
    v = np.asarray(pace, float)
    f = v[np.isfinite(v)]
    if len(f) < 2:
        return None
    s = float(f.std(ddof=1))
    if not (math.isfinite(s) and s > 0):
        return None
    return (v - f.mean()) / s
