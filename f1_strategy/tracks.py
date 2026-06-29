"""Track presets.

`laps` and `pit_loss` are approximate figures based on publicly reported
race lap counts and pit-lane time-loss reporting (see README "Data &
caveats" section for sources). `base_lap_time` is a rough representative
race-pace lap time derived from circuit length / typical race lap times,
not an official figure. `deg_multiplier` is an illustrative scalar
(1.0 = average) reflecting how hard a circuit is generally considered to
be on tyres -- street circuits like Monaco/Singapore run cooler and slower
so multiplier < 1, high-energy circuits like Silverstone/Suzuka run > 1.

These are deliberately simple, transparent approximations for a portfolio
project, not a substitute for real telemetry -- **except** `pit_loss` for
monaco, silverstone, and monza, which has been replaced with a value
calibrated from real 2024 race data (see `f1_strategy/calibration/`). That
calibration pipeline could not recover per-compound degradation rates
(the data source doesn't expose tyre compound), so `deg_multiplier` and
`base_lap_time` remain illustrative for every track, calibrated ones
included. See the README's "Data & caveats" section and
`f1_strategy/calibration/analyze.py` for exactly what was and wasn't
calibrated, and why.

`sc_probability` (chance of a Safety Car / VSC at some point in the race,
used by the Monte Carlo simulator in `f1_strategy/simulation.py`) is also
illustrative: it's informed by widely reported general trends -- street
circuits and historically incident-prone layouts run higher, low-risk
high-speed circuits run lower -- rather than fit to any specific dataset.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackPreset:
    key: str
    name: str
    laps: int
    pit_loss: float  # seconds lost per pit stop
    base_lap_time: float  # seconds, illustrative clean-air race pace
    deg_multiplier: float  # relative tyre degradation severity
    calibrated: bool = False  # True if pit_loss comes from real race data
    calibration_source: str | None = None  # human-readable provenance note
    sc_probability: float = 0.40  # illustrative P(safety car at some point in the race)
    circuit_length_km: float = 0.0  # approximate circuit length in kilometres


TRACKS: dict[str, TrackPreset] = {
    t.key: t
    for t in [
        TrackPreset(
            "monaco", "Monaco (Circuit de Monaco)", laps=78, pit_loss=24.24,
            base_lap_time=72.0, deg_multiplier=0.55, calibrated=True,
            calibration_source="Median real pit-stop duration, 2024 Monaco GP (n=7 clean stops; "
                                "most of the field's stops were red-flag artifacts and were excluded)",
            sc_probability=0.60, circuit_length_km=3.337,
        ),
        TrackPreset(
            "silverstone", "Silverstone (British GP)", laps=52, pit_loss=29.32,
            base_lap_time=88.0, deg_multiplier=1.15, calibrated=True,
            calibration_source="Median real pit-stop duration, 2024 British GP (n=44 clean stops)",
            sc_probability=0.35, circuit_length_km=5.891,
        ),
        TrackPreset("spa", "Spa-Francorchamps (Belgian GP)", laps=44, pit_loss=18.5, base_lap_time=106.0, deg_multiplier=1.0, sc_probability=0.45, circuit_length_km=7.004),
        TrackPreset(
            "monza", "Monza (Italian GP)", laps=53, pit_loss=24.70,
            base_lap_time=80.0, deg_multiplier=0.75, calibrated=True,
            calibration_source="Median real pit-stop duration, 2024 Italian GP (n=30 clean stops)",
            sc_probability=0.30, circuit_length_km=5.793,
        ),
        TrackPreset("singapore", "Marina Bay (Singapore GP)", laps=61, pit_loss=26.0, base_lap_time=100.0, deg_multiplier=0.85, sc_probability=0.65, circuit_length_km=4.940),
        TrackPreset("suzuka", "Suzuka (Japanese GP)", laps=53, pit_loss=20.5, base_lap_time=91.0, deg_multiplier=1.2, sc_probability=0.30, circuit_length_km=5.807),
        TrackPreset("custom", "Custom", laps=55, pit_loss=21.0, base_lap_time=90.0, deg_multiplier=1.0, sc_probability=0.40, circuit_length_km=0.0),
    ]
}


def get_track(key: str) -> TrackPreset:
    try:
        return TRACKS[key]
    except KeyError as exc:
        valid = ", ".join(TRACKS)
        raise ValueError(f"Unknown track '{key}'. Valid options: {valid}") from exc
