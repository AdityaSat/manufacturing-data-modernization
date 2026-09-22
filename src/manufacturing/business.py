"""Illustrative, pre-tax incremental cash flows. No ML-to-savings conversion."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_assumptions(path=None):
    return json.loads(Path(path or ROOT / "config/business_assumptions.json").read_text())


def validate_assumptions(a):
    positive = ["assets", "scheduled_hours_per_asset_year", "loss_per_machine_hour"]
    for key in positive:
        if not isinstance(a[key], (float, int)) or not math.isfinite(a[key]) or a[key] <= 0:
            raise ValueError(f"{key} must be a positive finite number")
    for key in ["unplanned_downtime_rate", "partial_ramp_realization", "discount_rate_annual"]:
        if not 0 <= a[key] <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
    for key in ["pilot_months", "partial_ramp_months", "horizon_months"]:
        if not isinstance(a[key], int) or a[key] < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
    if a["horizon_months"] < 1 or a["pilot_months"] + a["partial_ramp_months"] > a["horizon_months"]:
        raise ValueError("Ramp must fit inside a positive analysis horizon")
    for option in a["options"].values():
        if not 0 <= option["downtime_reduction"] <= 1:
            raise ValueError("downtime_reduction must be between 0 and 1")
        for group in ["implementation", "annual_operating"]:
            if any(not math.isfinite(v) or v < 0 for v in option[group].values()):
                raise ValueError("Costs must be finite and nonnegative")


def evaluate(a):
    validate_assumptions(a)
    hours = a["assets"] * a["scheduled_hours_per_asset_year"] * a["unplanned_downtime_rate"]
    pool = hours * a["loss_per_machine_hour"]
    months = a["horizon_months"]
    schedule = []
    for m in range(months + 1):
        ramp = 0 if m <= a["pilot_months"] else (
            a["partial_ramp_realization"] if m <= a["pilot_months"] + a["partial_ramp_months"] else 1)
        schedule.append({"month": m, "realization": ramp,
                         "discount_factor": (1 + a["discount_rate_annual"]) ** (-m / 12)})
    pv_opex_factor = sum(x["discount_factor"] / 12 for x in schedule[1:])
    pv_benefit_factor = sum(x["realization"] * x["discount_factor"] / 12 for x in schedule[1:])
    results = {}
    for key, option in a["options"].items():
        capex = sum(option["implementation"].values())
        opex = sum(option["annual_operating"].values())
        gross = pool * option["downtime_reduction"]
        cumulative, flows, payback = -capex, [], 0 if capex == 0 else None
        for row in schedule:
            m = row["month"]
            benefit = gross / 12 * row["realization"] if m else 0
            cost = opex / 12 if m else capex
            net = benefit - cost
            previous = cumulative
            cumulative = net if m == 0 else previous + net
            if m and payback is None and previous < 0 <= cumulative and net > 0:
                payback = m - 1 + (-previous) / net
            flows.append({**row, "benefit": benefit, "cost": cost, "net": net,
                          "cumulative": cumulative, "present_value": net * row["discount_factor"]})
        total_cost = capex + opex * months / 12
        results[key] = {"name": option["name"], "implementation": capex, "annual_opex": opex,
                        "annual_gross_savings": gross, "steady_annual_net": gross - opex,
                        "annual_hours_avoided": hours * option["downtime_reduction"],
                        "npv": sum(x["present_value"] for x in flows),
                        "payback_months": payback, "net_cash": cumulative,
                        "roi": cumulative / total_cost if total_cost else None,
                        "break_even_reduction": (capex + opex * pv_opex_factor) / (pool * pv_benefit_factor)
                        if pool * pv_benefit_factor else None, "cash_flows": flows}
    basic, ai = results["monitoring"], results["predictive"]
    incremental_break_even = (
        a["options"]["monitoring"]["downtime_reduction"] +
        (ai["implementation"] - basic["implementation"] +
         (ai["annual_opex"] - basic["annual_opex"]) * pv_opex_factor) / (pool * pv_benefit_factor)
    ) if pool * pv_benefit_factor else None
    return {"annual_downtime_hours": hours, "annual_downtime_cost": pool,
            "pv_benefit_factor": pv_benefit_factor, "pv_opex_factor": pv_opex_factor,
            "options": results, "incremental_npv": ai["npv"] - basic["npv"],
            "incremental_break_even_reduction": incremental_break_even,
            "basis": "All operating and cost inputs are illustrative assumptions. Pre-tax incremental cash flows versus doing nothing."}
