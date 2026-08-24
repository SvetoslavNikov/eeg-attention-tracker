"""Interactive attention plot (Plotly)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common.session import EEGSession
from score.attention import AttentionResult

PHASE_COLORS = {
    "baseline": "#94a3b8",
    "localizer": "#fb7185",
    "task": "#38bdf8",
}

_PLOT_CONFIG = {
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToAdd": ["v1hovermode"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "attention_score",
        "height": 900,
        "width": 1600,
        "scale": 2,
    },
}


def plot_attention(
    result: AttentionResult,
    session: EEGSession | None = None,
    *,
    save_path: str | Path | None = None,
    title: str | None = None,
    show: bool = True,
) -> Path | None:
    """Open (and optionally save) an interactive attention figure.

    Hover for exact values, scroll to zoom, drag to pan. Default Y range is
    the typical 1–99% band so leftover artifact spikes do not flatten the
    score; use the **Full range** button to see them.
    """
    fig = _build_figure(result, session, title=title)

    path: Path | None = None
    if save_path is not None:
        path = Path(save_path)
        if path.suffix.lower() != ".html":
            path = path.with_suffix(".html")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(
            str(path),
            include_plotlyjs=True,
            full_html=True,
            config=_PLOT_CONFIG,
            auto_open=show,
        )
    elif show:
        fig.show(config=_PLOT_CONFIG)
    return path


def _build_figure(
    result: AttentionResult,
    session: EEGSession | None,
    *,
    title: str | None,
) -> go.Figure:
    t_min = np.asarray(result.t, dtype=np.float64) / 60.0
    clock = _mmss_labels(result.t)

    att_range = _robust_range(result.attention, force_include=0.0)
    rel_range = _robust_range(
        np.concatenate([result.alpha_rel, result.theta_rel]),
        force_include=1.0,
    )
    abs_range = _robust_log_range(np.concatenate([result.alpha, result.theta]))
    att_full = _full_range(result.attention, force_include=0.0)
    rel_full = _full_range(
        np.concatenate([result.alpha_rel, result.theta_rel]),
        force_include=1.0,
    )
    abs_full = _full_log_range(np.concatenate([result.alpha, result.theta]))

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=(
            "Attention (z) — cropped to typical range",
            "Power vs this person's rest (1 = baseline)",
            "Absolute band power",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=t_min,
            y=result.attention,
            customdata=clock,
            name="attention",
            line=dict(color="#2563eb", width=1.6),
            hovertemplate="<b>%{customdata}</b><br>attention (z): %{y:.2f}<extra>attention</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=0.0, line_width=1, line_color="#111827", opacity=0.35, row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=t_min,
            y=result.alpha_rel,
            customdata=clock,
            name="alpha / rest",
            line=dict(color="#d97706", width=1.4),
            hovertemplate="<b>%{customdata}</b><br>alpha / rest: %{y:.2f}<extra>alpha / rest</extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t_min,
            y=result.theta_rel,
            customdata=clock,
            name="theta / rest",
            line=dict(color="#059669", width=1.4),
            hovertemplate="<b>%{customdata}</b><br>theta / rest: %{y:.2f}<extra>theta / rest</extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=1.0, line_width=1, line_color="#111827", opacity=0.35, row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=t_min,
            y=result.alpha,
            customdata=clock,
            name="alpha power",
            line=dict(color="#d97706", width=1.3),
            hovertemplate="<b>%{customdata}</b><br>alpha power: %{y:.3e}<extra>alpha power</extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t_min,
            y=result.theta,
            customdata=clock,
            name="theta power",
            line=dict(color="#059669", width=1.3),
            hovertemplate="<b>%{customdata}</b><br>theta power: %{y:.3e}<extra>theta power</extra>",
        ),
        row=3,
        col=1,
    )

    if session is not None:
        _add_phases(fig, session)

    heading = title or f"Attention — {result.subject_id} / {result.study_id}"
    fig.update_layout(
        template="plotly_white",
        title=dict(
            text=(
                f"{heading}<br>"
                "<sup>Scroll = zoom · drag = pan · hover = values · "
                "camera icon = PNG · Full range = artifact spikes</sup>"
            ),
            x=0.02,
            xanchor="left",
        ),
        height=880,
        width=1400,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.0),
        margin=dict(t=110, l=70, r=30, b=60),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=1.0,
                xanchor="right",
                y=1.16,
                yanchor="top",
                buttons=[
                    dict(
                        label="Typical range",
                        method="relayout",
                        args=[
                            {
                                "yaxis.range": att_range,
                                "yaxis2.range": rel_range,
                                "yaxis3.range": _log10_range(abs_range),
                                "yaxis3.type": "log",
                            }
                        ],
                    ),
                    dict(
                        label="Full range (spikes)",
                        method="relayout",
                        args=[
                            {
                                "yaxis.range": att_full,
                                "yaxis2.range": rel_full,
                                "yaxis3.range": _log10_range(abs_full),
                                "yaxis3.type": "log",
                            }
                        ],
                    ),
                ],
            )
        ],
    )

    fig.update_xaxes(showspikes=True, spikemode="across", spikethickness=1)
    fig.update_xaxes(title_text="Time (minutes)", row=3, col=1)
    fig.update_yaxes(title_text="z", range=att_range, row=1, col=1, zeroline=False)
    fig.update_yaxes(title_text="× baseline", range=rel_range, row=2, col=1)
    fig.update_yaxes(
        title_text="power",
        type="log",
        range=_log10_range(abs_range),
        row=3,
        col=1,
    )
    return fig


def _add_phases(fig: go.Figure, session: EEGSession) -> None:
    for name, (start, end) in session.phases.items():
        color = PHASE_COLORS.get(name, "#a78bfa")
        for row in (1, 2, 3):
            extra = {}
            if row == 1:
                extra = dict(
                    annotation_text=name,
                    annotation_position="top left",
                    annotation_font_size=11,
                    annotation_font_color="#334155",
                )
            fig.add_vrect(
                x0=start / 60.0,
                x1=end / 60.0,
                fillcolor=color,
                opacity=0.12,
                line_width=0,
                layer="below",
                row=row,
                col=1,
                **extra,
            )


def _mmss_labels(t_sec: np.ndarray) -> list[str]:
    labels: list[str] = []
    for raw in np.asarray(t_sec, dtype=np.float64):
        sign = "-" if raw < 0 else ""
        t = abs(float(raw))
        minutes = int(t // 60.0)
        seconds = t % 60.0
        labels.append(f"{sign}{minutes}:{seconds:04.1f}")
    return labels


def _robust_range(
    y: np.ndarray,
    *,
    pad: float = 0.12,
    force_include: float | None = None,
) -> list[float]:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return [-1.0, 1.0]
    lo, hi = np.percentile(y, [1.0, 99.0])
    if force_include is not None:
        lo = min(lo, force_include)
        hi = max(hi, force_include)
    if hi <= lo:
        hi = lo + 1.0
    span = hi - lo
    return [float(lo - pad * span), float(hi + pad * span)]


def _full_range(
    y: np.ndarray,
    *,
    pad: float = 0.06,
    force_include: float | None = None,
) -> list[float]:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return [-1.0, 1.0]
    lo, hi = float(np.min(y)), float(np.max(y))
    if force_include is not None:
        lo = min(lo, force_include)
        hi = max(hi, force_include)
    if hi <= lo:
        hi = lo + 1.0
    span = hi - lo
    return [lo - pad * span, hi + pad * span]


def _full_log_range(y: np.ndarray) -> list[float]:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y) & (y > 0)]
    if y.size == 0:
        return [1.0, 10.0]
    lo, hi = float(np.min(y)), float(np.max(y))
    lo = max(lo, hi * 1e-6)
    return [lo / 1.2, hi * 1.2]


def _robust_log_range(y: np.ndarray) -> list[float]:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y) & (y > 0)]
    if y.size == 0:
        return [1.0, 10.0]
    lo, hi = np.percentile(y, [1.0, 99.0])
    lo = max(float(lo), float(hi) * 1e-4)
    hi = max(float(hi), lo * 1.01)
    return [lo / 1.5, hi * 1.5]


def _log10_range(linear: list[float]) -> list[float]:
    lo, hi = linear
    lo = max(lo, 1e-30)
    hi = max(hi, lo * 1.01)
    return [float(np.log10(lo)), float(np.log10(hi))]
