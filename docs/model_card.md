# Model card

## Intended use

An educational demonstration of a governed data pipeline, imbalanced classification, and technology investment analysis. Output supports inspection of a public synthetic dataset. Production maintenance decisions, safety controls, and real-machine failure forecasting are outside the demonstrated scope.

## Source and target

UCI AI4I 2020 has 10,000 observations and 339 positive `Machine failure` labels. The raw CSV contains six source inputs, identifiers, and failure labels. One row is an observation. Product ID is not a physical machine ID. There is no usable timestamp or validated warning horizon in this analysis.

The pipeline retains the original main target. It reports 27 rows where the logical OR of the five component failure flags differs from the main target. It does not silently rewrite labels. This disagreement creates uncertainty in the labels used for evaluation.

## Input control

Allowed source features: product quality type, air temperature, process temperature, rotational speed, torque, and tool wear. Derived features: process minus air temperature, torque × rotational speed × 2π/60, and tool wear × torque.

The input allowlist excludes UDI, Product ID, Machine failure, TWF, HDF, PWF, OSF, and RNF. These exclusions are tested. Engineering uses available sensor fields and basic physics, not target columns. Because the synthetic generator uses related process rules, strong benchmark performance may reflect recovery of those rules.

## Experimental design

| Partition | Source UDI | Purpose |
|---|---|---|
| Training | 1–6,000 | Fit the encoder and random forest |
| Validation | 6,001–8,000 | Choose alert threshold |
| Test | 8,001–10,000 | Report final results |

The partition uses contiguous source order to reduce adjacent-row mixing. UDI ordering is a proxy only. It does not establish a chronological or asset-held-out real-world trial. The test period has only 39 failures, and prevalence differs across partitions. A production study should include multiple temporal windows, physical asset separation, uncertainty estimates, and enough failures to estimate performance reliably.

Random forest: 300 trees, maximum depth 12, minimum leaf size 2, balanced class weights, seed 42. One-hot encoding fits only on training rows. Hyperparameters are fixed. No test-set tuning occurs. Scores are uncalibrated rankings, not validated probabilities.

The threshold search evaluates 0.01 through 0.99 on validation data. It maximizes F2 while limiting alerts to 10% of validation records. Ties select the higher threshold. F2 emphasizes recall. This is an experimental policy, not a validated operational cost optimum.

Baseline alert rules: torque below 20 Nm, torque above 60 Nm, or tool wear above 220 minutes. These are simple demonstration thresholds chosen before inspecting holdout results. They are not equipment-vendor operating limits. The baseline and model use the same evaluation population.

## Results and interpretation

At threshold 0.14, the forest detects 29 failures, misses 10, raises 39 false alarms, and correctly leaves 1,922 normal records unflagged. Precision is 42.6%, recall 74.4%, and average precision 0.761. Baseline counts are 22 detected failures, 17 missed failures, 74 false alarms, and 1,887 true negatives.

Accuracy would obscure the rare-event problem. A model predicting no failures would look accurate while detecting none. Recall, precision, false alarms, and missed failures make the operational tradeoff visible.

There is no measured factory downtime reduction. Performance at contemporaneous classification cannot demonstrate that crews have time to intervene, that interventions work, or that operating savings exceed inspection costs. The financial model therefore uses a separately labeled downtime-reduction assumption.

Sources: [UCI dataset](https://doi.org/10.24432/C5HS5C), [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). Exact results and checksum: `reports/model_metrics.json`.
