"""Tests for clean pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from clean.pipeline import clean
from common.session import CANONICAL_CHANNELS, EEGSession


def test_clean_preserves_shape():
    n = 5000
    fs = 500.0
    data = np.random.randn(n, 4) * 100
    # inject a huge spike
    data[2500, :] = 1e6
    session = EEGSession(
        data=data,
        fs=fs,
        ch_names=CANONICAL_CHANNELS,
        time=np.arange(n) / fs,
        subject_id="P0",
        study_id="t",
    )
    out = clean(session)
    assert out.data.shape == session.data.shape
    assert np.max(np.abs(out.data[2500])) < np.max(np.abs(data[2500]))
