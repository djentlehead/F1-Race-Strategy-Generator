# F1 Race Strategy Generator

An F1 race strategy simulator built with Flask and Plotly. Pick a circuit, enter your tyre inventory, and the tool finds the fastest pit-stop strategy using a tyre degradation model, then stress-tests it with Monte Carlo simulation and a 1-stop sensitivity heatmap — all in a single no-scroll dashboard.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey) ![Plotly](https://img.shields.io/badge/Plotly-5.24-purple)

---

## Features

- **Strategy optimiser** — exhaustively searches 1-stop and 2-stop strategies across Soft, Medium, and Hard compounds; ranks by total fuel-corrected race time; enforces the FIA two-compound rule
- **Tyre degradation model** — linear deg rate + cliff penalty (quadratic once a tyre exceeds its compound's cliff age) + fuel burn-off correction per lap
- **Tyre cliff penalty** — mirrors real F1 behaviour where lap times are stable then fall off sharply; penalises strategies that run tyres past their natural life
- **Monte Carlo simulation** — 1,000 runs per strategy with randomised safety car appearances, deg variance, and pit timing noise; outputs win probability and P10–P90 time spread
- **Sensitivity heatmap** — shows how much time a 1-stop strategy loses vs the optimal depending on pit lap choice
- **Tyre inventory checker** — input your remaining new and used tyre sets; each strategy is flagged ✓ (feasible with new sets), ⚠ (needs a used set), or ✗ (insufficient sets)
- **Pit window indicator** — estimated optimal pit lap range for the best strategy
- **Real-data calibration** — pit-loss values for Monaco, Silverstone, and Monza are calibrated from 2024 race data; all other tracks use transparent approximations
- **10 circuits** — Bahrain, Jeddah, Melbourne, Monaco, Montréal, Silverstone, Monza, Singapore, Suzuka, and a custom-track mode

---

## Architecture

```
main.py                         Flask app — routes, strategy orchestration
f1_strategy/
  model.py                      Tyre degradation model and Compound enum
  strategy.py                   Exhaustive strategy search and heatmap
  simulation.py                 Monte Carlo race simulator
  plotting.py                   Plotly figure builder
  tracks.py                     Track presets (laps, pit loss, deg multiplier)
  inventory.py                  Tyre inventory feasibility checker
  calibration/
    analyze.py                  Calibration pipeline (pit-loss fitting)
    raw/                        2024 race data JSON (Monaco, Silverstone, Monza)
static/
  app.js                        Dashboard JS — form, fetch, Plotly rendering
  styles.css                    Dark theme, custom scrollbar, radial glow
templates/
  index.html                    Single-page no-scroll dashboard (Tailwind CDN)
tests/                          pytest suite — model, strategy, simulation, calibration
```

---

## Local setup

```bash
git clone https://github.com/djentlehead/F1-Race-Strategy-Generator.git
cd F1-Race-Strategy-Generator
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:5000` in your browser.

### Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

---

## Deployment

The repo ships with configuration for three deployment options:

| Method | File | Command |
|--------|------|---------|
| Gunicorn (bare) | `Procfile` | `gunicorn main:app` |
| Docker | `Dockerfile` | `docker build -t f1-strategy . && docker run -p 8000:8000 f1-strategy` |
| Render.com | `render.yaml` | Connect repo → auto-deploy |

---

## Data & caveats

This is a portfolio project, not a licensed simulation tool. The numbers are calibrated to produce sensible, comparable strategies — not to match any team's real telemetry.

| Parameter | Source |
|-----------|--------|
| `pit_loss` (Monaco, Silverstone, Monza) | Calibrated from 2024 race lap data |
| `pit_loss` (all other circuits) | Approximate figures from publicly reported race coverage |
| `base_lap_time` | Derived from circuit length and typical race pace; illustrative |
| `deg_multiplier` | Illustrative scalar reflecting a circuit's general tyre stress reputation |
| `sc_probability` | Informed by widely reported trends; not fitted to any dataset |
| Compound deltas and deg rates | Approximate values consistent with publicly discussed Pirelli behaviour |

The calibration pipeline (`f1_strategy/calibration/analyze.py`) fits pit-loss time from real stint data but cannot recover per-compound degradation rates because the data source does not expose tyre compound — so `deg_multiplier` and `base_lap_time` remain illustrative even for calibrated circuits.

---

## Tech stack

- **Backend** — Python 3.12, Flask 3.0, NumPy
- **Frontend** — Tailwind CSS (CDN), Plotly.js
- **Deployment** — Gunicorn, Docker, Render.com