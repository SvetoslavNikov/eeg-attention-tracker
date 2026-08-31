"""Tests for attention score directionality on synthetic signals."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from common.session import CANONICAL_CHANNELS, EEGSession
from score.attention import score_attention


def test_low_alpha_raises_score_vs_high_alpha():
    """Second half: lower alpha → higher mean attention than first half."""
    fs = 500.0
    dur = 120.0
    t = np.arange(0, dur, 1.0 / fs)
    n = len(t)
    # first 60s: strong 10 Hz (alpha); second 60s: strong 6 Hz (theta), weak alpha
    x = np.zeros(n)
    mid = n // 2
    x[:mid] = 2.0 * np.sin(2 * np.pi * 10.0 * t[:mid])
    x[mid:] = 2.0 * np.sin(2 * np.pi * 6.0 * t[mid:])
    data = np.column_stack([x, x, x * 0.1, x * 0.1])
    session = EEGSession(
        data=data,
        fs=fs,
        ch_names=CANONICAL_CHANNELS,
        time=t,
        subject_id="syn",
        study_id="syn",
        phases={"baseline": (0.0, 60.0)},
    )
    result = score_attention(session, window_sec=2.0, hop_sec=0.5)
    first = result.attention[result.t < 60]
    second = result.attention[result.t >= 62]
    assert second.mean() > first.mean()
    assert result.channels == ("AF3", "AF4")


def test_falls_back_to_all_channels_without_af():
    fs = 500.0
    dur = 40.0
    t = np.arange(0, dur, 1.0 / fs)
    n = len(t)
    x = np.sin(2 * np.pi * 10.0 * t)
    session = EEGSession(
        data=np.column_stack([x, x * 0.5, x * 0.7]),
        fs=fs,
        ch_names=("Ch00", "Ch01", "Ch02"),
        time=t,
        subject_id="syn",
        study_id="obci",
        phases={"baseline": (0.0, 10.0)},
    )
    result = score_attention(session, window_sec=2.0, hop_sec=0.5)
    assert result.channels == ("Ch00", "Ch01", "Ch02")
    assert np.isfinite(result.attention).all()
