/* main.js: draws every chart on the page.
   ----------------------------------------
   index.html contains one <figure class="chart-card"> per chart. Each card names its chart
   spec (data-spec) and the data files it needs (data-requires), and holds an empty
   <div class="chart-mount"> where the chart goes. This file:
     1. finds every chart card,
     2. checks that the card's data files exist and contain data,
     3. loads the card's spec (Vega-Lite, or Vega for the treemap and drill-down map) and draws it with vegaEmbed.
   If a data file is missing or empty, a "Data pending" card is shown instead, naming the file,
   columns and source it needs, so no values are ever invented to fill the gap.
   All chart logic lives in the spec files in specs/; this file only loads and draws them. */


/* ---------- Shared chart styling ---------- */

/* Colour roles, used the same way in every spec (and in css/style.css):
     orange  #eb6834  what to look at: the story's focus, or what the reader selected
     blue    #2a78d6  the data itself; the ramp #cde2fb -> #0d366b means "more"
     amber   #eda100  the second group when two groups are compared (girls vs boys)
     grey    #aeada5  context (other services, earlier year, longer videos)
     light   #e8e7e1  no data
   All chart text is 12px Atkinson Hyperlegible; facet headers and in-chart titles are 13px bold. */

/**
 * THEME: the Vega-Lite "config" every chart starts from.
 * Why: setting fonts, text sizes and colours once here keeps all 12 charts consistent with each
 * other and with the page's CSS, and keeps each spec short (it only states what is special about it).
 */
const THEME = {
  font: "Atkinson Hyperlegible, system-ui, sans-serif", // same body font as the page
  background: "#fcfcfb",                                 // same as the chart cards (--surface)
  view: { stroke: null },                                // remove the default grey box around each plot
  padding: 4,
  axis: {
    labelColor: "#52514e",
    titleColor: "#52514e",
    labelFontSize: 12,
    titleFontSize: 12,
    titleFontWeight: "normal",
    gridColor: "#e1e0d9",                                // light gridlines so the data stands out
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
  header: {                                              // panel titles in small multiples (chart 7)
    labelColor: "#0b0b0b",
    labelFontSize: 13,
    labelFontWeight: "bold",
    titleFontSize: 12
  },
  title: {                                               // in-chart titles (e.g. the waffle headline)
    font: "Atkinson Hyperlegible, system-ui, sans-serif",
    color: "#0b0b0b",
    fontSize: 13,
    fontWeight: "bold",
    anchor: "start",
    offset: 12
  },
  text: { font: "Atkinson Hyperlegible, system-ui, sans-serif", color: "#52514e", fontSize: 12 },
  range: {                                               // fallback palettes if a spec doesn't set its own
    category: ["#2a78d6", "#eda100", "#eb6834", "#aeada5"],
    ramp: ["#cde2fb", "#0d366b"]
  }
};

/**
 * EMBED_OPTIONS: the settings passed to vegaEmbed for every chart.
 * Why each one:
 *   renderer "svg": draw shapes as SVG elements, not a canvas picture, so charts stay sharp when
 *                   zoomed and screen readers and the browser inspector can see each mark.
 *   config THEME:   apply the shared styling above.
 *   loader:         see the comment on that line.
 *   actions:        the "..." menu on each chart: save as SVG/PNG, view the spec, open it in the
 *                   Vega Editor. The compiled Vega view is hidden because readers don't need it.
 */
const EMBED_OPTIONS = {
  renderer: "svg",
  config: THEME,
  // Ask the server whether each CSV has changed instead of reusing a cached copy, so an
  // updated data file (e.g. new columns) can't be paired with an old one from the cache.
  loader: vega.loader({ http: { cache: "no-cache" } }),
  actions: { export: true, source: true, compiled: false, editor: true }
};


/* ---------- Helper functions ---------- */

/**
 * hasData: does this data file exist and contain at least one row of data?
 * @param {string} path  file path from the card's data-requires attribute, e.g. "data/videos.csv"
 * @returns {Promise<boolean>}  true if the file loads and has a header row plus at least one data row
 * Why: a missing or header-only CSV would draw an empty chart with no explanation. Checking first
 * lets loadChart show a "Data pending" card that says exactly which file is missing.
 */
async function hasData(path) {
  try {
    // "no-store" skips the browser cache, so a file that was just added or fixed is seen straight away.
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return false;                // e.g. 404: the file doesn't exist
    const text = await res.text();
    // Split into lines (\r?\n handles both Windows and Unix line endings), drop blank lines,
    // and require a header row plus at least one data row.
    return text.trim().split(/\r?\n/).filter(line => line.trim() !== "").length >= 2;
  } catch (err) {
    return false;                             // network error: treat as missing rather than crash
  }
}

/**
 * escapeHtml: make any text safe to insert into the page as HTML.
 * @param {*} str  text to show (converted to a string first)
 * @returns {string}  the same text with & < > " ' replaced by their HTML codes
 * Why: renderPending and the error message build HTML from attribute values and error messages.
 * Escaping means that text is always shown as text and can never be run as HTML or a script.
 */
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/**
 * renderPending: show a "Data pending" card in place of a chart.
 * @param {HTMLElement} card     the chart's <figure>; its data-* attributes describe the chart
 * @param {HTMLElement} mount    the empty .chart-mount div inside the card
 * @param {string[]} missing     the data files that are missing or empty
 * Why: the project uses real data only. Instead of drawing a chart with invented values, the card
 * lists the chart type, the missing files, the columns they need and where the data comes from.
 * All 12 charts have data now, so this is a safety net (e.g. if a CSV fails to deploy).
 */
function renderPending(card, mount, missing) {
  const d = card.dataset;                     // card.dataset.idiom reads data-idiom, and so on
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


/* ---------- Main routine ---------- */

/**
 * loadChart: draw one chart card.
 * @param {HTMLElement} card  a <figure class="chart-card"> with data-spec and data-requires attributes
 * Steps:
 *   1. Read the list of data files the card needs.
 *   2. Check them all at once; if any is missing, show the "Data pending" card and stop.
 *   3. Load the spec file and draw it into the card with vegaEmbed.
 *   4. If anything fails, show a short error in this card only, so the other charts still load.
 * Why "async": loading files takes time. "await" pauses only this function while it waits,
 * so the page stays responsive and all the cards can load at the same time.
 */
async function loadChart(card) {
  const mount = card.querySelector(".chart-mount");
  // "data/a.csv, data/b.csv" -> ["data/a.csv", "data/b.csv"]  (trim spaces, drop empty entries)
  const required = (card.dataset.requires || "").split(",").map(s => s.trim()).filter(Boolean);

  // Check every file in parallel and wait for all the answers, e.g. [true, false].
  const checks = await Promise.all(required.map(hasData));
  // Keep the paths whose check failed ("_" = the path itself isn't needed here, only its index).
  const missing = required.filter((_, i) => !checks[i]);
  if (missing.length) {
    renderPending(card, mount, missing);
    return;
  }

  try {
    // Load the spec file and turn its JSON text into a JavaScript object.
    const spec = await fetch(card.dataset.spec, { cache: "no-store" }).then(r => {
      if (!r.ok) throw new Error(`Could not load ${card.dataset.spec}`);
      return r.json();
    });
    // vegaEmbed reads the spec's $schema: a Vega-Lite spec is compiled to Vega first, a Vega spec
    // (the treemap, the drill-down map) is used as it is. It then loads the spec's CSV files and draws the chart,
    // plus any menus or switches the spec defines, inside the mount div.
    await vegaEmbed(mount, spec, EMBED_OPTIONS);

    // A click often changes what the chart shows (e.g. the drill-down map opens a new level), which
    // can leave the old tooltip floating over the new view until the mouse moves. Hide it on click;
    // Vega shows the right tooltip again as soon as the mouse moves.
    mount.addEventListener("click", () => {
      const tip = document.getElementById("vg-tooltip-element");
      if (tip) tip.classList.remove("visible");
    });
  } catch (err) {
    console.error(card.id, err);              // full details for debugging (F12 -> Console)
    mount.innerHTML = `<p class="chart-error">This chart could not be drawn: ${escapeHtml(err.message)}</p>`;
  }
}

// Start: find every chart card that names a spec and load each one.
// The Part 5 before/after panel has no data-spec, so it is left alone.
// This script is the last thing in <body>, so every card already exists when this line runs.
document.querySelectorAll(".chart-card[data-spec]").forEach(loadChart);
