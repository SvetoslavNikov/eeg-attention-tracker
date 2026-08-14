"""Tests for EEGSession validation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from common.session import CANONICAL_CHANNELS, EEGSession


def _minimal(**kwargs) -> EEGSession:
    n = 1000
    defaults = dict(
        data=np.random.randn(n, 4),
        fs=500.0,
        ch_names=CANONICAL_CHANNELS,
        time=np.arange(n) / 500.0,
        subject_id="P33",
        study_id="test",
        phases={},
        source_path="",
    )
    defaults.update(kwargs)
    return EEGSession(**defaults)


def test_ok():
    s = _minimal()
    assert s.n_samples == 1000
    assert s.duration_sec == pytest.approx(999 / 500.0)


def test_wrong_shape():
    with pytest.raises(ValueError, match="\\(n, 4\\)"):
        _minimal(data=np.zeros((100, 3)))


def test_wrong_channels():
    with pytest.raises(ValueError, match="ch_names"):
        _minimal(ch_names=("Fz", "Cz", "Pz", "Oz"))
