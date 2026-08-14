"""Plot attention score and band-power traces."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from common.session import EEGSession
from score.attention import AttentionResult


def plot_attention(
    result: AttentionResult,
    session: EEGSession | None = None,
    *,
    save_path: str | Path | None = None,
    title: str | None = None,
) -> None:
    """Plot attention(t) and relative alpha/theta."""
    import matplotlib

    if save_path is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)

    axes[0].plot(result.t, result.attention, color="C0", lw=1.2)
    axes[0].axhline(0.0, color="k", lw=0.6, alpha=0.4)
    axes[0].set_ylabel("attention (z)")
    axes[0].set_title(
        title
        or f"Attention score — {result.subject_id} / {result.study_id}"
    )
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(result.t, result.alpha_rel, label="alpha / baseline", color="C1")
    axes[1].plot(result.t, result.theta_rel, label="theta / baseline", color="C2")
    axes[1].axhline(1.0, color="k", lw=0.6, alpha=0.4)
    axes[1].set_ylabel("rel. power")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(result.t, result.alpha, label="alpha", color="C1", alpha=0.9)
    axes[2].plot(result.t, result.theta, label="theta", color="C2", alpha=0.9)
    axes[2].set_yscale("log")
    axes[2].set_ylabel("abs. power")
    axes[2].set_xlabel("time (s)")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].grid(True, alpha=0.25)

    if session is not None:
        colors = {"baseline": "0.7", "localizer": "C3", "task": "C4"}
        for ax in axes:
            for name, (a, b) in session.phases.items():
                ax.axvspan(a, b, alpha=0.12, color=colors.get(name, "C5"), label=name)
        # de-duplicate legend labels on top axis
        handles, labels = axes[0].get_legend_handles_labels()
        if labels:
            by = dict(zip(labels, handles))
            axes[0].legend(by.values(), by.keys(), loc="upper right", fontsize=8)

    fig.tight_layout()
    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()
