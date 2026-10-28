// Homepost loader: Lovelace card (type: custom:homepost-card, best in a panel view) and the sidebar panel.
// Loaded on every page, so it stays tiny; the app itself (homepost-app.js) is imported on first use.
const base = new URL(".", import.meta.url).href;
const version = new URL(import.meta.url).searchParams.get("v") || "0";
let loading = null;
const loadApp = () => (loading ??= import(`${base}homepost-app.js?v=${version}`));

class HomepostHost extends HTMLElement {
  set hass(h) {
    this._hass = h;
    if (!this._app) {
      this._app = document.createElement("homepost-app");
      if (this.tagName.toLowerCase() === "homepost-panel") this._app.setAttribute("panel", "");
      this._app.toggleAttribute("narrow", !!this._narrow);
      this.appendChild(this._app);
      loadApp();
    }
    this._app.hass = h;
  }
  get hass() { return this._hass; }
  set narrow(n) { this._narrow = n; if (this._app) this._app.toggleAttribute("narrow", !!n); }
  set panel(_) {}
  set route(_) {}
}

class HomepostCard extends HomepostHost {
  setConfig(c) { this._config = c; }
  getCardSize() { return 20; }
  static getStubConfig() { return {}; }
}
class HomepostPanel extends HomepostHost {}

if (!customElements.get("homepost-card")) customElements.define("homepost-card", HomepostCard);
if (!customElements.get("homepost-panel")) customElements.define("homepost-panel", HomepostPanel);
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "homepost-card")) {
  window.customCards.push({ type: "homepost-card", name: "Homepost", description: "Your mail, fetched by Home Assistant (use a panel view)." });
}
