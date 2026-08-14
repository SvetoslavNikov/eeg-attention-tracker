"""Sliding-window band power over a 1D EEG-like signal.

Ported from old_stuff/old_code_for_band_power/sliding.py.

Pure function: numbers in, list of BandWindowResult out.
No file I/O, no plotting.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from features.bands import DEFAULT_BANDS
from features.types import BandWindowResult
"""
from __future__ import annotations

# name -> (fmin_hz, fmax_hz), half-open: fmin <= f < fmax
DEFAULT_BANDS: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}

# Bands used for the attention score (signal-only v1).
ATTENTION_BANDS: dict[str, tuple[float, float]] = {
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
}



"""
__all__ = ["DEFAULT_BANDS", "BandWindowResult", "sliding_band_powers"]


def sliding_band_powers(
    signal: Sequence[float] | np.ndarray,
    sfreq: float,
    window_sec: float = 2.0,
    hop_sec: float = 0.5,
    bands: Mapping[str, tuple[float, float]] | None = None,
) -> list[BandWindowResult]:
    """Slide a Hann-windowed FFT across signal and score each brain-wave band.

    Absolute band power is the mean of the one-sided periodogram bins that fall
    inside each band's frequency range (after DC removal and Hann tapering).
    """
    if sfreq <= 0:
        raise ValueError(f"sfreq must be > 0, got {sfreq}")
    if window_sec <= 0:
        raise ValueError(f"window_sec must be > 0, got {window_sec}")
    if hop_sec <= 0:
        raise ValueError(f"hop_sec must be > 0, got {hop_sec}")

    x = np.asarray(signal, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"signal must be 1D, got shape {x.shape}")

    window_samples = int(round(window_sec * sfreq))
    hop_samples = int(round(hop_sec * sfreq))
    if window_samples < 2:
        raise ValueError(
            f"window too short: window_sec={window_sec}, sfreq={sfreq} "
            f"-> {window_samples} samples (need >= 2)"
        )
    if hop_samples < 1:
        raise ValueError(
            f"hop too short: hop_sec={hop_sec}, sfreq={sfreq} -> {hop_samples} samples"
        )
    if len(x) < window_samples:
        raise ValueError(
            f"signal length {len(x)} is shorter than window_samples {window_samples}"
        )

    band_map = dict(bands) if bands is not None else dict(DEFAULT_BANDS)
    nyquist = sfreq / 2.0

    hann = np.hanning(window_samples)
    window_power = float(np.mean(hann**2))
    if window_power <= 0:
        raise RuntimeError("invalid Hann window power")

    results: list[BandWindowResult] = []
    block = 0
    start = 0
    n = len(x)

    while start + window_samples <= n:
        chunk = x[start : start + window_samples]
        chunk = chunk - np.mean(chunk)
        chunk = chunk * hann

        powers = _absolute_band_powers(
            chunk,
            sfreq=sfreq,
            bands=band_map,
            nyquist=nyquist,
            window_power=window_power,
        )

        results.append(
            BandWindowResult(
                block=block,
                offset_samples=start,
                offset_sec=start / sfreq,
                powers=powers,
            )
        )
        block += 1
        start += hop_samples

    return results


def _absolute_band_powers(
    windowed_chunk: np.ndarray,
    *,
    sfreq: float,
    bands: Mapping[str, tuple[float, float]],
    nyquist: float,
    window_power: float,
) -> dict[str, float]:
    """One-sided periodogram mean power per band (absolute, not relative)."""
    n = len(windowed_chunk)
    frequency_spectrum = np.fft.rfft(windowed_chunk)
    amplitude_spectrum = np.abs(frequency_spectrum)
    power_spectrum = amplitude_spectrum**2
    power_spectrum = power_spectrum / n
    power_spectrum = power_spectrum / window_power

    if n % 2 == 1:
        power_spectrum[1:] *= 2.0
    else:
        power_spectrum[1:-1] *= 2.0

    tested_freqs_hz = np.fft.rfftfreq(n, d=1.0 / sfreq)

    out: dict[str, float] = {}
    for name, (fmin, fmax) in bands.items():
        band_low_hz = max(0.0, float(fmin))
        band_high_hz = min(float(fmax), nyquist)
        if band_high_hz <= band_low_hz:
            out[name] = 0.0
            continue
        mask = (tested_freqs_hz >= band_low_hz) & (tested_freqs_hz < band_high_hz)
        if not np.any(mask):
            out[name] = 0.0
            continue
        out[name] = float(np.mean(power_spectrum[mask]))
    return out
