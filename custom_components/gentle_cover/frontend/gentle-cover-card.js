/**
 * Gentle Cover card — a room's curve on a dashboard, and where a running
 * move is on it. Read-only: curves are edited on the Gentle Cover page.
 *
 * Drawn in the dashboard's theme, not the page's slab, because it lives
 * among other cards. The curve is interpolated here for drawing only (the
 * same monotone cubic as curve.py); moves are always planned in Python.
 */

const W = 320;
const H = 150;
const M = { left: 8, right: 8, top: 10, bottom: 10 };
const xOf = (t) => M.left + t * (W - M.left - M.right);
const yOf = (p) => M.top + (1 - p / 100) * (H - M.top - M.bottom);

/** Fritsch–Carlson monotone cubic through the points, as in curve.py. */
const interpolator = (points) => {
  const x = points.map((p) => p[0]);
  const y = points.map((p) => p[1]);
  const n = x.length;
  const d = [];
  for (let k = 0; k < n - 1; k++) d.push((y[k + 1] - y[k]) / (x[k + 1] - x[k]));
  const m = new Array(n).fill(0);
  m[0] = d[0];
  m[n - 1] = d[n - 2];
  for (let k = 1; k < n - 1; k++) m[k] = d[k - 1] * d[k] > 0 ? (d[k - 1] + d[k]) / 2 : 0;
  for (let k = 0; k < n - 1; k++) {
    if (d[k] === 0) {
      m[k] = 0;
      m[k + 1] = 0;
      continue;
    }
    const a = m[k] / d[k];
    const b = m[k + 1] / d[k];
    const h = a * a + b * b;
    if (h > 9) {
      const tau = 3 / Math.sqrt(h);
      m[k] = tau * a * d[k];
      m[k + 1] = tau * b * d[k];
    }
  }
  return (tRaw) => {
    const t = Math.min(1, Math.max(0, tRaw));
    let k = 0;
    while (k < n - 2 && t > x[k + 1]) k++;
    const h = x[k + 1] - x[k];
    const u = (t - x[k]) / h;
    return (2 * u ** 3 - 3 * u ** 2 + 1) * y[k] + (u ** 3 - 2 * u ** 2 + u) * h * m[k]
      + (-2 * u ** 3 + 3 * u ** 2) * y[k + 1] + (u ** 3 - u ** 2) * h * m[k + 1];
  };
};

const esc = (text) =>
  String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class GentleCoverCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("Choose a gentle curtain (entity)");
    this.config = config;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this.config?.entity];
    if (state !== this._state) {
      this._state = state;
      this.render();
    }
  }

  connectedCallback() {
    // While a move runs the marker walks along the curve between updates.
    this._timer = setInterval(() => {
      if (this._state?.attributes?.move_started_at) this.render();
    }, 5000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() { return 3; }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) =>
      id.startsWith("cover.") && hass.states[id].attributes.open_curve);
    return { entity: entity || "" };
  }

  render() {
    if (!this.shadowRoot || !this.config) return;
    const state = this._state;
    const name = this.config.title || state?.attributes?.friendly_name || this.config.entity;
    let body;
    if (!state) {
      body = `<div class="message">${esc(this.config.entity)} not found</div>`;
    } else if (state.state === "unavailable") {
      // An unavailable entity carries no attributes, curves included.
      body = `<div class="message">Unavailable — the curtains are not reporting a position</div>`;
    } else if (!Array.isArray(state.attributes.open_curve)) {
      body = `<div class="message">${esc(this.config.entity)} is not a gentle curtain</div>`;
    } else {
      body = this.chart(state);
    }
    this.shadowRoot.innerHTML = `<style>
      ha-card { padding:16px; }
      .head { display:flex; align-items:baseline; gap:8px; margin-bottom:8px; }
      .name { font-size:16px; font-weight:500; flex:1; color:var(--primary-text-color); }
      .position { color:var(--secondary-text-color); font-variant-numeric:tabular-nums; }
      svg { display:block; width:100%; height:auto; }
      .grid { stroke:var(--divider-color); stroke-width:1; }
      .curve { fill:none; stroke:var(--primary-color); stroke-width:2.5; }
      .now { stroke:var(--secondary-text-color); stroke-width:1; stroke-dasharray:4 3; }
      .marker { fill:var(--primary-color); stroke:var(--card-background-color, #fff); stroke-width:2; }
      .status { margin-top:8px; color:var(--secondary-text-color); font-size:13px; }
      .message { color:var(--secondary-text-color); padding:16px 0; }
    </style>
    <ha-card>
      <div class="head"><span class="name">${esc(name)}</span>
        <span class="position">${state && state.attributes.current_position !== undefined ? `${state.attributes.current_position} %` : ""}</span></div>
      ${body}
    </ha-card>`;
  }

  chart(state) {
    const a = state.attributes;
    const moving = Boolean(a.move_started_at && a.move_span_s);
    const direction = moving ? a.move_direction : "open";
    const points = direction === "close" ? a.close_curve : a.open_curve;
    const at = interpolator(points);
    let path = "";
    for (let i = 0; i <= 100; i++) {
      path += `${i ? "L" : "M"}${xOf(i / 100).toFixed(1)},${yOf(at(i / 100)).toFixed(1)} `;
    }
    const grid = [0, 50, 100].map((p) =>
      `<line class="grid" x1="${M.left}" x2="${W - M.right}" y1="${yOf(p)}" y2="${yOf(p)}"></line>`).join("");
    const position = a.current_position;
    const now = position === undefined ? "" :
      `<line class="now" x1="${M.left}" x2="${W - M.right}" y1="${yOf(position)}" y2="${yOf(position)}"></line>`;
    let marker = "";
    let status = state.state === "unavailable" ? "Unavailable" : "";
    if (moving) {
      const elapsed = (Date.now() - new Date(a.move_started_at).getTime()) / 1000;
      const share = Math.min(1, Math.max(0, elapsed / a.move_span_s));
      const t = a.move_curve_start + (a.move_curve_end - a.move_curve_start) * share;
      marker = `<circle class="marker" cx="${xOf(t).toFixed(1)}" cy="${yOf(at(t)).toFixed(1)}" r="6"></circle>`;
      const left = Math.max(0, Math.ceil((a.move_span_s - elapsed) / 60));
      status = `${direction === "close" ? "Closing" : "Opening"} to ${a.target_position} % · ${left} min left`;
    }
    return `<svg viewBox="0 0 ${W} ${H}">${grid}${now}<path class="curve" d="${path}"></path>${marker}</svg>
      ${status ? `<div class="status">${esc(status)}</div>` : ""}`;
  }
}

if (!customElements.get("gentle-cover-card")) {
  customElements.define("gentle-cover-card", GentleCoverCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "gentle-cover-card",
    name: "Gentle Cover",
    description: "A room's opening or closing curve, and where a gentle move is on it.",
  });
}
