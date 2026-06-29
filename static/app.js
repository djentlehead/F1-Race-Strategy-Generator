// Frontend logic for the F1 Tyre Strategy Generator.
// Calls the real /calculate Flask endpoint (no client-side fake math) and
// renders the best strategy, a comparison table of alternatives, and the
// Plotly lap-time chart returned by the backend.

const trackSelect = document.getElementById("track");
const lapsInput = document.getElementById("laps");
const customFields = document.getElementById("custom-fields");
const pitLossInput = document.getElementById("pit_loss");
const baseLapTimeInput = document.getElementById("base_lap_time");
const degMultiplierInput = document.getElementById("deg_multiplier");
const form = document.getElementById("strategy-form");
const submitBtn = document.getElementById("submit-btn");
const submitLabel = document.getElementById("submit-label");

const emptyState = document.getElementById("empty-state");
const resultsContent = document.getElementById("results-content");
const errorBox = document.getElementById("error-box");

function selectedOption() {
  return trackSelect.options[trackSelect.selectedIndex];
}

function syncFieldsToTrack() {
  const opt = selectedOption();
  lapsInput.value = opt.dataset.laps;
  pitLossInput.value = opt.dataset.pitLoss;
  baseLapTimeInput.value = opt.dataset.baseLapTime;
  degMultiplierInput.value = opt.dataset.degMultiplier;
  customFields.classList.toggle("hidden", opt.value !== "custom");
}

trackSelect.addEventListener("change", syncFieldsToTrack);
window.addEventListener("DOMContentLoaded", syncFieldsToTrack);

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.classList.toggle("opacity-60", isLoading);
  submitLabel.textContent = isLoading ? "Crunching strategies…" : "Calculate Strategy";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
  resultsContent.classList.add("hidden");
  emptyState.classList.add("hidden");
}

function fmtDelta(seconds) {
  return `+${seconds.toFixed(2)}s`;
}

function fmtTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds - minutes * 60;
  return `${minutes}:${seconds.toFixed(2).padStart(5, "0")}`;
}

function renderMonteCarlo(mcResults) {
  const container = document.getElementById("mc-rows");
  container.innerHTML = "";

  // Sort by win probability, not deterministic time -- the point of this
  // panel is to show that they can disagree.
  const sorted = [...mcResults].sort((a, b) => b.win_probability - a.win_probability);
  const maxWin = Math.max(...sorted.map((r) => r.win_probability), 0.0001);

  sorted.forEach((r) => {
    const pct = (r.win_probability * 100).toFixed(1);
    const barWidth = Math.max((r.win_probability / maxWin) * 100, 2);
    const row = document.createElement("div");
    row.innerHTML = `
      <div class="flex justify-between items-center text-xs">
        <span class="flex items-center gap-1 text-gray-200 font-medium">
          ${compoundDots(r.strategy.compounds)}
          ${r.strategy.label}
          <span class="text-gray-600">(${r.strategy.stops}-stop)</span>
        </span>
        <span class="text-yellow-400 font-bold">${pct}%</span>
      </div>
      <div class="mt-0.5 h-1.5 rounded-full bg-gray-800 overflow-hidden">
        <div class="h-full bg-red-600 rounded-full" style="width:${barWidth}%"></div>
      </div>
    `;
    container.appendChild(row);
  });
}



// Simplified SVG circuit outlines — rough but recognizable shapes (viewBox 0 0 200 130)
const CIRCUIT_SVGS = {
  monza: {
    vb: "0 0 200 130",
    d: `<polyline points="22,42 50,40 52,30 58,40 82,40 84,30 90,40 158,36 185,50 180,80 165,95 138,88 130,98 106,110 50,110 22,90 22,42" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`,
  },
  monaco: {
    vb: "0 0 200 130",
    d: `<polyline points="22,95 65,90 82,72 92,45 102,32 118,28 130,46 132,68 120,76 108,88 142,92 166,86 168,98 158,110 125,110 118,100 108,112 82,115 48,110 22,100 22,95" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`,
  },
  silverstone: {
    vb: "0 0 200 130",
    d: `<polyline points="82,108 155,90 175,62 162,38 175,22 155,14 108,12 42,14 28,28 18,52 25,82 52,105 82,108" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`,
  },
  spa: {
    vb: "0 0 200 130",
    d: `<polyline points="155,28 170,48 148,58 130,72 112,90 90,78 78,55 74,40 72,20 55,20 48,35 38,28 30,50 25,78 38,100 65,112 105,115 135,110 148,102 155,112 158,100 155,28" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`,
  },
  singapore: {
    vb: "0 0 200 130",
    d: `<polyline points="165,65 170,42 158,22 120,15 85,15 48,28 25,50 22,80 30,105 65,118 110,118 145,108 158,92 148,80 162,72 165,65" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`,
  },
  suzuka: {
    vb: "0 0 200 130",
    // Two overlapping paths to create the figure-8; a dark gap at the crossover hides the under-road section
    d: `<polyline points="140,95 168,65 165,38 150,20 128,18 118,32 110,50 95,62 78,48 58,30 40,50 55,75 72,90 108,102 118,90 110,68 90,62" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>
        <line x1="108" y1="52" x2="108" y2="66" stroke="#111827" stroke-width="5"/>
        <line x1="108" y1="52" x2="110" y2="50" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>`,
  },
  custom: {
    vb: "0 0 200 130",
    d: `<text x="100" y="68" text-anchor="middle" fill="currentColor" font-size="12" font-family="sans-serif" opacity="0.3">CUSTOM TRACK</text>`,
  },
};

const COMPOUND_COLOR = { S: "#e10600", M: "#ffd700", H: "#bbbbbb" };

function compoundDots(compounds) {
  return compounds
    .map(
      (c) =>
        `<span class="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 border border-gray-700" style="background:${COMPOUND_COLOR[c] || "#888"}"></span>`
    )
    .join(`<span class="text-gray-600 text-xs mx-0.5">→</span>`);
}

function inventoryBadge(strategy) {
  if (!strategy.feasible) {
    const missing = strategy.unavailable.join(", ");
    return `<span class="text-red-500 font-bold" title="No ${missing} sets available">✗</span>`;
  }
  if (strategy.requires_used && strategy.requires_used.length > 0) {
    const used = strategy.requires_used.join(", ");
    return `<span class="text-yellow-500 font-bold" title="Needs used ${used} set">⚠</span>`;
  }
  return `<span class="text-green-500 font-bold" title="All sets available">✓</span>`;
}

function getConfidence(mcResults) {
  const best = mcResults.reduce((a, b) => (a.win_probability > b.win_probability ? a : b));
  if (best.win_probability >= 0.5)
    return { label: "CONFIDENCE HIGH", cls: "bg-green-950 text-green-400 border border-green-800" };
  if (best.win_probability >= 0.3)
    return { label: "CONFIDENCE MED", cls: "bg-yellow-950 text-yellow-400 border border-yellow-800" };
  return { label: "CONFIDENCE LOW", cls: "bg-red-950 text-red-400 border border-red-800" };
}

function getPitWindow(heatmap, threshold = 2.0) {
  const deltas = heatmap.deltas[heatmap.optimal_pair_idx];
  const window = heatmap.pit_laps.filter((_, i) => deltas[i] <= threshold);
  if (!window.length) return null;
  return { start: window[0], end: window[window.length - 1] };
}

function renderCircuitCard(track, calibration, best) {
  // SVG outline
  const circuit = CIRCUIT_SVGS[track.key] || CIRCUIT_SVGS.custom;
  document.getElementById("circuit-svg-wrap").innerHTML = `
    <svg viewBox="${circuit.vb}" class="w-full h-full text-gray-400" xmlns="http://www.w3.org/2000/svg">
      ${circuit.d}
    </svg>`;

  // Stats
  const lengthKm = track.circuit_length_km > 0 ? `${track.circuit_length_km.toFixed(3)} km` : "—";
  const raceDist =
    track.circuit_length_km > 0
      ? `${(track.circuit_length_km * track.laps).toFixed(1)} km`
      : "—";
  document.getElementById("circuit-stats").innerHTML = `
    <dt class="text-gray-500">Laps</dt>
    <dd class="text-gray-200 font-medium">${track.laps}</dd>
    <dt class="text-gray-500">Circuit length</dt>
    <dd class="text-gray-200 font-medium">${lengthKm}</dd>
    <dt class="text-gray-500">Race distance</dt>
    <dd class="text-gray-200 font-medium">${raceDist}</dd>
    <dt class="text-gray-500">Pit lane loss</dt>
    <dd class="text-gray-200 font-medium">${track.pit_loss.toFixed(2)}s</dd>`;

  // Calibration sub-section
  const calSection = document.getElementById("calibration-section");
  if (calibration) {
    calSection.classList.remove("hidden");
    document.getElementById("calibration-intro-inline").textContent =
      `${calibration.race_name} (${calibration.season}, round ${calibration.round}). ` +
      `Pit-loss calibrated from ${calibration.pit_loss_samples} real pit stops.`;
    document.getElementById("calibration-stats-inline").innerHTML = `
      <dt class="text-gray-500">Calibrated pit loss</dt>
      <dd class="text-gray-200">${calibration.pit_loss_seconds.toFixed(2)}s</dd>
      <dt class="text-gray-500">Deg slope</dt>
      <dd class="text-gray-200">${calibration.deg_slope_sec_per_lap.toFixed(3)} s/lap</dd>`;
    const list = document.getElementById("calibration-strategies-inline");
    list.innerHTML = "";
    Object.entries(calibration.actual_strategies).forEach(([driver, laps]) => {
      const item = document.createElement("li");
      item.innerHTML = `<span class="text-gray-500">${driver}:</span> ${laps.length ? laps.join(", ") : "—"}`;
      list.appendChild(item);
    });
    const rec = document.createElement("li");
    rec.className = "pt-0.5 text-gray-200";
    rec.innerHTML = `<span class="text-gray-500">our rec:</span> ${best.label}, lap${best.pit_laps.length > 1 ? "s" : ""} ${best.pit_laps.join(", ")}`;
    list.appendChild(rec);
  } else {
    calSection.classList.add("hidden");
  }
}

function renderHeatmap(heatmap) {
  // Cap the color scale at the 90th-percentile delta so cliff outliers don't
  // wash out the contrast in the interesting pit-window zone.
  const flat = heatmap.deltas.flat();
  const sorted = [...flat].sort((a, b) => a - b);
  const cap = Math.max(sorted[Math.floor(sorted.length * 0.9)] || 30, 5);

  const clipped = heatmap.deltas.map((row) => row.map((v) => Math.min(v, cap)));

  const heatTrace = {
    type: "heatmap",
    x: heatmap.pit_laps,
    y: heatmap.pairs,
    z: clipped,
    colorscale: [
      [0.00, "#166534"],
      [0.15, "#22c55e"],
      [0.40, "#fbbf24"],
      [1.00, "#ef4444"],
    ],
    zmin: 0,
    zmax: cap,
    colorbar: {
      title: "+s vs best",
      titleside: "right",
      tickfont: { color: "#9ca3af", size: 10 },
      titlefont: { color: "#9ca3af", size: 11 },
      thickness: 12,
    },
    hovertemplate: "Pit lap %{x}<br>%{y}<br><b>+%{z:.1f}s</b> vs best<extra></extra>",
    showscale: true,
  };

  const starTrace = {
    type: "scatter",
    x: [heatmap.optimal_pit_lap],
    y: [heatmap.pairs[heatmap.optimal_pair_idx]],
    mode: "markers+text",
    text: ["★"],
    textfont: { size: 14, color: "white" },
    textposition: "middle center",
    marker: { size: 1, opacity: 0 },
    hoverinfo: "skip",
    showlegend: false,
  };

  const layout = {
    template: "plotly_dark",
    margin: { t: 4, b: 36, l: 46, r: 62 },
    xaxis: { title: "Pit lap", tickfont: { size: 10 }, titlefont: { size: 10 }, color: "#9ca3af" },
    yaxis: { tickfont: { size: 10 }, color: "#9ca3af", automargin: true },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
  };

  Plotly.newPlot("heatmap-plot", [heatTrace, starTrace], layout, {
    responsive: true,
    displayModeBar: false,
  });
  requestAnimationFrame(() => Plotly.Plots.resize("heatmap-plot"));
}

function renderResults(data) {
  errorBox.classList.add("hidden");
  emptyState.classList.add("hidden");
  resultsContent.classList.remove("hidden");

  document.getElementById("result-track").textContent =
    `${data.track.name} · ${data.track.laps} laps` + (data.track.calibrated ? " · calibrated pit loss" : "");
  document.getElementById("best-strategy").textContent = data.strategy_text;
  document.getElementById("total-time").textContent = data.time_text;

  // Confidence badge
  const conf = getConfidence(data.monte_carlo);
  const badge = document.getElementById("confidence-badge");
  badge.textContent = conf.label;
  badge.className = `text-xs font-bold px-2 py-0.5 rounded-full ${conf.cls}`;
  badge.classList.remove("hidden");

  // Best-strategy inventory note
  const invNote = document.getElementById("best-inventory-note");
  if (!data.best.feasible) {
    invNote.textContent = `⚠ Insufficient ${data.best.unavailable.join(", ")} sets — adjust allocation`;
    invNote.className = "text-xs mt-1 text-red-400";
    invNote.classList.remove("hidden");
  } else if (data.best.requires_used && data.best.requires_used.length > 0) {
    invNote.textContent = `⚠ Requires used ${data.best.requires_used.join(", ")} — add time penalty`;
    invNote.className = "text-xs mt-1 text-yellow-500";
    invNote.classList.remove("hidden");
  } else {
    invNote.classList.add("hidden");
  }

  const tbody = document.getElementById("alt-rows");
  tbody.innerHTML = "";
  data.alternatives.forEach((alt) => {
    const delta = alt.total_time - data.best.total_time;
    const row = document.createElement("tr");
    const infeasible = !alt.feasible;
    row.className = `border-t border-gray-800 text-xs${infeasible ? " opacity-40" : ""}`;
    row.innerHTML = `
      <td class="py-1 flex items-center gap-1">${compoundDots(alt.compounds)} ${alt.label}</td>
      <td class="py-1 text-center text-gray-500">${alt.stops}</td>
      <td class="py-1 text-right text-gray-400">${infeasible ? "—" : fmtDelta(delta)}</td>
      <td class="py-1 text-center pl-2">${inventoryBadge(alt)}</td>
    `;
    tbody.appendChild(row);
  });

  // Compact margins + smaller font for the dashboard chart
  const plot = JSON.parse(data.plot);
  plot.layout.margin = { t: 32, b: 28, l: 46, r: 12 };
  plot.layout.font = { size: 10, color: "#9ca3af" };
  plot.layout.legend = { orientation: "h", y: 1.12, x: 0, font: { size: 10 } };
  plot.layout.title = { text: plot.layout.title?.text || "", font: { size: 11 }, y: 0.98 };
  Plotly.newPlot("plot", plot.data, plot.layout, { responsive: true, displayModeBar: false });
  // Force resize so Plotly fills the flex-1 container correctly
  requestAnimationFrame(() => Plotly.Plots.resize("plot"));

  // Pit window from heatmap (laps within 2s of optimal for the best compound pair)
  const pitWindow = getPitWindow(data.heatmap);
  const pitBar = document.getElementById("pit-window-bar");
  if (pitWindow) {
    document.getElementById("pit-window-laps").textContent = `LAP ${pitWindow.start} – ${pitWindow.end}`;
    document.getElementById("optimal-pit-lap").textContent = `LAP ${data.heatmap.optimal_pit_lap}`;
    pitBar.classList.remove("hidden");
  } else {
    pitBar.classList.add("hidden");
  }

  renderHeatmap(data.heatmap);
  renderMonteCarlo(data.monte_carlo);
  renderCircuitCard(data.track, data.calibration, data.best);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);

  const payload = {
    track: trackSelect.value,
    laps: lapsInput.value,
    inventory: {
      S: { new: parseInt(document.getElementById("inv-S-new").value) || 0, used: parseInt(document.getElementById("inv-S-used").value) || 0 },
      M: { new: parseInt(document.getElementById("inv-M-new").value) || 0, used: parseInt(document.getElementById("inv-M-used").value) || 0 },
      H: { new: parseInt(document.getElementById("inv-H-new").value) || 0, used: parseInt(document.getElementById("inv-H-used").value) || 0 },
    },
  };
  if (trackSelect.value === "custom") {
    payload.pit_loss = pitLossInput.value;
    payload.base_lap_time = baseLapTimeInput.value;
    payload.deg_multiplier = degMultiplierInput.value;
  }

  try {
    const response = await fetch("/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Something went wrong calculating the strategy.");
      return;
    }
    renderResults(data);
  } catch (err) {
    showError("Could not reach the server. Is it running?");
  } finally {
    setLoading(false);
  }
});

// Auto-run once on load so the page never looks empty.
window.addEventListener("DOMContentLoaded", () => {
  form.dispatchEvent(new Event("submit", { cancelable: true }));
});

// Keep Plotly charts filling their flex containers on window resize.
window.addEventListener("resize", () => {
  Plotly.Plots.resize("plot");
  Plotly.Plots.resize("heatmap-plot");
});
