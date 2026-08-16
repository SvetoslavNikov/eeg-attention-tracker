#!/usr/bin/env python3
"""Print LYS .npz EEG exports and .jsonl protocol logs so you can read them.

Usage (from attention-tracker/, with PYTHONPATH=src):

  python src/adapters/explanation/dump_session.py
  python src/adapters/explanation/dump_session.py ../data/lys_data/zork_task
  python src/adapters/explanation/dump_session.py path/to/file.npz
  python src/adapters/explanation/dump_session.py path/to/file.jsonl --samples 3
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from adapters.lys import load_lys

DATA_ROOT = ROOT.parent / "data" / "lys_data"

KNOWN_SESSIONS = [
    DATA_ROOT / "perceived_speech" / "audio_movie",
    DATA_ROOT / "perceived_speech" / "Bill_Ackman_part2",
    DATA_ROOT / "zork_task",
]

_PHASE_EVENTS = {
    "baseline_start",
    "baseline_end",
    "functional_localizer_start",
    "functional_localizer_end",
    "task_start",
    "quit",
    "end_experiment",
    "kernel_start_recording_result",
}


def _hr() -> None:
    print("-" * 72)


def _title(text: str) -> None:
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def _fmt_scalar(value: object) -> str:
    arr = np.asarray(value)
    if arr.shape == ():
        return repr(arr.item())
    if arr.size <= 8:
        return repr(arr.tolist())
    return f"array shape={arr.shape} dtype={arr.dtype}"


def _compact(value: object, limit: int = 90) -> object:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…"
    if isinstance(value, list) and len(value) > 6:
        return value[:6] + [f"… +{len(value) - 6} more"]
    return value


def dump_npz(path: Path, *, preview_rows: int = 3) -> None:
    _title(f"NPZ  {path}")
    raw = np.load(path, allow_pickle=True)
    keys = list(raw.files)
    print(f"keys: {keys}")
    print()

    for key in keys:
        arr = raw[key]
        print(f"  {key}")
        print(f"    dtype={arr.dtype}  shape={arr.shape}")
        if arr.shape == () or arr.size <= 8:
            print(f"    value={_fmt_scalar(arr)}")
            continue
        if key == "data" and arr.ndim == 2:
            print(f"    first {preview_rows} rows:")
            for row in arr[:preview_rows]:
                print(f"      {np.asarray(row, dtype=float)}")
            print(f"    last row: {np.asarray(arr[-1], dtype=float)}")
            print("    per-channel min / mean / max:")
            for i, col in enumerate(arr.T):
                col = np.asarray(col, dtype=float)
                print(
                    f"      ch{i}:  {col.min():.4g}  /  {col.mean():.4g}  /  {col.max():.4g}"
                )
        elif key == "time":
            t = np.asarray(arr, dtype=float)
            print(f"    first 3: {t[:3]}")
            print(f"    last  3: {t[-3:]}")
            if t.size >= 2:
                print(f"    duration: {t[-1] - t[0]:.3f} s")
                print(f"    median dt: {np.median(np.diff(t)) * 1000:.4f} ms")
        elif key == "impedance" and arr.ndim == 2:
            z = np.asarray(arr, dtype=float)
            print(f"    min={z.min():.4g}  max={z.max():.4g}  mean={z.mean():.4g}")
        else:
            print(f"    min={np.nanmin(arr)}  max={np.nanmax(arr)}")
    raw.close()


def _parse_jsonl(path: Path) -> tuple[dict[str, str], list[dict]]:
    header: dict[str, str] = {}
    events: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                body = line[1:].strip()
                if ":" in body:
                    k, v = body.split(":", 1)
                    header[k.strip()] = v.strip()
                continue
            events.append(json.loads(line))
    return header, events


def dump_jsonl(path: Path, *, samples: int) -> None:
    _title(f"JSONL  {path}")
    header, events = _parse_jsonl(path)
    print(f"header comments ({len(header)}):")
    for k, v in header.items():
        print(f"  {k}: {v or '(empty)'}")
    print()
    print(f"events: {len(events)}")

    counts = Counter(
        e.get("event", {}).get("event_type", "<missing event_type>") for e in events
    )
    print("event_type counts:")
    for name, n in counts.most_common():
        print(f"  {n:5d}  {name}")

    rec_start = None
    for e in events:
        ev = e.get("event", {})
        if ev.get("event_type") == "kernel_start_recording_result" and ev.get("ok", True):
            rec_start = float(e["timestamp"])
            break
    if rec_start is None and events:
        rec_start = float(events[0]["timestamp"])

    print()
    print("phase-ish timeline (seconds after kernel_start_recording_result):")
    for e in events:
        ev = e.get("event", {})
        et = ev.get("event_type")
        if et not in _PHASE_EVENTS:
            continue
        t_rel = float(e["timestamp"]) - rec_start
        extra = {
            k: _compact(v)
            for k, v in ev.items()
            if k != "event_type"
        }
        print(f"  t={t_rel:8.2f}s  {et}  {extra}")

    print()
    print(f"sample events (up to {samples} per type):")
    seen: Counter[str] = Counter()
    for e in events:
        ev = e.get("event", {})
        et = ev.get("event_type", "<missing>")
        if seen[et] >= samples:
            continue
        seen[et] += 1
        t_rel = float(e["timestamp"]) - rec_start
        payload = {k: _compact(v) for k, v in ev.items() if k != "event_type"}
        print(f"  [{et}] t={t_rel:.2f}s  {payload}")


def dump_adapter(npz_path: Path, jsonl_path: Path | None) -> None:
    _title("What adapters/lys.py keeps (EEGSession)")
    session = load_lys(npz_path, jsonl_path=jsonl_path)
    print(f"  source_path : {session.source_path}")
    print(f"  subject_id  : {session.subject_id}")
    print(f"  study_id    : {session.study_id}")
    print(f"  ch_names    : {session.ch_names}")
    print(f"  fs          : {session.fs:.6f} Hz")
    print(f"  n_samples   : {session.n_samples}")
    print(f"  duration    : {session.duration_sec:.3f} s")
    print(f"  data.shape  : {session.data.shape}  dtype={session.data.dtype}")
    print(f"  time[0],[-1]: {session.time[0]:.6f}, {session.time[-1]:.6f}")
    if session.phases:
        print("  phases (seconds on the EEG time axis):")
        for name, (a, b) in session.phases.items():
            print(f"    {name:10s}  [{a:8.2f}, {b:8.2f}]  ({b - a:.1f} s)")
    else:
        print("  phases      : {}  (no jsonl, or no start/end pair found)")
    print()
    print("  dropped from the raw files on purpose:")
    print("    npz: impedance, source_snirf, measurement_date/time")
    print("    jsonl: words, game commands, audio paths, localizer cues, …")


def _find_npz(folder: Path) -> Path | None:
    hits = sorted(folder.glob("EEG_RAW_*.npz"))
    return hits[0] if hits else None


def _find_jsonl(folder: Path) -> Path | None:
    hits = sorted(folder.glob("*.jsonl"))
    return hits[0] if len(hits) == 1 else None


def dump_target(target: Path, *, samples: int) -> None:
    target = target.resolve()
    if not target.exists():
        raise FileNotFoundError(target)

    if target.is_dir():
        npz = _find_npz(target)
        jsonl = _find_jsonl(target)
        if npz is None and jsonl is None:
            raise FileNotFoundError(f"no EEG_RAW_*.npz or *.jsonl in {target}")
        if npz is not None:
            dump_npz(npz)
        if jsonl is not None:
            dump_jsonl(jsonl, samples=samples)
        if npz is not None:
            dump_adapter(npz, jsonl)
        return

    if target.suffix == ".npz":
        dump_npz(target)
        sibling = _find_jsonl(target.parent)
        if sibling is not None:
            dump_jsonl(sibling, samples=samples)
        dump_adapter(target, sibling)
        return

    if target.suffix == ".jsonl":
        dump_jsonl(target, samples=samples)
        sibling = _find_npz(target.parent)
        if sibling is not None:
            dump_npz(sibling)
            dump_adapter(sibling, target)
        return

    raise ValueError(f"expected a folder, .npz, or .jsonl, got {target}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dump LYS .npz / .jsonl contents")
    p.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Session folder, .npz, or .jsonl. Default: all known LYS sessions.",
    )
    p.add_argument(
        "--samples",
        type=int,
        default=1,
        help="How many example events to print per jsonl event_type (default 1)",
    )
    args = p.parse_args(argv)

    if args.path is None:
        for folder in KNOWN_SESSIONS:
            if not folder.is_dir():
                print(f"SKIP missing {folder}")
                continue
            dump_target(folder, samples=args.samples)
            _hr()
        return 0

    dump_target(args.path, samples=args.samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
