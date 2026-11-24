"""Two-state Markov switching in mean and variance without AR terms, MSIH(2)-AR(0), estimated by EM.

Pure numpy, no data access. Specification: docs/steg2/c4_spec.md section 2 (register G-D, F-D1, F-D3).

    y_t = mu_{S_t} + sigma_{S_t} eps_t,   eps_t ~ N(0, 1),   S_t a Markov chain with free transition matrix P
    P(S_1 = j) = 0.5 (fixed, not estimated)

EM (Baum-Welch): Hamilton filter forward, Kim smoother backward, closed-form M-step. Start: mu = mean -/+ SD,
sigma^2 = SD^2, p_00 = p_11 = 0.95. Variance floor 0.01 x SD^2. After convergence the state with the lower mean is
labelled slowdown ("inbromsning") and put first. `filtered[:, 0]` is P(slowdown at t | y_1..y_t).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Technical choices (docs/steg2/c4_spec.md section 2). Changing one is a new method family.
P_START = 0.95
VAR_FLOOR = 0.01  # x sample variance
TOL = 1e-8  # |dlogL| < TOL * (1 + |logL|)
MAX_ITER = 1000
INIT = np.array([0.5, 0.5])
LOG2PI = math.log(2 * math.pi)


@dataclass
class Result:
    mu: np.ndarray  # (2,) state 0 = slowdown (lower mean), state 1 = expansion
    sigma2: np.ndarray  # (2,)
    P: np.ndarray  # (2, 2) P[i, j] = P(S_t = j | S_{t-1} = i)
    filtered: np.ndarray  # (T, 2)
    smoothed: np.ndarray  # (T, 2)
    loglik: float
    n_iter: int
    converged: bool
    history: list = field(default_factory=list)

    @property
    def p_slow(self) -> float:
        """Filtered P(slowdown) at the last month (the real-time value of F-D1)."""
        return float(self.filtered[-1, 0])


def _log_dens(y: np.ndarray, mu: np.ndarray, s2: np.ndarray) -> np.ndarray:
    return -0.5 * (LOG2PI + np.log(s2)[None, :] + (y[:, None] - mu[None, :]) ** 2 / s2[None, :])


def filter_smooth(y: np.ndarray, mu, s2, P, init=INIT):
    """Hamilton filter and Kim smoother. Returns filtered (T,2), predicted (T,2), smoothed (T,2), xi (T-1,2,2), logL."""
    y = np.asarray(y, float)
    T = len(y)
    ld = _log_dens(y, np.asarray(mu, float), np.asarray(s2, float))
    filt = np.empty((T, 2))
    pred = np.empty((T, 2))
    loglik = 0.0
    p = np.asarray(init, float)
    for t in range(T):
        pred[t] = p
        m = ld[t].max()
        w = p * np.exp(ld[t] - m)
        c = w.sum()
        loglik += math.log(c) + m
        filt[t] = w / c
        p = filt[t] @ P
    sm = np.empty((T, 2))
    sm[-1] = filt[-1]
    xi = np.empty((max(T - 1, 0), 2, 2))
    for t in range(T - 2, -1, -1):
        ratio = np.where(pred[t + 1] > 0, sm[t + 1] / np.maximum(pred[t + 1], 1e-300), 0.0)
        x = filt[t][:, None] * P * ratio[None, :]
        xi[t] = x
        sm[t] = x.sum(axis=1)
    return filt, pred, sm, xi, loglik


def fit(y, tol: float = TOL, max_iter: int = MAX_ITER) -> Result:
    y = np.asarray(y, float)
    if len(y) < 3 or not np.isfinite(y).all():
        raise ValueError("MS fit needs at least 3 finite values")
    ybar, s = float(y.mean()), float(y.std(ddof=1))
    if not s > 0:
        raise ValueError("MS fit needs a positive standard deviation")
    floor = VAR_FLOOR * s * s
    mu = np.array([ybar - s, ybar + s])
    s2 = np.array([s * s, s * s])
    P = np.array([[P_START, 1 - P_START], [1 - P_START, P_START]])
    hist, converged, old = [], False, None
    for it in range(1, max_iter + 1):
        filt, _pred, sm, xi, ll = filter_smooth(y, mu, s2, P)
        hist.append(ll)
        if old is not None and abs(ll - old) < tol * (1 + abs(ll)):
            converged = True
            break
        old = ll
        g = sm.sum(axis=0)
        mu = (sm * y[:, None]).sum(axis=0) / g
        s2 = np.maximum((sm * (y[:, None] - mu[None, :]) ** 2).sum(axis=0) / g, floor)
        num = xi.sum(axis=0)
        den = sm[:-1].sum(axis=0)
        P = np.where(den[:, None] > 0, num / np.maximum(den[:, None], 1e-300), 0.5)
        P = P / P.sum(axis=1, keepdims=True)
    filt, _pred, sm, _xi, ll = filter_smooth(y, mu, s2, P)
    order = np.argsort(mu, kind="stable")  # labelling rule: lower mean = slowdown, first
    return Result(mu[order], s2[order], P[np.ix_(order, order)], filt[:, order], sm[:, order], float(ll), it,
                  converged, hist)


def simulate(T: int, mu, sigma, P, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    P = np.asarray(P, float)
    s = np.empty(T, int)
    s[0] = rng.integers(2)
    for t in range(1, T):
        s[t] = rng.choice(2, p=P[s[t - 1]])
    y = np.asarray(mu, float)[s] + np.asarray(sigma, float)[s] * rng.standard_normal(T)
    return y, s
