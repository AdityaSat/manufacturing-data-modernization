# Business-case methodology

All costs, operating conditions, downtime reductions, and rollout timing are illustrative planning assumptions. The UCI data supplies no financial inputs. Replace them with plant records and scoped estimates before making an investment decision.

## Compare complete alternatives

Basic monitoring includes a centralized data foundation, a dashboard, threshold alerts, training, and ongoing support. Predictive maintenance includes that foundation plus model development, additional integration and compute, and an inspection allowance. The predictive option's total costs already include the foundation. Do not add the full monitoring cost again.

The common reference is doing nothing. Existing downtime loss is not charged as a project cost. Avoided downtime is an incremental project benefit.

## Calculation

1. Baseline annual downtime hours = assets × scheduled annual hours per asset × unplanned downtime rate.
2. Baseline annual downtime loss = baseline downtime hours × avoidable loss per machine-hour.
3. Gross annual benefit = baseline downtime loss × assumed downtime reduction.
4. Monthly net cash = gross annual benefit / 12 × realization − annual operating cost / 12.
5. At month 0, net cash is the negative implementation cost.
6. NPV = sum of each month's cash flow / (1 + annual discount rate)^(month / 12).

Benefits are zero during the pilot, 50% in the next three months, and fully realized afterward. Recurring costs run from month 1. This deliberately makes the pilot costly before savings appear. Payback interpolates the first cumulative cash-flow crossing, assuming uniform cash generation during that month.

The horizon is 36 months. ROI is undiscounted net cash divided by total implementation and recurring operating cost. This definition differs from NPV and from ROI calculated using implementation costs alone.

## Which break-even point?

The model reports three useful boundaries:

| Boundary | Meaning |
|---|---|
| Cash payback | When cumulative undiscounted cash first recovers implementation and incurred operating costs |
| Reduction for own NPV = 0 | Downtime reduction required for an option to beat doing nothing over the analysis horizon |
| Predictive reduction to beat monitoring | Total predictive reduction required for its NPV to equal monitoring's NPV, with the monitoring reduction fixed |

For the third boundary, let B be annual baseline downtime loss, F the sum of discounted monthly benefit realization / 12, and G the sum of discounted operating months / 12. Then:

`Predictive reduction = monitoring reduction + (extra implementation + extra annual operating cost × G) / (B × F)`

Base results: 21.135% total predictive downtime reduction equals monitoring's NPV. The 25% planning assumption is only 3.865 percentage points above that hurdle. This limited margin makes realized downtime reduction a critical pilot measurement.

## Avoid inflated savings

Use contribution margin or avoidable costs per hour instead of gross revenue. Determine whether stopped machines share a production bottleneck so the same loss is counted once. Reconcile planned and unplanned stops. Measure incremental inspection labor and any extra maintenance downtime. Attribute savings using matched operating periods or a controlled pilot, adjusting for production mix.

Taxes, financing, inflation, terminal value, benefits after month 36, and separate energy or labor savings are excluded. The illustrative discount rate is not a company-specific cost of capital. The 90-day plan does not automatically prove investment value, especially if too few failures occur during that period.

## Updating the deliverables

For the dashboard and Python results, edit `config/business_assumptions.json` and run `python run.py build`. For the workbook, edit blue cells on Assumptions. The Decision and Cash flows sheets recalculate. The deck is a snapshot, so update its figures after changing the case. These outputs are not live-linked to each other.
