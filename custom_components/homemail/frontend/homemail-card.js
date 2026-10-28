// Home-mail loader: Lovelace card (type: custom:homemail-card, best in a panel view) and the sidebar panel.
// Loaded on every page, so it stays tiny; the app itself (homemail-app.js) is imported on first use.
const base = new URL(".", import.meta.url).href;
const version = new URL(import.meta.url).searchParams.get("v") || "0";
let loading = null;
const loadApp = () => (loading ??= import(`${base}homemail-app.js?v=${version}`));

class HomemailHost extends HTMLElement {
  set hass(h) {
    this._hass = h;
    if (this._app) { this._app.hass = h; return; }
    // Create the element only after its class is defined: HA's scoped custom element registry refuses
    // to upgrade an element that existed before customElements.define().
    if (this._starting) return;
    this._starting = true;
    loadApp().then(() => {
      this._app = document.createElement("homemail-app");
      if (this.tagName.toLowerCase() === "homemail-panel") this._app.setAttribute("panel", "");
      this._app.toggleAttribute("narrow", !!this._narrow);
      this.appendChild(this._app);
      this._app.hass = this._hass;
    });
  }
  get hass() { return this._hass; }
  set narrow(n) { this._narrow = n; if (this._app) this._app.toggleAttribute("narrow", !!n); }
  set panel(_) {}
  set route(_) {}
}

class HomemailCard extends HomemailHost {
  setConfig(c) { this._config = c; }
  getCardSize() { return 20; }
  static getStubConfig() { return {}; }
}
class HomemailPanel extends HomemailHost {}

if (!customElements.get("homemail-card")) customElements.define("homemail-card", HomemailCard);
if (!customElements.get("homemail-panel")) customElements.define("homemail-panel", HomemailPanel);
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "homemail-card")) {
  window.customCards.push({ type: "homemail-card", name: "Home-mail", description: "Your mail, fetched by Home Assistant (use a panel view)." });
}
