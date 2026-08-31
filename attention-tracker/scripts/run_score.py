#!/usr/bin/env python3
"""CLI: EEG → clean → band power → attention score → plot.

Usage (from attention-tracker/ with PYTHONPATH=src):

  python scripts/run_score.py ../data/lys_data/perceived_speech/audio_movie/EEG_RAW_....npz
  python scripts/run_score.py path/to/file.npz --jsonl path/to/log.jsonl
  python scripts/run_score.py --all-lys
  python scripts/run_score.py ../data/openbci_eeg_data/Svetoslav\\ Recording
  python scripts/run_score.py path/to/OpenBCI-RAW-....txt --json path/to/session.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Allow running without installing the package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from adapters.lys import load_lys
from adapters.openbci import load_openbci
from clean.pipeline import clean
from common.session import EEGSession
from plot.score import plot_attention
from score.attention import AttentionResult, score_attention

DATA_ROOT = ROOT.parent / "data" / "lys_data"

LYS_SESSIONS = [
    DATA_ROOT / "perceived_speech" / "audio_movie",
    DATA_ROOT / "perceived_speech" / "Bill_Ackman_part2",
    DATA_ROOT / "zork_task",
]


def _find_npz(folder: Path) -> Path:
    hits = list(folder.glob("EEG_RAW_*.npz"))
    if not hits:
        raise FileNotFoundError(f"no EEG_RAW_*.npz in {folder}")
    return hits[0]


def _find_openbci_txt(folder: Path) -> Path:
    hits = sorted(folder.glob("OpenBCI-RAW*.txt")) + sorted(
        folder.glob("OpenBCI-RAW*.TXT")
    )
    if not hits:
        raise FileNotFoundError(f"no OpenBCI-RAW*.txt in {folder}")
    return hits[0]


def _output_dir_for(source_path: Path) -> Path:
    """Mirror under outputs/<relative-to-data>/attention/."""
    try:
        rel = source_path.resolve().relative_to((ROOT.parent / "data").resolve())
        return ROOT / "outputs" / rel.parent / "attention"
    except ValueError:
        return ROOT / "outputs" / "adhoc" / source_path.stem / "attention"


def load_session(
    path: Path,
    *,
    jsonl_path: Path | None = None,
    json_path: Path | None = None,
) -> EEGSession:
    path = Path(path)
    if path.is_dir():
        npzs = list(path.glob("EEG_RAW_*.npz"))
        if npzs:
            return load_lys(npzs[0], jsonl_path=jsonl_path)
        return load_openbci(_find_openbci_txt(path), json_path=json_path)
    suffix = path.suffix.lower()
    if suffix == ".npz":
        return load_lys(path, jsonl_path=jsonl_path)
    if suffix == ".txt":
        return load_openbci(path, json_path=json_path)
    raise ValueError(f"unsupported EEG path: {path}")


def run_one(
    path: Path,
    jsonl_path: Path | None = None,
    json_path: Path | None = None,
    *,
    skip_clean: bool = False,
    show: bool = True,
) -> Path:
    path = Path(path)
    session = load_session(path, jsonl_path=jsonl_path, json_path=json_path)
    source = Path(session.source_path) if session.source_path else path
    if not skip_clean:
        session = clean(session)
    result = score_attention(session)

    out_dir = _output_dir_for(source)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_path = out_dir / "attention_score.html"
    plot_attention(result, session, save_path=plot_path, show=show)

    notes = out_dir / "notes.md"
    notes.write_text(_notes_markdown(session, result, plot_path), encoding="utf-8")
    print(f"OK {source.name} → {plot_path}")
    return plot_path


def _notes_markdown(
    session: EEGSession, result: AttentionResult, plot_path: Path
) -> str:
    phase_str = ", ".join(
        f"{k}=[{a:.1f},{b:.1f}]" for k, (a, b) in session.phases.items()
    ) or "(none)"
    dropped = session.meta.get("dropped_channels") or []
    ch = ", ".join(result.channels) if result.channels else ", ".join(session.ch_names)
    lines = [
        f"# Attention score — {session.subject_id} / {session.study_id}",
        "",
        f"- source: `{session.source_path}`",
        f"- fs: {session.fs:.3f} Hz",
        f"- duration: {session.duration_sec:.1f} s",
        f"- channels used: {ch}",
        f"- dropped channels: {', '.join(dropped) if dropped else '(none)'}",
        f"- phases: {phase_str}",
        f"- mean attention (z): {float(result.attention.mean()):.3f}",
        f"- baseline alpha: {result.baseline_alpha:.4g}",
        f"- baseline theta: {result.baseline_theta:.4g}",
        f"- plot: `{plot_path.name}`",
        "",
        "## Phase means",
        "",
    ]
    for name, (a, b) in session.phases.items():
        mask = (result.t >= a) & (result.t < b)
        if int(np.count_nonzero(mask)) < 3:
            continue
        att = float(result.attention[mask].mean())
        alpha = float(result.alpha[mask].mean())
        theta = float(result.theta[mask].mean())
        ratio = alpha / theta if theta else float("nan")
        lines.append(
            f"- **{name}** [{a:.1f}, {b:.1f}]s  attention_z={att:.3f}  "
            f"alpha={alpha:.4g}  theta={theta:.4g}  alpha/theta={ratio:.3f}"
        )
    if "listen" in session.phases and "wander" in session.phases:
        def _mean(phase: str, arr: np.ndarray) -> float:
            a, b = session.phases[phase]
            mask = (result.t >= a) & (result.t < b)
            return float(arr[mask].mean()) if np.any(mask) else float("nan")

        la, wa = _mean("listen", result.alpha), _mean("wander", result.alpha)
        lt, wt = _mean("listen", result.theta), _mean("wander", result.theta)
        lz, wz = _mean("listen", result.attention), _mean("wander", result.attention)
        lines.extend(
            [
                "",
                "## Listen vs wander",
                "",
                f"- alpha wander/listen: {wa / la:.3f}" if la else "- alpha wander/listen: n/a",
                f"- theta wander/listen: {wt / lt:.3f}" if lt else "- theta wander/listen: n/a",
                f"- attention_z listen={lz:.3f}, wander={wz:.3f}",
                "",
                "Descriptive index only (n=1, listen-then-wander order). "
                "Not a validated classifier.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Signal-only attention score")
    p.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="EEG_RAW_*.npz, OpenBCI-RAW*.txt, or a session folder",
    )
    p.add_argument("--jsonl", type=Path, default=None, help="Optional LYS protocol log")
    p.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=None,
        help="Optional OpenBCI cue-protocol JSON",
    )
    p.add_argument(
        "--all-lys",
        action="store_true",
        help="Run all known LYS sessions under data/lys_data/",
    )
    p.add_argument("--skip-clean", action="store_true")
    p.add_argument(
        "--no-show",
        action="store_true",
        help="Save the HTML plot but do not open a browser window",
    )
    args = p.parse_args(argv)

    if args.all_lys:
        for folder in LYS_SESSIONS:
            if not folder.is_dir():
                print(f"SKIP missing {folder}")
                continue
            npz = _find_npz(folder)
            run_one(npz, skip_clean=args.skip_clean, show=False)
        return 0

    if args.path is None:
        p.error("provide an EEG path or --all-lys")
    run_one(
        args.path,
        jsonl_path=args.jsonl,
        json_path=args.json_path,
        skip_clean=args.skip_clean,
        show=not args.no_show,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
