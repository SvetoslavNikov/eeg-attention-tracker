"""OpenBCI adapter: rail drop, uniform time, JSON phase alignment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from adapters.openbci import load_openbci
from clean.pipeline import clean
from score.attention import score_attention

REAL_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "openbci_eeg_data"
    / "Svetoslav Recording"
)
REAL_TXT = REAL_DIR / "OpenBCI-RAW-2026-08-28_15-51-10.txt"
REAL_JSON = REAL_DIR / "svetoslav_session_1.json"


def _write_txt(
    path: Path,
    *,
    fs: float,
    exg: np.ndarray,
    unix0: float,
    burst_timestamp: bool = True,
) -> None:
    n, n_ch = exg.shape
    lines = [
        "%OpenBCI Raw EXG Data",
        f"%Number of channels = {n_ch}",
        f"%Sample Rate = {fs} Hz",
        "%Board = OpenBCI_GUI$BoardCytonWifiDaisy",
    ]
    cols = ["Sample Index"] + [f"EXG Channel {i}" for i in range(n_ch)]
    cols += ["Timestamp", "Marker Channel", "Timestamp (Formatted)"]
    lines.append(", ".join(cols))
    for i in range(n):
        ts = unix0 if burst_timestamp else unix0 + i / fs
        exg_s = ", ".join(f"{exg[i, c]:.6f}" for c in range(n_ch))
        lines.append(
            f"{float(i % 256)}, {exg_s}, {ts:.9f}, 0.0, 2026-01-01 00:00:00.000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, *, unix0: float, events: list[dict]) -> None:
    payload = {
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:01:00+00:00",
        "status": "completed",
        "events": events,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_rail_drop_and_uniform_time(tmp_path: Path):
    fs = 250.0
    n = 1000
    rng = np.random.default_rng(0)
    exg = rng.normal(0, 20, size=(n, 4))
    exg[:, 0] = 187500.0
    exg[:, 3] = 187500.0
    txt = tmp_path / "OpenBCI-RAW-2026-01-01_00-00-00.txt"
    _write_txt(txt, fs=fs, exg=exg, unix0=1_000_000.0, burst_timestamp=True)

    session = load_openbci(txt)
    assert session.fs == fs
    assert session.ch_names == ("Ch01", "Ch02")
    assert session.meta["dropped_channels"] == ["Ch00", "Ch03"]
    assert session.n_samples == n
    dt = np.diff(session.time)
    assert np.allclose(dt, 1.0 / fs)
    # bursty unix stamps must not become the time axis
    assert session.time[-1] == pytest.approx((n - 1) / fs)


def test_json_phases_aligned_to_unix0(tmp_path: Path):
    fs = 250.0
    n = 5000  # 20 s
    unix0 = 1_787_921_472.0
    rng = np.random.default_rng(1)
    exg = rng.normal(0, 15, size=(n, 3))
    txt = tmp_path / "OpenBCI-RAW-unit.txt"
    js = tmp_path / "svetoslav_session_1.json"
    _write_txt(txt, fs=fs, exg=exg, unix0=unix0)
    _write_json(
        js,
        unix0=unix0,
        events=[
            {
                "event": "wait",
                "start_unix": unix0 - 5.0,
                "end_unix": unix0 - 0.1,
            },
            {
                "event": "Wait a little bit",
                "start_unix": unix0 + 1.0,
                "end_unix": unix0 + 5.0,
            },
            {
                "event": "listen carefully",
                "start_unix": unix0 + 5.0,
                "end_unix": unix0 + 12.0,
            },
            {
                "event": "rest",
                "start_unix": unix0 + 12.0,
                "end_unix": unix0 + 13.0,
            },
            {
                "event": "Wander around",
                "start_unix": unix0 + 13.0,
                "end_unix": unix0 + 19.0,
            },
            {
                "event": "rest",
                "start_unix": unix0 + 19.0,
                "end_unix": unix0 + 19.8,
            },
            {
                "event": "audio_start",
                "start_unix": unix0 + 5.0,
                "end_unix": unix0 + 5.0,
            },
        ],
    )
    session = load_openbci(txt, js)
    assert "baseline" in session.phases
    assert "listen" in session.phases
    assert "wander" in session.phases
    assert "rest_1" in session.phases
    assert "rest_2" in session.phases
    assert "wait" not in session.phases
    a, b = session.phases["listen"]
    assert a == pytest.approx(5.0, abs=1e-6)
    assert b == pytest.approx(12.0, abs=1e-6)
    assert session.phases["baseline"][0] == pytest.approx(1.0, abs=1e-6)


def test_score_without_af_channels(tmp_path: Path):
    fs = 250.0
    dur = 30.0
    t = np.arange(0, dur, 1.0 / fs)
    n = len(t)
    x = np.zeros(n)
    mid = n // 2
    x[:mid] = 2.0 * np.sin(2 * np.pi * 10.0 * t[:mid])
    x[mid:] = 2.0 * np.sin(2 * np.pi * 6.0 * t[mid:])
    exg = np.column_stack([x, x * 0.8, x * 0.9])
    txt = tmp_path / "OpenBCI-RAW-syn.txt"
    _write_txt(txt, fs=fs, exg=exg, unix0=10.0, burst_timestamp=True)
    session = load_openbci(txt)
    session = session.replace(phases={"baseline": (0.0, 15.0)})
    result = score_attention(session, window_sec=2.0, hop_sec=0.5)
    first = result.attention[result.t < 15]
    second = result.attention[result.t >= 16]
    assert second.mean() > first.mean()
    assert result.channels == ("Ch00", "Ch01", "Ch02")


@pytest.mark.skipif(not REAL_TXT.is_file(), reason="OpenBCI recording not present")
def test_real_svetoslav_header_and_phases():
    session = load_openbci(REAL_TXT, REAL_JSON if REAL_JSON.is_file() else None)
    assert session.fs == 500.0
    assert session.n_channels >= 8
    assert "Ch00" not in session.ch_names
    assert session.duration_sec == pytest.approx(
        (session.n_samples - 1) / session.fs, rel=1e-6
    )
    dt = np.diff(session.time)
    assert np.allclose(dt, 1.0 / session.fs)
    if REAL_JSON.is_file():
        assert "baseline" in session.phases
        assert "listen" in session.phases
        assert "wander" in session.phases
        listen = session.phases["listen"]
        wander = session.phases["wander"]
        assert listen[1] - listen[0] > 300
        assert wander[1] - wander[0] > 300
        assert wander[0] >= listen[1]


def test_clean_accepts_openbci_session(tmp_path: Path):
    fs = 250.0
    n = 2000
    exg = np.random.randn(n, 2) * 30
    txt = tmp_path / "OpenBCI-RAW-c.txt"
    _write_txt(txt, fs=fs, exg=exg, unix0=1.0)
    session = load_openbci(txt)
    out = clean(session)
    assert out.data.shape == session.data.shape
    assert out.ch_names == session.ch_names
