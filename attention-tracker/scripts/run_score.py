#!/usr/bin/env python3
"""CLI: LYS EEG → clean → band power → attention score → plot.

Usage (from attention-tracker/ with PYTHONPATH=src):

  python scripts/run_score.py ../data/lys_data/perceived_speech/audio_movie/EEG_RAW_....npz
  python scripts/run_score.py path/to/file.npz --jsonl path/to/log.jsonl
  python scripts/run_score.py --all-lys
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without installing the package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from adapters.lys import load_lys
from clean.pipeline import clean
from plot.score import plot_attention
from score.attention import score_attention

# Repo data root (sibling of attention-tracker/)
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


def _output_dir_for(npz_path: Path) -> Path:
    """Mirror under outputs/lys_data/.../attention/."""
    try:
        rel = npz_path.resolve().relative_to((ROOT.parent / "data").resolve())
        # lys_data/perceived_speech/audio_movie/file.npz → outputs/lys_data/.../attention
        return ROOT / "outputs" / rel.parent / "attention"
    except ValueError:
        return ROOT / "outputs" / "adhoc" / npz_path.stem / "attention"


def run_one(
    npz_path: Path,
    jsonl_path: Path | None = None,
    *,
    skip_clean: bool = False,
) -> Path:
    session = load_lys(npz_path, jsonl_path=jsonl_path)
    if not skip_clean:
        session = clean(session)
    result = score_attention(session)

    out_dir = _output_dir_for(npz_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_path = out_dir / "attention_score.png"
    plot_attention(result, session, save_path=plot_path)

    notes = out_dir / "notes.md"
    phase_str = ", ".join(
        f"{k}=[{a:.1f},{b:.1f}]" for k, (a, b) in session.phases.items()
    ) or "(none)"
    notes.write_text(
        "\n".join(
            [
                f"# Attention score — {session.subject_id} / {session.study_id}",
                "",
                f"- source: `{session.source_path}`",
                f"- fs: {session.fs:.3f} Hz",
                f"- duration: {session.duration_sec:.1f} s",
                f"- phases: {phase_str}",
                f"- mean attention (z): {float(result.attention.mean()):.3f}",
                f"- baseline alpha: {result.baseline_alpha:.4g}",
                f"- baseline theta: {result.baseline_theta:.4g}",
                f"- plot: `{plot_path.name}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"OK {npz_path.name} → {plot_path}")
    return plot_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LYS signal-only attention score")
    p.add_argument("npz", nargs="?", type=Path, help="Path to EEG_RAW_*.npz")
    p.add_argument("--jsonl", type=Path, default=None, help="Optional protocol log")
    p.add_argument(
        "--all-lys",
        action="store_true",
        help="Run all known LYS sessions under data/lys_data/",
    )
    p.add_argument("--skip-clean", action="store_true")
    args = p.parse_args(argv)

    if args.all_lys:
        for folder in LYS_SESSIONS:
            if not folder.is_dir():
                print(f"SKIP missing {folder}")
                continue
            npz = _find_npz(folder)
            run_one(npz, skip_clean=args.skip_clean)
        return 0

    if args.npz is None:
        p.error("provide npz path or --all-lys")
    run_one(args.npz, jsonl_path=args.jsonl, skip_clean=args.skip_clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
