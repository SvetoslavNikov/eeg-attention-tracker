"""LYS continuous EEG session object."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

CANONICAL_CHANNELS: tuple[str, str, str, str] = ("AF4", "AF3", "FCz", "CPz")


@dataclass(frozen=True)
class EEGSession:
    """One LYS Flow 4-channel EEG recording.

    Attributes:
        data: Samples x channels, shape (n_samples, 4), float64.
        fs: Sampling rate in Hz.
        ch_names: Always AF4, AF3, FCz, CPz in that order.
        time: Sample times in seconds, shape (n_samples,).
        subject_id: e.g. \"P33\".
        study_id: LYS study / file descriptor id.
        phases: Named intervals in seconds on the same axis as ``time``,
            e.g. {\"baseline\": (t0, t1), \"localizer\": (...), \"task\": (...)}.
            Empty dict if no protocol log was provided.
        source_path: Path to the .npz this was loaded from.

        example:
    data.shape  : (644381, 4)  dtype=float64
    fs           : 500.000158 Hz
    ch_names     : ('AF4', 'AF3', 'FCz', 'CPz')
    time[0],[-1] : -0.246646, 1288.512947
    subject_id   : P33
    study_id     : bb05ebe
    phases       :
        baseline  [    3.38,    63.40]  (60.0 s)
        localizer [   63.40,   231.87]  (168.5 s)
        task      [  233.48,  1284.67]  (1051.2 s)
    source_path  : ...
    """

    data: np.ndarray
    fs: float
    ch_names: tuple[str, str, str, str]
    time: np.ndarray  # -0.246646, 1288.512947
    subject_id: str
    study_id: str
    phases: dict[str, tuple[float, float]] = field(default_factory=dict)
    source_path: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", np.asarray(self.data, dtype=np.float64))
        object.__setattr__(self, "time", np.asarray(self.time, dtype=np.float64))
        object.__setattr__(self, "fs", float(self.fs))
        object.__setattr__(self, "ch_names", tuple(self.ch_names))
        self.validate()

    def validate(self) -> None:
        if self.data.ndim != 2 or self.data.shape[1] != 4:
            raise ValueError(f"data must be (n, 4), got {self.data.shape}")
        if self.ch_names != CANONICAL_CHANNELS:
            raise ValueError(
                f"ch_names must be {CANONICAL_CHANNELS}, got {self.ch_names}"
            )
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
        }
        base.update(kwargs)
        return EEGSession(**base)
