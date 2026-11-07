"""Reproduces the figures quoted in powerbi/README.md using only the standard library.

The DAX in powerbi/measures.dax cannot run here, so these tests pin the same
definitions (Power W, Wear Bucket, FailureModes filtering) in Python.
"""
import csv
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = ["TWF", "HDF", "PWF", "OSF", "RNF"]


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def power_w(r):
    return float(r["Torque [Nm]"]) * float(r["Rotational speed [rpm]"]) * 2 * math.pi / 60


def wear_bucket(r):
    return min(math.floor(int(r["Tool wear [min]"]) / 50) * 50, 200)


class PowerBiFigures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read(ROOT / "data" / "raw" / "ai4i2020.csv")
        cls.holdout = read(ROOT / "reports" / "holdout_predictions.csv")

    def rate(self, rows):
        return sum(int(r["Machine failure"]) for r in rows) / len(rows)

    def test_overview(self):
        self.assertEqual(len(self.rows), 10000)
        self.assertEqual(sum(int(r["Machine failure"]) for r in self.rows), 339)

    def test_failure_rate_by_type(self):
        for t, n, f in [("L", 6000, 235), ("M", 2997, 83), ("H", 1003, 21)]:
            sub = [r for r in self.rows if r["Type"] == t]
            self.assertEqual(len(sub), n)
            self.assertEqual(sum(int(r["Machine failure"]) for r in sub), f)

    def test_wear_is_a_threshold(self):
        by = {}
        for r in self.rows:
            by.setdefault(wear_bucket(r), []).append(r)
        low = [self.rate(by[b]) for b in (0, 50, 100, 150)]
        self.assertTrue(all(0.02 < x < 0.03 for x in low))
        self.assertEqual(len(by[200]), 801)
        self.assertEqual(sum(int(r["Machine failure"]) for r in by[200]), 123)
        self.assertGreater(self.rate(by[200]), 0.15)

    def test_power_failures_sit_outside_band(self):
        for r in self.rows:
            outside = power_w(r) < 3500 or power_w(r) > 9000
            self.assertEqual(outside, r["PWF"] == "1")
        self.assertEqual(sum(r["PWF"] == "1" for r in self.rows), 95)

    def test_failure_mode_table_matches_power_query(self):
        counts = {}
        for r in self.rows:
            if r["Machine failure"] != "1":
                continue
            flags = [m for m in MODES if r[m] == "1"]
            for m in flags or ["NONE"]:
                counts[m] = counts.get(m, 0) + 1
        self.assertEqual(counts["NONE"], 9)
        self.assertEqual(counts["RNF"], 1)
        # 18 of 19 RNF flags are on rows that are not failures
        rnf = [r for r in self.rows if r["RNF"] == "1"]
        self.assertEqual(len(rnf), 19)
        self.assertEqual(sum(r["Machine failure"] == "0" for r in rnf), 18)

    def test_holdout_matches_published_metrics(self):
        self.assertEqual(len(self.holdout), 2000)
        fails = [r for r in self.holdout if r["machine_failure"] == "1"]
        self.assertEqual(len(fails), 39)
        self.assertEqual(sum(r["model_alert"] == "1" for r in fails), 29)
        self.assertEqual(sum(r["monitoring_alert"] == "1" for r in fails), 22)
        self.assertEqual(sum(r["model_alert"] == "1" for r in self.holdout), 68)
        self.assertEqual(sum(r["monitoring_alert"] == "1" for r in self.holdout), 96)


if __name__ == "__main__":
    unittest.main()
