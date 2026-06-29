import numpy as np
import pytest

from f1_strategy.model import Compound, fuel_correction, lap_time_array
from f1_strategy.tracks import get_track


@pytest.fixture
def track():
    return get_track("monza")


def test_compound_from_str_aliases():
    assert Compound.from_str("soft") is Compound.SOFT
    assert Compound.from_str("S") is Compound.SOFT
    assert Compound.from_str("hard") is Compound.HARD


def test_compound_from_str_invalid():
    with pytest.raises(ValueError):
        Compound.from_str("ultrasoft")


def test_lap_time_increases_with_age(track):
    ages = np.arange(30)
    times = lap_time_array(Compound.SOFT, ages, track)
    # degradation should be monotonically non-decreasing as the tyre ages
    assert np.all(np.diff(times) >= 0)


def test_soft_faster_than_medium_faster_than_hard_when_fresh(track):
    zero = np.array([0])
    soft = lap_time_array(Compound.SOFT, zero, track)[0]
    medium = lap_time_array(Compound.MEDIUM, zero, track)[0]
    hard = lap_time_array(Compound.HARD, zero, track)[0]
    assert soft < medium < hard


def test_cliff_makes_late_degradation_steeper(track):
    ages = np.arange(40)
    times = lap_time_array(Compound.SOFT, ages, track)
    deltas = np.diff(times)
    # the per-lap time loss late in the stint (past the cliff) should exceed
    # the per-lap loss early in the stint
    assert deltas[-1] > deltas[1]


def test_fuel_correction_reduces_lap_time():
    remaining = np.array([10, 0])
    saved = fuel_correction(remaining)
    assert saved[0] > saved[1] == 0


def test_unknown_track_raises():
    with pytest.raises(ValueError):
        get_track("nonexistent-track")
