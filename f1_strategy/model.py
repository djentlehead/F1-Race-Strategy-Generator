"""Tyre degradation model.

The model behind a single lap time is:

    lap_time(age) = base_lap_time
                  + compound_offset
                  + linear_deg_rate * age * track.deg_multiplier
                  + cliff_penalty(age)
                  - fuel_correction(absolute_lap)

`age` is how many laps the tyre has completed since it was fitted (0 on the
out-lap). `cliff_penalty` kicks in once a tyre passes its compound's
approximate "cliff" age, after which deg accelerates quadratically -- this
mirrors the well known real-world behaviour where tyres are fine for a
while and then fall off sharply, rather than degrading perfectly linearly.

All numeric constants are illustrative approximations of publicly discussed
F1 tyre behaviour (Pirelli compound deltas of a few tenths, deg rates of a
few hundredths of a second per lap, a fuel effect of ~0.03-0.06s/lap as fuel
burns off), not licensed Pirelli/F1 data. They are tuned so the model
produces sensible, comparable strategies rather than to match any single
real session lap-for-lap.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from .tracks import TrackPreset


class Compound(str, Enum):
    SOFT = "S"
    MEDIUM = "M"
    HARD = "H"

    @classmethod
    def from_str(cls, value: str) -> "Compound":
        value = value.strip().upper()
        aliases = {
            "SOFT": "S",
            "MEDIUM": "M",
            "HARD": "H",
        }
        value = aliases.get(value, value)
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown tyre compound '{value}'. Use one of S, M, H."
            ) from exc


# Lap-time offset relative to the Soft compound, in seconds. Softs are
# fastest but degrade quickest; Hards are slowest but most durable.
COMPOUND_OFFSET: dict[Compound, float] = {
    Compound.SOFT: 0.0,
    Compound.MEDIUM: 0.35,
    Compound.HARD: 0.70,
}

# Approximate linear degradation rate, seconds added per lap of tyre age.
DEG_RATE: dict[Compound, float] = {
    Compound.SOFT: 0.085,
    Compound.MEDIUM: 0.045,
    Compound.HARD: 0.022,
}

# Age (in laps) after which a tyre is considered to be "on the cliff" and
# degradation accelerates sharply.
CLIFF_AGE: dict[Compound, int] = {
    Compound.SOFT: 14,
    Compound.MEDIUM: 24,
    Compound.HARD: 36,
}

# Quadratic penalty coefficient applied to laps run past the cliff age.
CLIFF_RATE: dict[Compound, float] = {
    Compound.SOFT: 0.05,
    Compound.MEDIUM: 0.035,
    Compound.HARD: 0.02,
}

# Approximate lap-time benefit (seconds) per lap of fuel burned off.
FUEL_EFFECT_PER_LAP = 0.035


def lap_time_array(compound: Compound, ages: np.ndarray, track: TrackPreset) -> np.ndarray:
    """Vectorised lap time (seconds, before fuel correction) for an array of tyre ages."""
    ages = np.asarray(ages, dtype=float)
    linear = DEG_RATE[compound] * track.deg_multiplier * ages
    cliff_age = CLIFF_AGE[compound]
    over = np.clip(ages - cliff_age, a_min=0, a_max=None)
    cliff = CLIFF_RATE[compound] * track.deg_multiplier * over**2
    return track.base_lap_time + COMPOUND_OFFSET[compound] + linear + cliff


def fuel_correction(absolute_laps_remaining: np.ndarray) -> np.ndarray:
    """Seconds *saved* on a lap given how many laps of fuel remain after it."""
    return FUEL_EFFECT_PER_LAP * np.asarray(absolute_laps_remaining, dtype=float)


@dataclass(frozen=True)
class Tyre:
    """A tyre of a given compound and age, used for single lap-time lookups.

    Kept around mainly for readability / parity with the original API --
    the strategy search itself uses the vectorised `lap_time_array` above
    for performance.
    """

    compound: Compound
    age: int
    track: TrackPreset

    def lap_time(self) -> float:
        return float(lap_time_array(self.compound, np.array([self.age]), self.track)[0])
