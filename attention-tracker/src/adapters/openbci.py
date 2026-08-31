"""Load OpenBCI GUI TXT exports (+ optional JSON protocol) into EEGSession."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from common.session import EEGSession

# Cyton ADS1299 full-scale rail in OpenBCI GUI µV units.
RAIL_UV = 187_000.0
RAIL_FRAC = 0.05

_SKIP_EVENTS = {
    "wait",
    "start",
    "audio_start",
    "audio_stop",
}

_EVENT_TO_PHASE = {
    "wait a little bit": "baseline",
    "listen carefully": "listen",
    "wander around": "wander",
    "blink hard": "blink",
    "clench jaw": "jaw",
    "nod": "nod",
    "move your eyes": "eyes",
}

_SAMPLE_RATE_RE = re.compile(r"sample\s*rate\s*=\s*([0-9.]+)", re.I)
_N_CH_RE = re.compile(r"number\s*of\s*channels\s*=\s*([0-9]+)", re.I)
_BOARD_RE = re.compile(r"board\s*=\s*(.+)", re.I)


def load_openbci(
    txt_path: str | Path,
    json_path: str | Path | None = None,
    *,
    rail_uv: float = RAIL_UV,
    rail_frac: float = RAIL_FRAC,
) -> EEGSession:
    """Load an OpenBCI GUI ``OpenBCI-RAW-*.txt`` recording.

    Time is reconstructed as ``arange(n) / fs`` (GUI timestamps are bursty).
    Protocol event unix times are mapped with ``event_unix - first_eeg_unix``.
    Channels at the amplifier rail are dropped.

    Args:
        txt_path: OpenBCI GUI text export.
        json_path: Optional cue-protocol JSON (``svetoslav_session_*.json``).
            If omitted, a single ``*.json`` next to the txt is used when present.
        rail_uv: Absolute µV threshold treated as railed.
        rail_frac: Drop a channel if this fraction of samples are railed.
    """
    txt_path = Path(txt_path)
    header = _parse_header(txt_path)
    fs = header["fs"]
    raw = np.loadtxt(
        txt_path,
        delimiter=",",
        skiprows=header["skiprows"],
        usecols=header["usecols"],
    )
    if raw.ndim == 1:
        raw = raw.reshape(1, -1)

    n_exg = len(header["ch_names"])
    exg = np.asarray(raw[:, :n_exg], dtype=np.float64)
    unix = np.asarray(raw[:, n_exg], dtype=np.float64)

    if exg.shape[0] > 1 and np.allclose(exg[0], 0.0):
        exg = exg[1:]
        unix = unix[1:]

    if exg.shape[0] < 2:
        raise ValueError(f"too few samples in {txt_path}")

    keep, dropped = _keep_channels(exg, header["ch_names"], rail_uv, rail_frac)
    if not keep:
        raise ValueError(f"all channels railed in {txt_path}")
    data = exg[:, keep]
    ch_names = tuple(header["ch_names"][i] for i in keep)

    n = data.shape[0]
    time = np.arange(n, dtype=np.float64) / fs
    unix0 = float(unix[0])

    if json_path is None:
        json_path = _guess_json(txt_path)
    phases: dict[str, tuple[float, float]] = {}
    if json_path is not None:
        phases = _phases_from_json(
            Path(json_path),
            unix0=unix0,
            t0=float(time[0]),
            t1=float(time[-1]),
        )

    subject_id = _subject_from_path(txt_path)
    study_id = _study_from_path(txt_path)

    return EEGSession(
        data=data,
        fs=fs,
        ch_names=ch_names,
        time=time,
        subject_id=subject_id,
        study_id=study_id,
        phases=phases,
        source_path=str(txt_path.resolve()),
        meta={
            "board": header.get("board", ""),
            "n_raw_channels": n_exg,
            "dropped_channels": dropped,
            "rail_uv": float(rail_uv),
            "unix0": unix0,
        },
    )


def _parse_header(path: Path) -> dict:
    fs: float | None = None
    n_ch_hdr: int | None = None
    board = ""
    header_line = -1
    cols: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            s = line.strip()
            if s.startswith("%"):
                body = s.lstrip("%").strip()
                if m := _SAMPLE_RATE_RE.search(body):
                    fs = float(m.group(1))
                elif m := _N_CH_RE.search(body):
                    n_ch_hdr = int(m.group(1))
                elif m := _BOARD_RE.search(body):
                    board = m.group(1).strip()
                continue
            if not s:
                continue
            cols = [c.strip() for c in s.split(",")]
            header_line = i
            break
    if header_line < 0 or not cols:
        raise ValueError(f"no column header in {path}")
    if fs is None or fs <= 0:
        raise ValueError(f"missing sample rate in {path}")

    exg_idx: list[int] = []
    ch_names: list[str] = []
    ts_idx: int | None = None
    for i, name in enumerate(cols):
        low = name.lower()
        if low.startswith("exg channel"):
            tail = name.split()[-1]
            try:
                n = int(float(tail))
            except ValueError:
                n = len(exg_idx)
            exg_idx.append(i)
            ch_names.append(f"Ch{n:02d}")
        elif low == "timestamp":
            ts_idx = i
    if not exg_idx:
        raise ValueError(f"no EXG columns in {path}")
    if ts_idx is None:
        raise ValueError(f"no Timestamp column in {path}")
    if n_ch_hdr is not None and n_ch_hdr != len(exg_idx):
        raise ValueError(
            f"header says {n_ch_hdr} channels, found {len(exg_idx)} EXG columns"
        )
    return {
        "fs": fs,
        "board": board,
        "ch_names": ch_names,
        "skiprows": header_line + 1,
        "usecols": exg_idx + [ts_idx],
    }


def _keep_channels(
    exg: np.ndarray,
    names: list[str],
    rail_uv: float,
    rail_frac: float,
) -> tuple[list[int], list[str]]:
    frac = np.mean(np.abs(exg) >= rail_uv, axis=0)
    keep = [i for i, f in enumerate(frac) if f < rail_frac]
    dropped = [names[i] for i, f in enumerate(frac) if f >= rail_frac]
    return keep, dropped


def _guess_json(txt_path: Path) -> Path | None:
    candidates = sorted(
        p
        for p in txt_path.parent.glob("*.json")
        if p.is_file() and not p.name.lower().startswith(".")
    )
    if len(candidates) == 1:
        return candidates[0]
    sessions = [p for p in candidates if "session" in p.name.lower()]
    if len(sessions) == 1:
        return sessions[0]
    return None


def _phases_from_json(
    path: Path,
    *,
    unix0: float,
    t0: float,
    t1: float,
) -> dict[str, tuple[float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload.get("events") or []
    phases: dict[str, tuple[float, float]] = {}
    rest_i = 0
    for ev in events:
        raw = str(ev.get("event", "")).strip()
        key = raw.lower()
        if key in _SKIP_EVENTS:
            continue
        try:
            start_unix = float(ev["start_unix"])
            end_unix = float(ev["end_unix"])
        except (KeyError, TypeError, ValueError):
            continue
        a = start_unix - unix0
        b = end_unix - unix0
        a = max(float(a), t0)
        b = min(float(b), t1)
        if b - a < 0.5:
            continue
        if key == "rest":
            rest_i += 1
            name = f"rest_{rest_i}"
        else:
            name = _EVENT_TO_PHASE.get(key, _slug(raw))
            name = _unique_name(name, phases)
        phases[name] = (a, b)
    return phases


def _unique_name(name: str, used: dict) -> str:
    if name not in used:
        return name
    i = 2
    while f"{name}_{i}" in used:
        i += 1
    return f"{name}_{i}"


def _slug(raw: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return s or "event"


def _subject_from_path(txt_path: Path) -> str:
    parent = txt_path.parent.name.strip()
    if parent and parent.lower() not in {"openbci_eeg_data", "data", "recordings"}:
        return parent.replace(" Recording", "").replace(" recording", "").strip() or parent
    return "unknown"


def _study_from_path(txt_path: Path) -> str:
    stem = txt_path.stem
    stem = re.sub(r"^OpenBCI-RAW-?", "", stem, flags=re.I)
    return stem or txt_path.stem
