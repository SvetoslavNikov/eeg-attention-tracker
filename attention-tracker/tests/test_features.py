"""Tests for sliding band power (ported script)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from features.band_power import sliding_band_powers
from features.bands import ATTENTION_BANDS


def test_alpha_sine_has_high_alpha():
    fs = 500.0
    t = np.arange(0, 10.0, 1.0 / fs)
    # 10 Hz sine → alpha band
    x = np.sin(2 * np.pi * 10.0 * t)
    results = sliding_band_powers(
        x, sfreq=fs, window_sec=2.0, hop_sec=0.5, bands=ATTENTION_BANDS
    )
    assert len(results) > 5
    alphas = [r.powers["alpha"] for r in results]
    thetas = [r.powers["theta"] for r in results]
    assert np.mean(alphas) > np.mean(thetas) * 5


def test_rejects_2d():
    import pytest

    with pytest.raises(ValueError, match="1D"):
        sliding_band_powers(np.zeros((100, 2)), sfreq=100.0)
