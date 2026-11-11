"""Hausmeister-Analyse-Engine: Baseline, Anomalie, Trend."""
from __future__ import annotations

import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

# Fallback-Kapazitäten, falls der Coordinator nichts anderes vorgibt:
# 14 Tage à 12 Samples pro Stunde bzw. 7 Tage à 5 Minuten.
DEFAULT_MAX_BASELINE_SAMPLES = 336
DEFAULT_TREND_SAMPLES = 2016

_POWER_KEYWORDS = ("power", "energy", "strom", "energie", "verbrauch", "watt")
_HUMIDITY_KEYWORDS = ("humidity", "feucht")


@dataclass
class Insight:
    """Eine menschenlesbare Erkenntnis statt nur einem Zahlenwert."""

    state: str = "normal"              # normal / warnung / kritisch
    deviation_pct: float = 0.0         # Abweichung von Baseline in %
    z_score: float = 0.0
    trend_pct_per_day: float = 0.0     # Trend pro Tag
    message: str = ""                  # z.B. „seit 6 Tagen ungewöhnlich hoch"
    anomaly_since: datetime | None = None


@dataclass
class SensorMemory:
    """Gedächtnis für einen einzelnen Sensor."""

    samples: deque = field(default_factory=lambda: deque(maxlen=DEFAULT_TREND_SAMPLES))
    baseline_by_hour: dict[int, deque] = field(default_factory=dict)
    anomaly_streak_start: datetime | None = None

    def __post_init__(self) -> None:
        if not self.baseline_by_hour:
            self.baseline_by_hour = {
                h: deque(maxlen=DEFAULT_MAX_BASELINE_SAMPLES) for h in range(24)
            }


class HausmeisterEngine:
    """Analysiert Rohsensoren und erzeugt Insights."""

    MIN_BASELINE = 6

    def __init__(
        self,
        sensitivity: float = 2.0,
        baseline_days: int = 14,
        max_baseline_samples: int | None = None,
        trend_samples: int | None = None,
    ) -> None:
        self.sensitivity = sensitivity
        self.baseline_days = baseline_days
        self.max_baseline_samples = max_baseline_samples or DEFAULT_MAX_BASELINE_SAMPLES
        self.trend_samples = trend_samples or DEFAULT_TREND_SAMPLES
        self.memory: dict[str, SensorMemory] = {}

    def _get_memory(self, entity_id: str) -> SensorMemory:
        if entity_id not in self.memory:
            mem = SensorMemory()
            mem.samples = deque(mem.samples, maxlen=self.trend_samples)
            mem.baseline_by_hour = {
                h: deque(b, maxlen=self.max_baseline_samples)
                for h, b in mem.baseline_by_hour.items()
            }
            self.memory[entity_id] = mem
        return self.memory[entity_id]

    def analyze(
        self,
        entity_id: str,
        value: float,
        now: datetime,
        friendly_name: str = "",
        unit: str = "",
    ) -> Insight:
        mem = self._get_memory(entity_id)
        mem.samples.append((now, value))
        bucket = mem.baseline_by_hour[now.hour]
        bucket.append(value)

        insight = Insight()

        # Baseline ohne den aktuellen Wert: der Messwert darf seine eigene
        # Referenz nicht verwässern.
        hist = list(bucket)[:-1]
        if len(hist) < self.MIN_BASELINE:
            insight.message = "Hausmeister sammelt noch Basisdaten…"
            return insight

        baseline = statistics.median(hist)
        spread = statistics.pstdev(hist)

        if baseline != 0:
            insight.deviation_pct = round(((value - baseline) / abs(baseline)) * 100, 1)

        insight.z_score = self._z_score(value, baseline, spread)
        insight.trend_pct_per_day = self._trend(mem.samples, now)

        if abs(insight.z_score) >= self.sensitivity:
            if mem.anomaly_streak_start is None:
                mem.anomaly_streak_start = now
            days = (now - mem.anomaly_streak_start).days
            insight.anomaly_since = mem.anomaly_streak_start
            insight.state = (
                "kritisch" if abs(insight.z_score) >= self.sensitivity * 2 else "warnung"
            )
            insight.message = self._build_message(
                friendly_name or entity_id, insight, days
            )
        else:
            if mem.anomaly_streak_start and abs(insight.z_score) < self.sensitivity * 0.5:
                mem.anomaly_streak_start = None
            insight.message = "Alles im grünen Bereich."

        return insight

    def _z_score(self, value: float, baseline: float, spread: float) -> float:
        if spread > 0:
            return round((value - baseline) / spread, 2)

        # Konstante Historie (pstdev = 0): Ohne Streuung bliebe der Z-Score
        # für immer 0 und selbst drastische Sprünge würden nie auffallen.
        # Jede Änderung zählt deshalb als echte Veränderung.
        delta = abs(value - baseline)
        if delta == 0:
            return 0.0
        relative = delta / max(abs(baseline), 1.0)
        return round(max(self.sensitivity + 0.01, relative * 2), 2)

    def _trend(self, samples: deque, now: datetime) -> float:
        cutoff = now - timedelta(days=7)
        pts = [(t, v) for (t, v) in samples if t >= cutoff]
        if len(pts) < 10:
            return 0.0

        n = len(pts)
        t0 = pts[0][0].timestamp()
        xs = [(t.timestamp() - t0) / 86400 for (t, _) in pts]
        ys = [v for (_, v) in pts]

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom == 0 or abs(mean_y) < 1e-9:
            return 0.0
        slope = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom

        return round((slope / abs(mean_y)) * 100, 2)

    def _build_message(self, display: str, insight: Insight, days: int) -> str:
        name = display
        direction = "hoch" if insight.deviation_pct > 0 else "niedrig"
        lowered = name.lower()

        if any(k in lowered for k in _HUMIDITY_KEYWORDS) and days >= 2:
            return (
                f"Die Luftfeuchtigkeit ({name}) ist seit {days} Tagen "
                f"ungewöhnlich {direction} ({insight.deviation_pct:+.0f} %). "
                f"Mögliche Ursache: Lüftungsverhalten, Wassereintritt oder "
                f"defekter Trockner."
            )
        if any(k in lowered for k in _POWER_KEYWORDS) and insight.deviation_pct:
            return (
                f"{name} verbraucht {abs(insight.deviation_pct):.0f} % "
                f"{'mehr' if insight.deviation_pct > 0 else 'weniger'} Energie "
                f"als üblich. Gerät prüfen (Filter, Dichtung, Alter)."
            )
        if insight.deviation_pct:
            return (
                f"{name} weicht um {insight.deviation_pct:+.1f} % von der "
                f"Baseline ab (Z-Score {insight.z_score})."
            )
        return f"{name} verhält sich ungewöhnlich (Z-Score {insight.z_score})."

    # ------------------------------------------------------------------
    # Persistenz: Baseline und Anomalie-Streaks über Neustarts retten.
    # Die Roh-Samples (für den Trend) werden bewusst nicht gespeichert —
    # der Trend baut sich aus den laufenden Updates neu auf.
    # ------------------------------------------------------------------

    def export_memory(self) -> dict:
        """Serialisiert alle Baselines für den Store."""
        sensors: dict[str, dict] = {}
        for entity_id, mem in self.memory.items():
            baseline = {
                str(hour): [float(v) for v in bucket]
                for hour, bucket in mem.baseline_by_hour.items()
                if len(bucket)
            }
            if not baseline and mem.anomaly_streak_start is None:
                continue
            sensors[entity_id] = {
                "baseline": baseline,
                "streak_start": (
                    mem.anomaly_streak_start.isoformat()
                    if mem.anomaly_streak_start
                    else None
                ),
            }
        return {"version": 1, "sensors": sensors}

    def import_memory(self, data: dict) -> None:
        """Lädt eine zuvor exportierte Baseline zurück."""
        if not isinstance(data, dict) or "sensors" not in data:
            return
        for entity_id, payload in data["sensors"].items():
            mem = self._get_memory(entity_id)
            for hour, values in (payload.get("baseline") or {}).items():
                try:
                    h = int(hour)
                    if 0 <= h <= 23:
                        mem.baseline_by_hour[h].extend(float(v) for v in values)
                except (TypeError, ValueError):
                    _LOGGER.warning("Baseline für %s (Stunde %s) übersprungen", entity_id, hour)
            streak = payload.get("streak_start")
            if streak:
                try:
                    mem.anomaly_streak_start = datetime.fromisoformat(streak)
                except ValueError:
                    pass
