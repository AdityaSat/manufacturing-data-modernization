# Interview walkthrough

## Explain the decision first

“This project asks whether a factory should invest in basic monitoring or add predictive maintenance. I connected a Python/SQL prototype to an explicit investment model so the recommendation depends on both technical evidence and cost.”

## Walk through the work

1. Open the machine-health dashboard. Explain that rows are synthetic observations, not live machines. Filter a product type and inspect a flagged record.
2. Open Model evidence. Explain precision using the 29 genuine failures among 68 alerts. Explain recall using the 29 detected failures among 39 total failures.
3. Show how excluding the failure-mode columns prevents target leakage. Those columns describe the answer and would make the model look artificially strong.
4. Open Business case. Reduce the assumed predictive downtime reduction from 25% to 20%. Its incremental NPV falls below monitoring's because the break-even hurdle is about 21.1%.
5. Open the workbook. Trace downtime hours to gross savings, then monthly operating costs and implementation spend. Show how the initial pilot delays payback.
6. Finish with the rollout plan. Explain why precision, actionable lead time, and attributable savings must improve before scaling.

## Questions you should be able to answer

| Question | Core reasoning |
|---|---|
| Why not report accuracy? | Failures are rare. A model can appear accurate by always predicting normal operation. |
| Why a separate validation set? | Threshold selection is a modeling decision. Using the test set would contaminate the final evaluation. |
| Why choose a forest? | The problem has nonlinear interactions, mixed source inputs, and a manageable data volume. |
| Does recall become downtime reduction? | No. Useful warning time, intervention success, failure severity, and crew availability determine avoided downtime. |
| Why does AI pay back later despite higher NPV? | It requires more initial investment, while its larger later cash flows create more value over the full horizon. |
| What would change your recommendation? | Lower realized savings, overlapping machine losses, higher integration costs, or excessive inspection effort. |
| What did you leave out? | Real equipment ingestion, production security, timestamped advance-warning validation, and actual factory ROI. |

## Accurate résumé language

Use this only after you have reviewed the implementation, run it yourself, and can explain your contribution:

“Developed a Python/SQL manufacturing analytics prototype using 10,000 synthetic observations and an Excel investment model comparing monitoring with predictive maintenance. Evaluated holdout detection tradeoffs and proposed a 90-day pilot with explicit financial and operational decision gates.”

You can describe the $69K incremental NPV as an **illustrative modeled result**. Do not describe it as realized client savings or imply that this work was performed for an employer. The project was developed with AI assistance. Review, understand, and adapt it before presenting it as evidence of your skills.
