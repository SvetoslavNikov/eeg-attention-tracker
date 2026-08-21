#!/usr/bin/env python3
"""Show the three clean() pieces separately on one channel.

From attention-tracker/:

  PYTHONPATH=src python src/clean/show_clean.py
  PYTHONPATH=src python src/clean/show_clean.py path/to/EEG_RAW_....npz
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from adapters.lys import load_lys
from clean.pipeline import _interp_mask

DATA_ROOT = ROOT.parent / "data" / "lys_data"
CHANNEL = "AF3"
FMIN = 0.5
FMAX = 40.0
ARTIFACT_Z = 8.0


def _default_npz() -> Path:
    hits = list(DATA_ROOT.rglob("EEG_RAW_*.npz"))
    if not hits:
        raise FileNotFoundError(f"no EEG_RAW_*.npz under {DATA_ROOT}")
    return sorted(hits)[0]


def _window(t: np.ndarray, center: float, half: float) -> slice:
    i0 = int(np.searchsorted(t, center - half))
    i1 = int(np.searchsorted(t, center + half))
    return slice(max(i0, 0), max(i1, i0 + 1))


def _apply_filter(
    x: np.ndarray,
    fs: float,
    *,
    btype: str,
    cutoff: float | list[float],
) -> np.ndarray:
    nyq = fs / 2.0
    if btype == "band":
        low, high = cutoff
        wn = [max(low / nyq, 1e-6), min(high / nyq, 0.999)]
    else:
        wn = min(max(float(cutoff) / nyq, 1e-6), 0.999)
    b, a = butter(4, wn, btype=btype)
    padlen = min(3 * max(len(a), len(b)), len(x) - 1)
    return filtfilt(b, a, x, padlen=padlen)


def _remove_artifacts(x: np.ndarray, fs: float) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad <= 0:
        return x.copy()
    thr = ARTIFACT_Z * 1.4826 * mad
    bad = np.abs(x - med) > thr
    if not np.any(bad):
        return x.copy()
    return _interp_mask(x, bad, max_run=int(round(2.0 * fs)))


def main() -> int:
    npz = Path(sys.argv[1]) if len(sys.argv) > 1 else _default_npz()
    session = load_lys(npz)
    ch = session.channel_index(CHANNEL)
    raw = session.data[:, ch]
    t = session.time
    fs = session.fs

    no_high = _apply_filter(raw, fs, btype="low", cutoff=FMAX)  # drop > 40 Hz
    no_low = _apply_filter(raw, fs, btype="high", cutoff=FMIN)  # drop < 0.5 Hz
    # Real clean() interpolates AFTER the 0.5–40 band-pass, not on raw.
    band = _apply_filter(raw, fs, btype="band", cutoff=[FMIN, FMAX])
    no_art = _remove_artifacts(band, fs)

    i_spike = int(np.argmax(np.abs(raw)))
    t_spike = float(t[i_spike])
    n_bad_raw = int(np.sum(np.abs(raw - np.median(raw)) > ARTIFACT_Z * 1.4826 * np.median(np.abs(raw - np.median(raw)))))
    band_med = np.median(band)
    band_mad = np.median(np.abs(band - band_med))
    n_bad_after_filter = int(np.sum(np.abs(band - band_med) > ARTIFACT_Z * 1.4826 * band_mad)) if band_mad > 0 else 0

    print(f"file     {npz.name}")
    print(f"session  {session.subject_id} / {session.study_id}")
    print(f"channel  {CHANNEL}")
    print()
    print("Same recording, one change at a time:")
    print(f"  raw                    max |x| = {np.max(np.abs(raw)):.4g}")
    print(f"  freqs > {FMAX:g} Hz gone      max |x| = {np.max(np.abs(no_high)):.4g}")
    print(f"  freqs < {FMIN:g} Hz gone      max |x| = {np.max(np.abs(no_low)):.4g}")
    print(f"  0.5–40 Hz only         max |x| = {np.max(np.abs(band)):.4g}")
    print(f"  then artifacts gone    max |x| = {np.max(np.abs(no_art)):.4g}")
    print()
    print(f"biggest raw jump at t={t_spike:.3f} s")
    print(f"  raw                    {raw[i_spike]:.4g}")
    print(f"  after 0.5–40 Hz filter {band[i_spike]:.4g}")
    print(f"  after artifact step    {no_art[i_spike]:.4g}")
    print(f"  samples flagged on raw: {n_bad_raw}  (after filter: {n_bad_after_filter})")

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(11, 8))
    fig.suptitle(f"one change at a time — {CHANNEL} — {session.subject_id}/{session.study_id}")

    # Fast jitter is small vs the big voltage; zoom + show the leftover.
    sl_hi = _window(t, float(t[0] + 20.0), 0.4)
    axes[0].plot(t[sl_hi], raw[sl_hi], color="0.55", lw=1.0, label="raw")
    axes[0].plot(t[sl_hi], no_high[sl_hi], color="C0", lw=1.3, label="> 40 Hz removed")
    cut_hi = raw[sl_hi] - no_high[sl_hi]
    ax0b = axes[0].twinx()
    ax0b.plot(t[sl_hi], cut_hi, color="C2", lw=0.9, alpha=0.75, label="what was cut (fast part)")
    ax0b.set_ylabel("cut out", color="C2")
    axes[0].set_title("1) remove frequencies over 40 Hz (zoomed; green = the jitter we dropped)")
    axes[0].set_ylabel("voltage")
    lines0, labels0 = axes[0].get_legend_handles_labels()
    lines0b, labels0b = ax0b.get_legend_handles_labels()
    axes[0].legend(lines0 + lines0b, labels0 + labels0b, loc="upper right", fontsize=8)

    sl_lo = _window(t, float(t[0] + 20.0), 6.0)
    axes[1].plot(t[sl_lo], raw[sl_lo], color="0.55", lw=1.0, label="raw")
    axes[1].plot(t[sl_lo], no_low[sl_lo], color="C1", lw=1.2, label="< 0.5 Hz removed")
    axes[1].set_title("2) remove frequencies under 0.5 Hz (slow wander / offset)")
    axes[1].set_ylabel("voltage")
    axes[1].legend(loc="upper right", fontsize=8)

    # Artifact step as in clean(): after the 0.5–40 filter, not on raw.
    sl_sp = _window(t, t_spike, 1.5)
    axes[2].plot(t[sl_sp], band[sl_sp], color="0.55", lw=1.0, label="after 0.5–40 Hz filter")
    axes[2].plot(t[sl_sp], no_art[sl_sp], color="C3", lw=1.3, label="then artifacts replaced")
    axes[2].set_title("3) replace crazy jumps (this step runs AFTER the filter)")
    axes[2].set_ylabel("voltage")
    axes[2].set_xlabel("time (s)")
    axes[2].legend(loc="upper right", fontsize=8)

    for ax in axes:
        ax.grid(True, alpha=0.25)

    fig.tight_layout()
    out = ROOT / "outputs" / "show_clean.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120)
    print(f"\nplot saved → {out}")
    if plt.get_backend().lower() != "agg":
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
