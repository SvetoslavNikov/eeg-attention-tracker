"""Smoke test: load real LYS Way of Kings session."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from adapters.lys import load_lys
from clean.pipeline import clean
from common.session import CANONICAL_CHANNELS
from score.attention import score_attention

DATA = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "lys_data"
    / "perceived_speech"
    / "audio_movie"
)
NPZ = DATA / "EEG_RAW_study-perceivedspeech_sub-p33_desc-95afb90.npz"
JSONL = DATA / "perceived_speech_log_20260629_182907.jsonl"


@pytest.mark.skipif(not NPZ.is_file(), reason="LYS npz not present")
def test_load_and_score_audio_movie():
    session = load_lys(NPZ, jsonl_path=JSONL if JSONL.is_file() else None)
    assert session.ch_names == CANONICAL_CHANNELS
    assert session.data.shape[1] == 4
    assert session.fs > 100
    assert session.subject_id == "P33"
    if JSONL.is_file():
        assert "baseline" in session.phases
        assert "task" in session.phases

    cleaned = clean(session)
    result = score_attention(cleaned)
    assert len(result.t) == len(result.attention)
    assert len(result.attention) > 50
    assert np.isfinite(result.attention).all()
