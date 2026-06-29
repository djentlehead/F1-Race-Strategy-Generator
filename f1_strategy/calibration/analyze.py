"""Real-data calibration analysis.

This module turns the raw race data snapshots in ``f1_strategy/calibration/raw/``
into calibrated numbers we can compare against this project's illustrative
track constants (see ``f1_strategy/tracks.py``).

Honesty note up front: the literal FastF1 library cannot reach its data
backends from this project's development sandbox (the network is
allow-listed and FastF1's endpoints aren't on it). What's used here instead
is the Jolpica API, an Ergast-compatible mirror of the *same* official F1
timing data FastF1 itself wraps, fetched directly over HTTPS. It exposes
real lap times, real pit-stop laps, and real pit-stop durations -- but,
unlike FastF1's telemetry, it does **not** expose which tyre compound a
driver was on for a given lap. That means:

- Pit-stop duration *can* be calibrated directly and honestly (see
  ``pit_loss_seconds`` below) -- it's an observed quantity, no compound
  knowledge required.
- Per-compound degradation rate (`DEG_RATE` in ``model.py``) *cannot* be
  recovered from this data, because we can't tell a stint on Mediums from
  a stint on Hards. What we compute instead is an **aggregate** degradation
  slope per circuit (seconds/lap, across all real stints regardless of
  compound), which is still a legitimate real-world signal for *relative*
  degradation severity between circuits -- i.e. it can validate (or
  challenge) the *ranking* implied by ``deg_multiplier``, even though it
  can't calibrate any single compound's curve.
- "Base lap time" is approximated as a low-percentile clean lap early in
  the run, which reflects a fuelled-up race lap, not a qualifying lap on
  a fresh single-lap-pace tyre -- so it's a sanity check, not a
  like-for-like substitute for ``base_lap_time``.

Every number this module produces is traceable back to the raw JSON files
checked into this repo, which were fetched once and snapshotted (not
re-fetched at request time) so the app and its tests work fully offline.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RAW_DIR = Path(__file__).parent / "raw"

# Laps slower than this multiple of a driver's own median clean lap are
# treated as contaminated (pit lane transit, safety car / VSC, red flag,
# incidents, rain) and excluded from pace/degradation fitting.
OUTLIER_FACTOR = 1.4

# Real pit-stop "duration" values above this are not a normal stationary
# pit stop (e.g. Monaco 2024's lap-1 entries are red-flag stoppage
# artifacts, recorded as multi-minute "stops") and are excluded from the
# pit-loss calibration.
PIT_DURATION_OUTLIER_SECONDS = 60.0

_TIME_RE = re.compile(r"^(?:(\d+):)?(\d+(?:\.\d+)?)$")


def parse_time(value: str | None) -> float | None:
    """Parse an Ergast-style "M:SS.mmm" or "SS.mmm" string into seconds."""
    if not value:
        return None
    match = _TIME_RE.match(value.strip())
    if not match:
        return None
    minutes, seconds = match.groups()
    total = float(seconds)
    if minutes:
        total += int(minutes) * 60
    return total


@dataclass(frozen=True)
class StintFit:
    driver: str
    start_lap: int
    length: int
    slope_sec_per_lap: float
    laps_used: int


@dataclass(frozen=True)
class TrackCalibration:
    circuit_id: str
    race_name: str
    season: int
    round: int
    source: str
    drivers_sampled: tuple[str, ...]
    pit_loss_seconds: float
    pit_loss_samples: int
    pace_proxy_seconds: float
    deg_slope_sec_per_lap: float
    stint_fits: tuple[StintFit, ...]
    actual_strategies: dict[str, tuple[int, ...]]

    def to_dict(self) -> dict:
        return {
            "circuit_id": self.circuit_id,
            "race_name": self.race_name,
            "season": self.season,
            "round": self.round,
            "source": self.source,
            "drivers_sampled": list(self.drivers_sampled),
            "pit_loss_seconds": round(self.pit_loss_seconds, 2),
            "pit_loss_samples": self.pit_loss_samples,
            "pace_proxy_seconds": round(self.pace_proxy_seconds, 2),
            "deg_slope_sec_per_lap": round(self.deg_slope_sec_per_lap, 4),
            "n_stints_fitted": len(self.stint_fits),
            "actual_strategies": {
                driver: list(laps) for driver, laps in self.actual_strategies.items()
            },
        }


def _load_raw(circuit_id: str) -> dict:
    path = RAW_DIR / f"{circuit_id}_2024.json"
    with open(path) as f:
        return json.load(f)


def _driver_pit_laps(pitstops: list[dict], driver: str) -> list[int]:
    laps = sorted(p["lap"] for p in pitstops if p["driverId"] == driver)
    return laps


def _segment_stints(n_laps: int, pit_laps: list[int]) -> list[tuple[int, int]]:
    """Return (start_lap, end_lap) 1-indexed inclusive ranges between stops."""
    bounds = [0] + pit_laps + [n_laps]
    stints = []
    for start, end in zip(bounds[:-1], bounds[1:]):
        if end > start:
            stints.append((start + 1, end))
    return stints


def _fit_stint_slope(lap_times: np.ndarray, ages: np.ndarray) -> float | None:
    if len(lap_times) < 4:
        return None
    slope, _intercept = np.polyfit(ages, lap_times, 1)
    return float(slope)


def calibrate_track(circuit_id: str) -> TrackCalibration:
    raw = _load_raw(circuit_id)
    pitstops = raw["pitstops"]

    # --- Pit-loss calibration: median of "normal" stop durations across
    # the whole field (not just our sampled panel), excluding red-flag /
    # incident artifacts. ---
    durations = [
        d
        for p in pitstops
        if (d := parse_time(p.get("duration"))) is not None
        and d < PIT_DURATION_OUTLIER_SECONDS
    ]
    pit_loss = float(np.median(durations)) if durations else float("nan")

    pace_samples: list[float] = []
    deg_slopes: list[float] = []
    stint_fits: list[StintFit] = []
    actual_strategies: dict[str, tuple[int, ...]] = {}

    for driver, raw_laps in raw["laps"].items():
        lap_times = np.array([parse_time(t) for t in raw_laps], dtype=float)
        n_laps = len(lap_times)
        median = float(np.median(lap_times))
        clean_mask = lap_times < median * OUTLIER_FACTOR

        pit_laps = _driver_pit_laps(pitstops, driver)
        actual_strategies[driver] = tuple(pit_laps)

        # Early-race clean laps (laps 3-10) approximate "fresh tyre, full
        # fuel" pace without relying on the very first 1-2 laps, which are
        # often bunched up / affected by start procedure.
        window = slice(2, 10)
        early_clean = lap_times[window][clean_mask[window]]
        if len(early_clean) > 0:
            pace_samples.append(float(np.percentile(early_clean, 10)))

        for start, end in _segment_stints(n_laps, pit_laps):
            # Exclude the in-lap (pit lap itself) and the out-lap (cold
            # tyres) from the stint's regression window. Every stint's
            # first lap is either the standing-start lap (stint 1) or the
            # out-lap right after a stop (every later stint) -- both are
            # mechanically different from representative green-flag pace,
            # so always drop it.
            fit_start = start + 1
            fit_end = end - 1 if end in pit_laps else end
            if fit_end - fit_start < 3:
                continue
            idx = np.arange(fit_start, fit_end + 1) - 1  # 0-indexed
            idx = idx[(idx >= 0) & (idx < n_laps)]
            stint_times = lap_times[idx]
            stint_clean = clean_mask[idx]
            if stint_clean.sum() < 4:
                continue
            ages = np.arange(len(idx))[stint_clean]
            slope = _fit_stint_slope(stint_times[stint_clean], ages)
            if slope is None:
                continue
            # Degradation should be non-negative; a clearly negative slope
            # usually means the "stint" still contains a contaminated lap
            # the outlier filter missed (e.g. a brief VSC). Drop it rather
            # than let it cancel out real degradation elsewhere.
            if slope < -0.05:
                continue
            deg_slopes.append(slope)
            stint_fits.append(
                StintFit(
                    driver=driver,
                    start_lap=fit_start,
                    length=fit_end - fit_start + 1,
                    slope_sec_per_lap=slope,
                    laps_used=int(stint_clean.sum()),
                )
            )

    return TrackCalibration(
        circuit_id=circuit_id,
        race_name=raw["raceName"],
        season=raw["season"],
        round=raw["round"],
        source=raw["source"],
        drivers_sampled=tuple(raw["drivers_sampled"]),
        pit_loss_seconds=pit_loss,
        pit_loss_samples=len(durations),
        pace_proxy_seconds=float(np.mean(pace_samples)) if pace_samples else float("nan"),
        deg_slope_sec_per_lap=float(np.mean(deg_slopes)) if deg_slopes else float("nan"),
        stint_fits=tuple(stint_fits),
        actual_strategies=actual_strategies,
    )


CALIBRATED_CIRCUITS = ("monza", "silverstone", "monaco")


def calibrate_all() -> dict[str, TrackCalibration]:
    return {c: calibrate_track(c) for c in CALIBRATED_CIRCUITS}


if __name__ == "__main__":
    for circuit, result in calibrate_all().items():
        print(f"\n=== {circuit} ({result.race_name}) ===")
        print(f"pit_loss_seconds   = {result.pit_loss_seconds:.2f} (n={result.pit_loss_samples})")
        print(f"pace_proxy_seconds = {result.pace_proxy_seconds:.2f}")
        print(f"deg_slope_sec/lap  = {result.deg_slope_sec_per_lap:.4f} (n_stints={len(result.stint_fits)})")
        print(f"actual strategies  = {result.actual_strategies}")
