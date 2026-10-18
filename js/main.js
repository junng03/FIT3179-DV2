/* Loads each chart's Vega-Lite spec from specs/ and embeds it.
   If a chart's data file is missing or empty, a "data pending" card is shown
   instead, naming the file, columns and source it needs. No values are invented. */

/* Colour roles, used the same way in every spec (and in css/style.css):
     orange  #eb6834  what to look at: the story's focus, or what the reader selected
     blue    #2a78d6  the data itself; the ramp #cde2fb -> #0d366b means "more"
     amber   #eda100  the second group when two groups are compared (girls vs boys)
     grey    #aeada5  context (other services, earlier year, longer videos)
     light   #e8e7e1  no data
   All chart text is 12px Atkinson Hyperlegible; facet headers and in-chart titles are 13px bold. */
const THEME = {
  font: "Atkinson Hyperlegible, system-ui, sans-serif",
  background: "#fcfcfb",
  view: { stroke: null },
  padding: 4,
  axis: {
    labelColor: "#52514e",
    titleColor: "#52514e",
    labelFontSize: 12,
    titleFontSize: 12,
    titleFontWeight: "normal",
    gridColor: "#e1e0d9",
    domainColor: "#c3c2b7",
    tickColor: "#c3c2b7"
  },
  legend: {
    labelColor: "#52514e",
    titleColor: "#52514e",
    labelFontSize: 12,
    titleFontSize: 12,
    titleFontWeight: "normal",
    symbolType: "circle"
  },
  header: {
    labelColor: "#0b0b0b",
    labelFontSize: 13,
    labelFontWeight: "bold",
    titleFontSize: 12
  },
  title: {
    font: "Atkinson Hyperlegible, system-ui, sans-serif",
    color: "#0b0b0b",
    fontSize: 13,
    fontWeight: "bold",
    anchor: "start",
    offset: 12
  },
  text: { font: "Atkinson Hyperlegible, system-ui, sans-serif", color: "#52514e", fontSize: 12 },
  range: {
    category: ["#2a78d6", "#eda100", "#eb6834", "#aeada5"],
    ramp: ["#cde2fb", "#0d366b"]
  }
};

const EMBED_OPTIONS = {
  renderer: "svg",
  config: THEME,
  // Ask the server whether each CSV has changed instead of reusing a cached copy, so an
  // updated data file (e.g. new columns) can't be paired with an old one from the cache.
  loader: vega.loader({ http: { cache: "no-cache" } }),
  actions: { export: true, source: true, compiled: false, editor: true }
};

async function hasData(path) {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return false;
    const text = await res.text();
    // Need a header row plus at least one data row.
    return text.trim().split(/\r?\n/).filter(line => line.trim() !== "").length >= 2;
  } catch (err) {
    return false;
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderPending(card, mount, missing) {
  const d = card.dataset;
  mount.innerHTML = `
    <div class="pending" role="note">
      <span class="badge">Data pending</span>
      <dl>
        <dt>Idiom</dt><dd>${escapeHtml(d.idiom || "")}</dd>
        <dt>Needs</dt><dd>${missing.map(f => `<code>${escapeHtml(f)}</code>`).join(", ")}</dd>
        <dt>Columns</dt><dd><code>${escapeHtml(d.columns || "")}</code></dd>
        <dt>Source</dt><dd>${escapeHtml(d.source || "")}</dd>
        <dt>Spec</dt><dd><a href="${escapeHtml(d.spec)}">${escapeHtml(d.spec)}</a></dd>
      </dl>
    </div>`;
}

async function loadChart(card) {
  const mount = card.querySelector(".chart-mount");
  const required = (card.dataset.requires || "").split(",").map(s => s.trim()).filter(Boolean);

  const checks = await Promise.all(required.map(hasData));
  const missing = required.filter((_, i) => !checks[i]);
  if (missing.length) {
    renderPending(card, mount, missing);
    return;
  }

  try {
    const spec = await fetch(card.dataset.spec, { cache: "no-store" }).then(r => {
      if (!r.ok) throw new Error(`Could not load ${card.dataset.spec}`);
      return r.json();
    });
    await vegaEmbed(mount, spec, EMBED_OPTIONS);
  } catch (err) {
    console.error(card.id, err);
    mount.innerHTML = `<p class="chart-error">This chart could not be drawn: ${escapeHtml(err.message)}</p>`;
  }
}

document.querySelectorAll(".chart-card[data-spec]").forEach(loadChart);
