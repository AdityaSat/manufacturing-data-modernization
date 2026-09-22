"""Checks protect leakage, data integrity and investment-decision arithmetic."""
import copy
import json
import sqlite3
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from manufacturing.business import evaluate, load_assumptions
from manufacturing.pipeline import features, validate_and_prepare, split_labels, select_threshold


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(ROOT / "data/raw/ai4i2020.csv")

    def test_source_completeness(self):
        d, _ = validate_and_prepare(self.raw)
        self.assertEqual((len(d), int(d.machine_failure.sum())), (10000, 339))

    def test_duplicate_and_missing_rejected(self):
        bad = pd.concat([self.raw, self.raw.iloc[:1]])
        with self.assertRaises(ValueError):
            validate_and_prepare(bad)
        bad = self.raw.copy()
        bad.loc[0, "Torque [Nm]"] = np.nan
        with self.assertRaises(ValueError):
            validate_and_prepare(bad)

    def test_targets_and_ids_cannot_leak(self):
        d, _ = validate_and_prepare(self.raw)
        x = features(d)
        changed = d.copy()
        for col in ["machine_failure", "twf", "hdf", "pwf", "osf", "rnf", "observation_id"]:
            changed[col] = 999
        changed.product_id = "altered"
        pd.testing.assert_frame_equal(x, features(changed))

    def test_split_separation(self):
        s = split_labels(10000)
        self.assertEqual(list(np.where(s == "train")[0][[0, -1]]), [0, 5999])
        self.assertEqual(list(np.where(s == "validation")[0][[0, -1]]), [6000, 7999])
        self.assertEqual(list(np.where(s == "test")[0][[0, -1]]), [8000, 9999])

    def test_threshold_respects_capacity(self):
        scores = np.linspace(0, .99, 100)
        y = np.array([0] * 85 + [1] * 15)
        threshold = select_threshold(y, scores, .10)
        self.assertLessEqual(float((scores >= threshold).mean()), .10)

    def test_sql_and_metrics_reconcile(self):
        with sqlite3.connect(ROOT / "data/warehouse.db") as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM observation_health").fetchone()[0], 10000)
            sql = con.execute("SELECT SUM(machine_failure),SUM(model_alert),SUM(CASE WHEN model_alert=1 AND machine_failure=1 THEN 1 ELSE 0 END) FROM observation_health WHERE split='test'").fetchone()
        m = json.loads((ROOT / "reports/model_metrics.json").read_text())["test"]["model"]
        self.assertEqual(sql, (m["failures"], m["tp"] + m["fp"], m["tp"]))
        self.assertEqual(m["tn"] + m["fp"] + m["fn"] + m["tp"], m["rows"])


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.a = load_assumptions()

    def test_cashflow_timing(self):
        b = evaluate(self.a)["options"]["predictive"]
        self.assertEqual(b["cash_flows"][0]["net"], -145000)
        self.assertEqual(b["cash_flows"][3]["benefit"], 0)
        self.assertAlmostEqual(b["cash_flows"][4]["benefit"], 200000 / 24)
        self.assertAlmostEqual(sum(r["net"] for r in b["cash_flows"][1:13]), 75000)
        self.assertAlmostEqual(b["payback_months"], 17.6)
        self.assertAlmostEqual(b["net_cash"], 230000)

    def test_zero_benefit_never_pays_back(self):
        self.a["options"]["predictive"]["downtime_reduction"] = 0
        b = evaluate(self.a)["options"]["predictive"]
        self.assertIsNone(b["payback_months"])
        self.assertLess(b["npv"], 0)

    def test_incremental_break_even_is_npv_equality(self):
        b = evaluate(self.a)
        self.a["options"]["predictive"]["downtime_reduction"] = b["incremental_break_even_reduction"]
        self.assertAlmostEqual(evaluate(self.a)["incremental_npv"], 0, places=7)

    def test_zero_discount_matches_undiscounted_cash(self):
        self.a["discount_rate_annual"] = 0
        b = evaluate(self.a)["options"]["predictive"]
        self.assertAlmostEqual(b["npv"], b["net_cash"])

    def test_zero_downtime_returns_no_break_even(self):
        self.a["unplanned_downtime_rate"] = 0
        self.assertIsNone(evaluate(self.a)["incremental_break_even_reduction"])

    def test_invalid_costs_rejected(self):
        self.a["options"]["monitoring"]["annual_operating"]["Platform and compute"] = -1
        with self.assertRaises(ValueError):
            evaluate(self.a)


if __name__ == "__main__":
    unittest.main()
