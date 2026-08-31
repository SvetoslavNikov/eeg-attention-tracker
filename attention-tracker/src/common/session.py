"""Continuous EEG session object (LYS Flow or other adapters)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

CANONICAL_CHANNELS: tuple[str, str, str, str] = ("AF4", "AF3", "FCz", "CPz")


@dataclass(frozen=True)
class EEGSession:
    """One continuous EEG recording.

    LYS Flow sessions still use channels AF4, AF3, FCz, CPz in that order.
    Other adapters (e.g. OpenBCI) may use any channel count and names.

    Attributes:
        data: Samples x channels, shape (n_samples, n_channels), float64.
        fs: Sampling rate in Hz.
        ch_names: Channel names; length must match ``data.shape[1]``.
        time: Sample times in seconds, shape (n_samples,).
        subject_id: e.g. \"P33\".
        study_id: Study / file descriptor id.
        phases: Named intervals in seconds on the same axis as ``time``,
            e.g. {\"baseline\": (t0, t1), \"listen\": (...), \"wander\": (...)}.
            Empty dict if no protocol log was provided.
        source_path: Path this was loaded from.
        meta: Adapter-specific extras (dropped channels, board, …).
    """

    data: np.ndarray
    fs: float
    ch_names: tuple[str, ...]
    time: np.ndarray
    subject_id: str
    study_id: str
    phases: dict[str, tuple[float, float]] = field(default_factory=dict)
    source_path: str = ""
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", np.asarray(self.data, dtype=np.float64))
        object.__setattr__(self, "time", np.asarray(self.time, dtype=np.float64))
        object.__setattr__(self, "fs", float(self.fs))
        object.__setattr__(self, "ch_names", tuple(self.ch_names))
        object.__setattr__(self, "phases", dict(self.phases))
        object.__setattr__(self, "meta", dict(self.meta))
        self.validate()

    def validate(self) -> None:
        if self.data.ndim != 2 or self.data.shape[1] < 1:
            raise ValueError(f"data must be (n, n_ch>=1), got {self.data.shape}")
        if len(self.ch_names) != self.data.shape[1]:
            raise ValueError(
                f"ch_names length {len(self.ch_names)} != n_channels {self.data.shape[1]}"
            )
        if len(set(self.ch_names)) != len(self.ch_names):
            raise ValueError(f"duplicate channel names: {self.ch_names}")
        if any(not str(n) for n in self.ch_names):
            raise ValueError(f"channel names must be non-empty strings, got {self.ch_names}")
        if self.fs <= 0:
            raise ValueError(f"fs must be > 0, got {self.fs}")
        if self.time.shape != (self.data.shape[0],):
            raise ValueError(
                f"time length {self.time.shape} != n_samples {self.data.shape[0]}"
            )
        if not np.isfinite(self.data).all():
            raise ValueError("data contains non-finite values")
        n = self.data.shape[0]
        duration = float(self.time[-1] - self.time[0]) if n > 1 else 0.0
        t0 = float(self.time[0])
        t1 = float(self.time[-1]) if n else t0
        for name, (a, b) in self.phases.items():
            if b < a:
                raise ValueError(f"phase {name!r}: end < start ({a}, {b})")
            # allow slight overhang; hard-fail only if completely outside
            if b < t0 or a > t1:
                raise ValueError(
                    f"phase {name!r} ({a}, {b}) outside recording [{t0}, {t1}]"
                )
        _ = duration

    @property
    def n_samples(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[1])

    @property
    def duration_sec(self) -> float:
        if self.n_samples < 2:
            return 0.0
        return float(self.time[-1] - self.time[0])

    def channel_index(self, name: str) -> int:
        try:
            return self.ch_names.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc

    def replace(self, **kwargs) -> EEGSession:
        """Return a copy with selected fields replaced."""
        base = {
            "data": self.data,
            "fs": self.fs,
            "ch_names": self.ch_names,
            "time": self.time,
            "subject_id": self.subject_id,
            "study_id": self.study_id,
            "phases": self.phases,
            "source_path": self.source_path,
            "meta": self.meta,
        }
        base.update(kwargs)
        return EEGSession(**base)
