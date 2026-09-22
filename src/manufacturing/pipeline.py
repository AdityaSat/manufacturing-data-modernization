"""Validate UCI AI4I, load SQLite, train without target leakage, export evidence."""
import argparse
import hashlib
import io
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (average_precision_score, confusion_matrix, fbeta_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .business import ROOT, evaluate, load_assumptions

DATA_URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
COLUMN_MAP = {"UDI": "observation_id", "Product ID": "product_id", "Type": "product_type",
              "Air temperature [K]": "air_temperature_k", "Process temperature [K]": "process_temperature_k",
              "Rotational speed [rpm]": "rotational_speed_rpm", "Torque [Nm]": "torque_nm",
              "Tool wear [min]": "tool_wear_min", "Machine failure": "machine_failure",
              **{x: x.lower() for x in ["TWF", "HDF", "PWF", "OSF", "RNF"]}}
NUMERIC_FEATURES = ["air_temperature_k", "process_temperature_k", "rotational_speed_rpm", "torque_nm",
                    "tool_wear_min", "temperature_gap_k", "power_w", "wear_torque"]
FEATURES = ["product_type", *NUMERIC_FEATURES]
SEED = 42


def download(destination):
    """Download only on explicit --download. The repository includes the original CSV."""
    with urllib.request.urlopen(DATA_URL, timeout=60) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        # Read a known member. Do not extract arbitrary paths from a remote archive.
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read("ai4i2020.csv"))


def validate_and_prepare(raw):
    if set(raw.columns) != set(COLUMN_MAP):
        raise ValueError("Unexpected schema: expected the original 14-column UCI AI4I CSV")
    if raw.empty or raw.isna().any().any():
        raise ValueError("Input must contain records with no missing values")
    d = raw.rename(columns=COLUMN_MAP).copy()
    if d.observation_id.duplicated().any():
        raise ValueError("Duplicate observation identifiers")
    if not d.product_type.isin(["L", "M", "H"]).all():
        raise ValueError("Unknown product quality type")
    numeric = [c for c in d if c not in ["product_type", "product_id"]]
    for col in numeric:
        d[col] = pd.to_numeric(d[col], errors="raise")
        if not np.isfinite(d[col]).all():
            raise ValueError(f"Non-finite value in {col}")
    binary = ["machine_failure", "twf", "hdf", "pwf", "osf", "rnf"]
    if not d[binary].isin([0, 1]).all().all():
        raise ValueError("Failure labels must be binary")
    positive = ["observation_id", "air_temperature_k", "process_temperature_k", "rotational_speed_rpm", "torque_nm"]
    if (d[positive] <= 0).any().any() or (d.tool_wear_min < 0).any():
        raise ValueError("Invalid sensor values")
    if (d.observation_id % 1 != 0).any():
        raise ValueError("Observation identifiers must be integers")
    d = d.sort_values("observation_id").reset_index(drop=True)
    modes = d[["twf", "hdf", "pwf", "osf", "rnf"]].max(axis=1)
    quality = {"rows": len(d), "missing_cells": 0, "duplicate_ids": 0,
               "label_mode_disagreements": int((modes != d.machine_failure).sum()),
               "note": "Original target retained even where component failure flags disagree."}
    return d, quality


def features(d):
    """Explicit allowlist excludes IDs, target and all failure-mode flags."""
    x = d[["product_type", *NUMERIC_FEATURES[:5]]].copy()
    x["temperature_gap_k"] = x.process_temperature_k - x.air_temperature_k
    x["power_w"] = x.torque_nm * x.rotational_speed_rpm * (2 * np.pi / 60)
    x["wear_torque"] = x.tool_wear_min * x.torque_nm
    return x[FEATURES]


def split_labels(n):
    # UDI order is a proxy for source sequence, not real elapsed time or asset identity.
    return np.array(["train"] * int(n * .6) + ["validation"] * (int(n * .8) - int(n * .6)) +
                    ["test"] * (n - int(n * .8)))


def monitoring_alerts(d):
    """Simple fixed single-sensor rules chosen before looking at holdout labels."""
    return ((d.torque_nm < 20) | (d.torque_nm > 60) | (d.tool_wear_min > 220)).astype(int).to_numpy()


def metrics(y, prediction, scores=None):
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {"rows": len(y), "failures": int(np.sum(y)), "tn": int(tn), "fp": int(fp),
            "fn": int(fn), "tp": int(tp), "precision": float(precision_score(y, prediction, zero_division=0)),
            "recall": float(recall_score(y, prediction, zero_division=0)),
            "f2": float(fbeta_score(y, prediction, beta=2, zero_division=0)),
            "alert_rate": float(np.mean(prediction)),
            "average_precision": float(average_precision_score(y, scores)) if scores is not None else None,
            "roc_auc": float(roc_auc_score(y, scores)) if scores is not None and len(set(y)) == 2 else None}


def select_threshold(y, scores, max_alert_rate=.10):
    candidates = []
    for threshold in np.linspace(.01, .99, 99):
        pred = scores >= threshold
        if pred.mean() <= max_alert_rate:
            candidates.append((fbeta_score(y, pred, beta=2, zero_division=0), threshold))
    if not candidates:
        return 1.01  # Safe no-alert fallback when no candidate meets capacity.
    return float(max(candidates)[1])


def run(root=ROOT, download_data=False):
    root = Path(root)
    csv = root / "data/raw/ai4i2020.csv"
    if download_data:
        download(csv)
    if not csv.exists():
        raise FileNotFoundError("Dataset missing. Run python run.py build --download")
    d, quality = validate_and_prepare(pd.read_csv(csv))
    split = split_labels(len(d))
    x, y = features(d), d.machine_failure.to_numpy()
    for label in ["train", "validation", "test"]:
        if len(set(y[split == label])) != 2:
            raise ValueError(f"{label} split requires both classes")
    pre = ColumnTransformer([("type", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["product_type"]),
                             ("sensors", "passthrough", NUMERIC_FEATURES)])
    model = Pipeline([("features", pre), ("classifier", RandomForestClassifier(
        n_estimators=300, max_depth=12, min_samples_leaf=2, class_weight="balanced", random_state=SEED, n_jobs=2))])
    model.fit(x[split == "train"], y[split == "train"])
    scores = model.predict_proba(x)[:, 1]
    threshold = select_threshold(y[split == "validation"], scores[split == "validation"])
    pred, basic = (scores >= threshold).astype(int), monitoring_alerts(d)
    test = split == "test"
    report = {
        "dataset": {"name": "UCI AI4I 2020", "doi": "https://doi.org/10.24432/C5HS5C", "synthetic": True,
                    "rows": len(d), "failures": int(y.sum()), "failure_rate": float(y.mean()),
                    "sha256": hashlib.sha256(csv.read_bytes()).hexdigest()},
        "quality": quality, "seed": SEED, "sklearn_version": sklearn.__version__,
        "features": FEATURES, "threshold": threshold,
        "threshold_policy": "Maximum validation F2 among thresholds 0.01..0.99 with at most 10% validation alerts. Higher threshold wins ties.",
        "split": {label: {"rows": int((split == label).sum()), "failures": int(y[split == label].sum()),
                          "udi_min": int(d.loc[split == label, "observation_id"].min()),
                          "udi_max": int(d.loc[split == label, "observation_id"].max())}
                  for label in ["train", "validation", "test"]},
        "test": {"model": metrics(y[test], pred[test], scores[test]), "monitoring": metrics(y[test], basic[test])},
        "validation": metrics(y[split == "validation"], pred[split == "validation"], scores[split == "validation"]),
        "limitation": "Contemporaneous synthetic failure detection. No timestamps or physical machine identities. No demonstrated advance warning, real-factory accuracy, or causal downtime savings. Scores are uncalibrated rankings."
    }
    predictions = pd.DataFrame({"observation_id": d.observation_id, "split": split, "model_score": scores,
                                "model_alert": pred, "monitoring_alert": basic})
    db = root / "data/warehouse.db"
    with sqlite3.connect(db) as con:
        d.to_sql("observations", con, if_exists="replace", index=False)
        predictions.to_sql("predictions", con, if_exists="replace", index=False)
        con.execute("CREATE UNIQUE INDEX observations_udi ON observations(observation_id)")
        con.execute("CREATE UNIQUE INDEX predictions_udi ON predictions(observation_id)")
        con.executescript((root / "sql/warehouse.sql").read_text())
        records = pd.read_sql_query("SELECT * FROM observation_health WHERE split='test' ORDER BY model_score DESC", con)
        summary = pd.read_sql_query("SELECT * FROM quality_summary", con).to_dict(orient="records")
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "model_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    records.to_csv(reports / "holdout_predictions.csv", index=False, float_format="%.8f")
    assumptions = load_assumptions(root / "config/business_assumptions.json")
    business = evaluate(assumptions)
    (reports / "business_case_results.json").write_text(json.dumps(business, indent=2) + "\n")
    payload = {"metrics": report, "records": json.loads(records.to_json(orient="records", double_precision=8)),
               "summary": summary, "assumptions": assumptions, "business": business}
    (root / "dashboard/data.json").write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    # A portable copy opens directly in a browser and uses the same UI code and data.
    dash = root / "dashboard"
    if (dash / "index.html").exists():
        html = (dash / "index.html").read_text()
        script = (dash / "business.js").read_text().replace("export function", "function") + "\n" + (
            (dash / "app.js").read_text().replace("import {evaluateBusiness} from './business.js';", ""))
        html = html.replace('<link rel="stylesheet" href="styles.css">', '<style>' + (dash / "styles.css").read_text() + '</style>')
        html = html.replace('<script type="module" src="app.js"></script>', '')
        html = html.replace('</body>', '<script id="project-data" type="application/json">' +
                            json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c") +
                            '</script><script type="module">' + script + '</script></body>')
        (dash / "standalone.html").write_text(html)
    print(json.dumps({"dataset_rows": len(d), "test_metrics": report["test"],
                      "threshold": threshold, "label_disagreements": quality["label_mode_disagreements"],
                      "predictive_npv": round(business["options"]["predictive"]["npv"]),
                      "incremental_break_even_reduction": business["incremental_break_even_reduction"]}, indent=2))
    return report, business


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    run(download_data=parser.parse_args().download)
