import { useMemo } from "react";

/* ------------------------------------------------------------------ */
/* Status-Farben (orientiert an Home-Assistant-Alarmfarben)            */
/* ------------------------------------------------------------------ */
const STATUS = {
  kritisch: { color: "#f44336", label: "Kritisch" },
  warnung: { color: "#ff9800", label: "Warnung" },
  normal: { color: "#4caf50", label: "Normal" },
  sammelt: { color: "#90a4ae", label: "Sammelt Daten" },
};

const ICON_KEYWORDS = [
  ["feucht", "humidity", "mdi:water-percent"],
  ["co2", "mdi:molecule-co2"],
  ["strom", "energie", "energy", "power", "verbrauch", "watt", "mdi:flash"],
  ["temperatur", "temperature", "temp", "mdi:thermometer"],
  ["batterie", "battery", "mdi:battery"],
  ["tuer", "tür", "fenster", "door", "window", "mdi:door-open"],
];

function pickIcon(entity) {
  const hay = `${entity.entity_id} ${entity.attributes?.friendly_name ?? ""}`.toLowerCase();
  for (const row of ICON_KEYWORDS) {
    for (let i = 0; i < row.length - 1; i++) {
      if (hay.includes(row[i])) return row[row.length - 1];
    }
  }
  return "mdi:radar";
}

/* ------------------------------------------------------------------ */
/* Daten                                                               */
/* ------------------------------------------------------------------ */

const isInsightSensor = (state) =>
  state.entity_id.startsWith("sensor.") &&
  state.attributes &&
  state.attributes.nachricht !== undefined;

function statusOf(state) {
  if (state.state === "kritisch") return "kritisch";
  if (state.state === "warnung") return "warnung";
  if ((state.attributes?.nachricht ?? "").includes("sammelt")) return "sammelt";
  return "normal";
}

function collectInsights(hass, config) {
  if (!hass?.states) return [];
  let list;
  if (Array.isArray(config.entities) && config.entities.length) {
    list = config.entities.map((id) => hass.states[id]).filter(Boolean);
  } else {
    list = Object.values(hass.states);
  }
  return list.filter(isInsightSensor).map((state) => {
    const status = statusOf(state);
    const trendState = hass.states[state.entity_id.replace("_insight", "_trend")];
    const trend = trendState ? parseFloat(trendState.state) : NaN;
    let daysAnomalous = 0;
    const since = state.attributes?.anomalie_seit;
    if (since) daysAnomalous = Math.max(0, Math.floor((Date.now() - new Date(since).getTime()) / 86400000));
    return {
      entity: state,
      status,
      deviation: state.attributes?.abweichung_prozent,
      zScore: state.attributes?.z_score,
      trend: Number.isFinite(trend) ? trend : null,
      daysAnomalous,
    };
  });
}

const STATUS_ORDER = { kritisch: 0, warnung: 1, sammelt: 2, normal: 3 };

/* ------------------------------------------------------------------ */
/* UI                                                                  */
/* ------------------------------------------------------------------ */

function Chip({ children, color, title }) {
  return (
    <span className="hm-chip" title={title} style={color ? { color, borderColor: `${color}55` } : undefined}>
      {children}
    </span>
  );
}

function SensorCard({ item, onMoreInfo }) {
  const { entity, status, deviation, zScore, trend, daysAnomalous } = item;
  const meta = STATUS[status];
  const rawName = entity.attributes?.friendly_name ?? entity.entity_id;
  const name = rawName.replace(/^Hausmeister\s+/, "");
  const message = entity.attributes?.nachricht ?? "";
  const icon = pickIcon(entity);

  return (
    <div
      className="hm-sensor"
      style={{ borderLeftColor: meta.color }}
      onClick={() => onMoreInfo(entity.entity_id)}
      title="Details anzeigen"
    >
      <div className="hm-sensor-head">
        <ha-icon class="hm-icon" icon={icon} style={{ color: meta.color }} />
        <span className="hm-name">{name}</span>
        <span className="hm-badge" style={{ background: `${meta.color}22`, color: meta.color }}>
          {meta.label}
        </span>
      </div>
      <div className="hm-message">{message}</div>
      <div className="hm-chips">
        {deviation !== undefined && deviation !== null && (
          <Chip color={meta.color} title="Abweichung von der Baseline">
            {deviation > 0 ? "▲" : deviation < 0 ? "▼" : "•"} {Math.abs(deviation).toFixed(1)} %
          </Chip>
        )}
        {trend !== null && (
          <Chip title="7-Tage-Trend pro Tag">
            {trend > 0.05 ? "↗" : trend < -0.05 ? "↘" : "→"} {Math.abs(trend).toFixed(1)} %/Tag
          </Chip>
        )}
        {status === "kritisch" && daysAnomalous > 0 && (
          <Chip color={meta.color} title="Anomalie besteht seit">
            seit {daysAnomalous} T.
          </Chip>
        )}
        {zScore !== undefined && zScore !== null && status !== "normal" && status !== "sammelt" && (
          <Chip title="Z-Score">z = {zScore}</Chip>
        )}
      </div>
    </div>
  );
}

export default function App({ hass, config, onMoreInfo }) {
  const items = useMemo(() => collectInsights(hass, config), [hass, config]);
  const sorted = [...items].sort(
    (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] ||
      (b.daysAnomalous - a.daysAnomalous) ||
      a.entity.entity_id.localeCompare(b.entity.entity_id)
  );

  const counts = { kritisch: 0, warnung: 0, normal: 0, sammelt: 0 };
  for (const item of items) counts[item.status]++;

  return (
    <ha-card class="hm-root">
      <style>{STYLES}</style>
      <div className="hm-wrap">
        <div className="hm-header">
          <ha-icon class="hm-title-icon" icon="mdi:home-search" />
          <span className="hm-title">{config.title ?? "Hausmeister"}</span>
          <span className="hm-pills">
            {counts.kritisch > 0 && (
              <span className="hm-pill" style={{ color: STATUS.kritisch.color }}>
                ● {counts.kritisch}
              </span>
            )}
            {counts.warnung > 0 && (
              <span className="hm-pill" style={{ color: STATUS.warnung.color }}>
                ● {counts.warnung}
              </span>
            )}
            {counts.normal > 0 && (
              <span className="hm-pill" style={{ color: STATUS.normal.color }}>
                ● {counts.normal}
              </span>
            )}
            {counts.sammelt > 0 && (
              <span className="hm-pill" style={{ color: STATUS.sammelt.color }}>
                ● {counts.sammelt}
              </span>
            )}
          </span>
        </div>

        {sorted.length === 0 ? (
          <div className="hm-empty">
            Keine Hausmeister-Sensoren gefunden. {'\n'}
            Entweder die Integration einrichten oder <code>entities:</code> in der Karten-Konfiguration setzen.
          </div>
        ) : (
          <div className="hm-grid">
            {sorted.map((item) => (
              <SensorCard key={item.entity.entity_id} item={item} onMoreInfo={onMoreInfo} />
            ))}
          </div>
        )}
      </div>
    </ha-card>
  );
}

const STYLES = `
:host {
  display: block;
}
.hm-wrap {
  padding: 14px 16px 16px;
  font-family: var(--paper-font-body1_-_font-family, "Inter", system-ui, sans-serif);
  color: var(--primary-text-color, #e1e1e1);
}
.hm-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.hm-title-icon { color: var(--accent-color, #4caf50); font-size: 22px; }
.hm-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.2px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hm-pills { display: flex; gap: 8px; font-size: 12px; font-weight: 600; }
.hm-pill { white-space: nowrap; }
.hm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 10px;
}
.hm-sensor {
  background: var(--secondary-background-color, rgba(255, 255, 255, 0.05));
  border-radius: 10px;
  border-left: 3px solid #888;
  padding: 10px 12px 9px;
  cursor: pointer;
  transition: transform 0.12s ease, background 0.12s ease;
  min-width: 0;
}
.hm-sensor:hover {
  transform: translateY(-1px);
  background: var(--secondary-background-color, rgba(255, 255, 255, 0.09));
}
.hm-sensor-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.hm-icon { flex: none; }
.hm-name {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hm-badge {
  flex: none;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-radius: 6px;
  padding: 2px 6px;
}
.hm-message {
  margin-top: 5px;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--secondary-text-color, #9a9aa2);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.hm-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.hm-chip {
  font-size: 10.5px;
  font-weight: 600;
  border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.14));
  border-radius: 999px;
  padding: 2px 8px;
  color: var(--secondary-text-color, #b9b9c0);
  white-space: nowrap;
}
.hm-empty {
  font-size: 12.5px;
  color: var(--secondary-text-color, #9a9aa2);
  white-space: pre-line;
  padding: 8px 2px;
}
.hm-empty code {
  background: var(--secondary-background-color, rgba(255,255,255,0.08));
  border-radius: 4px;
  padding: 1px 4px;
}
`;
