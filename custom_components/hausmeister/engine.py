"""Hausmeister-Analyse-Engine: Baseline, Anomalie, Trend."""
from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)


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
    samples: deque = field(default_factory=lambda: deque(maxlen=20000))
    baseline_by_hour: dict[int, list[float]] = field(
        default_factory=lambda: {h: deque(maxlen=60) for h in range(24)}
    )
    anomaly_streak_start: datetime | None = None
    last_anomaly_value: float | None = None


class HausmeisterEngine:
    """Analysiert Rohsensoren und erzeugt Insights."""

    def __init__(self, sensitivity: float = 2.0, baseline_days: int = 14):
        self.sensitivity = sensitivity
        self.baseline_days = baseline_days
        self.memory: dict[str, SensorMemory] = {}

    def _get_memory(self, entity_id: str) -> SensorMemory:
        if entity_id not in self.memory:
            self.memory[entity_id] = SensorMemory()
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
        mem.baseline_by_hour[now.hour].append(value)

        insight = Insight()

        hist = list(mem.baseline_by_hour[now.hour])
        if len(hist) < 6:
            insight.message = "Hausmeister sammelt noch Basisdaten…"
            return insight

        baseline = statistics.median(hist)
        spread = statistics.pstdev(hist) if len(hist) > 1 else 0.0

        if baseline != 0:
            insight.deviation_pct = round(((value - baseline) / abs(baseline)) * 100, 1)

        if spread > 0:
            insight.z_score = round((value - baseline) / spread, 2)

        insight.trend_pct_per_day = self._trend(mem.samples, now)

        is_anomaly = abs(insight.z_score) >= self.sensitivity

        if is_anomaly:
            if mem.anomaly_streak_start is None:
                mem.anomaly_streak_start = now
            days = (now - mem.anomaly_streak_start).days
            insight.anomaly_since = mem.anomaly_streak_start
            insight.state = "kritisch" if abs(insight.z_score) >= self.sensitivity * 2 else "warnung"
            insight.message = self._build_message(
                entity_id, friendly_name, insight, days, unit
            )
        else:
            if mem.anomaly_streak_start and abs(insight.z_score) < self.sensitivity * 0.5:
                mem.anomaly_streak_start = None
            insight.message = "Alles im grünen Bereich."

        return insight

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
        if denom == 0:
            return 0.0
        slope = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom

        if mean_y == 0:
            return 0.0
        return round((slope / abs(mean_y)) * 100, 2)

    def _build_message(
        self,
        entity_id: str,
        name: str,
        insight: Insight,
        days: int,
        unit: str,
    ) -> str:
        direction = "hoch" if insight.deviation_pct > 0 else "niedrig"
        display = name or entity_id

        if "humidity" in entity_id and days >= 2:
            return (
                f"Die Luftfeuchtigkeit ({display}) ist seit {days} Tagen "
                f"ungewöhnlich {direction} ({insight.deviation_pct:+.0f} %). "
                f"Mögliche Ursache: Lüftungsverhalten, Wassereintritt oder defekter Trockner."
            )
        if "power" in entity_id or "energy" in entity_id:
            return (
                f"{display} verbraucht {abs(insight.deviation_pct):.0f} % "
                f"{'mehr' if insight.deviation_pct > 0 else 'weniger'} Energie als üblich. "
                f"Gerät prüfen (Filter, Dichtung, Alter)."
            )
        return (
            f"{display} weicht um {insight.deviation_pct:+.1f} % von der Baseline ab "
            f"(Z-Score {insight.z_score})."
        )
