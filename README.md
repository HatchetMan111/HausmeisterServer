# 🏠 Hausmeister für Home Assistant

Der Hausmeister überwacht deine bestehenden Sensoren und erzeugt daraus
**Predictive-Maintenance-Erkenntnisse** statt nackter Zahlen.

## Beispiele

- „Die Luftfeuchtigkeit im Keller ist seit 6 Tagen ungewöhnlich hoch."
- „Der Gefrierschrank benötigt 18 % mehr Energie als vor drei Monaten."
- „Die Waschmaschine verbraucht beim Schleudern zunehmend mehr Strom."

## Features

- **Baseline pro Tageszeit** — lernt das normale Verhalten jedes Sensors je Stunde
- **Z-Score-Anomalien** mit Warn- und Kritisch-Stufe (Empfindlichkeit einstellbar)
- **7-Tage-Trend** in % pro Tag (lineare Regression)
- **Persistente Baseline** — überlebt Home-Assistant-Neustarts (`.storage`)
- **Live-Optionen** — Änderungen im Options-Dialog greifen sofort, ohne Reload
  (die gelernte Baseline geht dabei **nicht** verloren)
- **Feste Baseline-Kapazität** — der Baseline-Zeitraum (Tage) stimmt unabhängig
  vom Analyse-Intervall
- **Dashboard-Karte** (React + Vite) siehe unten

## Installation (via HACS)

1. HACS → ⋮ → *Benutzerdefinierte Repositories*
2. URL des Repos eintragen, Kategorie **Integration**
3. „Hausmeister" suchen und installieren
4. Home Assistant neu starten
5. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Hausmeister**

## Sensoren

Pro überwachtem Sensor entstehen drei Entitäten unter dem Device **Hausmeister**:

| Entität | Inhalt |
|---|---|
| `… Status` | `normal` / `warnung` / `kritisch` + Attribute `nachricht`, `abweichung_prozent`, `z_score`, `anomalie_seit` |
| `… Abweichung` | Abweichung von der Baseline in % |
| `… Trend` | 7-Tage-Trend in % pro Tag |

## Optionen

Alle Optionen sind später über ⚙️ → **Hausmeister konfigurieren** änderbar:

| Option | Standard | Bedeutung |
|---|---|---|
| Zu überwachende Sensoren | – | Nur numerische Sensor-Entitäten auswählbar |
| Empfindlichkeit | 2.0 | Z-Score-Schwelle für Anomalien (höher = strenger) |
| Baseline-Zeitraum | 14 Tage | Historie pro Tageszeit |
| Analyse-Intervall | 300 s | Wie oft analysiert wird (30–3600 s) |

## Dashboard-Karte (ab v0.3.0 automatisch dabei)

Die Karte zeigt alle Insights auf einen Blick: Status-Badges, Klartext-Meldung,
Abweichung, Trend und Anomalie-Dauer — kritische Sensoren zuerst.

**Plug & Play:** Die Card wird mit der Integration installiert und beim
Einrichten automatisch als Lovelace-Ressource registriert — kein Kopieren,
keine manuelle Ressource. Einfach im Dashboard *Karte hinzufügen* →
**Hausmeister Card** wählen (oder per YAML):

```yaml
type: custom:hausmeister-card
title: Hausmeister
# optional: nur bestimmte Insights zeigen (Standard: alle, die die Integration liefert)
# entities:
#   - sensor.hausmeister_luftfeuchtigkeit_keller_status
```

Die Card liegt unter `/hausmeister/hausmeister-card.js` und wird direkt von der
Integration ausgeliefert (ohne Browser-Caching — HACS-Updates greifen sofort).

**Sonderfall YAML-Modus:** Läuft Lovelace im YAML-Modus, kann HA die Ressource
nicht automatisch anlegen (Warnung im Log). Dann in `lovelace/resources.yaml`
ergänzen:

```yaml
- res_type: module
  url: /hausmeister/hausmeister-card.js
```

Weiterentwicklung der Card (nur für Entwickler):

```bash
cd dashboard
npm install
npm run build:ha      # baut die Card und kopiert sie in die Integration
npm run build:demo    # Demo mit Mock-Daten (dist-demo/ statisch servieren)
npm run dev
```

## Funktionsweise

Die Engine lernt eine **Baseline pro Stunde** (Standard: 14 Tage) und erkennt
Abweichungen per Z-Score. Sonderfall **konstante Sensoren** (Streuung 0): jede
Änderung zählt als Anomalie — ohne diesen Fallback bliebe der Z-Score für immer 0.
Zusätzlich wird ein **7-Tage-Trend** per linearer Regression berechnet. Die
Baseline wird regelmäßig in den HA-Store geschrieben (30 s Debounce) und beim
Start wieder geladen; der Trend baut sich aus den laufenden Updates neu auf.

## Entwicklung

```bash
python3 -m unittest tests.test_engine -v   # Engine-Tests (ohne HA)
cd dashboard && npm run build:ha           # Card bauen + in Integration kopieren
```

## Roadmap

- [x] Persistente Baseline über Neustarts (Store-Anbindung)
- [ ] Spezialprofile: Waschmaschinen-Zyklen erkennen
- [ ] Heizung: Aufheizzeit messen
- [ ] Fenster-auf-bei-Heizung-an-Erkennung
