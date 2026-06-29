import pytest

from f1_strategy.calibration.analyze import (
    CALIBRATED_CIRCUITS,
    calibrate_all,
    calibrate_track,
    parse_time,
)


def test_parse_time_seconds_only():
    assert parse_time("24.239") == pytest.approx(24.239)


def test_parse_time_minutes_and_seconds():
    assert parse_time("1:28.971") == pytest.approx(88.971)


def test_parse_time_handles_none_and_empty():
    assert parse_time(None) is None
    assert parse_time("") is None


def test_calibrate_all_covers_expected_circuits():
    results = calibrate_all()
    assert set(results) == set(CALIBRATED_CIRCUITS)


@pytest.mark.parametrize("circuit", CALIBRATED_CIRCUITS)
def test_calibration_produces_plausible_pit_loss(circuit):
    # A real Cup-era F1 pit stop (stationary time + pit lane delta) lands
    # comfortably within this band for every circuit in this dataset; a
    # value way outside it would mean the outlier filter let bad data
    # (e.g. Monaco's red-flag "stops") through.
    result = calibrate_track(circuit)
    assert 15.0 < result.pit_loss_seconds < 40.0
    assert result.pit_loss_samples > 0


@pytest.mark.parametrize("circuit", CALIBRATED_CIRCUITS)
def test_calibration_records_real_driver_strategies(circuit):
    result = calibrate_track(circuit)
    assert set(result.actual_strategies) == {"norris", "leclerc", "hamilton"}
    for laps in result.actual_strategies.values():
        assert list(laps) == sorted(laps)


def test_monaco_pit_loss_excludes_red_flag_artifacts():
    """Monaco 2024's lap-1 'pit stops' were multi-minute red-flag stoppage
    artifacts (durations like "39:18.026"). If the outlier filter failed,
    the median would be wildly inflated by these."""
    result = calibrate_track("monaco")
    assert result.pit_loss_seconds < 40.0
    # Only the handful of genuine, post-restart stops should survive.
    assert result.pit_loss_samples < 10


def test_silverstone_has_higher_real_degradation_than_monza_or_monaco():
    """Directional validation, not a precise fit: Silverstone's high-energy
    layout is expected to chew through tyres faster than Monza's low-load
    circuit or Monaco's low-speed street track, and the real aggregate
    stint-slope data should reflect that ranking even though it can't
    calibrate any single compound's curve (see analyze.py docstring)."""
    silverstone = calibrate_track("silverstone")
    monza = calibrate_track("monza")
    monaco = calibrate_track("monaco")
    assert silverstone.deg_slope_sec_per_lap > monza.deg_slope_sec_per_lap
    assert silverstone.deg_slope_sec_per_lap > monaco.deg_slope_sec_per_lap


def test_to_dict_is_json_serializable_shape():
    result = calibrate_track("monza")
    d = result.to_dict()
    assert set(d) >= {
        "circuit_id", "race_name", "season", "round", "source",
        "drivers_sampled", "pit_loss_seconds", "pit_loss_samples",
        "pace_proxy_seconds", "deg_slope_sec_per_lap", "n_stints_fitted",
        "actual_strategies",
    }
    assert isinstance(d["actual_strategies"], dict)
