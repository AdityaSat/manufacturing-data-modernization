# Power BI report: Machine Health and Failure Drivers

**Question:** what conditions make a machine fail, and what should a maintenance team watch?

The dataset has no timestamps, so tool wear (minutes) is the time-like axis. This folder holds the
Power Query and DAX needed to build the report in Power BI Desktop. The `.pbix` file itself is not
included; it has to be built and saved in Power BI Desktop.

| File | Purpose |
|---|---|
| [`power_query.m`](power_query.m) | Four queries: `DataFolder`, `ai4i` (units dropped from column names), `FailureModes`, `holdout` |
| [`measures.dax`](measures.dax) | Calculated columns, measures, and the small `Method` table |
| [`../tests/test_powerbi_figures.py`](../tests/test_powerbi_figures.py) | Reproduces every number quoted below from the raw CSV |

## Build steps

1. Power BI Desktop > Transform data. Create the four queries from `power_query.m` and set `DataFolder`
   to your clone path. Close and apply.
2. Model view: relate `FailureModes[UDI]` to `ai4i[UDI]` (many to one) and set cross-filter direction to
   **Both**, so the failure-mode slicer filters `ai4i`. `holdout` and `Method` stay unrelated.
3. Paste the calculated columns and measures from `measures.dax`. Set *Sort by column* on
   `Wear Bucket Label` to `Wear Bucket`.
4. Build the pages below.

### Page 1, Overview
- KPI cards: `[Observations]`, `[Failures]`, `[Failure Rate]`.
- Failure rate by product type: bar, axis `ai4i[Type]`, value `[Failure Rate]`.
- Failures by failure mode: bar, axis `FailureModes[Failure Mode]`, value `[Mode Failures]`.
- Failure rate by tool wear: column, axis `ai4i[Wear Bucket Label]`, value `[Failure Rate]`.
- Torque vs. rotational speed: scatter, X `Rotational Speed rpm`, Y `Torque Nm`, legend `Outcome`.
  Optionally add a second scatter or a table with `Power Band`.
- Slicers: `ai4i[Type]` and `FailureModes[Failure Mode]`.

### Page 2, Model results
- Clustered bar: axis `Method[Method]`, values `[Caught]` and `[Missed]`.
- Cards or table by `Method[Method]`: `[Recall]` and `[Precision]`.
- Add a text box: *2,000 held-out observations, 39 failures. Synthetic data; not production-ready.*

## What the data shows (verified from the raw CSV)

| Finding | Value |
|---|---|
| Observations / failures / failure rate | 10,000 / 339 / 3.39% |
| Failure rate by type | L 3.92% (235 of 6,000), M 2.77% (83 of 2,997), H 2.09% (21 of 1,003) |
| Failure rate by wear, 0-49 / 50-99 / 100-149 / 150-199 | 2.21% / 2.25% / 2.27% / 2.66% |
| Failure rate at 200+ min of wear | 15.4% (123 of 801) |
| Power failures outside 3,500-9,000 W | 95 of 95 fall outside; no other row does |
| Holdout recall, monitoring vs random forest | 22 of 39 (56.4%) vs 29 of 39 (74.4%) |
| Holdout precision, monitoring vs random forest | 22.9% vs 42.6% (pilot target is 50%) |

## Pitfalls this build avoids

- **Wear is a threshold, not a steady climb.** The rate sits near 2-3% until 200 minutes, then jumps
  roughly sixfold. Describe it as "failures spike once wear passes about 200 minutes."
- **Random failures are mostly not failures.** 18 of the 19 `RNF` flags are on rows where
  `Machine failure = 0`. `FailureModes` keeps only failed machines, so Random shows 1, not 19.
- **Mode bars overlap.** 24 rows carry more than one mode flag, and 9 failures carry none (shown as
  *Unspecified*). Bars can add up to more than 339.
- **The 250+ wear bucket has only 2 rows**, both failures. It is merged into `200+`.
- **Failure-mode slicer and rate.** With a mode selected, `[Failure Rate]` reads 100% because every
  remaining row is a failure. Use `[Failures]` in the wear and type visuals when slicing by mode.
- **Brackets and spaces.** The queries rename `Air temperature [K]` to `Air Temp K` and so on. Columns
  with spaces still need quoting in DAX, as in `ai4i[Machine failure]`.

## Suggested summary

"Built a Power BI report on 10,000 synthetic machine records. Failure rate stays near 2-3% until tool
wear passes about 200 minutes, then jumps to 15%. Every power failure sits outside the 3,500-9,000 W
band. A maintenance team could use that to prioritize tool changes. The model page shows the random
forest catching 29 of 39 held-out failures against 22 for basic monitoring, with precision (42.6%)
still short of the 50% pilot target."
