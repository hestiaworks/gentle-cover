/**
 * Gentle Cover — the page where a room's movement is drawn.
 *
 * One file, one shadow root, no build step, in the slab language Room
 * Thermostat and NSPanel Companion are drawn in. The rules that keep that
 * language intact, copied from there because both are easy to break:
 *
 *   1. A border is ALWAYS var(--line), never var(--accent). Accent marks the
 *      one thing you selected: a primary button fill, the inset bar of the
 *      selected row, the underline of the active tab, the selected point, a
 *      focus ring.
 *   2. Accent as text is var(--accent-ink), never var(--accent).
 *
 * The page draws and edits; the rules live in Python. Every edit asks the
 * server for a preview, which runs the same planner a real move runs, so the
 * steps on the chart are the commands the curtains will get.
 */

const FONT_FACES = `
@font-face { font-family:Barlow; font-style:normal; font-weight:400; font-display:swap;
  src:url('/gentle_cover/frontend/fonts/barlow-400.woff2') format('woff2'); }
@font-face { font-family:Barlow; font-style:normal; font-weight:500; font-display:swap;
  src:url('/gentle_cover/frontend/fonts/barlow-500.woff2') format('woff2'); }
@font-face { font-family:Barlow; font-style:normal; font-weight:600; font-display:swap;
  src:url('/gentle_cover/frontend/fonts/barlow-600.woff2') format('woff2'); }
@font-face { font-family:Barlow; font-style:normal; font-weight:700; font-display:swap;
  src:url('/gentle_cover/frontend/fonts/barlow-700.woff2') format('woff2'); }
@font-face { font-family:'Roboto Mono'; font-style:normal; font-weight:400 500; font-display:swap;
  src:url('/gentle_cover/frontend/fonts/roboto-mono-latin.woff2') format('woff2'); }`;

const installFonts = () => {
  const id = "gentle-cover-fonts";
  if (document.getElementById(id)) return;
  const style = document.createElement("style");
  style.id = id;
  style.textContent = FONT_FACES;
  document.head.appendChild(style);
};

const STYLES = `
:host {
  --canvas:#0E1012; --surface:#171B1F; --surface-raised:#242B33; --accent-wash:#33200F;
  --ink:#F2F5F7; --muted:#949CA3; --disabled:#4A5158; --line:#2F373E;
  --accent:#F36D21; --accent-ink:#FF9455; --on-accent:#0E1012;
  --danger:#D24A3F; --danger-wash:#2E1512; --ok:#34C759;
  --radius:2px; --row:40px; --control:36px; --control-sm:28px; --app-bar:56px; --tab-bar:44px;
  --font:Barlow,system-ui,-apple-system,sans-serif;
  --mono:'Roboto Mono',ui-monospace,SFMono-Regular,monospace;
  display:block; min-height:100%; background:var(--canvas); color:var(--ink);
  font-family:var(--font); font-size:14px; font-variant-numeric:tabular-nums;
}
*, *::before, *::after { box-sizing:border-box; }
h1,h2,p { margin:0; }

button {
  height:var(--control); padding:0 16px; display:inline-flex; align-items:center;
  justify-content:center; gap:8px; border:1px solid var(--line); border-radius:var(--radius);
  background:var(--surface-raised); color:var(--ink); font:600 14px/1 var(--font);
  cursor:pointer; white-space:nowrap;
}
button:hover { background:var(--line); }
button:active { transform:translateY(1px); }
button.primary { background:var(--accent); border-color:var(--accent); color:var(--on-accent); }
button.primary:hover { filter:brightness(1.08); background:var(--accent); }
button.quiet { background:transparent; border-color:transparent; color:var(--muted); }
button.quiet:hover { background:var(--surface-raised); color:var(--ink); }
button.small { height:var(--control-sm); padding:0 12px; font-size:13px; }
button:disabled { background:var(--surface); color:var(--disabled); border-color:var(--line); cursor:default; transform:none; filter:none; }
input {
  height:var(--control); width:100%; padding:0 12px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--canvas); color:var(--ink); font:500 13px/1 var(--mono);
}
:is(button,input,[tabindex]):focus-visible { outline:2px solid var(--accent); outline-offset:1px; }

.app-bar { min-height:calc(var(--app-bar) + env(safe-area-inset-top, 0px)); display:flex;
  align-items:center; gap:12px; padding:env(safe-area-inset-top, 0px) 32px 0;
  border-bottom:1px solid var(--line); }
.app-bar .mark { width:8px; height:8px; background:var(--accent); flex:none; }
.app-bar .title { font:700 15px/1 var(--font); }
.app-bar .spacer { flex:1; }
.menu { display:none; }
:host([narrow]) .menu { display:inline-flex; }
.save-state { font:400 13px/1 var(--font); color:var(--muted); }
.save-state.dirty { color:var(--accent-ink); }

.page { padding:32px; max-width:1180px; margin:0 auto; }
.layout { display:grid; grid-template-columns:232px minmax(0,1fr); gap:32px; align-items:start; }
:host([narrow]) .page { padding:16px; }
:host([narrow]) .layout { grid-template-columns:minmax(0,1fr); gap:16px; }
:host([narrow]) .app-bar { padding-left:8px; padding-right:16px; }

.group-label { font:600 11px/1 var(--font); letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); margin-bottom:8px; }
.band { border:1px solid var(--line); }
.band > * + * { border-top:1px solid var(--line); }
.row { min-height:var(--row); display:flex; align-items:center; gap:12px; padding:8px 16px; cursor:pointer; }
.row:hover { background:var(--surface-raised); }
.row.selected { background:var(--accent-wash); box-shadow:inset 3px 0 0 var(--accent); }
.row .grow { flex:1; min-width:0; }
.row .name { font:600 14px/1.2 var(--font); }
.row .sub { font:400 12px/1.4 var(--font); color:var(--muted); }

.tabs { height:var(--tab-bar); display:flex; border-bottom:1px solid var(--line); margin-bottom:20px; }
.tabs button { height:100%; border:0; border-radius:0; background:transparent; color:var(--muted); padding:0 16px; }
.tabs button:hover { background:transparent; color:var(--ink); }
.tabs button.active { color:var(--ink); box-shadow:inset 0 -2px 0 var(--accent); }
.tabs button:focus-visible { outline-offset:-2px; }

.chart { border:1px solid var(--line); background:var(--surface); }
.chart svg { display:block; width:100%; height:auto; touch-action:none; user-select:none; }
.toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:12px 0; }
.toolbar .spacer { flex:1; }
.toolbar .label { font:600 12px/1 var(--font); color:var(--muted); margin-right:4px; }
.fields { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:16px; margin-top:8px; }
:host([narrow]) .fields { grid-template-columns:minmax(0,1fr); }
.field { display:flex; flex-direction:column; gap:6px; }
.field .label { font:600 12px/1 var(--font); color:var(--muted); }
.field .hint { font:400 12px/1.5 var(--font); color:var(--muted); }
.summary { margin-top:20px; padding:12px 16px; border:1px solid var(--line); font:400 13px/1.5 var(--font); color:var(--muted); }
.summary strong { color:var(--ink); font-weight:600; }
.actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:20px; }
.notice { margin-bottom:16px; padding:10px 16px; border:1px solid var(--line); background:var(--danger-wash); }
.notice.info { background:var(--surface); }
.empty { padding:48px 16px; text-align:center; color:var(--muted); line-height:1.6; }
.empty a { color:var(--accent-ink); }
.mono { font-family:var(--mono); }
input[aria-invalid="true"] { border-color:var(--danger); }
.hint { font:400 12px/1.5 var(--font); color:var(--muted); }
.room-form { display:flex; flex-direction:column; gap:20px; }
.room-form .group { display:flex; flex-direction:column; gap:8px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.curtains { width:100%; border-collapse:collapse; border:1px solid var(--line); }
.curtains th { font:600 11px/1 var(--font); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); }
.curtains td { padding:8px 12px; border-top:1px solid var(--line); vertical-align:middle; }
.curtains td.tick, .curtains th.tick { text-align:center; width:72px; }
.curtains .real { font:600 14px/1.2 var(--font); }
.curtains .real .sub { font:500 11px/1.4 var(--mono); color:var(--muted); }
.curtains .own { display:flex; align-items:center; gap:8px; }
.curtains .own input[type=text] { height:var(--control-sm); }
.table-wrap { overflow-x:auto; }
.chip { display:inline-flex; align-items:center; gap:6px; height:var(--control-sm); padding:0 4px 0 10px;
  border:1px solid var(--line); background:var(--surface-raised); font:500 12px/1 var(--mono); }
.chip button { height:22px; width:22px; padding:0; border:0; background:transparent; color:var(--muted); }
.chip button:hover { color:var(--ink); background:transparent; }
.add-row { display:flex; gap:8px; }
.curtain-row { display:grid; grid-template-columns:auto minmax(0,1fr); gap:12px; align-items:center; }
.check { display:flex; align-items:center; gap:10px; font:600 14px/1 var(--font); cursor:pointer; white-space:nowrap; }
.check input { appearance:none; width:16px; height:16px; margin:0; border:1px solid var(--disabled); border-radius:var(--radius); background:transparent; cursor:pointer; flex:none; padding:0; }
.check input:checked { background:var(--accent); border-color:var(--accent); }
.check input[type=radio] { border-radius:50%; }
.check input[type=radio]:checked { border:4px solid var(--accent); background:transparent; }
.radios { display:flex; flex-wrap:wrap; gap:20px; }
pre.homekit { margin:0; padding:12px 16px; border:1px solid var(--line); background:var(--canvas); font:500 12px/1.6 var(--mono); overflow-x:auto; }

/* chart marks */
.grid line { stroke:var(--line); stroke-width:1; }
.axis text { fill:var(--muted); font:500 11px var(--mono); }
.curve { fill:none; stroke:var(--ink); stroke-width:2; }
.hit { fill:none; stroke:transparent; stroke-width:18; cursor:copy; }
.stairs { fill:none; stroke:var(--muted); stroke-width:1.5; stroke-dasharray:4 3; }
.cmd { fill:var(--muted); }
.handle { fill:var(--surface); stroke:var(--ink); stroke-width:2; cursor:grab; }
.handle.fixed { fill:var(--ink); cursor:default; }
.handle.selected { fill:var(--accent); stroke:var(--accent); }
.handle:focus { outline:none; }
.handle:focus-visible { stroke:var(--accent); stroke-width:3; }
.handle-hit { fill:transparent; cursor:grab; }
`;

// Chart geometry, in viewBox units.
const W = 720;
const H = 320;
const M = { left: 48, right: 20, top: 16, bottom: 36 };
const PLOT_W = W - M.left - M.right;
const PLOT_H = H - M.top - M.bottom;
const xOf = (t) => M.left + t * PLOT_W;
const yOf = (p) => M.top + (1 - p / 100) * PLOT_H;

const KEYS = {
  open: { curve: "open_curve", duration: "open_duration", label: "Opening" },
  close: { curve: "close_curve", duration: "close_duration", label: "Closing" },
};
const PRESET_LABELS = { slow_start: "Slow start", even: "Even", hold_then_open: "Hold then open" };
const OPTION_KEYS = [
  "open_duration", "close_duration", "open_curve", "close_curve", "step_interval", "min_step",
  "normal_enabled", "normal_name", "gentle_enabled", "gentle_name", "scale",
  "normal_covers", "gentle_covers", "individual",
];
const TABS = [["open", "Opening"], ["close", "Closing"], ["room", "Room"]];
const NUMBER_FIELDS = { open_duration: [1, 120], close_duration: [1, 120], step_interval: [30, 600], min_step: [1, 50] };

/** A real curtain's name without the room's name in front (as options.py). */
const defaultOwnName = (curtainName, roomTitle) => {
  const name = curtainName.trim();
  const title = roomTitle.trim();
  if (title && name.toLowerCase().startsWith(title.toLowerCase())) {
    const rest = name.slice(title.length).trim();
    if (rest) return rest;
  }
  return name;
};

/** A position as the room counts it; the curtains always say 100 = open. */
const inScale = (position, scale) => (scale === "closed_is_100" ? 100 - position : position);

const esc = (text) =>
  String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const round = (value, step) => Math.round(value / step) * step;

const formatSeconds = (seconds) => {
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (!minutes) return `${rest} s`;
  return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
};

const normalise = (options) => {
  const result = {};
  for (const key of OPTION_KEYS) {
    const value = options[key];
    if (key.endsWith("_curve")) result[key] = value.map(([t, p]) => [Number(t), Number(p)]);
    else if (key === "individual") result[key] = structuredClone(value || {});
    else if (Array.isArray(value)) result[key] = [...value];
    else if (key in NUMBER_FIELDS) result[key] = Number(value);
    else result[key] = value;
  }
  return result;
};

class GentleCoverPage extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.rooms = [];
    this.presets = {};
    this.selected = null;
    this.tab = "open";
    this.draft = null;
    this.saved = null;
    this.point = null;
    this.preview = null;
    this.draftRoom = null;
    this.savedRoom = null;
    this.coverChoices = [];
    this.previewBusy = false;
    this.previewAgain = false;
    this.error = "";
    this.status = "";
    this.loaded = false;
  }

  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first && this.isConnected) this.load();
    else if (this.loaded) this.refreshLive();
  }

  set narrow(value) { this.toggleAttribute("narrow", Boolean(value)); }
  set panel(value) { this._panel = value; }

  connectedCallback() {
    // Home Assistant may hand the panel its hass, narrow and panel before this
    // module has defined the element. Those land as plain properties that
    // would hide the setters for good; move them through the setters.
    for (const key of ["hass", "narrow", "panel"]) {
      if (Object.prototype.hasOwnProperty.call(this, key)) {
        const value = this[key];
        delete this[key];
        this[key] = value;
      }
    }
    installFonts();
    this.renderShell();
    if (this._hass && !this.loaded) this.load();
  }

  async call(message) {
    if (!this._hass) throw new Error("Home Assistant is not ready");
    return this._hass.connection.sendMessagePromise(message);
  }

  async load() {
    try {
      const result = await this.call({ type: "gentle_cover/rooms" });
      this.rooms = result.rooms;
      this.presets = result.presets;
      this.coverChoices = result.cover_choices || [];
      this.loaded = true;
      this.error = "";
      const keep = this.rooms.find((room) => room.entry_id === this.selected);
      this.selectRoom(keep ? keep.entry_id : this.rooms[0]?.entry_id ?? null, true);
    } catch (err) {
      this.error = err?.message || "Could not read the rooms";
      this.renderBody();
    }
  }

  // --- state ------------------------------------------------------------------

  room() { return this.rooms.find((room) => room.entry_id === this.selected) || null; }

  dirty() {
    if (!this.draft || !this.saved) return false;
    return JSON.stringify([this.draft, this.draftRoom]) !== JSON.stringify([this.saved, this.savedRoom]);
  }

  scale() { return this.draft?.scale || "open_is_100"; }

  selectRoom(entryId, force = false) {
    if (!force && entryId === this.selected) return;
    if (!force && this.dirty() && !window.confirm("Discard the unsaved changes to this room?")) return;
    this.selected = entryId;
    const room = this.room();
    this.saved = room ? normalise(room.options) : null;
    if (this.saved) {
      // Options saved before curtains were chosen move all of them.
      this.saved.normal_covers = this.saved.normal_covers || [...room.covers];
      this.saved.gentle_covers = this.saved.gentle_covers || [...room.covers];
      this.saved.individual = this.saved.individual || {};
    }
    this.draft = this.saved ? structuredClone(this.saved) : null;
    this.savedRoom = room ? { title: room.title, covers: [...room.covers] } : null;
    this.draftRoom = this.savedRoom ? structuredClone(this.savedRoom) : null;
    this.preview = null;
    this.point = null;
    this.status = "";
    this.renderBody();
    this.requestPreview();
  }

  selectTab(tab) {
    this.tab = tab;
    this.preview = null;
    this.point = null;
    this.renderBody();
    this.requestPreview();
  }

  curve() { return this.draft[KEYS[this.tab].curve]; }

  setCurve(points) {
    this.draft[KEYS[this.tab].curve] = points;
    this.edited();
  }

  edited() {
    this.status = "";
    this.renderChart();
    this.renderSaveState();
    this.requestPreview();
  }

  // --- preview: one request in flight, the latest wins ----------------------

  /** The preview of what is on screen, or none. */
  shownPreview() {
    const preview = this.preview;
    return preview && preview.entry === this.selected && preview.tab === this.tab ? preview : null;
  }

  async requestPreview() {
    if (!this.draft || this.tab === "room") return;
    if (this.previewBusy) {
      this.previewAgain = true;
      return;
    }
    this.previewBusy = true;
    const asked = { entry: this.selected, tab: this.tab };
    try {
      const result = await this.call({
        type: "gentle_cover/preview",
        direction: this.tab,
        curve: this.curve(),
        duration: this.draft[KEYS[this.tab].duration],
        step_interval: this.draft.step_interval,
        min_step: this.draft.min_step,
      });
      this.preview = { ...asked, ...result };
      this.error = "";
    } catch (err) {
      this.preview = null;
      this.error = err?.message || "Could not plan this curve";
    }
    this.previewBusy = false;
    if (this.previewAgain) {
      this.previewAgain = false;
      this.requestPreview();
      return;
    }
    this.renderChart();
    this.renderSummary();
    this.renderNotice();
  }

  // --- saving and testing -------------------------------------------------------

  async save() {
    const room = this.room();
    if (!room) return false;
    try {
      const result = await this.call({
        type: "gentle_cover/save",
        entry_id: room.entry_id,
        options: this.draft,
        title: this.draftRoom.title,
        covers: this.draftRoom.covers,
      });
      room.options = result.options;
      room.title = result.title;
      room.covers = result.covers;
      this.saved = normalise(result.options);
      this.draft = structuredClone(this.saved);
      this.savedRoom = { title: result.title, covers: [...result.covers] };
      this.draftRoom = structuredClone(this.savedRoom);
      this.error = "";
      this.status = "Saved";
      // Curtains switched on or off change the room's entities.
      setTimeout(() => this.reloadRooms(), 1500);
      this.renderSaveState();
      this.renderNotice();
      return true;
    } catch (err) {
      this.error = err?.message || "Could not save";
      this.renderNotice();
      return false;
    }
  }

  async reloadRooms() {
    try {
      const result = await this.call({ type: "gentle_cover/rooms" });
      this.rooms = result.rooms;
      this.coverChoices = result.cover_choices || [];
      if (!this.dirty()) {
        const keep = this.rooms.find((room) => room.entry_id === this.selected);
        if (keep) this.selectRoom(keep.entry_id, true);
      }
    } catch (err) {
      // The next load will try again; nothing on screen is wrong meanwhile.
    }
  }

  async test(direction) {
    if (!this.draft?.gentle_enabled) return;
    let entityId = this.room()?.gentle_entity_id;
    if (this.dirty()) {
      const savedAt = Date.now();
      if (!(await this.save())) return;
      // Saving reloads the room; a command sent before its gentle curtain is
      // back would be lost with the old one.
      this.status = "Applying the new settings…";
      this.renderSaveState();
      entityId = await this.waitForGentle(savedAt);
      if (!entityId) {
        this.error = "The room did not come back after saving; try Test again.";
        this.renderNotice();
        return;
      }
    }
    if (!entityId) return;
    try {
      await this._hass.callService("cover", direction === "open" ? "open_cover" : "close_cover", {
        entity_id: entityId,
      });
      this.status = direction === "open" ? "Opening — watch the curtains" : "Closing — watch the curtains";
    } catch (err) {
      this.error = err?.message || "Could not start the move";
      this.renderNotice();
      this.status = "";
    }
    this.renderSaveState();
  }

  /** The room's gentle curtain once it has been set up again after a save. */
  async waitForGentle(savedAt) {
    for (let i = 0; i < 40; i++) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      if (i % 4 === 3) await this.reloadRooms();
      const id = this.room()?.gentle_entity_id;
      const state = id && this._hass?.states[id];
      if (state && state.state !== "unavailable" && new Date(state.last_changed).getTime() >= savedAt) {
        return id;
      }
    }
    return null;
  }

  // --- rendering ----------------------------------------------------------------

  renderShell() {
    this.shadowRoot.innerHTML = `<style>${STYLES}</style>
      <header class="app-bar">
        <button class="quiet icon menu" data-menu title="Menu">☰</button>
        <span class="mark"></span><span class="title">Gentle Cover</span>
        <span class="spacer"></span>
        <span class="save-state" data-save-state></span>
        <button class="primary" data-save disabled>Save</button>
      </header>
      <main class="page" data-body></main>`;
    this.shadowRoot.querySelector("[data-menu]").addEventListener("click", () =>
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    this.shadowRoot.querySelector("[data-save]").addEventListener("click", () => this.save());
    this.renderBody();
  }

  renderSaveState() {
    const state = this.shadowRoot.querySelector("[data-save-state]");
    const button = this.shadowRoot.querySelector("[data-save]");
    if (!state || !button) return;
    const dirty = this.dirty();
    state.textContent = dirty ? "Unsaved changes" : this.status;
    state.classList.toggle("dirty", dirty);
    button.disabled = !dirty;
  }

  renderNotice() {
    const notice = this.shadowRoot.querySelector("[data-notice]");
    if (!notice) return;
    notice.hidden = !this.error;
    notice.textContent = this.error;
  }

  renderBody() {
    const body = this.shadowRoot.querySelector("[data-body]");
    if (!body) return;
    if (!this.loaded) {
      body.innerHTML = this.error
        ? `<div class="notice">${esc(this.error)}</div>`
        : `<div class="empty">Reading the rooms…</div>`;
      return;
    }
    if (!this.rooms.length) {
      body.innerHTML = `<div class="empty">No rooms yet.<br>Add one in
        <a href="/config/integrations/integration/gentle_cover">Settings → Devices &amp; services → Gentle Cover</a>.</div>`;
      this.renderSaveState();
      return;
    }
    const room = this.room();
    const keys = KEYS[this.tab];
    const presets = Object.keys(this.presets[this.tab] || {});
    body.innerHTML = `
      <div class="notice" data-notice hidden></div>
      <div class="layout">
        <section>
          <div class="group-label">Rooms</div>
          <div class="band" data-rooms>
            ${this.rooms.map((r) => `
              <div class="row ${r.entry_id === this.selected ? "selected" : ""}" data-room="${esc(r.entry_id)}" tabindex="0">
                <div class="grow"><div class="name">${esc(r.title)}</div>
                <div class="sub mono" data-live="${esc(r.entity_id || "")}" data-scale="${esc(r.entry_id === this.selected ? this.scale() : r.options.scale || "open_is_100")}"></div></div>
              </div>`).join("")}
          </div>
        </section>
        <section>
          <nav class="tabs">
            ${TABS.map(([key, label]) =>
              `<button data-tab="${key}" class="${key === this.tab ? "active" : ""}">${label}</button>`).join("")}
          </nav>
          ${this.tab === "room" ? this.roomForm(room) : this.movementForm(room, keys, presets)}
        </section>
      </div>`;
    this.bindBody(body);
    if (this.tab !== "room") {
      this.renderChart();
      this.renderSummary();
    }
    this.renderNotice();
    this.renderSaveState();
    this.refreshLive();
  }

  movementForm(room, keys, presets) {
    return `
          <div class="chart" data-chart></div>
          <div class="toolbar">
            <span class="label">Presets</span>
            ${presets.map((name) => `<button class="small" data-preset="${name}">${esc(PRESET_LABELS[name] || name)}</button>`).join("")}
            <span class="spacer"></span>
            <button class="small" data-remove disabled>Remove point</button>
          </div>
          <div class="fields">
            <label class="field"><span class="label">${keys.label} duration (min)</span>
              <input type="number" min="1" max="120" step="1" data-field="${keys.duration}" value="${this.draft[keys.duration]}">
              <span class="hint">A full ${this.tab === "open" ? "opening" : "closing"}; shorter moves take part of it.</span></label>
            <label class="field"><span class="label">Step interval (s)</span>
              <input type="number" min="30" max="600" step="10" data-field="step_interval" value="${this.draft.step_interval}">
              <span class="hint">Shared by opening and closing.</span></label>
            <label class="field"><span class="label">Smallest move (%)</span>
              <input type="number" min="1" max="50" step="1" data-field="min_step" value="${this.draft.min_step}">
              <span class="hint">Smaller steps are combined; tiny moves make the motor twitch.</span></label>
          </div>
          <div class="summary" data-summary></div>
          <div class="actions">
            <button data-test="open" ${this.draft.gentle_enabled ? "" : "disabled"}>Test opening</button>
            <button data-test="close" ${this.draft.gentle_enabled ? "" : "disabled"}>Test closing</button>
            ${this.draft.gentle_enabled ? "" : `<span class="hint">Switch the gentle curtain on in the Room tab to test a curve.</span>`}
          </div>`;
  }

  roomForm(room) {
    const d = this.draft;
    const r = this.draftRoom;
    const names = Object.fromEntries(this.coverChoices.map((c) => [c.entity_id, c.name]));
    const shown = (name) => [r.title.trim(), (name || "").trim()].filter(Boolean).join(" ");
    const curtain = (key, label, hint) => `
            <div class="group">
              <div class="curtain-row">
                <label class="check"><input type="checkbox" data-bool="${key}_enabled" ${d[`${key}_enabled`] ? "checked" : ""}> ${label}</label>
                <input type="text" maxlength="64" data-text="${key}_name" value="${esc(d[`${key}_name`])}"
                  placeholder="(just the room's name)" ${d[`${key}_enabled`] ? "" : "disabled"}>
              </div>
              <span class="hint">${hint} Shown as <strong data-shown="${key}">${esc(shown(d[`${key}_name`]))}</strong>.</span>
            </div>`;
    const own = room?.own_entity_ids || {};
    const enabled = [
      [d.normal_enabled, room?.normal_entity_id],
      [d.gentle_enabled, room?.gentle_entity_id],
      ...r.covers.map((id) => [d.individual[id]?.enabled, own[id]]),
    ].filter(([on]) => on).map(([, id]) => `      - ${id || "(created when you save)"}`);
    const realName = (id) => names[id] || this._hass?.states[id]?.attributes?.friendly_name || id;
    return `
          <div class="room-form">
            <label class="field"><span class="label">Room name</span>
              <input type="text" maxlength="64" data-room-title value="${esc(r.title)}"></label>
            <div class="group">
              <span class="group-label">Curtains</span>
              ${r.covers.length ? `<div class="table-wrap"><table class="curtains">
                <thead><tr><th>Real curtain</th><th class="tick">Normal</th><th class="tick">Gentle</th><th>On its own</th><th></th></tr></thead>
                <tbody>
                ${r.covers.map((id, i) => {
                  const mine = d.individual[id] || { enabled: false, name: defaultOwnName(realName(id), r.title) };
                  return `<tr>
                    <td class="real">${esc(realName(id))}<div class="sub">${esc(id)}</div></td>
                    <td class="tick"><label class="check" style="justify-content:center"><input type="checkbox" data-member="normal_covers" data-id="${esc(id)}"
                      aria-label="Normal curtain moves ${esc(realName(id))}" ${d.normal_covers.includes(id) ? "checked" : ""}></label></td>
                    <td class="tick"><label class="check" style="justify-content:center"><input type="checkbox" data-member="gentle_covers" data-id="${esc(id)}"
                      aria-label="Gentle curtain moves ${esc(realName(id))}" ${d.gentle_covers.includes(id) ? "checked" : ""}></label></td>
                    <td><div class="own"><label class="check"><input type="checkbox" data-own="${esc(id)}"
                      aria-label="${esc(realName(id))} on its own" ${mine.enabled ? "checked" : ""}></label>
                      <input type="text" maxlength="64" data-own-name="${esc(id)}" value="${esc(mine.name)}"
                        placeholder="(just the room's name)" ${mine.enabled ? "" : "disabled"}></div></td>
                    <td><button class="quiet small" data-uncover="${i}" title="Remove ${esc(id)} from the room">✕</button></td>
                  </tr>`;
                }).join("")}
                </tbody></table></div>
              <span class="hint">Normal and Gentle: which real curtains each of the room's curtains moves. On its own: a full-speed curtain for just that one, named after the room like the others.</span>`
                : `<span class="hint">No curtains yet.</span>`}
              <div class="add-row">
                <input type="text" list="cover-choices" data-cover-input placeholder="cover.bedroom_curtains_left">
                <datalist id="cover-choices">
                  ${this.coverChoices.filter((c) => !r.covers.includes(c.entity_id))
                    .map((c) => `<option value="${esc(c.entity_id)}">${esc(c.name)}</option>`).join("")}
                </datalist>
                <button data-add-cover>Add</button>
              </div>
            </div>
            ${curtain("normal", "Normal curtain", "Moves straight to where it is sent, all curtains together.")}
            ${curtain("gentle", "Gentle curtain", "Moves along the room's curves.")}
            <span class="hint">Names come after the room's name, as Home Assistant shows every device's entities; renaming the room renames its curtains. The Home app then drops the room's name again for accessories in that room.</span>
            <div class="group">
              <span class="group-label">Scale</span>
              <div class="radios">
                <label class="check"><input type="radio" name="scale" value="open_is_100" ${d.scale !== "closed_is_100" ? "checked" : ""}> 100 % = open</label>
                <label class="check"><input type="radio" name="scale" value="closed_is_100" ${d.scale === "closed_is_100" ? "checked" : ""}> 100 % = closed</label>
              </div>
              <span class="hint">How this page, the card and the gentle_cover.move action count. Home Assistant and HomeKit always use 100 % = open.</span>
            </div>
            <div class="group">
              <span class="group-label">HomeKit</span>
              <span class="hint">To show these curtains in the Home app, add them under <span class="mono">homekit: filter: include_entities:</span> in configuration.yaml and restart.</span>
              <pre class="homekit" data-homekit>${esc(enabled.join("\n"))}</pre>
              <div><button class="small" data-copy-homekit>Copy</button></div>
            </div>
          </div>`;
  }

  bindBody(body) {
    body.querySelectorAll("[data-room]").forEach((row) => {
      row.addEventListener("click", () => this.selectRoom(row.dataset.room));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") this.selectRoom(row.dataset.room);
      });
    });
    body.querySelectorAll("[data-tab]").forEach((button) =>
      button.addEventListener("click", () => this.selectTab(button.dataset.tab)));
    body.querySelectorAll("[data-preset]").forEach((button) =>
      button.addEventListener("click", () => {
        this.point = null;
        this.setCurve(structuredClone(this.presets[this.tab][button.dataset.preset]));
      }));
    body.querySelector("[data-remove]")?.addEventListener("click", () => this.removePoint());
    body.querySelectorAll("[data-field]").forEach((input) =>
      input.addEventListener("input", () => {
        // An empty or out-of-range field is left out of the draft until it
        // holds something the room can use.
        const [low, high] = NUMBER_FIELDS[input.dataset.field];
        const value = input.value.trim() === "" ? NaN : Number(input.value);
        const usable = Number.isFinite(value) && value >= low && value <= high;
        input.setAttribute("aria-invalid", String(!usable));
        if (!usable) return;
        this.draft[input.dataset.field] = value;
        this.edited();
      }));
    this.bindRoomForm(body);
    body.querySelectorAll("[data-test]").forEach((button) =>
      button.addEventListener("click", () => this.test(button.dataset.test)));
  }

  bindRoomForm(body) {
    const changed = () => {
      this.status = "";
      this.renderSaveState();
    };
    const showNames = () => {
      for (const key of ["normal", "gentle"]) {
        const node = body.querySelector(`[data-shown="${key}"]`);
        if (node) node.textContent = [this.draftRoom.title.trim(), (this.draft[`${key}_name`] || "").trim()].filter(Boolean).join(" ");
      }
    };
    body.querySelector("[data-room-title]")?.addEventListener("input", (event) => {
      this.draftRoom.title = event.target.value;
      showNames();
      changed();
    });
    body.querySelectorAll("[data-text]").forEach((input) =>
      input.addEventListener("input", () => {
        this.draft[input.dataset.text] = input.value;
        showNames();
        changed();
      }));
    body.querySelectorAll("[data-bool]").forEach((box) =>
      box.addEventListener("change", () => {
        const key = box.dataset.bool;
        const other = key === "normal_enabled" ? "gentle_enabled" : "normal_enabled";
        if (!box.checked && !this.draft[other]) {
          // A room with neither curtain would have nothing to show.
          box.checked = true;
          this.error = "A room needs at least one curtain; switch the other one on first.";
          this.renderNotice();
          return;
        }
        this.draft[key] = box.checked;
        this.error = "";
        this.renderBody();
      }));
    body.querySelectorAll("input[name=scale]").forEach((radio) =>
      radio.addEventListener("change", () => {
        this.draft.scale = radio.value;
        this.renderBody();
      }));
    body.querySelectorAll("[data-uncover]").forEach((button) =>
      button.addEventListener("click", () => {
        const [id] = this.draftRoom.covers.splice(Number(button.dataset.uncover), 1);
        // Gone from the room, gone from every choice that named it.
        this.draft.normal_covers = this.draft.normal_covers.filter((c) => c !== id);
        this.draft.gentle_covers = this.draft.gentle_covers.filter((c) => c !== id);
        delete this.draft.individual[id];
        this.renderBody();
      }));
    body.querySelectorAll("[data-member]").forEach((box) =>
      box.addEventListener("change", () => {
        const key = box.dataset.member;
        const id = box.dataset.id;
        const list = this.draft[key].filter((c) => c !== id);
        if (box.checked) list.push(id);
        this.draft[key] = this.draftRoom.covers.filter((c) => list.includes(c));
        changed();
      }));
    body.querySelectorAll("[data-own]").forEach((box) =>
      box.addEventListener("change", () => {
        const id = box.dataset.own;
        const name = body.querySelector(`[data-own-name="${CSS.escape(id)}"]`)?.value ?? "";
        this.draft.individual[id] = { enabled: box.checked, name };
        this.renderBody();
      }));
    body.querySelectorAll("[data-own-name]").forEach((input) =>
      input.addEventListener("input", () => {
        const id = input.dataset.ownName;
        this.draft.individual[id] = { enabled: Boolean(this.draft.individual[id]?.enabled), name: input.value };
        changed();
      }));
    const add = () => {
      const input = body.querySelector("[data-cover-input]");
      const id = input?.value.trim();
      if (!id || this.draftRoom.covers.includes(id)) return;
      if (!this.coverChoices.some((c) => c.entity_id === id)) {
        this.error = `${id} is not a curtain that takes a position.`;
        this.renderNotice();
        return;
      }
      this.draftRoom.covers.push(id);
      // A new curtain moves with both of the room's curtains, like the rest.
      this.draft.normal_covers = this.draftRoom.covers.filter((c) => c === id || this.draft.normal_covers.includes(c));
      this.draft.gentle_covers = this.draftRoom.covers.filter((c) => c === id || this.draft.gentle_covers.includes(c));
      this.error = "";
      this.renderBody();
    };
    body.querySelector("[data-add-cover]")?.addEventListener("click", add);
    body.querySelector("[data-cover-input]")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") add();
    });
    body.querySelector("[data-copy-homekit]")?.addEventListener("click", async () => {
      const text = body.querySelector("[data-homekit]")?.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
        this.status = "Copied";
      } catch (err) {
        this.status = "Select the lines and copy them";
      }
      this.renderSaveState();
    });
  }

  refreshLive() {
    this.shadowRoot.querySelectorAll("[data-live]").forEach((node) => {
      const state = this._hass?.states[node.dataset.live];
      if (!state) {
        node.textContent = node.dataset.live ? "not available" : "no entity";
        return;
      }
      const position = state.attributes.current_position;
      const scale = node.dataset.scale;
      const shown = position === undefined ? "" : ` · ${Math.round(inScale(position, scale))} %${scale === "closed_is_100" ? " closed" : ""}`;
      node.textContent = `${state.state}${shown}`;
    });
  }

  renderSummary() {
    const node = this.shadowRoot.querySelector("[data-summary]");
    if (!node) return;
    const preview = this.shownPreview();
    if (!preview) {
      node.textContent = "Planning…";
      return;
    }
    const steps = preview.steps;
    const last = steps.length ? steps[steps.length - 1][0] : 0;
    const what = this.tab === "open" ? "opening" : "closing";
    node.innerHTML = `A full ${what} sends <strong>${steps.length} command${steps.length === 1 ? "" : "s"}</strong>:
      the first at once, the last after <strong>${esc(formatSeconds(last))}</strong>.
      The curve takes ${esc(formatSeconds(preview.span_s))}.`;
  }

  renderChart() {
    const host = this.shadowRoot.querySelector("[data-chart]");
    if (!host || !this.draft) return;
    const points = this.curve();
    const durationMin = this.draft[KEYS[this.tab].duration];
    const preview = this.shownPreview();

    const tick = [1, 2, 5, 10, 15, 30].find((step) => durationMin / step <= 10) || 60;
    const xTicks = [];
    for (let minute = 0; minute <= durationMin + 1e-9; minute += tick) xTicks.push(minute);

    const grid = [0, 25, 50, 75, 100].map((p) =>
      `<line x1="${M.left}" x2="${W - M.right}" y1="${yOf(p)}" y2="${yOf(p)}"></line>`).join("") +
      xTicks.map((m) => `<line x1="${xOf(m / durationMin)}" x2="${xOf(m / durationMin)}" y1="${M.top}" y2="${H - M.bottom}"></line>`).join("");
    const axis = [0, 25, 50, 75, 100].map((p) =>
      `<text x="${M.left - 8}" y="${yOf(p) + 4}" text-anchor="end">${inScale(p, this.scale())}%</text>`).join("") +
      xTicks.map((m) => `<text x="${xOf(m / durationMin)}" y="${H - M.bottom + 20}" text-anchor="middle">${m}m</text>`).join("");

    // Until the server has drawn the curve, straight lines between the points.
    const samples = preview?.samples || points;
    const path = samples.map(([t, p], i) => `${i ? "L" : "M"}${xOf(t).toFixed(1)},${yOf(p).toFixed(1)}`).join(" ");

    let stairs = "";
    let commands = "";
    if (preview && preview.steps.length) {
      const span = durationMin * 60;
      const t0 = preview.t_start || 0;
      let position = this.tab === "open" ? 0 : 100;
      let d = `M${xOf(t0).toFixed(1)},${yOf(position).toFixed(1)}`;
      for (const [seconds, target] of preview.steps) {
        const x = xOf(clamp(t0 + seconds / span, 0, 1)).toFixed(1);
        d += ` H${x} V${yOf(target).toFixed(1)}`;
        commands += `<circle class="cmd" cx="${x}" cy="${yOf(target).toFixed(1)}" r="3.5"></circle>`;
        position = target;
      }
      d += ` H${xOf(1).toFixed(1)}`;
      stairs = `<path class="stairs" d="${d}"></path>`;
    }

    const handles = points.map(([t, p], i) => {
      const fixed = i === 0 || i === points.length - 1;
      const cls = `handle${fixed ? " fixed" : ""}${i === this.point ? " selected" : ""}`;
      const label = `Point at ${Math.round(t * durationMin * 10) / 10} min, ${Math.round(p)} %`;
      return `<g data-point="${i}">
        ${fixed ? "" : `<circle class="handle-hit" cx="${xOf(t)}" cy="${yOf(p)}" r="14"></circle>`}
        <rect class="${cls}" x="${xOf(t) - 6}" y="${yOf(p) - 6}" width="12" height="12"
          ${fixed ? "" : `tabindex="0" role="slider" aria-label="${esc(label)}"`}></rect></g>`;
    }).join("");

    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" data-svg>
      <g class="grid">${grid}</g><g class="axis">${axis}</g>
      ${stairs}${commands}
      <path class="curve" d="${path}"></path>
      <path class="hit" d="${path}" data-hit></path>
      ${handles}
    </svg>`;
    this.bindChart(host);
    const remove = this.shadowRoot.querySelector("[data-remove]");
    if (remove) remove.disabled = this.point === null;
  }

  // --- chart interaction --------------------------------------------------------

  toCurve(svg, event) {
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const local = pt.matrixTransform(svg.getScreenCTM().inverse());
    return { t: (local.x - M.left) / PLOT_W, p: (1 - (local.y - M.top) / PLOT_H) * 100 };
  }

  /** Keep a point between its neighbours in time, and never backwards. */
  place(index, t, p) {
    const points = this.curve();
    const before = points[index - 1];
    const after = points[index + 1];
    const tt = clamp(round(t, 0.001), before[0] + 0.01, after[0] - 0.01);
    const [low, high] = this.tab === "open" ? [before[1], after[1]] : [after[1], before[1]];
    const pp = clamp(round(p, 0.5), low, high);
    points[index] = [Number(tt.toFixed(3)), pp];
  }

  bindChart(host) {
    const svg = host.querySelector("[data-svg]");
    host.querySelectorAll("[data-point]").forEach((group) => {
      const index = Number(group.dataset.point);
      const last = this.curve().length - 1;
      if (index === 0 || index === last) return;
      const handle = group.querySelector("rect");
      group.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        this.point = index;
        // Followed on the window, not the handle: every move redraws the
        // chart, which replaces the handle the drag began on.
        const move = (e) => {
          if (e.buttons === 0) {
            up();
            return;
          }
          const current = this.shadowRoot.querySelector("[data-svg]");
          if (!current) return;
          const { t, p } = this.toCurve(current, e);
          this.place(index, t, p);
          this.edited();
        };
        const up = () => {
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
          window.removeEventListener("pointercancel", up);
          this.shadowRoot.querySelector(`[data-point="${index}"] rect`)?.focus();
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
        window.addEventListener("pointercancel", up);
        this.renderChart();
      });
      handle.addEventListener("keydown", (event) => {
        const [t, p] = this.curve()[index];
        const moves = { ArrowLeft: [-0.01, 0], ArrowRight: [0.01, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
        if (moves[event.key]) {
          event.preventDefault();
          this.point = index;
          this.place(index, t + moves[event.key][0], p + moves[event.key][1]);
          this.edited();
          this.shadowRoot.querySelector(`[data-point="${index}"] rect`)?.focus();
        } else if (event.key === "Delete" || event.key === "Backspace") {
          event.preventDefault();
          this.point = index;
          this.removePoint();
        }
      });
      handle.addEventListener("focus", () => {
        if (this.point !== index) {
          this.point = index;
          const remove = this.shadowRoot.querySelector("[data-remove]");
          if (remove) remove.disabled = false;
          handle.classList.add("selected");
        }
      });
    });
    host.querySelector("[data-hit]").addEventListener("pointerdown", (event) => {
      event.preventDefault();
      const { t } = this.toCurve(svg, event);
      this.addPoint(t);
    });
  }

  addPoint(t) {
    const points = this.curve();
    const at = clamp(round(t, 0.001), 0.01, 0.99);
    const index = points.findIndex(([pt]) => pt > at);
    if (index <= 0) return;
    const before = points[index - 1];
    const after = points[index];
    if (at - before[0] < 0.01 || after[0] - at < 0.01) return;
    // The new point sits on the curve as drawn, so adding one changes nothing
    // until it is moved.
    const samples = this.shownPreview()?.samples || null;
    let p = before[1] + ((after[1] - before[1]) * (at - before[0])) / (after[0] - before[0]);
    if (samples) {
      const k = clamp(Math.floor(at * 100), 0, 99);
      const [t0, p0] = samples[k];
      const [t1, p1] = samples[k + 1];
      p = p0 + ((p1 - p0) * (at - t0)) / (t1 - t0);
    }
    const [low, high] = this.tab === "open" ? [before[1], after[1]] : [after[1], before[1]];
    points.splice(index, 0, [Number(at.toFixed(3)), clamp(round(p, 0.5), low, high)]);
    this.point = index;
    this.edited();
  }

  removePoint() {
    const points = this.curve();
    if (this.point === null || this.point <= 0 || this.point >= points.length - 1) return;
    points.splice(this.point, 1);
    this.point = null;
    this.edited();
  }
}

// Home Assistant mounts a built-in panel as ha-panel-<component name>.
if (!customElements.get("ha-panel-gentle-cover-page")) {
  customElements.define("ha-panel-gentle-cover-page", GentleCoverPage);
}
if (!customElements.get("gentle-cover-page")) {
  customElements.define("gentle-cover-page", class extends GentleCoverPage {});
}
