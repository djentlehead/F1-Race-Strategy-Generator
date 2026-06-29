"""Monte Carlo race simulation.

`strategy.py` answers "which strategy has the lowest *expected* total time,
assuming a clean, deterministic race?" That's a reasonable first answer,
but real races aren't deterministic -- lap times vary a little from lap to
lap, and a safety car can turn a marginal strategy into the winning one (or
vice versa) depending on exactly when it falls.

This module runs many randomized trials of the *same* race and reports, per
candidate strategy, a win probability (how often it had the lowest total
time) alongside its time distribution -- not just one number.

Two things make the comparison fair and the result meaningful:

1. **Common random numbers.** Within a single trial, every candidate
   strategy experiences the *same* lap-noise draw and the *same"
   safety-car event (if any). Without this, two strategies could differ
   just because they "got" different random conditions, which would be
   noise pretending to be signal. With it, the only thing that varies
   between strategies in a trial is how *that* strategy's own pit laps
   happen to interact with *that* trial's conditions -- which is exactly
   the thing we want to measure.
2. **A "free pit stop" mechanic.** Under a safety car the whole field
   slows down together, so the time lost pitting is much smaller than
   under green-flag conditions. A strategy that happens to need a stop
   while the safety car it didn't know was coming is out gets a discount
   on that stop, in that trial. Across thousands of trials this surfaces
   *why* real strategists sometimes prefer a stop that looks slightly
   worse on paper: it has more chances to get lucky.

All of the random-process parameters below (lap-time noise, safety car
pace penalty, safety car pit-stop discount, safety car duration) are
illustrative estimates, not fit to data -- see the module docstring in
`tracks.py` for the same caveat on `sc_probability`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import Compound, fuel_correction, lap_time_array
from .strategy import StrategyResult
from .tracks import TrackPreset


@dataclass(frozen=True)
class SimulationConfig:
    n_trials: int = 4000
    lap_noise_std: float = 0.25  # seconds, illustrative per-lap execution/traffic noise
    sc_pace_factor: float = 1.35  # lap time multiplier while a safety car is out
    sc_pit_discount: float = 0.35  # pit_loss multiplier for a stop taken under a safety car
    sc_min_duration: int = 3  # laps
    sc_max_duration: int = 6  # laps
    seed: int | None = None


@dataclass(frozen=True)
class StrategySimResult:
    strategy: StrategyResult
    win_probability: float
    mean_time: float
    std_time: float
    p10_time: float
    p50_time: float
    p90_time: float

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.to_dict(),
            "win_probability": round(self.win_probability, 4),
            "mean_time": round(self.mean_time, 2),
            "std_time": round(self.std_time, 2),
            "p10_time": round(self.p10_time, 2),
            "p50_time": round(self.p50_time, 2),
            "p90_time": round(self.p90_time, 2),
        }


def per_lap_clean_times(strategy: StrategyResult, track: TrackPreset) -> np.ndarray:
    """Deterministic, fuel-corrected lap time for every lap of the race.

    Mirrors the cumulative-time math in `strategy.py` lap-by-lap instead of
    as a running total, so Monte Carlo noise and safety-car effects can be
    applied per lap before being summed back up.
    """
    boundaries = [0] + list(strategy.pit_laps) + [track.laps]
    out = np.empty(track.laps, dtype=float)
    for compound_str, start, end in zip(strategy.compounds, boundaries[:-1], boundaries[1:]):
        compound = Compound.from_str(compound_str)
        ages = np.arange(end - start)
        out[start:end] = lap_time_array(compound, ages, track)

    lap_numbers = np.arange(1, track.laps + 1)
    laps_remaining_after = track.laps - lap_numbers
    out = out - fuel_correction(laps_remaining_after)
    return out


def simulate_strategies(
    track: TrackPreset,
    strategies: list[StrategyResult],
    config: SimulationConfig | None = None,
) -> list[StrategySimResult]:
    """Run a Monte Carlo race simulation comparing `strategies` head-to-head.

    Returns one `StrategySimResult` per input strategy, in the same order.
    """
    if not strategies:
        return []
    config = config or SimulationConfig()
    rng = np.random.default_rng(config.seed)
    laps = track.laps
    n_strategies = len(strategies)
    n_trials = config.n_trials

    clean = np.stack([per_lap_clean_times(s, track) for s in strategies])  # (n_strategies, laps)

    # Shared (common-random-number) draws across all strategies in a trial.
    noise = rng.normal(0.0, config.lap_noise_std, size=(n_trials, laps))

    sc_occurs = rng.random(n_trials) < track.sc_probability
    lo, hi = 2, max(laps - 3, 2)
    if hi > lo:
        sc_start = rng.integers(lo, hi, size=n_trials)
    else:
        sc_start = np.ones(n_trials, dtype=int)
        sc_occurs = np.zeros(n_trials, dtype=bool)
    sc_length = rng.integers(config.sc_min_duration, config.sc_max_duration + 1, size=n_trials)

    lap_numbers = np.arange(1, laps + 1)
    sc_mask = (
        sc_occurs[:, None]
        & (lap_numbers[None, :] >= sc_start[:, None])
        & (lap_numbers[None, :] < sc_start[:, None] + sc_length[:, None])
    )  # (n_trials, laps)

    sc_time_add = track.base_lap_time * (config.sc_pace_factor - 1.0)
    lap_times = (
        clean[:, None, :]
        + noise[None, :, :]
        + np.where(sc_mask, sc_time_add, 0.0)[None, :, :]
    )  # (n_strategies, n_trials, laps)
    race_time = lap_times.sum(axis=2)  # (n_strategies, n_trials)

    pit_loss = np.zeros((n_strategies, n_trials))
    for i, strat in enumerate(strategies):
        for pit_lap in strat.pit_laps:
            under_sc = sc_mask[:, pit_lap - 1]
            pit_loss[i] += np.where(under_sc, track.pit_loss * config.sc_pit_discount, track.pit_loss)

    total_time = race_time + pit_loss  # (n_strategies, n_trials)
    winners = np.argmin(total_time, axis=0)  # (n_trials,)

    results = []
    for i, strat in enumerate(strategies):
        times = total_time[i]
        results.append(
            StrategySimResult(
                strategy=strat,
                win_probability=float(np.mean(winners == i)),
                mean_time=float(times.mean()),
                std_time=float(times.std()),
                p10_time=float(np.percentile(times, 10)),
                p50_time=float(np.percentile(times, 50)),
                p90_time=float(np.percentile(times, 90)),
            )
        )
    return results
