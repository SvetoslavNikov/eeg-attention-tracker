"""Map band power → continuous attention index (signal only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.session import EEGSession
from features.multichannel import SessionBandPowers, session_band_powers


@dataclass(frozen=True)
class AttentionResult:
    """Time-resolved attention score for one session."""

    t: np.ndarray
    attention: np.ndarray
    alpha: np.ndarray
    theta: np.ndarray
    alpha_rel: np.ndarray
    theta_rel: np.ndarray
    baseline_alpha: float
    baseline_theta: float
    subject_id: str
    study_id: str


def score_attention(
    session: EEGSession,
    *,
    window_sec: float = 2.0,
    hop_sec: float = 0.5,
    channels: tuple[str, ...] = ("AF3", "AF4"),
    baseline_fallback_sec: float = 60.0,
) -> AttentionResult:
    """Continuous engagement-style score from frontal alpha/theta power.

    Formula (v1, transparent):
        alpha_rel = alpha / baseline_alpha
        theta_rel = theta / baseline_theta
        raw = theta_rel - alpha_rel
        attention = z-score of raw over the full session

    Higher score ≈ more theta relative to baseline and less alpha relative
    to baseline (classic active / engaged sketch). Not a validated classifier.

    Baseline: ``session.phases[\"baseline\"]`` if present, else first
    ``baseline_fallback_sec`` seconds of the recording.
    """
    bp = session_band_powers(
        session,
        channels=channels,
        window_sec=window_sec,
        hop_sec=hop_sec,
    )
    return score_from_band_powers(
        session, bp, baseline_fallback_sec=baseline_fallback_sec
    )


def score_from_band_powers(
    session: EEGSession,
    bp: SessionBandPowers,
    *,
    baseline_fallback_sec: float = 60.0,
) -> AttentionResult:
    if "alpha" not in bp.powers or "theta" not in bp.powers:
        raise ValueError("band powers must include 'alpha' and 'theta'")

    alpha = bp.powers["alpha"]
    theta = bp.powers["theta"]
    t = bp.t

    t0, t1 = _baseline_window(session, fallback_sec=baseline_fallback_sec)
    mask = (t >= t0) & (t <= t1)
    if not np.any(mask):
        # first few windows
        n = max(1, int(round(baseline_fallback_sec / bp.hop_sec)))
        mask = np.zeros(len(t), dtype=bool)
        mask[:n] = True

    baseline_alpha = float(np.median(alpha[mask]))
    baseline_theta = float(np.median(theta[mask]))
    if baseline_alpha <= 0:
        baseline_alpha = float(np.mean(alpha) + 1e-20)
    if baseline_theta <= 0:
        baseline_theta = float(np.mean(theta) + 1e-20)

    alpha_rel = alpha / baseline_alpha
    theta_rel = theta / baseline_theta
    raw = theta_rel - alpha_rel
    mu = float(np.mean(raw))
    sigma = float(np.std(raw))
    if sigma < 1e-12:
        attention = np.zeros_like(raw)
    else:
        attention = (raw - mu) / sigma

    return AttentionResult(
        t=t,
        attention=attention,
        alpha=alpha,
        theta=theta,
        alpha_rel=alpha_rel,
        theta_rel=theta_rel,
        baseline_alpha=baseline_alpha,
        baseline_theta=baseline_theta,
        subject_id=session.subject_id,
        study_id=session.study_id,
    )


def _baseline_window(
    session: EEGSession, *, fallback_sec: float
) -> tuple[float, float]:
    if "baseline" in session.phases:
        return session.phases["baseline"]
    t_start = float(session.time[0])
    return t_start, t_start + fallback_sec
