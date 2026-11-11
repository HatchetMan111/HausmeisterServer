"""Unit-Tests für die Hausmeister-Engine (ohne Home-Assistant-Abhängigkeiten).

Ausführen: python3 -m unittest tests.test_engine -v
"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hausmeister"))

from engine import HausmeisterEngine  # noqa: E402

NOW = datetime(2026, 11, 11, 8, 0, 0)


def feed(engine, entity_id, values, start=NOW, step_minutes=5, hour=8):
    """Spielt eine Wertehistorie ein und gibt den letzten Insight zurück."""
    t = start
    insight = None
    for v in values:
        t = t.replace(hour=hour) + timedelta(minutes=(t.minute - t.minute) + step_minutes)
        insight = engine.analyze(entity_id, v, t, friendly_name="Testsensor", unit="°C")
    return insight


class BaselineTest(unittest.TestCase):
    def test_sammelphase_bis_genug_historie(self):
        engine = HausmeisterEngine()
        insight = feed(engine, "sensor.test", [21.0] * 4)
        self.assertIn("sammelt", insight.message)
        self.assertEqual(insight.state, "normal")

    def test_normaler_wert_bleibt_gruen(self):
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        insight = feed(engine, "sensor.test", hist + [21.0])
        self.assertEqual(insight.state, "normal")
        self.assertEqual(insight.message, "Alles im grünen Bereich.")

    def test_anomalie_wird_erkannt(self):
        engine = HausmeisterEngine()
        # Weite Historie: Sprung auf 31,5 landet zwischen Warn- und Kritschwelle
        hist = [15.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
        insight = feed(engine, "sensor.test", hist + [31.5])
        self.assertEqual(insight.state, "warnung")
        self.assertGreaterEqual(insight.z_score, 2.0)
        self.assertLess(insight.z_score, 4.0)
        self.assertTrue(insight.message)

    def test_drastischer_sprung_ist_kritisch(self):
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        insight = feed(engine, "sensor.test", hist + [30.0])
        self.assertEqual(insight.state, "kritisch")
        self.assertGreaterEqual(insight.z_score, 4.0)

    def test_kritisch_ab_doppelter_schwelle(self):
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        insight = feed(engine, "sensor.test", hist + [60.0])
        self.assertEqual(insight.state, "kritisch")

    def test_konstante_historie_sprung_wird_erkannt(self):
        """Regression: pstdev=0 darf niemals z=0 erzwingen."""
        engine = HausmeisterEngine()
        insight = feed(engine, "sensor.konstant", [21.0] * 10 + [30.0])
        self.assertEqual(insight.state, "warnung")
        self.assertGreaterEqual(insight.z_score, 2.0)

    def test_konstante_historie_ohne_aenderung_still(self):
        engine = HausmeisterEngine()
        insight = feed(engine, "sensor.konstant", [21.0] * 11)
        self.assertEqual(insight.state, "normal")

    def test_aktueller_wert_verfaelscht_baseline_nicht(self):
        """Der neue Wert darf nicht in die Baseline einfließen, gegen die er geprüft wird."""
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        feed(engine, "sensor.test", hist)
        med_before = __import__("statistics").median(hist)
        insight = engine.analyze("sensor.test", 100.0, NOW + timedelta(minutes=45),
                                 friendly_name="Testsensor")
        self.assertAlmostEqual(insight.deviation_pct,
                               round((100.0 - med_before) / med_before * 100, 1))


class TrendTest(unittest.TestCase):
    def test_steigender_trend(self):
        engine = HausmeisterEngine(sensitivity=5.0)
        t = NOW - timedelta(days=7)
        values = [20 + i * 0.2 for i in range(80)]
        insight = None
        for i, v in enumerate(values):
            t = t + timedelta(hours=2)
            insight = engine.analyze("sensor.trend", v, t, friendly_name="Trendsensor")
        self.assertGreater(insight.trend_pct_per_day, 0.5)

    def test_trend_ohne_daten_null(self):
        engine = HausmeisterEngine()
        insight = engine.analyze("sensor.trend2", 20.0, NOW, friendly_name="T")
        self.assertEqual(insight.trend_pct_per_day, 0.0)


class PersistenzTest(unittest.TestCase):
    def test_export_import_roundtrip(self):
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        feed(engine, "sensor.test", hist + [40.0])  # Anomalie erzeugen
        data = engine.export_memory()

        engine2 = HausmeisterEngine()
        engine2.import_memory(data)
        self.assertIn("sensor.test", engine2.memory)
        self.assertTrue(len(engine2.memory["sensor.test"].baseline_by_hour[8]) >= 6)
        self.assertIsNotNone(engine2.memory["sensor.test"].anomaly_streak_start)

        # Nach Import sofort wieder voll analysierbar (keine Sammelphase)
        t = NOW + timedelta(days=1)
        t = t.replace(hour=8)
        insight = engine2.analyze("sensor.test", 21.0, t, friendly_name="Testsensor")
        self.assertNotIn("sammelt", insight.message)

    def test_import_von_muell_crash_sicher(self):
        engine = HausmeisterEngine()
        engine.import_memory({"version": 1, "sensors": {"s": {"baseline": {"9": ["x", 1.0], "10": [1.0, 2.0]}}}})
        engine.import_memory({"kaputt": True})
        engine.import_memory(None)
        self.assertEqual(len(engine.memory["s"].baseline_by_hour[9]), 0)   # schlechte Stunde: übersprungen
        self.assertEqual(len(engine.memory["s"].baseline_by_hour[10]), 2)  # gute Stunde: übernommen

    def test_streak_start_isoformat_roundtrip(self):
        engine = HausmeisterEngine()
        hist = [20.5, 21.0, 21.5, 20.8, 21.2, 21.4, 20.9, 21.1]
        feed(engine, "sensor.test", hist + [50.0])
        data = engine.export_memory()
        self.assertIn("2026-11-11T", data["sensors"]["sensor.test"]["streak_start"])


class KapazitaetTest(unittest.TestCase):
    def test_max_baseline_samples_wird_angerwandt(self):
        engine = HausmeisterEngine(max_baseline_samples=8)
        feed(engine, "sensor.kap", [21.0 + (i % 3) * 0.1 for i in range(40)])
        self.assertEqual(len(engine.memory["sensor.kap"].baseline_by_hour[8]), 8)


if __name__ == "__main__":
    unittest.main()
