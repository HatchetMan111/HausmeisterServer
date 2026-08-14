# 🏠 Hausmeister für Home Assistant

Der Hausmeister überwacht deine bestehenden Sensoren und erzeugt daraus
**Predictive-Maintenance-Erkenntnisse** statt nackter Zahlen.

## Beispiele

- „Die Luftfeuchtigkeit im Keller ist seit 6 Tagen ungewöhnlich hoch."
- „Der Gefrierschrank benötigt 18 % mehr Energie als vor drei Monaten."
- „Die Waschmaschine verbraucht beim Schleudern zunehmend mehr Strom."

## Installation (via HACS)

1. HACS → ⋮ → *Benutzerdefinierte Repositories*
2. URL deines Repos eintragen, Kategorie **Integration**
3. „Hausmeister" suchen und installieren
4. Home Assistant neu starten
5. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Hausmeister**

## Funktionsweise

Die Engine lernt eine **Baseline pro Stunde** (Standard: 14 Tage) und
erkennt Abweichungen per Z-Score. Zusätzlich wird ein **7-Tage-Trend**
berechnet.

## Roadmap

- [ ] Spezialprofile: Waschmaschinen-Zyklen erkennen
- [ ] Heizung: Aufheizzeit messen
- [ ] Fenster-auf-bei-Heizung-an-Erkennung
- [ ] Persistente Baseline über Neustarts (Recorder-Anbindung)
