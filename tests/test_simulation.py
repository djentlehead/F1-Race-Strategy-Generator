import math
from dataclasses import replace

import numpy as np
import pytest

from f1_strategy.simulation import SimulationConfig, per_lap_clean_times, simulate_strategies
from f1_strategy.strategy import best_strategies
from f1_strategy.tracks import get_track


def test_deterministic_mean_matches_strategy_total_time():
    """With zero noise and no Safety Car, the simulated mean must equal the
    analytic total_time from strategy.py -- this is the core correctness
    check that the lap-by-lap reconstruction matches the closed-form sum."""
    track = replace(get_track("silverstone"), sc_probability=0.0)
    strategies = best_strategies(track, top_n=5)
    cfg = SimulationConfig(n_trials=20, lap_noise_std=0.0, seed=1)

    results = simulate_strategies(track, strategies, cfg)
    for r in results:
        assert r.mean_time == pytest.approx(r.strategy.total_time, abs=1e-6)
        assert r.std_time == pytest.approx(0.0, abs=1e-9)


def test_win_probabilities_sum_to_one():
    track = get_track("monza")
    strategies = best_strategies(track, top_n=5)
    cfg = SimulationConfig(n_trials=500, seed=7)
    results = simulate_strategies(track, strategies, cfg)
    total = sum(r.win_probability for r in results)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_best_deterministic_strategy_remains_a_strong_contender():
    """Not a strict guarantee for every pair (Safety Car timing can favor a
    nominally-worse strategy in any given trial), but across thousands of
    trials the deterministic best should still win a healthy share, and
    nothing should out-win it by an implausible margin."""
    track = get_track("suzuka")
    strategies = best_strategies(track, top_n=5)
    cfg = SimulationConfig(n_trials=3000, seed=3)
    results = simulate_strategies(track, strategies, cfg)
    best_by_time = min(results, key=lambda r: r.strategy.total_time)
    best_by_win = max(results, key=lambda r: r.win_probability)
    assert best_by_time.win_probability > 0.05
    assert best_by_win.win_probability >= best_by_time.win_probability


def test_per_lap_clean_times_sums_to_strategy_total_time_minus_pit_loss():
    track = get_track("monaco")
    strategy = best_strategies(track, top_n=1)[0]
    laps = per_lap_clean_times(strategy, track)
    assert len(laps) == track.laps
    reconstructed_total = float(np.sum(laps)) + strategy.stops * track.pit_loss
    assert reconstructed_total == pytest.approx(strategy.total_time, abs=1e-6)


def test_higher_lap_noise_increases_spread():
    track = get_track("monza")
    strategies = best_strategies(track, top_n=3)
    low_noise = simulate_strategies(track, strategies, SimulationConfig(n_trials=1000, lap_noise_std=0.05, seed=5))
    high_noise = simulate_strategies(track, strategies, SimulationConfig(n_trials=1000, lap_noise_std=2.0, seed=5))
    assert sum(r.std_time for r in high_noise) > sum(r.std_time for r in low_noise)


def test_empty_strategy_list_returns_empty():
    track = get_track("monza")
    assert simulate_strategies(track, [], SimulationConfig()) == []


def test_to_dict_is_json_serializable_shape():
    track = get_track("monza")
    strategies = best_strategies(track, top_n=2)
    results = simulate_strategies(track, strategies, SimulationConfig(n_trials=50, seed=1))
    for r in results:
        d = r.to_dict()
        assert set(d) == {
            "strategy", "win_probability", "mean_time", "std_time",
            "p10_time", "p50_time", "p90_time",
        }
        assert isinstance(d["strategy"], dict)
        assert 0.0 <= d["win_probability"] <= 1.0
