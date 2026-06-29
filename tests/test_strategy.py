from dataclasses import replace

from f1_strategy.strategy import best_strategies
from f1_strategy.tracks import get_track


def test_best_strategies_sorted_ascending():
    track = get_track("monza")
    results = best_strategies(track, top_n=3)
    times = [r.total_time for r in results]
    assert times == sorted(times)


def test_strategy_uses_at_least_two_compounds():
    track = get_track("silverstone")
    for result in best_strategies(track, top_n=5):
        assert len(set(result.compounds)) >= 2


def test_pit_laps_within_race_distance():
    track = get_track("spa")
    for result in best_strategies(track, top_n=5):
        for pit_lap in result.pit_laps:
            assert 0 < pit_lap < track.laps
        assert list(result.pit_laps) == sorted(result.pit_laps)


def test_stops_count_matches_pit_laps():
    track = get_track("suzuka")
    for result in best_strategies(track, top_n=5):
        assert result.stops == len(result.pit_laps)
        assert len(result.compounds) == result.stops + 1


def test_higher_pit_loss_never_improves_best_time():
    track = get_track("monaco")
    cheap_pit = replace(track, pit_loss=5.0)
    expensive_pit = replace(track, pit_loss=40.0)
    cheap_best = best_strategies(cheap_pit, top_n=1)[0].total_time
    expensive_best = best_strategies(expensive_pit, top_n=1)[0].total_time
    assert expensive_best >= cheap_best


def test_short_race_falls_back_to_one_stop_only():
    track = get_track("custom")
    short = replace(track, laps=2)
    results = best_strategies(short, top_n=5)
    assert all(r.stops == 1 for r in results)
