"""Canonical EEG frequency bands (Hz).

Ported from old_stuff/old_code_for_band_power/bands.py.
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
