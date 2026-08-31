"""Interactive plot builds and writes HTML."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from common.session import CANONICAL_CHANNELS, EEGSession
from plot.score import plot_attention
from score.attention import score_attention


def test_plot_writes_html(tmp_path: Path):
    fs = 500.0
    dur = 30.0
    t = np.arange(0, dur, 1.0 / fs)
    x = np.sin(2 * np.pi * 10.0 * t)
    session = EEGSession(
        data=np.column_stack([x, x, x * 0.1, x * 0.1]),
        fs=fs,
        ch_names=CANONICAL_CHANNELS,
        time=t,
        subject_id="syn",
        study_id="syn",
        phases={"baseline": (0.0, 10.0), "task": (10.0, 30.0)},
    )
    result = score_attention(session, window_sec=2.0, hop_sec=0.5)
    out = tmp_path / "attention_score.html"
    path = plot_attention(result, session, save_path=out, show=False)
    assert path == out
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "attention" in text
    assert "Typical range" in text
    assert len(text) > 10_000


def test_plot_listen_wander_phases(tmp_path: Path):
    fs = 250.0
    dur = 40.0
    t = np.arange(0, dur, 1.0 / fs)
    x = np.sin(2 * np.pi * 10.0 * t)
    session = EEGSession(
        data=np.column_stack([x, x]),
        fs=fs,
        ch_names=("Ch01", "Ch02"),
        time=t,
        subject_id="syn",
        study_id="obci",
        phases={
            "baseline": (0.0, 8.0),
            "listen": (8.0, 24.0),
            "wander": (24.0, 40.0),
        },
    )
    result = score_attention(session, window_sec=2.0, hop_sec=0.5)
    out = tmp_path / "attention_score.html"
    path = plot_attention(result, session, save_path=out, show=False)
    assert path == out
    text = out.read_text(encoding="utf-8")
    assert "listen" in text
    assert "wander" in text
