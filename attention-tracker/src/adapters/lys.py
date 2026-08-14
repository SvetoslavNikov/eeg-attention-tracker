"""Load LYS Kernel Flow EEG exports into EEGSession."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from common.session import CANONICAL_CHANNELS, EEGSession

# Protocol events that define phase boundaries (seconds aligned to EEG time).
_PHASE_START = {
    "baseline_start": "baseline",
    "functional_localizer_start": "localizer",
    "task_start": "task",
}
_PHASE_END = {
    "baseline_end": "baseline",
    "functional_localizer_end": "localizer",
    "quit": "task",
    "end_experiment": "task",
}


def load_lys(
    npz_path: str | Path,
    jsonl_path: str | Path | None = None,
) -> EEGSession:
    """Load a LYS ``EEG_RAW_*.npz`` file.

    Args:
        npz_path: Path to the EEG export.
        jsonl_path: Optional session protocol log. Used only to set
            baseline / localizer / task phase windows on the EEG time axis.
            Words, commands, and audio are ignored.

    Returns:
        Validated ``EEGSession`` with channels in canonical order.
    """
    npz_path = Path(npz_path)
    raw = np.load(npz_path, allow_pickle=True)

    data = np.asarray(raw["data"], dtype=np.float64)
    if data.ndim != 2 or data.shape[1] != 4:
        raise ValueError(f"expected (n, 4) EEG data, got {data.shape}")

    fs = float(np.asarray(raw["fs_hz"]).item())
    time = np.asarray(raw["time"], dtype=np.float64)
    if time.shape[0] != data.shape[0]:
        raise ValueError("time and data length mismatch")

    ch_raw = raw["channel_names"]
    # object array of strings
    ch_names = tuple(str(c) for c in np.asarray(ch_raw).tolist())
    if len(ch_names) != 4:
        raise ValueError(f"expected 4 channel names, got {ch_names}")

    order = _channel_order(ch_names)
    data = data[:, order]
    ch_names = CANONICAL_CHANNELS

    subject_id = str(np.asarray(raw["subject_id"]).item())
    study_id = str(np.asarray(raw["study_id"]).item())

    phases: dict[str, tuple[float, float]] = {}
    if jsonl_path is not None:
        phases = _phases_from_jsonl(Path(jsonl_path), eeg_t0=float(time[0]), eeg_t1=float(time[-1]))
    elif (guess := _guess_jsonl(npz_path)) is not None:
        phases = _phases_from_jsonl(guess, eeg_t0=float(time[0]), eeg_t1=float(time[-1]))

    return EEGSession(
        data=data,
        fs=fs,
        ch_names=ch_names,
        time=time,
        subject_id=subject_id,
        study_id=study_id,
        phases=phases,
        source_path=str(npz_path.resolve()),
    )


def _channel_order(ch_names: tuple[str, ...]) -> list[int]:
    """Permutation that reorders ``ch_names`` to ``CANONICAL_CHANNELS``."""
    index = {name: i for i, name in enumerate(ch_names)}
    missing = [c for c in CANONICAL_CHANNELS if c not in index]
    if missing:
        raise ValueError(f"missing channels {missing}; have {list(ch_names)}")
    return [index[c] for c in CANONICAL_CHANNELS]


def _guess_jsonl(npz_path: Path) -> Path | None:
    """If a single *.jsonl sits next to the npz, use it."""
    candidates = sorted(npz_path.parent.glob("*.jsonl"))
    if len(candidates) == 1:
        return candidates[0]
    return None


def _parse_jsonl_events(path: Path) -> list[dict]:
    events: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            events.append(json.loads(line))
    return events


def _phases_from_jsonl(
    path: Path,
    *,
    eeg_t0: float,
    eeg_t1: float,
) -> dict[str, tuple[float, float]]:
    """Map protocol phase events onto EEG seconds.

    EEG ``time`` is relative to recording start (~0). Log timestamps are
    absolute. We take ``kernel_start_recording_result`` as EEG t≈0 and convert
    phase events to seconds on that axis.
    """
    events = _parse_jsonl_events(path)
    if not events:
        return {}

    rec_start: float | None = None
    for e in events:
        ev = e.get("event", {})
        if ev.get("event_type") == "kernel_start_recording_result" and ev.get("ok", True):
            rec_start = float(e["timestamp"])
            break
    if rec_start is None:
        # fall back: first event
        rec_start = float(events[0]["timestamp"])

    starts: dict[str, float] = {}
    ends: dict[str, float] = {}
    for e in events:
        ev = e.get("event", {})
        et = ev.get("event_type")
        t_rel = float(e["timestamp"]) - rec_start
        if et in _PHASE_START:
            starts[_PHASE_START[et]] = t_rel
        if et in _PHASE_END:
            # task may get quit then end_experiment; keep first end
            name = _PHASE_END[et]
            if name not in ends:
                ends[name] = t_rel

    phases: dict[str, tuple[float, float]] = {}
    for name in ("baseline", "localizer", "task"):
        if name in starts and name in ends:
            a = max(eeg_t0, starts[name])
            b = min(eeg_t1, ends[name])
            if b > a:
                phases[name] = (a, b)
    return phases
