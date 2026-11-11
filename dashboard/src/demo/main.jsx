/* Demo: Hausmeister-Card mit Mock-Daten außerhalb von Home Assistant testen. */
import "../main.js";

/* Fallback für <ha-icon>, falls HA nicht geladen ist (nur Demo!). */
if (!customElements.get("ha-icon")) {
  const EMOJI = {
    "mdi:water-percent": "💧",
    "mdi:flash": "⚡",
    "mdi:thermometer": "🌡️",
    "mdi:battery": "🔋",
    "mdi:radar": "📡",
    "mdi:molecule-co2": "🫧",
    "mdi:door-open": "🚪",
    "mdi:home-search": "🏠",
  };
  class HaIconFallback extends HTMLElement {
    static get observedAttributes() {
      return ["icon"];
    }
    connectedCallback() {
      this._update();
    }
    attributeChangedCallback() {
      this._update();
    }
    set icon(value) {
      this.setAttribute("icon", value);
    }
    get icon() {
      return this.getAttribute("icon");
    }
    _update() {
      this.textContent = EMOJI[this.getAttribute("icon")] ?? "•";
    }
  }
  customElements.define("ha-icon", HaIconFallback);
}

const iso = (daysAgo, hour = 8) => {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, 12, 0, 0);
  return d.toISOString();
};

const insight = (name, state, nachricht, extra = {}) => ({
  state,
  attributes: { friendly_name: name, nachricht, ...extra },
});

const MOCK_STATES = {
  "sensor.luftfeuchtigkeit_keller_insight": insight(
    "Hausmeister Luftfeuchtigkeit Keller Status",
    "kritisch",
    "Die Luftfeuchtigkeit (Luftfeuchtigkeit Keller) ist seit 6 Tagen ungewöhnlich hoch (+23 %). Mögliche Ursache: Lüftungsverhalten, Wassereintritt oder defekter Trockner.",
    { abweichung_prozent: 23.0, z_score: 3.4, anomalie_seit: iso(6) }
  ),
  "sensor.luftfeuchtigkeit_keller_trend": {
    state: "1.8",
    attributes: { friendly_name: "Hausmeister Luftfeuchtigkeit Keller Trend" },
  },
  "sensor.gefrierschrank_energie_insight": insight(
    "Hausmeister Gefrierschrank Energie Status",
    "warnung",
    "Gefrierschrank Energie verbraucht 18 % mehr Energie als üblich. Gerät prüfen (Filter, Dichtung, Alter).",
    { abweichung_prozent: 18.2, z_score: 2.6, anomalie_seit: iso(3) }
  ),
  "sensor.gefrierschrank_energie_trend": {
    state: "0.9",
    attributes: { friendly_name: "Hausmeister Gefrierschrank Energie Trend" },
  },
  "sensor.waschmaschine_energie_insight": insight(
    "Hausmeister Waschmaschine Energie Status",
    "warnung",
    "Waschmaschine Energie verbraucht 9 % mehr Energie als üblich. Gerät prüfen (Filter, Dichtung, Alter).",
    { abweichung_prozent: 9.1, z_score: 2.2, anomalie_seit: iso(1) }
  ),
  "sensor.waschmaschine_energie_trend": {
    state: "0.2",
    attributes: { friendly_name: "Hausmeister Waschmaschine Energie Trend" },
  },
  "sensor.wohnzimmer_temperatur_insight": insight(
    "Hausmeister Wohnzimmer Temperatur Status",
    "normal",
    "Alles im grünen Bereich.",
    { abweichung_prozent: -1.4, z_score: 0.3 }
  ),
  "sensor.wohnzimmer_temperatur_trend": {
    state: "-0.1",
    attributes: { friendly_name: "Hausmeister Wohnzimmer Temperatur Trend" },
  },
  "sensor.heizung_vorlauf_insight": insight(
    "Hausmeister Heizung Vorlauf Status",
    "normal",
    "Hausmeister sammelt noch Basisdaten…",
    { abweichung_prozent: 0.0, z_score: 0.0 }
  ),
  "sensor.heizung_vorlauf_trend": {
    state: "0.0",
    attributes: { friendly_name: "Hausmeister Heizung Vorlauf Trend" },
  },
};

const mockHass = { states: MOCK_STATES };

/* hass.states-Werte tragen immer ihre entity_id — im Mock nachträglich gesetzt. */
for (const [entity_id, stateObj] of Object.entries(MOCK_STATES)) {
  stateObj.entity_id = entity_id;
}

customElements.whenDefined("hausmeister-card").then(() => {
  const card = document.getElementById("card");
  card.setConfig({ title: "Hausmeister" });
  card.hass = mockHass;

  const card2 = document.getElementById("card-config");
  card2.setConfig({
    title: "Keller & Geräte",
    entities: [
      "sensor.luftfeuchtigkeit_keller_insight",
      "sensor.gefrierschrank_energie_insight",
      "sensor.waschmaschine_energie_insight",
    ],
  });
  card2.hass = mockHass;
});
