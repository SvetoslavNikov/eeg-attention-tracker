"""Return types for sliding band-power analysis.

Ported from old_stuff/old_code_for_band_power/types.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BandWindowResult:
    """One sliding window of band-power scores.

    Attributes:
        block: 0-based window index.
        offset_samples: Start index of this window in the original signal.
        offset_sec: Start time in seconds (offset_samples / sfreq).
        powers: Absolute band power per wave name, e.g. {"alpha": 12.3, ...}.
    """

    block: int
    offset_samples: int
    offset_sec: float
    powers: dict[str, float]
