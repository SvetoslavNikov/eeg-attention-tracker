"""Signal cleaning for LYS EEGSession."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

from common.session import EEGSession


def clean(
    session: EEGSession,
    *,
    fmin: float = 0.5,
    fmax: float = 40.0,
    artifact_z: float = 8.0,
    interp_max_samples: int | None = None,
) -> EEGSession:
    """Band-pass and suppress large artifacts; return a new session.

    - Zero-phase Butterworth band-pass (``fmin``–``fmax`` Hz).
    - Samples with |x - median| > ``artifact_z`` * MAD (per channel) are
      linearly interpolated. Short spikes (cough-like) are removed without
      changing length or channel count.

    Absolute µV thresholds are not used (LYS exports are not calibrated).
    """
    x = np.array(session.data, dtype=np.float64, copy=True)
    fs = session.fs
    nyq = fs / 2.0
    low = max(fmin / nyq, 1e-6)
    high = min(fmax / nyq, 0.999)
    if high <= low:
        raise ValueError(f"invalid band-pass for fs={fs}: {fmin}-{fmax}")

    b, a = butter(4, [low, high], btype="band")
    # filtfilt needs enough samples
    padlen = min(3 * max(len(a), len(b)), x.shape[0] - 1)
    for ch in range(x.shape[1]):
        x[:, ch] = filtfilt(b, a, x[:, ch], padlen=padlen)

    if interp_max_samples is None:
        interp_max_samples = int(round(2.0 * fs))  # up to ~2 s bursts

    for ch in range(x.shape[1]):
        col = x[:, ch]
        med = np.median(col)
        mad = np.median(np.abs(col - med))
        if mad <= 0:
            continue
        # consistent with approx normal: sigma ≈ 1.4826 * MAD
        thr = artifact_z * 1.4826 * mad
        bad = np.abs(col - med) > thr
        if not np.any(bad):
            continue
        x[:, ch] = _interp_mask(col, bad, max_run=interp_max_samples)

    return session.replace(data=x)


def _interp_mask(col: np.ndarray, bad: np.ndarray, *, max_run: int) -> np.ndarray:
    """Interpolate bad samples; leave long bad runs unchanged (masked as med)."""
    out = col.copy()
    n = len(col)
    good = ~bad
    if not np.any(good):
        return out

    # mark runs longer than max_run as "don't interp from neighbors" → set to median of good
    i = 0
    long_bad = np.zeros(n, dtype=bool)
    while i < n:
        if not bad[i]:
            i += 1
            continue
        j = i
        while j < n and bad[j]:
            j += 1
        if (j - i) > max_run:
            long_bad[i:j] = True
        i = j

    interp_bad = bad & ~long_bad
    idx = np.arange(n)
    if np.any(interp_bad):
        out[interp_bad] = np.interp(idx[interp_bad], idx[good], col[good])
    if np.any(long_bad):
        out[long_bad] = float(np.median(col[good]))
    return out
