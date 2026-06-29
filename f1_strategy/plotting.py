"""Build the Plotly figure for a chosen strategy."""

from __future__ import annotations

import json

import numpy as np
import plotly
import plotly.graph_objects as go

from .model import CLIFF_AGE, Compound, fuel_correction, lap_time_array
from .strategy import StrategyResult
from .tracks import TrackPreset

COMPOUND_COLOR = {
    Compound.SOFT: "#e10600",   # F1 soft red
    Compound.MEDIUM: "#ffd700",  # medium yellow
    Compound.HARD: "#f5f5f5",   # hard white (outlined so it's visible)
}
COMPOUND_LINE = {
    Compound.SOFT: dict(color=COMPOUND_COLOR[Compound.SOFT], width=3),
    Compound.MEDIUM: dict(color=COMPOUND_COLOR[Compound.MEDIUM], width=3),
    Compound.HARD: dict(color="#bbbbbb", width=3, dash="solid"),
}


def stint_boundaries(result: StrategyResult, laps: int) -> list[tuple[int, int]]:
    """Return (start_lap, end_lap) 1-indexed inclusive ranges for each stint."""
    bounds = [0, *result.pit_laps, laps]
    return [(bounds[i] + 1, bounds[i + 1]) for i in range(len(bounds) - 1)]


def build_figure(result: StrategyResult, track: TrackPreset) -> go.Figure:
    fig = go.Figure()
    boundaries = stint_boundaries(result, track.laps)

    for stint_idx, ((start, end), compound_str) in enumerate(zip(boundaries, result.compounds)):
        compound = Compound(compound_str)
        ages = np.arange(end - start + 1)
        raw = lap_time_array(compound, ages, track)
        absolute_laps = np.arange(start, end + 1)
        laps_remaining = track.laps - absolute_laps
        corrected = raw - fuel_correction(laps_remaining)

        fig.add_trace(
            go.Scatter(
                x=absolute_laps,
                y=corrected,
                mode="lines+markers",
                name=f"Stint {stint_idx + 1}: {compound.value}",
                line=COMPOUND_LINE[compound],
                marker=dict(size=5),
            )
        )

        # Shade the danger zone: laps after the compound's cliff age where
        # degradation accelerates quadratically. The cliff penalty first
        # applies at age = cliff_age + 1, so we shade from cliff_age + 0.5.
        cliff_absolute = start + CLIFF_AGE[compound]
        if cliff_absolute < end:
            fig.add_vrect(
                x0=cliff_absolute + 0.5,
                x1=end + 0.5,
                fillcolor="rgba(255, 100, 0, 0.13)",
                line_width=0,
                annotation_text=f"{compound.value} cliff ⚠",
                annotation_position="top left",
                annotation_font_color="#f97316",
                annotation_font_size=10,
            )

    for pit_lap in result.pit_laps:
        fig.add_vline(
            x=pit_lap + 0.5,
            line=dict(color="#888", dash="dot", width=1.5),
            annotation_text="PIT",
            annotation_position="top",
        )

    fig.update_layout(
        title=f"{track.name}: {result.label} ({result.stops}-stop)",
        xaxis_title="Lap",
        yaxis_title="Lap time (s, fuel-corrected)",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=70, b=40),
    )
    return fig


def figure_to_json(fig: go.Figure) -> str:
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
