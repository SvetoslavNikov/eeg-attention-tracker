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
    assert s.n_channels == 4
    assert s.duration_sec == pytest.approx(999 / 500.0)


def test_wrong_ndim():
    with pytest.raises(ValueError, match="n_ch"):
        _minimal(data=np.zeros(100))


def test_channel_count_mismatch():
    with pytest.raises(ValueError, match="ch_names length"):
        _minimal(data=np.zeros((100, 3)))


def test_duplicate_channel_names():
    with pytest.raises(ValueError, match="duplicate"):
        _minimal(ch_names=("AF4", "AF3", "AF4", "CPz"))


def test_n_channel_openbci_ok():
    n = 200
    names = ("Ch00", "Ch01", "Ch02")
    s = EEGSession(
        data=np.random.randn(n, 3),
        fs=250.0,
        ch_names=names,
        time=np.arange(n) / 250.0,
        subject_id="S",
        study_id="t",
    )
    assert s.n_channels == 3
    assert s.channel_index("Ch01") == 1
