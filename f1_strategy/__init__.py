"""f1_strategy: a small, educational tyre-strategy modelling package.

This package estimates good Formula 1 pit-stop strategies from a simplified,
publicly-sourced approximation of tyre degradation, fuel-burn effect and
pit-lane time loss. It is NOT built on official Pirelli/F1 telemetry -- the
constants in `tracks.py` and `model.py` are illustrative approximations
based on publicly reported lap counts, pit-lane loss times and typical
compound deltas. See the README for sources and caveats.
"""

from .model import Tyre, Compound
from .tracks import TrackPreset, TRACKS
from .strategy import StrategyResult, best_strategies

__all__ = [
    "Tyre",
    "Compound",
    "TrackPreset",
    "TRACKS",
    "StrategyResult",
    "best_strategies",
]
