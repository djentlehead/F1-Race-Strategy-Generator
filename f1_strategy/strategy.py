"""Strategy search: brute-force but vectorised with numpy.

A "strategy" is a sequence of stints (compound + stint length), separated by
pit stops. We search over 1-stop strategies (2 stints) and 2-stop
strategies (3 stints), enforce the real FIA rule that a dry race must use
at least two different compounds, and rank everything by total race time
(pit-lane loss included, fuel-burn benefit included).

Performance note: rather than re-summing lap times for every candidate
pit lap in a Python loop (the original O(laps^2) implementation), we
precompute a cumulative-time table per compound with `np.cumsum` once,
so the cost of *any* stint length is an O(1) array lookup. The 2-stop
search is then a vectorised, broadcasted sum over an upper-triangular
grid of pit laps for each of the (up to 24) valid compound triples,
instead of a triple-nested loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product

import numpy as np

from .model import Compound, FUEL_EFFECT_PER_LAP, lap_time_array
from .tracks import TrackPreset


@dataclass(frozen=True)
class StrategyResult:
    stops: int
    compounds: tuple[str, ...]
    pit_laps: tuple[int, ...]  # lap number (1-indexed) *after* which each stop happens
    total_time: float

    @property
    def label(self) -> str:
        return " → ".join(self.compounds)

    def to_dict(self) -> dict:
        return {
            "stops": self.stops,
            "compounds": list(self.compounds),
            "pit_laps": list(self.pit_laps),
            "total_time": self.total_time,
            "label": self.label,
        }


def _cumulative_time(compound: Compound, max_laps: int, track: TrackPreset) -> np.ndarray:
    """cum[k] = time (s) to run k consecutive laps on a fresh tyre of `compound`."""
    ages = np.arange(max_laps)
    laps = lap_time_array(compound, ages, track)
    return np.concatenate([[0.0], np.cumsum(laps)])


def _total_fuel_benefit(laps: int) -> float:
    """Total seconds saved race-wide from fuel burn-off.

    This depends only on the absolute lap number, not on which tyre is
    fitted, so it is a constant offset across every strategy -- it doesn't
    change which strategy is *best*, but it matters for reporting a
    realistic total race time.
    """
    laps_remaining_after_each_lap = np.arange(laps - 1, -1, -1)
    return float(FUEL_EFFECT_PER_LAP * laps_remaining_after_each_lap.sum())


def _valid_compound_tuples(length: int) -> list[tuple[Compound, ...]]:
    """All compound sequences of given length using >= 2 distinct compounds (FIA rule)."""
    all_tuples = product(list(Compound), repeat=length)
    return [t for t in all_tuples if len(set(t)) >= 2]


def optimize_one_stop(track: TrackPreset, cum: dict[Compound, np.ndarray]) -> StrategyResult:
    laps = track.laps
    best: StrategyResult | None = None
    pit_lap = np.arange(1, laps)  # laps run on first compound, 1..laps-1
    for c1, c2 in permutations(Compound, 2):
        stint1 = cum[c1][pit_lap]
        stint2 = cum[c2][laps - pit_lap]
        total = stint1 + stint2 + track.pit_loss
        idx = int(np.argmin(total))
        candidate = StrategyResult(
            stops=1,
            compounds=(c1.value, c2.value),
            pit_laps=(int(pit_lap[idx]),),
            total_time=float(total[idx]),
        )
        if best is None or candidate.total_time < best.total_time:
            best = candidate
    assert best is not None
    return best


def optimize_two_stop(track: TrackPreset, cum: dict[Compound, np.ndarray]) -> StrategyResult:
    laps = track.laps
    if laps < 3:
        # Not enough laps to make a 2-stop strategy meaningful.
        return optimize_one_stop(track, cum)

    lap1 = np.arange(1, laps - 1)
    lap2 = np.arange(1, laps - 1)
    L1, L2 = np.meshgrid(lap1, lap2, indexing="ij")
    valid = L2 > L1  # lap2 strictly after lap1

    best: StrategyResult | None = None
    for c1, c2, c3 in _valid_compound_tuples(3):
        stint1 = cum[c1][L1]
        stint2 = cum[c2][np.clip(L2 - L1, 0, laps)]
        stint3 = cum[c3][laps - L2]
        total = np.where(valid, stint1 + stint2 + stint3 + 2 * track.pit_loss, np.inf)
        flat_idx = int(np.argmin(total))
        i, j = np.unravel_index(flat_idx, total.shape)
        candidate_time = float(total[i, j])
        if best is None or candidate_time < best.total_time:
            best = StrategyResult(
                stops=2,
                compounds=(c1.value, c2.value, c3.value),
                pit_laps=(int(L1[i, j]), int(L2[i, j])),
                total_time=candidate_time,
            )
    assert best is not None
    return best


def one_stop_heatmap(track: TrackPreset) -> dict:
    """Return the time-cost grid for every 1-stop (compound-pair × pit-lap) combination.

    Returned dict:
      pit_laps       — list[int], pit lap numbers 1..laps-1
      pairs          — list[str], compound pair labels e.g. ["S→M", ...]
      deltas         — list[list[float]], seconds above the global 1-stop optimum;
                       shape [n_pairs][n_pit_laps], 0.0 at the best cell
      optimal_pit_lap  — pit lap of the overall best 1-stop strategy
      optimal_pair_idx — index into `pairs` of the overall best
    """
    cum = {c: _cumulative_time(c, track.laps, track) for c in Compound}
    fuel_benefit = _total_fuel_benefit(track.laps)
    pit_lap_arr = np.arange(1, track.laps)

    pairs = list(permutations(Compound, 2))
    times = []
    for c1, c2 in pairs:
        total = cum[c1][pit_lap_arr] + cum[c2][track.laps - pit_lap_arr] + track.pit_loss - fuel_benefit
        times.append(total)

    all_times = np.stack(times)  # (n_pairs, n_pit_laps)
    global_min = float(np.min(all_times))
    deltas = [[round(float(v - global_min), 3) for v in row] for row in all_times]

    flat_idx = int(np.argmin(all_times))
    opt_pair_idx, opt_pit_idx = np.unravel_index(flat_idx, all_times.shape)
    return {
        "pit_laps": pit_lap_arr.tolist(),
        "pairs": [f"{c1.value}→{c2.value}" for c1, c2 in pairs],
        "deltas": deltas,
        "optimal_pit_lap": int(pit_lap_arr[opt_pit_idx]),
        "optimal_pair_idx": int(opt_pair_idx),
    }


def best_strategies(track: TrackPreset, top_n: int = 3) -> list[StrategyResult]:
    """Return the `top_n` best strategies (mixing 1-stop and 2-stop) by total time.

    Total times include the constant race-wide fuel benefit so the
    reported numbers look like a real race time, even though that
    constant doesn't affect which strategy ranks best.
    """
    cum = {c: _cumulative_time(c, track.laps, track) for c in Compound}

    candidates: list[StrategyResult] = []

    # One-stop: best per ordered compound pair, so the top-N list can show
    # genuinely different strategies rather than N near-identical pit laps.
    for c1, c2 in permutations(Compound, 2):
        pit_lap = np.arange(1, track.laps)
        total = cum[c1][pit_lap] + cum[c2][track.laps - pit_lap] + track.pit_loss
        idx = int(np.argmin(total))
        candidates.append(
            StrategyResult(
                stops=1,
                compounds=(c1.value, c2.value),
                pit_laps=(int(pit_lap[idx]),),
                total_time=float(total[idx]),
            )
        )

    # Two-stop: best per compound triple.
    laps = track.laps
    if laps >= 3:
        lap1 = np.arange(1, laps - 1)
        lap2 = np.arange(1, laps - 1)
        L1, L2 = np.meshgrid(lap1, lap2, indexing="ij")
        valid = L2 > L1
        for c1, c2, c3 in _valid_compound_tuples(3):
            stint1 = cum[c1][L1]
            stint2 = cum[c2][np.clip(L2 - L1, 0, laps)]
            stint3 = cum[c3][laps - L2]
            total = np.where(valid, stint1 + stint2 + stint3 + 2 * track.pit_loss, np.inf)
            flat_idx = int(np.argmin(total))
            i, j = np.unravel_index(flat_idx, total.shape)
            candidates.append(
                StrategyResult(
                    stops=2,
                    compounds=(c1.value, c2.value, c3.value),
                    pit_laps=(int(L1[i, j]), int(L2[i, j])),
                    total_time=float(total[i, j]),
                )
            )

    fuel_benefit = _total_fuel_benefit(track.laps)
    adjusted = [
        StrategyResult(c.stops, c.compounds, c.pit_laps, c.total_time - fuel_benefit)
        for c in candidates
    ]
    adjusted.sort(key=lambda r: r.total_time)
    return adjusted[:top_n]
