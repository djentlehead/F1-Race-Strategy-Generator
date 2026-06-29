from __future__ import annotations

from dataclasses import asdict, replace

from flask import Flask, jsonify, render_template, request

from f1_strategy.calibration.analyze import calibrate_all
from f1_strategy.inventory import TyreInventory
from f1_strategy.plotting import build_figure, figure_to_json
from f1_strategy.simulation import SimulationConfig, simulate_strategies
from f1_strategy.strategy import best_strategies, one_stop_heatmap
from f1_strategy.tracks import TRACKS, get_track

app = Flask(__name__)


CALIBRATION = {circuit: result.to_dict() for circuit, result in calibrate_all().items()}

SIMULATION_CONFIG = SimulationConfig(seed=42)


def format_time(total_seconds: float) -> str:
    minutes, seconds = divmod(max(total_seconds, 0), 60)
    return f"{int(minutes)}:{seconds:05.2f}"


@app.route("/")
def home():
    return render_template("index.html", tracks=list(TRACKS.values()))


@app.route("/api/tracks")
def api_tracks():
    return jsonify([asdict(t) for t in TRACKS.values()])


@app.route("/api/calibration")
def api_calibration():
    return jsonify(CALIBRATION)


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}

    track_key = data.get("track", "monza")
    try:
        track = get_track(track_key)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    overrides = {}
    if data.get("laps") not in (None, ""):
        try:
            laps = int(data["laps"])
        except (TypeError, ValueError):
            return jsonify({"error": "laps must be an integer."}), 400
        if laps < 2:
            return jsonify({"error": "Need at least 2 laps to plan a pit stop."}), 400
        if laps > 100:
            return jsonify({"error": "laps must be 100 or fewer."}), 400
        overrides["laps"] = laps

    if track_key == "custom":
        for field in ("pit_loss", "base_lap_time", "deg_multiplier"):
            if data.get(field) not in (None, ""):
                try:
                    overrides[field] = float(data[field])
                except (TypeError, ValueError):
                    return jsonify({"error": f"{field} must be a number."}), 400

    if overrides:
        track = replace(track, **overrides)

    inventory = TyreInventory.from_dict(data.get("inventory"))

    results = best_strategies(track, top_n=5)
    best = results[0]
    fig = build_figure(best, track)
    sim_results = simulate_strategies(track, results, SIMULATION_CONFIG)

    def annotate(r):
        d = r.to_dict()
        d.update(inventory.check(list(r.compounds)))
        return d

    return jsonify(
        {
            "plot": figure_to_json(fig),
            "best": annotate(best),
            "alternatives": [annotate(r) for r in results[1:]],
            "track": {
                "key": track.key,
                "name": track.name,
                "laps": track.laps,
                "pit_loss": track.pit_loss,
                "circuit_length_km": track.circuit_length_km,
                "calibrated": track.calibrated,
                "calibration_source": track.calibration_source,
                "sc_probability": track.sc_probability,
            },
            "strategy_text": (
                f"Best strategy: {best.label} ({best.stops}-stop), "
                f"pit on lap{'s' if len(best.pit_laps) > 1 else ''} "
                f"{', '.join(str(p) for p in best.pit_laps)}"
            ),
            "time_text": f"Total time: {format_time(best.total_time)}",
            "monte_carlo": [s.to_dict() for s in sim_results],
            "calibration": CALIBRATION.get(track.key),
            "heatmap": one_stop_heatmap(track),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)