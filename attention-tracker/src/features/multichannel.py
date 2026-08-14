"""Run sliding band power on LYS 4-channel sessions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from common.session import EEGSession
from features.band_power import sliding_band_powers
from features.bands import ATTENTION_BANDS


@dataclass(frozen=True)
class SessionBandPowers:
    """Band power over time for a multi-channel session.

    Attributes:
        t: Window center times in EEG seconds (aligned to session.time[0]).
        powers: dict band_name -> array (n_windows,) — mean over selected channels.
        per_channel: dict channel -> dict band -> (n_windows,)
        window_sec: Window length used.
        hop_sec: Hop used.
    """

    t: np.ndarray
    powers: dict[str, np.ndarray]
    per_channel: dict[str, dict[str, np.ndarray]]
    window_sec: float
    hop_sec: float


def session_band_powers(
    session: EEGSession,
    *,
    channels: Sequence[str] | None = None,
    window_sec: float = 2.0,
    hop_sec: float = 0.5,
    bands: Mapping[str, tuple[float, float]] | None = None,
) -> SessionBandPowers:
    """Sliding band power; average selected channels into one power series per band.

    Default channels: AF3, AF4 (frontal pair for engagement-style features).
    ``offset_sec`` from the 1D scorer is relative to sample 0; we shift by
    ``session.time[0]`` so times match EEG / phase axes.
    """
    band_map = dict(bands) if bands is not None else dict(ATTENTION_BANDS)
    ch_list = list(channels) if channels is not None else ["AF3", "AF4"]

    per_channel: dict[str, dict[str, np.ndarray]] = {}
    t_rel: np.ndarray | None = None

    for name in ch_list:
        idx = session.channel_index(name)
        sig = session.data[:, idx]
        results = sliding_band_powers(
            sig,
            sfreq=session.fs,
            window_sec=window_sec,
            hop_sec=hop_sec,
            bands=band_map,
        )
        if not results:
            raise ValueError(f"no windows for channel {name}")
        # use window center: start + window/2
        if t_rel is None:
            t_rel = np.array(
                [r.offset_sec + 0.5 * window_sec for r in results], dtype=np.float64
            )
        per_channel[name] = {
            b: np.array([r.powers[b] for r in results], dtype=np.float64)
            for b in band_map
        }

    assert t_rel is not None
    t = t_rel + float(session.time[0])

    powers: dict[str, np.ndarray] = {}
    for b in band_map:
        stack = np.stack([per_channel[ch][b] for ch in ch_list], axis=0)
        powers[b] = np.mean(stack, axis=0)

    return SessionBandPowers(
        t=t,
        powers=powers,
        per_channel=per_channel,
        window_sec=window_sec,
        hop_sec=hop_sec,
    )
