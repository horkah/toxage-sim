// Charts of the explorer as the web component <tox-chart chart="id">.
// The chart specs come from explorer/charts.py through the JSON script
// element #chart-data. Three types: bars, line, scatter. Plain SVG, no library.
// A line chart can carry markers (vertical lines) and dashed series.
// Pure helpers are exported for the tests in explorer/tests/charts.test.mjs.

const W = 460;

// Escape text for HTML and SVG.
export function esc(value) {
  return String(value).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

// A round step (1, 2, 2.5 or 5 times a power of ten) at least as large as raw.
export function niceStep(raw) {
  if (!(raw > 0)) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 2.5, 5, 10]) if (raw <= m * magnitude * (1 + 1e-9)) return m * magnitude;
  return 10 * magnitude;
}

// Round tick values that cover min..max.
export function niceTicks(min, max, count = 5) {
  if (max <= min) max = min + 1;
  const step = niceStep((max - min) / count);
  const first = Math.floor(min / step + 1e-9) * step;
  const ticks = [];
  for (let v = first; v < max + step - 1e-9 * step; v += step) ticks.push(+v.toFixed(10));
  if (ticks.length < 2) ticks.push(+(first + step).toFixed(10));
  return ticks;
}

// Linear map from domain [d0, d1] to range [r0, r1].
export function scale(d0, d1, r0, r1) {
  return (v) => (d1 === d0 ? (r0 + r1) / 2 : r0 + ((v - d0) * (r1 - r0)) / (d1 - d0));
}

// A value as text of an axis or a tooltip: percent, whole number or two decimals.
export function fmt(value, format) {
  if (value === null || value === undefined) return "–";
  if (format === "pct") return `${+(100 * value).toFixed(1)}%`;
  if (format === "int") return String(Math.round(value));
  return String(+value.toFixed(2));
}

// SVG path through points, as steps (horizontal, then vertical) if step is true.
export function linePath(points, sx, sy, step = false) {
  return points
    .map(([x, y], i) => {
      const p = `${sx(x).toFixed(1)},${sy(y).toFixed(1)}`;
      if (i === 0) return `M${p}`;
      return step ? `H${sx(x).toFixed(1)}V${sy(y).toFixed(1)}` : `L${p}`;
    })
    .join("");
}

// Address of the current page with some query parameters replaced.
// An array value sets the parameter once per element.
export function withParams(href, params) {
  const url = new URL(href);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.delete(key);
    for (const v of [].concat(value)) url.searchParams.append(key, v);
  }
  return url.pathname + url.search;
}

// An SVG text element at (x, y).
function text(x, y, content, cls = "", extra = "") {
  return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" class="${cls}" ${extra}>${esc(content)}</text>`;
}

// The legend below a chart: one swatch per series, and the selected patient if marked.
function legend(items, highlighted, what = "selected patient") {
  const entries = items.map((s) => `<span><i class="sw s-${esc(s.cls)}"></i>${esc(s.name)}</span>`);
  if (highlighted) entries.push(`<span><i class="sw s-hl"></i>${esc(what)}</span>`);
  return entries.length ? `<div class="legend">${entries.join("")}</div>` : "";
}

// Bar chart, vertical or horizontal, grouped or stacked; categories can be links that set a filter.
function bars(spec) {
  const { categories: cats, series, stacked, horizontal, highlight } = spec;
  const counts = spec.counts || [];
  const links = spec.links || [];
  const format = spec.value.format;
  const totals = cats.map((_, i) =>
    stacked ? series.reduce((s, x) => s + (x.values[i] || 0), 0) : Math.max(...series.map((x) => x.values[i] || 0)));
  const ticks = niceTicks(0, Math.max(...totals, format === "pct" ? 0.01 : 1));
  const top = ticks.at(-1);
  const labels = cats.map((c, i) => (counts.length ? `${c} · ${counts[i]}` : c));
  const tip = (i) => [labels[i], ...series.map((s) => `${s.name}: ${fmt(s.values[i], format)}`)].join("\n");
  const parts = [];
  let height;

  if (horizontal) {
    const left = Math.min(200, 12 + 6.8 * Math.max(...labels.map((l) => l.length)));
    const band = stacked ? 20 : series.length * 9 + 10;
    height = 8 + cats.length * band + 36;
    const sx = scale(0, top, left, W - 14);
    const bottom = height - 36;
    for (const t of ticks) {
      parts.push(`<line class="grid" x1="${sx(t)}" x2="${sx(t)}" y1="8" y2="${bottom}"/>`);
      parts.push(text(sx(t), bottom + 14, fmt(t, format), "tick", 'text-anchor="middle"'));
    }
    parts.push(text((left + W - 14) / 2, bottom + 30, spec.value.label, "axis", 'text-anchor="middle"'));
    cats.forEach((_, i) => {
      const y0 = 8 + i * band;
      const hl = i === highlight;
      const g = [`<title>${esc(tip(i))}</title>`,
        `<rect class="hit${hl ? " hl-band" : ""}" x="0" y="${y0}" width="${W}" height="${band}"/>`,
        text(left - 6, y0 + band / 2 + 4, labels[i], hl ? "cat hl-text" : "cat", 'text-anchor="end"')];
      let x = left;
      series.forEach((s, j) => {
        const v = s.values[i];
        if (v === null || v === undefined) return;
        const w = Math.max(0, sx(v) - left);
        const y = stacked ? y0 + 4 : y0 + 5 + j * 9;
        g.push(`<rect class="s-${esc(s.cls)}" x="${(stacked ? x : left).toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="${stacked ? band - 8 : 8}" rx="1.5"/>`);
        if (stacked) x += w;
      });
      parts.push(`<g class="cat-group${links[i] ? " link" : ""}"${links[i] ? ` data-link="${i}"` : ""}>${g.join("")}</g>`);
    });
  } else {
    const rotate = cats.length > 7;
    height = rotate ? 290 : 270;
    const left = 46, bottom = height - (rotate ? 74 : 54), right = W - 10;
    const band = (right - left) / cats.length;
    const sy = scale(0, top, bottom, 10);
    for (const t of ticks) {
      parts.push(`<line class="grid" x1="${left}" x2="${right}" y1="${sy(t)}" y2="${sy(t)}"/>`);
      parts.push(text(left - 5, sy(t) + 4, fmt(t, format), "tick", 'text-anchor="end"'));
    }
    parts.push(text(12, (bottom + 10) / 2, spec.value.label, "axis", `text-anchor="middle" transform="rotate(-90 12 ${(bottom + 10) / 2})"`));
    if (spec.axis) parts.push(text((left + right) / 2, height - 4, spec.axis, "axis", 'text-anchor="middle"'));
    cats.forEach((c, i) => {
      const x0 = left + i * band;
      const hl = i === highlight;
      const lx = x0 + band / 2;
      const g = [`<title>${esc(tip(i))}</title>`,
        `<rect class="hit${hl ? " hl-band" : ""}" x="${x0}" y="10" width="${band}" height="${bottom - 10}"/>`,
        rotate
          ? text(lx, bottom + 10, c, hl ? "cat hl-text" : "cat", `text-anchor="end" transform="rotate(-45 ${lx.toFixed(1)} ${bottom + 10})"`)
          : text(lx, bottom + 14, c, hl ? "cat hl-text" : "cat", 'text-anchor="middle"')];
      let y = bottom;
      const inner = stacked ? band - 4 : (band - 4) / series.length;
      series.forEach((s, j) => {
        const v = s.values[i] || 0;
        const h = bottom - sy(v);
        const x = stacked ? x0 + 2 : x0 + 2 + j * inner;
        const yy = stacked ? y - h : bottom - h;
        g.push(`<rect class="s-${esc(s.cls)}" x="${x.toFixed(1)}" y="${yy.toFixed(1)}" width="${Math.max(1, inner - 1).toFixed(1)}" height="${h.toFixed(1)}" rx="1.5"/>`);
        if (stacked) y -= h;
      });
      parts.push(`<g class="cat-group${links[i] ? " link" : ""}"${links[i] ? ` data-link="${i}"` : ""}>${g.join("")}</g>`);
    });
    parts.push(`<line class="axisline" x1="${left}" x2="${right}" y1="${bottom}" y2="${bottom}"/>`);
  }
  return { height, svg: parts.join(""), legend: legend(series, highlight !== null && highlight !== undefined, spec.highlight_name) };
}

// Axes, grid and labels of a chart with numeric x and y; returns the scales for the marks.
function frame(spec, height, left = 50, bottom = 40) {
  const x = spec.x, y = spec.y;
  const xt = niceTicks(x.min, x.max), yt = niceTicks(y.min, y.max);
  const sx = scale(xt[0], xt.at(-1), left, W - 12);
  const sy = scale(yt[0], yt.at(-1), height - bottom, 10);
  const parts = [];
  for (const t of xt) {
    parts.push(`<line class="grid" x1="${sx(t)}" x2="${sx(t)}" y1="10" y2="${height - bottom}"/>`);
    parts.push(text(sx(t), height - bottom + 14, fmt(t, x.format), "tick", 'text-anchor="middle"'));
  }
  for (const t of yt) {
    parts.push(`<line class="grid" x1="${left}" x2="${W - 12}" y1="${sy(t)}" y2="${sy(t)}"/>`);
    parts.push(text(left - 5, sy(t) + 4, fmt(t, y.format), "tick", 'text-anchor="end"'));
  }
  parts.push(text((left + W - 12) / 2, height - 6, x.label, "axis", 'text-anchor="middle"'));
  const mid = (height - bottom + 10) / 2;
  parts.push(text(12, mid, y.label, "axis", `text-anchor="middle" transform="rotate(-90 12 ${mid})"`));
  return { sx, sy, parts, xt, yt, left };
}

// Line chart: series as lines or steps, optional dots, a diagonal, a marker and vertical event lines.
function line(spec) {
  const height = 270;
  const { sx, sy, parts, xt, yt } = frame(spec, height);
  if (spec.diagonal) {
    const end = Math.min(xt.at(-1), yt.at(-1));
    parts.push(`<line class="diagonal" x1="${sx(0)}" y1="${sy(0)}" x2="${sx(end)}" y2="${sy(end)}"><title>perfect calibration</title></line>`);
  }
  for (const s of spec.series) {
    if (!s.points.length) continue;
    parts.push(`<path class="ln s-${esc(s.cls)}${s.dash ? " dash" : ""}" d="${linePath(s.points, sx, sy, s.step)}"><title>${esc(s.name)}</title></path>`);
    if (s.dots) {
      for (const [x, y] of s.points) {
        parts.push(`<circle class="dot s-${esc(s.cls)}" cx="${sx(x).toFixed(1)}" cy="${sy(y).toFixed(1)}" r="4"><title>${esc(`predicted ${fmt(x, spec.x.format)}, observed ${fmt(y, spec.y.format)}`)}</title></circle>`);
      }
    }
  }
  const m = spec.marker;
  if (m && m.x !== null && m.x !== undefined) {
    const x = sx(m.x);
    parts.push(`<line class="marker" x1="${x}" x2="${x}" y1="10" y2="${height - 40}"/>`);
    parts.push(text(Math.min(x + 4, W - 80), 22, m.label, "hl-text"));
  }
  // Markers: vertical lines at points in time, e.g. the events of a patient.
  for (const k of spec.markers || []) {
    const x = sx(k.x).toFixed(1);
    parts.push(`<line class="mk mk-${esc(k.cls)}" x1="${x}" x2="${x}" y1="10" y2="${height - 40}"><title>${esc(k.label)}</title></line>`);
  }
  return { height, svg: parts.join(""), legend: legend(spec.series.concat(spec.marker_legend || []), !!m) };
}

// Scatter plot of patients, coloured by outcome; points select a patient, the selected one has a crosshair.
function scatter(spec) {
  const height = 290;
  const { sx, sy, parts, left } = frame(spec, height);
  const order = [...spec.points].sort((a, b) => a[2] - b[2]);
  const classes = spec.classes;
  for (const [x, y, c, id] of order) {
    parts.push(`<circle class="pt s-${esc(classes[c].cls)}" data-id="${esc(id)}" cx="${sx(x).toFixed(1)}" cy="${sy(y).toFixed(1)}" r="2.6"><title>${esc(`${id}: ${fmt(x, spec.x.format)}, ${fmt(y, spec.y.format)} (${classes[c].name})`)}</title></circle>`);
  }
  const h = spec.highlight;
  if (h) {
    const [x, y] = [sx(h[0]), sy(h[1])];
    parts.push(`<line class="marker" x1="${x}" x2="${x}" y1="10" y2="${height - 40}"/><line class="marker" x1="${left}" x2="${W - 12}" y1="${y}" y2="${y}"/>`);
    parts.push(`<circle class="hl-point" cx="${x}" cy="${y}" r="6"><title>${esc(h[2])}</title></circle>`);
  }
  return { height, svg: parts.join(""), legend: legend(classes, !!h) };
}

const RENDER = { bars, line, scatter };
let data, source;

// The chart data of the page. A page swapped in place brings its own element.
function chartData() {
  const el = document.getElementById("chart-data");
  if (el !== source) {
    source = el;
    data = el ? JSON.parse(el.textContent) : {};
  }
  return data;
}

// The element <tox-chart chart="id">: draws the chart with that id from the chart data of the page.
export class ToxChart extends (globalThis.HTMLElement ?? class {}) {
  // Draw the chart when the element enters the page.
  connectedCallback() {
    const spec = chartData()[this.getAttribute("chart")];
    if (!spec) return;
    this.spec = spec;
    let body;
    if (spec.empty) {
      body = `<p class="empty">No patients in the selection.</p>`;
    } else {
      const { height, svg, legend: keys } = RENDER[spec.type](spec);
      body = `<svg viewBox="0 0 ${W} ${height}" role="img" aria-label="${esc(spec.title)}">${svg}</svg>${keys}`;
      if (spec.note) body += `<p class="chart-note">${esc(spec.note)}</p>`;
    }
    this.innerHTML = `<figure><figcaption>${esc(spec.title)}</figcaption>${body}</figure>`;
    this.addEventListener("click", (event) => this.follow(event));
  }

  // A click on a point selects the patient, a click on a category applies its filter.
  follow(event) {
    const target = event.target.closest("[data-id], [data-link]");
    if (!target) return;
    const params = target.dataset.id !== undefined
      ? { patient: target.dataset.id }
      : this.spec.links[Number(target.dataset.link)];
    if (!params) return;
    const url = withParams(location.href, params);
    // The page script loads it in place; without it, as a new page.
    if (document.documentElement.dataset.router === "1") {
      document.dispatchEvent(new CustomEvent("toxage:navigate", { detail: url }));
    } else {
      location.href = url;
    }
  }
}

if (globalThis.customElements && !customElements.get("tox-chart")) {
  customElements.define("tox-chart", ToxChart);
}
