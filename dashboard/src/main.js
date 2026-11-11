import { HausmeisterCard } from "./element.jsx";

customElements.define("hausmeister-card", HausmeisterCard);

// Lovelace-Karten-Registrierung (damit die Karte im Karten-Picker auftaucht)
window.customCards = window.customCards || [];
window.customCards.push({
  type: "hausmeister-card",
  name: "Hausmeister Card",
  description: "Predictive-Maintenance-Übersicht der Hausmeister-Integration",
});
