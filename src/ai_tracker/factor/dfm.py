"""One-factor mixed-frequency dynamic factor model with missing data: Kalman filter, RTS smoother and EM.

Pure numpy, no data access. Specification: docs/steg2/c3_spec.md (fixed before the first real-data run).

Model for one block, months t = 1..T, series i = 1..N (z-scores, NaN = not observed):

    z_it = lambda_i * h_i' s_t + e_it,      e_it ~ N(0, R_i), independent (white noise)
    s_t  = (f_t, f_{t-1}, f_{t-2})'
    f_t  = a * f_{t-1} + u_t,               u_t ~ N(0, 1)   (innovation variance fixed at 1: scale normalisation)

h_i = (1, 0, 0) for a monthly series and for a quarterly stock or share (observed in the quarter's last month),
h_i = (1/3, 1/3, 1/3) for a quarterly flow observed in the quarter's last month (F-B20: the quarter's year-on-year
rate is the mean of the three monthly year-on-year rates). s_0 ~ N(0, stationary covariance of the AR(1)).

Because R is diagonal and there are only two observation vectors h, the filter works in information form with 3x3
matrices only: M_t = P_pred^-1 + sum_i (lambda_i^2 / R_i) h_i h_i'. The log-likelihood uses the Woodbury identity and
the matrix determinant lemma. Missing observations simply drop out of the sums (ragged edge).

EM (Shumway-Stoffer; Banbura-Modugno 2014 for missing data): E-step = smoother; M-step closed form for lambda_i, R_i
and a (the state contains f_{t-1}, so E[f_t f_{t-1}] is an element of the smoothed state covariance).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

MONTHLY, FLOW, STOCK = "M", "QF", "QS"  # observation types
H = {MONTHLY: np.array([1.0, 0.0, 0.0]), STOCK: np.array([1.0, 0.0, 0.0]), FLOW: np.full(3, 1.0 / 3.0)}

# Technical choices (docs/steg2/c3_spec.md, section 5). Changing one is a new method family.
R_FLOOR = 0.01  # lower bound for an idiosyncratic variance (z units)
A_MAX = 0.99  # |a| is clipped to this (stationarity)
TOL = 1e-4  # EM stops when |dlogL| / mean(|logL_new|, |logL_old|) < TOL
MAX_ITER = 200
LOG2PI = math.log(2 * math.pi)


@dataclass
class Params:
    lam: np.ndarray  # (N,)
    R: np.ndarray  # (N,)
    a: float


@dataclass
class Result:
    params: Params
    f: np.ndarray  # (T,) smoothed factor E[f_t | all data]
    f_var: np.ndarray  # (T,) smoothed variance
    f_filt: np.ndarray  # (T,) filtered factor E[f_t | data up to t]
    loglik: float
    n_iter: int
    converged: bool
    history: list = field(default_factory=list)  # log-likelihood per iteration


def transition(a: float) -> np.ndarray:
    return np.array([[a, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def stationary_cov(a: float) -> np.ndarray:
    """Cov(f_t, f_{t-k}) = a^k / (1 - a^2) for the 3-vector (f_t, f_{t-1}, f_{t-2})."""
    v = 1.0 / (1.0 - a * a)
    return np.array([[v * a ** abs(i - j) for j in range(3)] for i in range(3)])


def _obs_stats(z: np.ndarray, kinds: list[str], lam: np.ndarray, R: np.ndarray):
    """Per month: C_t = H'R^-1 H (3x3), b_t = H'R^-1 z (3), q_t = z'R^-1 z, logdetR_t, n_t (observed count)."""
    obs = np.isfinite(z)
    zz = np.where(obs, z, 0.0)
    T = z.shape[0]
    C = np.zeros((T, 3, 3))
    b = np.zeros((T, 3))
    for kind in (MONTHLY, STOCK, FLOW):
        idx = [i for i, k in enumerate(kinds) if k == kind]
        if not idx:
            continue
        h = H[kind]
        w = obs[:, idx] * (lam[idx] ** 2 / R[idx])  # (T, n_k)
        C += w.sum(axis=1)[:, None, None] * np.outer(h, h)[None]
        b += (zz[:, idx] * lam[idx] / R[idx]).sum(axis=1)[:, None] * h[None]
    q = (zz ** 2 / R).sum(axis=1)
    logdetR = (obs * np.log(R)).sum(axis=1)
    n = obs.sum(axis=1)
    return C, b, q, logdetR, n


def smoother(z: np.ndarray, kinds: list[str], p: Params):
    """Kalman filter + RTS smoother. Returns (x_s (T,3), P_s (T,3,3), x_f (T,3), loglik)."""
    T = z.shape[0]
    A = transition(p.a)
    Qm = np.zeros((3, 3))
    Qm[0, 0] = 1.0
    C, b, q, logdetR, n = _obs_stats(z, kinds, p.lam, p.R)
    x = np.zeros(3)
    P = stationary_cov(p.a)
    xp = np.zeros((T, 3))
    Pp = np.zeros((T, 3, 3))
    xf = np.zeros((T, 3))
    Pf = np.zeros((T, 3, 3))
    ll = 0.0
    for t in range(T):
        x_pred = A @ x
        P_pred = A @ P @ A.T + Qm
        xp[t], Pp[t] = x_pred, P_pred
        if n[t] == 0:
            x, P = x_pred, P_pred
        else:
            info = np.linalg.inv(P_pred)
            M = info + C[t]
            Minv = np.linalg.inv(M)
            Minv = 0.5 * (Minv + Minv.T)
            x = Minv @ (info @ x_pred + b[t])
            P = Minv
            # innovation v = z - H x_pred; v'S^-1 v = v'R^-1 v - g' M^-1 g, g = H'R^-1 v
            g = b[t] - C[t] @ x_pred
            vRv = q[t] - 2 * x_pred @ b[t] + x_pred @ C[t] @ x_pred
            quad = vRv - g @ Minv @ g
            logdetS = logdetR[t] + np.linalg.slogdet(P_pred)[1] + np.linalg.slogdet(M)[1]
            ll += -0.5 * (n[t] * LOG2PI + logdetS + quad)
        xf[t], Pf[t] = x, P
    xs = np.zeros((T, 3))
    Ps = np.zeros((T, 3, 3))
    xs[-1], Ps[-1] = xf[-1], Pf[-1]
    for t in range(T - 2, -1, -1):
        J = Pf[t] @ A.T @ np.linalg.inv(Pp[t + 1])
        xs[t] = xf[t] + J @ (xs[t + 1] - xp[t + 1])
        Ps[t] = Pf[t] + J @ (Ps[t + 1] - Pp[t + 1]) @ J.T
    return xs, Ps, xf, float(ll)


def initial_params(z: np.ndarray, kinds: list[str]) -> Params:
    """Deterministic start (spec section 5): f0 = cross-sectional mean of the observed z per month (a quarterly value
    counts in all three months of its quarter), linearly interpolated over months without data and held constant
    before the first and after the last; rescaled so that the AR(1) fit of f0 has unit innovation SD; lambda_i = OLS
    of z_i on h_i' s0 (no constant), R_i = residual variance (floored), a = OLS of f0_t on f0_{t-1} (clipped)."""
    T, N = z.shape
    spread = np.full_like(z, np.nan)
    for i, k in enumerate(kinds):
        col = z[:, i]
        if k == MONTHLY:
            spread[:, i] = col
        else:
            for t in np.flatnonzero(np.isfinite(col)):
                spread[max(t - 2, 0): t + 1, i] = col[t]
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(spread).sum(axis=1)
        f0 = np.where(cnt > 0, np.nansum(spread, axis=1) / np.maximum(cnt, 1), np.nan)
    ok = np.flatnonzero(np.isfinite(f0))
    if len(ok) == 0:
        f0 = np.zeros(T)
    else:
        f0 = np.interp(np.arange(T), ok, f0[ok])
    a = _ar1(f0)
    resid = f0[1:] - a * f0[:-1]
    sd = float(np.std(resid)) if len(resid) > 1 else 1.0
    f0 = f0 / sd if sd > 1e-8 else f0
    s0 = np.column_stack([f0, np.r_[f0[0], f0[:-1]], np.r_[f0[0], f0[0], f0[:-2]] if T > 1 else f0])
    lam = np.zeros(N)
    R = np.ones(N)
    for i, k in enumerate(kinds):
        o = np.isfinite(z[:, i])
        x = s0[o] @ H[k]
        y = z[o, i]
        den = float(x @ x)
        lam[i] = float(x @ y) / den if den > 1e-12 else 0.0
        R[i] = max(float(np.mean((y - lam[i] * x) ** 2)) if o.any() else 1.0, R_FLOOR)
    return Params(lam, R, a)


def _ar1(f: np.ndarray) -> float:
    if len(f) < 3:
        return 0.0
    den = float(f[:-1] @ f[:-1])
    a = float(f[1:] @ f[:-1]) / den if den > 1e-12 else 0.0
    return float(np.clip(a, -A_MAX, A_MAX))


def m_step(z: np.ndarray, kinds: list[str], xs: np.ndarray, Ps: np.ndarray, p: Params) -> Params:
    obs = np.isfinite(z)
    Ess = Ps + np.einsum("ti,tj->tij", xs, xs)  # E[s_t s_t']
    lam = p.lam.copy()
    R = p.R.copy()
    for i, k in enumerate(kinds):
        o = obs[:, i]
        if not o.any():
            continue
        h = H[k]
        hx = xs[o] @ h
        hEh = np.einsum("i,tij,j->t", h, Ess[o], h)
        y = z[o, i]
        den = float(hEh.sum())
        lam[i] = float(y @ hx) / den if den > 1e-12 else 0.0
        R[i] = max(float(np.mean(y * y - 2 * lam[i] * y * hx + lam[i] ** 2 * hEh)), R_FLOOR)
    # a: sum_t E[f_t f_{t-1}] / sum_t E[f_{t-1}^2], t = 1..T (f_{t-1} is element 1 of s_t)
    num, den = float(Ess[:, 0, 1].sum()), float(Ess[:, 1, 1].sum())
    a = float(np.clip(num / den, -A_MAX, A_MAX)) if den > 1e-12 else 0.0
    return Params(lam, R, a)


def fit(z: np.ndarray, kinds: list[str], tol: float = TOL, max_iter: int = MAX_ITER) -> Result:
    """EM from the deterministic start until the relative log-likelihood change is below `tol` (or `max_iter`).
    Sign: the factor is flipped so that the sum of the loadings is positive."""
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or z.shape[1] != len(kinds):
        raise ValueError("z must be (T, N) with one kind per column")
    p = initial_params(z, kinds)
    history, converged, it = [], False, 0
    old = -np.inf
    for it in range(1, max_iter + 1):
        xs, Ps, _xf, ll = smoother(z, kinds, p)
        history.append(ll)
        if np.isfinite(old) and abs(ll - old) / max((abs(ll) + abs(old)) / 2, 1e-12) < tol:
            converged = True
            break
        old = ll
        p = m_step(z, kinds, xs, Ps, p)
    xs, Ps, xf, ll = smoother(z, kinds, p)
    sign = -1.0 if p.lam.sum() < 0 else 1.0
    p = Params(p.lam * sign, p.R, p.a)
    return Result(p, sign * xs[:, 0], Ps[:, 0, 0], sign * xf[:, 0], ll, it, converged, history)


# ------------------------------------------------------------------ simulation (tests)


def simulate(T: int, kinds: list[str], lam, R, a: float, seed: int = 0):
    """Draw (z, f) from the model. Quarterly series are observed only in months 3, 6, 9, ... (t % 3 == 2)."""
    rng = np.random.default_rng(seed)
    lam, R = np.asarray(lam, float), np.asarray(R, float)
    burn = 50
    f = np.zeros(T + burn)
    for t in range(1, T + burn):
        f[t] = a * f[t - 1] + rng.standard_normal()
    f = f[burn:]
    z = np.full((T, len(kinds)), np.nan)
    for i, k in enumerate(kinds):
        for t in range(2, T) if k != MONTHLY else range(T):
            if k != MONTHLY and t % 3 != 2:
                continue
            s = np.array([f[t], f[t - 1], f[t - 2]]) if t >= 2 else np.array([f[t], f[t], f[t]])
            z[t, i] = lam[i] * (H[k] @ s) + math.sqrt(R[i]) * rng.standard_normal()
    return z, f
