// Power Query (M) for the "Machine Health and Failure Drivers" report.
// Create each query below in Power BI Desktop: Home > Transform data > New Source >
// Blank Query > Advanced Editor, paste the code, and give the query the name in its heading.
// Load order does not matter, but DataFolder must exist before the others refresh.

// ---------------------------------------------------------------------------
// Query: DataFolder   (a text value; change it to where you cloned the repo)
// ---------------------------------------------------------------------------
"C:\Users\ssatr\OneDrive\Documents\GitHub\manufacturing-data-modernization"

// ---------------------------------------------------------------------------
// Query: ai4i   (10,000 machine observations; units removed from column names)
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(
        File.Contents(DataFolder & "\data\raw\ai4i2020.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"UDI", Int64.Type}, {"Product ID", type text}, {"Type", type text},
            {"Air temperature [K]", type number}, {"Process temperature [K]", type number},
            {"Rotational speed [rpm]", Int64.Type}, {"Torque [Nm]", type number},
            {"Tool wear [min]", Int64.Type}, {"Machine failure", Int64.Type},
            {"TWF", Int64.Type}, {"HDF", Int64.Type}, {"PWF", Int64.Type},
            {"OSF", Int64.Type}, {"RNF", Int64.Type}
        },
        "en-US"
    ),
    Renamed = Table.RenameColumns(
        Typed,
        {
            {"Air temperature [K]", "Air Temp K"},
            {"Process temperature [K]", "Process Temp K"},
            {"Rotational speed [rpm]", "Rotational Speed rpm"},
            {"Torque [Nm]", "Torque Nm"},
            {"Tool wear [min]", "Tool Wear Min"}
        }
    )
in
    Renamed

// ---------------------------------------------------------------------------
// Query: FailureModes   (one row per failure mode per failed machine)
// Only rows with Machine failure = 1 are kept. In the raw file 18 of the 19 RNF
// (random failure) flags sit on rows where Machine failure = 0, so counting flags
// directly would overstate random failures. 9 failures carry no mode flag at all;
// they appear as "Unspecified" so the bars add up to the failure count.
// A machine with two modes appears twice, so bar totals can exceed total failures.
// ---------------------------------------------------------------------------
let
    Failed = Table.SelectRows(ai4i, each [Machine failure] = 1),
    WithNone = Table.AddColumn(
        Failed, "NONE",
        each if [TWF] + [HDF] + [PWF] + [OSF] + [RNF] = 0 then 1 else 0,
        Int64.Type
    ),
    Slim = Table.SelectColumns(WithNone, {"UDI", "TWF", "HDF", "PWF", "OSF", "RNF", "NONE"}),
    Unpivoted = Table.UnpivotOtherColumns(Slim, {"UDI"}, "Mode Code", "Flag"),
    Flagged = Table.SelectRows(Unpivoted, each [Flag] = 1),
    Named = Table.AddColumn(
        Flagged, "Failure Mode",
        each
            if [Mode Code] = "TWF" then "Tool wear"
            else if [Mode Code] = "HDF" then "Heat dissipation"
            else if [Mode Code] = "PWF" then "Power"
            else if [Mode Code] = "OSF" then "Overstrain"
            else if [Mode Code] = "RNF" then "Random"
            else "Unspecified",
        type text
    )
in
    Table.SelectColumns(Named, {"UDI", "Failure Mode"})

// ---------------------------------------------------------------------------
// Query: holdout   (2,000 held-out test observations with model and baseline alerts)
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(
        File.Contents(DataFolder & "\reports\holdout_predictions.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"observation_id", Int64.Type}, {"product_id", type text}, {"product_type", type text},
            {"air_temperature_k", type number}, {"process_temperature_k", type number},
            {"rotational_speed_rpm", Int64.Type}, {"torque_nm", type number},
            {"tool_wear_min", Int64.Type}, {"machine_failure", Int64.Type},
            {"temperature_gap_k", type number}, {"power_w", type number}, {"split", type text},
            {"model_score", type number}, {"model_alert", Int64.Type},
            {"monitoring_alert", Int64.Type}
        },
        "en-US"
    )
in
    Typed
