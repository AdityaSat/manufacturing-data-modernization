# Architecture and implementation choices

## Working prototype

| Layer | Implementation | Reason |
|---|---|---|
| Source | Bundled UCI CSV with checksum | Reproducible and usable offline |
| Validation | Python schema, null, range, label, and identifier checks | Reject invalid inputs before analysis |
| Storage | SQLite observations and predictions tables | Demonstrate persistent relational storage without cloud cost |
| Transformation | SQL health and quality-summary views | Keep metrics queryable and traceable |
| Modeling | Training-only preprocessing and random forest | Capture nonlinear interactions with controlled evaluation |
| Consumption | JSON export and browser dashboard | Make results accessible without an account or extra frontend packages |
| Investment analysis | Python and independently verified Excel formulas | Make benefits, costs, and decision boundaries inspectable |

The warehouse grain is one observation. Unique indexes protect one-to-one joining by observation ID. A rebuild replaces the source and prediction tables, then recreates analytical views. The pipeline can be run repeatedly without appending duplicates.

The dashboard is a static snapshot. It does not connect to operating equipment or stream live events. The local server binds only to localhost. There is no production authentication, role-based access, or alert dispatch. These are production requirements outside this prototype.

## A possible factory implementation

Start with read-only ingestion from approved OT gateways. Land timestamped sensor records in a raw zone, enforce a schema and asset registry, and publish curated tables for maintenance analysts. Join work-order outcomes and downtime events by asset and time. Select the storage and orchestration platform after assessing existing licenses, latency, scale, and support capability. The prototype does not establish a preferred cloud vendor.

Use a separate inference service or scheduled scoring job with versioned models, logged inputs, and operator acknowledgement. Record whether each alert led to inspection, what was found, available lead time, and whether downtime was actually prevented.

## Controls to carry into a pilot

| Control | Owner | Evidence |
|---|---|---|
| Consistent physical asset IDs and timestamps | OT engineer | Sensor-to-asset mapping and clock checks |
| Data ownership and access | Data owner | Least-privilege roles and audit trail |
| Network separation | OT security owner | Approved read-only gateway and reviewed data path |
| Model validity | Data science lead | Temporal and asset-separated tests and drift monitoring |
| Human review | Reliability engineer | Inspection workload, acknowledgement, and outcomes |
| Investment attribution | Finance partner | Avoided downtime reconciliation and cost records |

The first pilot gate is at least 95% completeness of required data. Proposed model gates are at least 70% recall, 50% precision, and 24 hours of actionable lead time on real records. These thresholds are planning targets to confirm with plant engineering. The current synthetic test falls short of the precision target and cannot evaluate lead time.
