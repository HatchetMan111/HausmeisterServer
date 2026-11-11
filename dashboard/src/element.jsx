import { createElement } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

/** Custom-Element-Wrapper: verbindet Home Assistant (hass) mit React. */
export class HausmeisterCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._root = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  setConfig(config) {
    this._config = { title: "Hausmeister", ...config };
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { min_rows: 2 };
  }

  _render() {
    if (!this._root) {
      this._root = createRoot(this.shadowRoot);
    }
    this._root.render(
      createElement(App, {
        hass: this._hass,
        config: this._config,
        onMoreInfo: (entityId) => {
          this.dispatchEvent(
            new CustomEvent("hass-more-info", {
              bubbles: true,
              composed: true,
              detail: { entityId },
            })
          );
        },
      })
    );
  }
}
