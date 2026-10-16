"""Generate the SPG Operational Dashboard semantic model as TMDL (PBIP format)."""
import os, uuid, json, textwrap

def stable_logical_id(platform_path):
    """Keep the Fabric logicalId stable across regenerations: Fabric identifies items by it."""
    try:
        return json.load(open(platform_path))["config"]["logicalId"]
    except Exception:
        return str(uuid.uuid4())

ROOT = os.environ.get("PBIP_ROOT", "/home/claude/repo")
SM = os.path.join(ROOT, "SPG Operational Dashboard.SemanticModel")
DEF = os.path.join(SM, "definition")
TBL = os.path.join(DEF, "tables")
os.makedirs(TBL, exist_ok=True)
os.makedirs(os.path.join(DEF, "cultures"), exist_ok=True)

import re as _re
def q(name):
    return name if _re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name) else "'" + name.replace("'", "''") + "'"

def lt():  # lineage tag
    return str(uuid.uuid4())

def w(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace("\n", "\r\n") if False else text)

def ind(text, n):
    pad = "\t" * n
    return "\n".join(pad + l if l.strip() else l for l in text.splitlines())

# ---------------------------------------------------------------- M helpers
WORKFLOW_MAP = """fnWorkflow = (w as nullable text) as nullable text =>
    let k = if w = null then null else Text.Lower(Text.Trim(w)),
        r = [renewal="Renewal", #"policy in force"="Policy in force", #"new business"="New business",
             #"support processing"="Support processing", #"billing discrepancy"="Billing discrepancy",
             #"ae requests"="AE requests", #"sfc accounting"="SFC Accounting", claims="Claims", diary="Diary"]
    in if k = null then null else (Record.FieldOrDefault(r, k, Text.Proper(w)))"""

BAND_FN = """fnBand = (age as nullable number) as text =>
    if age = null then "Unknown"
    else if age <= 7 then "0-7" else if age <= 15 then "8-15" else if age <= 30 then "16-30"
    else if age <= 60 then "31-60" else if age <= 90 then "61-90" else "90+" """

SCOPE_FN = """fnScope = (n as nullable text) as text =>
    let s = if n = null then "" else n
    in if Text.StartsWith(s, "Monarch") or Text.StartsWith(s, "SWIS") or Text.StartsWith(s, "SA-IR-") or Text.StartsWith(s, "RSP")
          or Text.StartsWith(s, "CSR.") or Text.StartsWith(s, "int.z") or Text.Contains(s, "Support") or Text.EndsWith(s, "Renewal") or Text.Contains(s, "Unassigned")
       then "Shared queue"
       else if Text.StartsWith(s, "RPRO.") or Text.StartsWith(s, "EOX.") or Text.StartsWith(s, "PAT.") or Text.StartsWith(s, "SCM.") then "Vendor"
       else "Internal" """

STAGE_FN = """fnStage = (step as nullable text) as nullable text =>
    let s = if step = null then "" else step
    in if List.AnyTrue(List.Transform({"Ren - Begin Renewal","Ren - Gather Renewal Information","Ren - Review Renewal Submission","Ren - DB Auto Renew"}, each Text.StartsWith(s, _))) then "Not yet quoted"
       else if List.AnyTrue(List.Transform({"Ren - Quote Entry","Ren - Quote Sent","Ren: Quote Sent","Ren - Quote to Agent","Ren - Pend for Info"}, each Text.StartsWith(s, _))) then "Quoted - with agent"
       else if Text.StartsWith(s, "Bind - ") then "Bound - awaiting issue"
       else if Text.StartsWith(s, "Ren - Non Renew") or Text.StartsWith(s, "Ren - Send Off Risk") then "Not renewing"
       else null"""

REWORK_FN = """fnIsRework = (step as nullable text) as logical =>
    let s = if step = null then "" else Text.Lower(step)
    in List.AnyTrue(List.Transform({"revision","re-quote","requote","re-issue","reissue","re-rate","rerate","re-invoice","reinvoice","correction","rework"}, each Text.Contains(s, _)))"""

OPEN_M = f"""let
    {WORKFLOW_MAP},
    {BAND_FN},
    {SCOPE_FN},
    {STAGE_FN},
    Source = SPG_Workbook,
    Sheet = Source{{[Item="OpenTasks", Kind="Sheet"]}}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
        {{"FileNumber", type text}}, {{"PolicyNumber", type text}}, {{"Insured", type text}}, {{"Team", type text}}, {{"Department", type text}},
        {{"Brand", type text}}, {{"Workflow", type text}}, {{"Step", type text}}, {{"AssignedTo", type text}}, {{"FromUser", type text}},
        {{"AccountExec", type text}}, {{"CSR", type text}}, {{"AgentName", type text}}, {{"Status", type text}},
        {{"AgeDays_fromInitiated", Int64.Type}}, {{"DaysSinceAvailable", Int64.Type}}, {{"SLA_days_placeholder", Int64.Type}},
        {{"AgingBucket", type text}}, {{"Scheduled_notYetAvailable", type logical}}, {{"OutOfService", type logical}} }}),
    Renamed = Table.RenameColumns(Typed, {{
        {{"FileNumber", "File number"}}, {{"PolicyNumber", "Policy number"}}, {{"AssignedTo", "Assigned to"}}, {{"FromUser", "From user"}},
        {{"AccountExec", "Account executive"}}, {{"AgentName", "Agent name"}}, {{"AgeDays_fromInitiated", "Age (days)"}},
        {{"DaysSinceAvailable", "Days since available"}}, {{"SLA_days_placeholder", "SLA source (days)"}}, {{"AgingBucket", "Source aging bucket"}} }}),
    Removed = Table.RemoveColumns(Renamed, {{"Scheduled_notYetAvailable", "OutOfService"}}),
    WorkflowNorm = Table.TransformColumns(Removed, {{{{"Workflow", fnWorkflow, type text}}}}),
    AssignedFill = Table.ReplaceValue(WorkflowNorm, null, "(Unassigned)", Replacer.ReplaceValue, {{"Assigned to"}}),
    AddSLA = Table.AddColumn(AssignedFill, "SLA (days)", each List.Min({{[#"SLA source (days)"], SLA_Cap_Days}}), Int64.Type),
    AddSched = Table.AddColumn(AddSLA, "Scheduled", each [#"Days since available"] < 0, type logical),
    AddOOS = Table.AddColumn(AddSched, "Out of service", each (not [Scheduled]) and [#"Age (days)"] > [#"SLA (days)"], type logical),
    AddService = Table.AddColumn(AddOOS, "Service", each if [Scheduled] then "Scheduled" else if [Out of service] then "Out of service" else "Within service", type text),
    AddBand = Table.AddColumn(AddService, "Aging band", each fnBand([#"Age (days)"]), type text),
    AddOver30 = Table.AddColumn(AddBand, "Over 30 days", each [#"Age (days)"] > 30, type logical),
    AddOver90 = Table.AddColumn(AddOver30, "Over 90 days", each [#"Age (days)"] > 90, type logical),
    AddScope = Table.AddColumn(AddOver90, "Staff scope", each fnScope([#"Assigned to"]), type text),
    AddLine = Table.AddColumn(AddScope, "Line of business", each if Text.Contains([Department], "Personal") then "Personal" else if Text.Contains([Department], "Commercial") then "Commercial" else "Other", type text),
    AddStage = Table.AddColumn(AddLine, "Renewal stage", each if [Workflow] = "Renewal" then fnStage([Step]) else null, type text),
    AddStageOrder = Table.AddColumn(AddStage, "Renewal stage order", each if [#"Renewal stage"] = "Not yet quoted" then 1 else if [#"Renewal stage"] = "Quoted - with agent" then 2 else if [#"Renewal stage"] = "Bound - awaiting issue" then 3 else if [#"Renewal stage"] = "Not renewing" then 4 else null, Int64.Type),
    AddInPipeline = Table.AddColumn(AddStageOrder, "In renewal pipeline", each [#"Renewal stage"] <> null, type logical),
    AddInitiated = Table.AddColumn(AddInPipeline, "Date initiated", each Date.AddDays(SnapshotDate, -[#"Age (days)"]), type date),
    AddAvailable = Table.AddColumn(AddInitiated, "Available date", each Date.AddDays(SnapshotDate, -[#"Days since available"]), type date),
    AddUnassigned = Table.AddColumn(AddAvailable, "Is unassigned", each [#"Assigned to"] = "(Unassigned)", type logical),
    AddReceivedYday = Table.AddColumn(AddUnassigned, "Received yesterday", each [#"Days since available"] >= 0 and [#"Days since available"] <= 1, type logical)
in
    AddReceivedYday"""

COMPLETED_M = f"""let
    {WORKFLOW_MAP},
    {REWORK_FN},
    Source = SPG_Workbook,
    Sheet = Source{{[Item="Completed", Kind="Sheet"]}}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
        {{"Workflow", type text}}, {{"Step", type text}}, {{"ReleasedBy", type text}}, {{"HoursInStep", type number}},
        {{"TurnaroundDays_initiatedToRelease", type number}}, {{"SLA_days_placeholder", Int64.Type}}, {{"MetSLA", type logical}} }}),
    Renamed = Table.RenameColumns(Typed, {{
        {{"ReleasedBy", "Released by"}}, {{"HoursInStep", "Hours in step"}}, {{"TurnaroundDays_initiatedToRelease", "Turnaround (days)"}},
        {{"SLA_days_placeholder", "SLA (days)"}}, {{"MetSLA", "Met SLA"}} }}),
    WorkflowNorm = Table.TransformColumns(Renamed, {{{{"Workflow", fnWorkflow, type text}}}}),
    AddRework = Table.AddColumn(WorkflowNorm, "Is rework", each fnIsRework([Step]), type logical),
    AddReleaseType = Table.AddColumn(AddRework, "Release type", each if [#"Is rework"] then "Rework" else "Production", type text),
    AddHoursBand = Table.AddColumn(AddReleaseType, "Hours band", each if [#"Hours in step"] <= 2 then "<= 2 h" else if [#"Hours in step"] <= 4 then "2-4 h" else if [#"Hours in step"] <= 24 then "4-24 h" else "Over a day", type text),
    AddHoursBandOrder = Table.AddColumn(AddHoursBand, "Hours band order", each if [#"Hours in step"] <= 2 then 1 else if [#"Hours in step"] <= 4 then 2 else if [#"Hours in step"] <= 24 then 3 else 4, Int64.Type),
    AddReleaseDate = Table.AddColumn(AddHoursBandOrder, "Release date", each Date.AddDays(SnapshotDate, -1), type date),
    AddIndex = Table.AddIndexColumn(AddReleaseDate, "Release id", 1, 1, Int64.Type)
in
    AddIndex"""

COMPLIANCE_M = f"""let
    {BAND_FN},
    Source = SPG_Workbook,
    Sheet = Source{{[Item="Compliance", Kind="Sheet"]}}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {{
        {{"FileNumber", type text}}, {{"FileName_key", type text}}, {{"State", type text}}, {{"UA", type text}}, {{"AssignedTo", type text}},
        {{"Team", type text}}, {{"DaysPastDue_posIsLate", Int64.Type}}, {{"AgeDays_fromInitiated", Int64.Type}}, {{"DueBand", type text}},
        {{"Note", type text}}, {{"Carrier", type text}} }}),
    Renamed = Table.RenameColumns(Typed, {{
        {{"FileNumber", "File number"}}, {{"FileName_key", "File name"}}, {{"AssignedTo", "Assigned to"}},
        {{"DaysPastDue_posIsLate", "Days past due"}}, {{"AgeDays_fromInitiated", "Age (days)"}}, {{"DueBand", "Due band code"}} }}),
    AddDueBand = Table.AddColumn(Renamed, "Due band", each if [#"Due band code"] = "past" then "Past due" else if [#"Due band code"] = "red" then "Due within 14 days" else if [#"Due band code"] = "amber" then "Due in 15-30 days" else if [#"Due band code"] = "green" then "On track" else "No due date", type text),
    AddDueOrder = Table.AddColumn(AddDueBand, "Due band order", each if [#"Due band code"] = "past" then 1 else if [#"Due band code"] = "red" then 2 else if [#"Due band code"] = "amber" then 3 else if [#"Due band code"] = "green" then 4 else 5, Int64.Type),
    AddFining = Table.AddColumn(AddDueOrder, "Fining state", each List.Contains(Text.Split(Fining_States, ","), [State]), type logical),
    AddBand = Table.AddColumn(AddFining, "Aging band", each fnBand([#"Age (days)"]), type text),
    AddOver30 = Table.AddColumn(AddBand, "Over 30 days", each [#"Age (days)"] > 30, type logical),
    AddDueDate = Table.AddColumn(AddOver30, "Due date", each if [#"Due band code"] = "nodate" then null else Date.AddDays(SnapshotDate, -[#"Days past due"]), type date),
    AddInitiated = Table.AddColumn(AddDueDate, "Date initiated", each Date.AddDays(SnapshotDate, -[#"Age (days)"]), type date),
    AddState = Table.AddColumn(AddInitiated, "Filing state", each if [State] = "Processing" then "(Processing)" else [State], type text)
in
    AddState"""

DIM_TEAM_M = """let
    A = Table.SelectColumns(OpenTasks, {"Team"}),
    B = Table.SelectColumns(Compliance, {"Team"}),
    U = Table.Distinct(Table.Combine({A, B})),
    NoNull = Table.SelectRows(U, each [Team] <> null),
    Sorted = Table.Sort(NoNull, {{"Team", Order.Ascending}})
in
    Sorted"""

DIM_WORKFLOW_M = """let
    A = Table.SelectColumns(OpenTasks, {"Workflow"}),
    B = Table.SelectColumns(Completed, {"Workflow"}),
    U = Table.Distinct(Table.Combine({A, B})),
    NoNull = Table.SelectRows(U, each [Workflow] <> null),
    Sorted = Table.Sort(NoNull, {{"Workflow", Order.Ascending}})
in
    Sorted"""

DIM_STEP_M = """let
    A = Table.SelectColumns(OpenTasks, {"Step"}),
    B = Table.SelectColumns(Completed, {"Step"}),
    U = Table.Distinct(Table.Combine({A, B})),
    NoNull = Table.SelectRows(U, each [Step] <> null),
    AddIntake = Table.AddColumn(NoNull, "Intake step", each List.Contains({"NB - Clear Submission","Mail - New Mail Review","Bind - Process Binder/Invoice","Mail - Indexing & Distribution"}, [Step]), type logical),
    AddHourTarget = Table.AddColumn(AddIntake, "Hour target", each if [Step] = "Bind - Process Binder/Invoice" then 8 else if [#"Intake step"] then 4 else null, Int64.Type),
    Sorted = Table.Sort(AddHourTarget, {{"Step", Order.Ascending}})
in
    Sorted"""

DIM_PERSON_M = f"""let
    {SCOPE_FN},
    A = Table.RenameColumns(Table.SelectColumns(OpenTasks, {{"Assigned to"}}), {{{{"Assigned to", "Person"}}}}),
    B = Table.RenameColumns(Table.SelectColumns(Completed, {{"Released by"}}), {{{{"Released by", "Person"}}}}),
    C = Table.RenameColumns(Table.SelectColumns(Compliance, {{"Assigned to"}}), {{{{"Assigned to", "Person"}}}}),
    U = Table.Distinct(Table.Combine({{A, B, C}})),
    NoNull = Table.SelectRows(U, each [Person] <> null),
    AddScope = Table.AddColumn(NoNull, "Staff scope", each fnScope([Person]), type text),
    AddDisplay = Table.AddColumn(AddScope, "Display name", each if Text.StartsWith([Person], "RPRO.") then Text.Range([Person], 5) else [Person], type text),
    AddVendor = Table.AddColumn(AddDisplay, "Is vendor", each [#"Staff scope"] = "Vendor", type logical),
    Sorted = Table.Sort(AddVendor, {{{{"Person", Order.Ascending}}}})
in
    Sorted"""

DIM_BAND_M = """let
    Source = #table(type table [#"Aging band" = text, #"Band order" = Int64.Type, #"Band label" = text, #"Band colour" = text],
        {{"0-7", 1, "0-7 days", "#3EBD5E"}, {"8-15", 2, "8-15 days", "#F3B921"}, {"16-30", 3, "16-30 days", "#FF8A00"},
         {"31-60", 4, "31-60 days", "#E8702A"}, {"61-90", 5, "61-90 days", "#D02D4F"}, {"90+", 6, "Over 90 days", "#8B1E3F"}, {"Unknown", 7, "Unknown", "#8A949C"}})
in
    Source"""

# ------------------------------------------------------------ TMDL writers
def column(name, dtype, src=None, hidden=False, sort_by=None, fmt=None, summ="none", key=False):
    s = f"\tcolumn {q(name)}\n\t\tdataType: {dtype}\n"
    if key: s += "\t\tisKey\n"
    if hidden: s += "\t\tisHidden\n"
    if fmt: s += f"\t\tformatString: {fmt}\n"
    s += f"\t\tlineageTag: {lt()}\n"
    if sort_by: s += f"\t\tsortByColumn: {q(sort_by)}\n"
    s += f"\t\tsummarizeBy: {summ}\n\t\tsourceColumn: {src or name}\n\n\t\tannotation SummarizationSetBy = User\n\n"
    return s

def table(name, cols, m, hidden=False, desc=None):
    s = f"table {q(name)}\n"
    if hidden: s += "\tisHidden\n"
    s += f"\tlineageTag: {lt()}\n\n"
    for c in cols: s += c
    s += f"\tpartition {q(name)} = m\n\t\tmode: import\n\t\tsource =\n"
    s += ind(m, 4) + "\n\n"
    s += "\tannotation PBI_ResultType = Table\n"
    return s

T = {}
T["OpenTasks"] = table("OpenTasks", [
    column("File number", "string"), column("Policy number", "string"), column("Insured", "string"), column("Team", "string"),
    column("Department", "string"), column("Brand", "string"), column("Workflow", "string"), column("Step", "string"),
    column("Assigned to", "string"), column("From user", "string"), column("Account executive", "string"), column("CSR", "string"),
    column("Agent name", "string"), column("Status", "string"), column("Age (days)", "int64", fmt="0"), column("Days since available", "int64", fmt="0"),
    column("SLA source (days)", "int64", fmt="0", hidden=True), column("Source aging bucket", "string", hidden=True),
    column("SLA (days)", "int64", fmt="0"), column("Scheduled", "boolean"), column("Out of service", "boolean"), column("Service", "string"),
    column("Aging band", "string"), column("Over 30 days", "boolean"), column("Over 90 days", "boolean"), column("Staff scope", "string"),
    column("Line of business", "string"), column("Renewal stage", "string", sort_by="Renewal stage order"), column("Renewal stage order", "int64", hidden=True),
    column("In renewal pipeline", "boolean"), column("Date initiated", "dateTime", fmt="dd mmm yyyy"), column("Available date", "dateTime", fmt="dd mmm yyyy"),
    column("Is unassigned", "boolean"), column("Received yesterday", "boolean"),
], OPEN_M)

T["Completed"] = table("Completed", [
    column("Workflow", "string"), column("Step", "string"), column("Released by", "string"), column("Hours in step", "double", fmt="#,0.0"),
    column("Turnaround (days)", "double", fmt="#,0.0"), column("SLA (days)", "int64", fmt="0"), column("Met SLA", "boolean"),
    column("Is rework", "boolean"), column("Release type", "string"), column("Hours band", "string", sort_by="Hours band order"),
    column("Hours band order", "int64", hidden=True), column("Release date", "dateTime", fmt="dd mmm yyyy"), column("Release id", "int64", hidden=True),
], COMPLETED_M)

T["Compliance"] = table("Compliance", [
    column("File number", "string"), column("File name", "string"), column("State", "string"), column("UA", "string"), column("Assigned to", "string"),
    column("Team", "string"), column("Days past due", "int64", fmt="0"), column("Age (days)", "int64", fmt="0"), column("Due band code", "string", hidden=True),
    column("Note", "string"), column("Carrier", "string"), column("Due band", "string", sort_by="Due band order"), column("Due band order", "int64", hidden=True),
    column("Fining state", "boolean"), column("Aging band", "string"), column("Over 30 days", "boolean"), column("Due date", "dateTime", fmt="dd mmm yyyy"),
    column("Date initiated", "dateTime", fmt="dd mmm yyyy"), column("Filing state", "string"),
], COMPLIANCE_M)

T["Dim Team"] = table("Dim Team", [column("Team", "string", key=True)], DIM_TEAM_M)
T["Dim Workflow"] = table("Dim Workflow", [column("Workflow", "string", key=True)], DIM_WORKFLOW_M)
T["Dim Step"] = table("Dim Step", [column("Step", "string", key=True), column("Intake step", "boolean"), column("Hour target", "int64", fmt="0")], DIM_STEP_M)
T["Dim Person"] = table("Dim Person", [column("Person", "string", key=True), column("Staff scope", "string"), column("Display name", "string"), column("Is vendor", "boolean")], DIM_PERSON_M)
T["Dim Aging Band"] = table("Dim Aging Band", [column("Aging band", "string", key=True, sort_by="Band order"), column("Band order", "int64", hidden=True), column("Band label", "string", sort_by="Band order"), column("Band colour", "string", hidden=True)], DIM_BAND_M)

# ------------------------------------------------------------ measures
M = []  # (name, dax, format, folder)
def m(name, dax, fmt=None, folder=None, desc=None):
    M.append((name, dax, fmt, folder, desc))

PCT = "0.0%;-0.0%;0.0%"
N0 = "#,0"
# Work on hand
m("Open items (all)", "COUNTROWS ( OpenTasks )", N0, "Work on hand", "Every open task row, including work scheduled ahead.")
m("Work on hand", "CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = FALSE () )", N0, "Work on hand", "Open tasks available to be worked now (scheduled-ahead work excluded).")
m("Scheduled (not yet available)", "CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = TRUE () )", N0, "Work on hand")
m("Files on hand", "CALCULATE ( DISTINCTCOUNT ( OpenTasks[File number] ), OpenTasks[Scheduled] = FALSE () )", N0, "Work on hand")
m("Out of service", "CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Out of service] = TRUE () )", N0, "Work on hand", "Work on hand older than its step service level.")
m("Within service", "[Work on hand] - [Out of service]", N0, "Work on hand")
m("Out of service %", "DIVIDE ( [Out of service], [Work on hand] )", PCT, "Work on hand")
m("Oldest item (days)", "CALCULATE ( MAX ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )", "0", "Work on hand")
m("Median age (days)", "CALCULATE ( MEDIAN ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )", "0.0", "Work on hand")
m("Over 30 days", "CALCULATE ( [Work on hand], OpenTasks[Over 30 days] = TRUE () )", N0, "Work on hand")
m("Over 90 days", "CALCULATE ( [Work on hand], OpenTasks[Over 90 days] = TRUE () )", N0, "Work on hand")
m("Over 90 days %", "DIVIDE ( [Over 90 days], [Work on hand] )", PCT, "Work on hand")
m("Share of work on hand", "DIVIDE ( [Work on hand], CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Aging Band' ), REMOVEFILTERS ( OpenTasks[Aging band] ) ) )", PCT, "Work on hand")
m("Received yesterday", "CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Received yesterday] = TRUE () )", N0, "Work on hand")
m("Service status", 'SWITCH ( TRUE (), ISBLANK ( [Out of service %] ), BLANK (), [Out of service %] <= Thresholds[Green max], "Green", [Out of service %] <= Thresholds[Amber max], "Amber", "Red" )', None, "Status")
m("Service status colour", 'SWITCH ( [Service status], "Green", "#3EBD5E", "Amber", "#F3B921", "Red", "#D02D4F", "#8A949C" )', None, "Status")
m("Service status icon", 'SWITCH ( [Service status], "Green", UNICHAR ( 9679 ) & " Green", "Amber", UNICHAR ( 9679 ) & " Amber", "Red", UNICHAR ( 9679 ) & " Red", BLANK () )', None, "Status")
m("Work on hand subtitle", 'FORMAT ( [Files on hand], "#,0" ) & " files  |  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d  |  " & FORMAT ( [Over 30 days], "#,0" ) & " over 30 d"', None, "Status")
m("Out of service subtitle", 'FORMAT ( [Out of service], "#,0" ) & " of " & FORMAT ( [Work on hand], "#,0" ) & " available items past service level"', None, "Status")
# Unassigned
m("Unassigned items", "CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )", N0, "Unassigned")
m("Unassigned files", "CALCULATE ( [Files on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )", N0, "Unassigned")
m("Unassigned over 30 days", "CALCULATE ( [Over 30 days], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )", N0, "Unassigned")
m("Unassigned out of service", "CALCULATE ( [Out of service], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )", N0, "Unassigned")
m("Unassigned out of service %", "DIVIDE ( [Unassigned out of service], [Unassigned items] )", PCT, "Unassigned")
m("Unassigned oldest (days)", "CALCULATE ( [Oldest item (days)], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )", "0", "Unassigned")
# Renewal
m("Renewals in pipeline", "CALCULATE ( [Work on hand], OpenTasks[In renewal pipeline] = TRUE () )", N0, "Renewal pipeline")
m("Share of renewals", "DIVIDE ( [Renewals in pipeline], CALCULATE ( [Renewals in pipeline], REMOVEFILTERS ( OpenTasks[Renewal stage] ) ) )", PCT, "Renewal pipeline")
m("Not yet quoted", 'CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not yet quoted" )', N0, "Renewal pipeline")
m("Quoted - with agent", 'CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Quoted - with agent" )', N0, "Renewal pipeline")
m("Bound - awaiting issue", 'CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Bound - awaiting issue" )', N0, "Renewal pipeline")
m("Not renewing", 'CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not renewing" )', N0, "Renewal pipeline")
m("Not quoted %", "DIVIDE ( [Not yet quoted], [Renewals in pipeline] )", PCT, "Renewal pipeline")
m("Renewal stage subtitle", 'FORMAT ( [Share of renewals], "0%" ) & " of renewals  |  " & FORMAT ( [Out of service], "#,0" ) & " out of service  |  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d"', None, "Renewal pipeline")
# Completed
m("Completed yesterday", "COUNTROWS ( Completed )", N0, "Completed", "Release/Kill actions on the day before the snapshot. Release = completed.")
m("Met SLA on completion", "CALCULATE ( COUNTROWS ( Completed ), Completed[Met SLA] = TRUE () )", N0, "Completed")
m("Within SLA on completion %", "DIVIDE ( [Met SLA on completion], [Completed yesterday] )", PCT, "Completed")
m("Median turnaround (days)", "MEDIAN ( Completed[Turnaround (days)] )", "0.0", "Completed")
m("Average turnaround (days)", "AVERAGE ( Completed[Turnaround (days)] )", "0.0", "Completed")
m("Median hours in step", "MEDIAN ( Completed[Hours in step] )", "0.0", "Completed")
m("Median time in step", 'VAR h = [Median hours in step] RETURN IF ( ISBLANK ( h ), BLANK (), IF ( h < 24, FORMAT ( h, "0.0" ) & " h", FORMAT ( h / 24, "0.0" ) & " d" ) )', None, "Completed")
m("Rework released", "CALCULATE ( COUNTROWS ( Completed ), Completed[Is rework] = TRUE () )", N0, "Completed")
m("Production released", "[Completed yesterday] - [Rework released]", N0, "Completed")
m("Rework rate", "DIVIDE ( [Rework released], [Completed yesterday] )", PCT, "Completed")
m("Within hour target", "SUMX ( Completed, IF ( Completed[Hours in step] <= RELATED ( 'Dim Step'[Hour target] ), 1, 0 ) )", N0, "Completed")
m("Within hour target %", "DIVIDE ( [Within hour target], [Completed yesterday] )", PCT, "Completed")
# Compliance
m("Open filings", "COUNTROWS ( Compliance )", N0, "Compliance")
m("Past due", 'CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "past" )', N0, "Compliance")
m("Past due - fining states", "CALCULATE ( [Past due], Compliance[Fining state] = TRUE () )", N0, "Compliance")
m("Past due and over 30 days (stuck)", "CALCULATE ( [Past due], Compliance[Over 30 days] = TRUE () )", N0, "Compliance")
m("Due within 14 days", 'CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "red" )', N0, "Compliance")
m("Due in 15-30 days", 'CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "amber" )', N0, "Compliance")
m("On track", 'CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "green" )', N0, "Compliance")
m("Filings over 30 days old", "CALCULATE ( COUNTROWS ( Compliance ), Compliance[Over 30 days] = TRUE () )", N0, "Compliance")
m("Oldest past due (days)", 'CALCULATE ( MAX ( Compliance[Days past due] ), Compliance[Due band code] = "past" )', "+0;-0;0", "Compliance")
m("Compliance status", 'IF ( [Past due] > 0, "Past due", IF ( [Due within 14 days] > 0, "Due within 14 days", "On track" ) )', None, "Compliance")
m("Fining state flag", 'IF ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Fining state] = TRUE () ) > 0, "FINES", "" )', None, "Compliance")

def measures_table():
    s = "table '_Measures'\n\tlineageTag: " + lt() + "\n\n"
    for name, dax, fmt, folder, desc in M:
        safe = name
        if desc: s += f"\t/// {desc}\n"
        if "\n" in dax:
            s += f"\tmeasure {q(safe)} =\n" + ind(dax, 3) + "\n"
        else:
            s += f"\tmeasure {q(safe)} = {dax}\n"
        if fmt: s += f"\t\tformatString: {fmt}\n"
        if folder: s += f"\t\tdisplayFolder: {folder}\n"
        s += f"\t\tlineageTag: {lt()}\n\n"
    s += "\tcolumn 'Measure key'\n\t\tdataType: int64\n\t\tisHidden\n\t\tlineageTag: " + lt() + "\n\t\tsummarizeBy: none\n\t\tsourceColumn: Measure key\n\n\t\tannotation SummarizationSetBy = User\n\n"
    s += "\tpartition '_Measures' = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n\t\t\t\t    Source = #table(type table [#\"Measure key\" = Int64.Type], {{1}})\n\t\t\t\tin\n\t\t\t\t    Source\n\n\tannotation PBI_ResultType = Table\n"
    return s
T["_Measures"] = measures_table()

# Thresholds (calculated table with service thresholds exposed to measures)
T["Thresholds"] = ("table Thresholds\n\tisHidden\n\tlineageTag: " + lt() + "\n\n"
    + column("Green max", "double", fmt="0%") + column("Amber max", "double", fmt="0%")
    + "\tpartition Thresholds = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n\t\t\t\t    Source = #table(type table [#\"Green max\" = number, #\"Amber max\" = number], {{Green_Max_OutOfService, Amber_Max_OutOfService}})\n\t\t\t\tin\n\t\t\t\t    Source\n\n\tannotation PBI_ResultType = Table\n")

# measures reference Thresholds[Green max] as a scalar: use a measure wrapper instead of column ref
# patch: replace Thresholds[Green max] / [Amber max] in DAX with MAX() over hidden table
for i, (name, dax, fmt, folder, desc) in enumerate(M):
    dax = dax.replace("Thresholds[Green max]", "MAX ( Thresholds[Green max] )").replace("Thresholds[Amber max]", "MAX ( Thresholds[Amber max] )")
    M[i] = (name, dax, fmt, folder, desc)
T["_Measures"] = measures_table()

for name, text in T.items():
    w(os.path.join(TBL, f"{name}.tmdl"), text)

# ------------------------------------------------------------ expressions
EXPR = f"""expression DataPath = "C:\\Data\\SPG_Dashboard_Mockup_Data.xlsx" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Text

expression SnapshotDate = #date(2026, 9, 16) meta [IsParameterQuery=true, Type="Date", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Date

expression SLA_Cap_Days = 60 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Number

expression Fining_States = "NY" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Text

expression Green_Max_OutOfService = 0.15 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Number

expression Amber_Max_OutOfService = 0.30 meta [IsParameterQuery=true, Type="Number", IsParameterQueryRequired=true]
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Number

expression SPG_Workbook =
\t\tlet
\t\t    Binary = if Text.StartsWith(Text.Lower(DataPath), "http") then Web.Contents(DataPath) else File.Contents(DataPath),
\t\t    Source = Excel.Workbook(Binary, null, true)
\t\tin
\t\t    Source
\tlineageTag: {lt()}

\tannotation PBI_ResultType = Table
"""
w(os.path.join(DEF, "expressions.tmdl"), EXPR)

# ------------------------------------------------------------ relationships
RELS = [
    ("OpenTasks", "Team", "Dim Team", "Team"),
    ("Compliance", "Team", "Dim Team", "Team"),
    ("OpenTasks", "Workflow", "Dim Workflow", "Workflow"),
    ("Completed", "Workflow", "Dim Workflow", "Workflow"),
    ("OpenTasks", "Step", "Dim Step", "Step"),
    ("Completed", "Step", "Dim Step", "Step"),
    ("OpenTasks", "Assigned to", "Dim Person", "Person"),
    ("Completed", "Released by", "Dim Person", "Person"),
    ("Compliance", "Assigned to", "Dim Person", "Person"),
    ("OpenTasks", "Aging band", "Dim Aging Band", "Aging band"),
    ("Compliance", "Aging band", "Dim Aging Band", "Aging band"),
]
r = ""
for ft, fc, tt, tc in RELS:
    r += f"relationship {uuid.uuid4()}\n\tfromColumn: {q(ft)}.{q(fc)}\n\ttoColumn: {q(tt)}.{q(tc)}\n\n"
w(os.path.join(DEF, "relationships.tmdl"), r)

# ------------------------------------------------------------ model / database / culture
order = ["DataPath", "SnapshotDate", "SLA_Cap_Days", "Fining_States", "Green_Max_OutOfService", "Amber_Max_OutOfService", "SPG_Workbook",
         "OpenTasks", "Completed", "Compliance", "Dim Team", "Dim Workflow", "Dim Step", "Dim Person", "Dim Aging Band", "Thresholds", "_Measures"]
model = ("model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
         + "annotation PBI_QueryOrder = " + json.dumps(order) + "\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n\n"
         + "annotation PBIDesktopVersion = 2.138.1452.0 (25.02)\n\n"
         + "".join(f"ref table {q(t)}\n" for t in order[7:]) + "\nref cultureInfo en-US\n")
w(os.path.join(DEF, "model.tmdl"), model)
w(os.path.join(DEF, "database.tmdl"), "database\n\tcompatibilityLevel: 1601\n")
w(os.path.join(DEF, "cultures", "en-US.tmdl"), "cultureInfo en-US\n\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  \"Version\": \"1.0.0\",\n\t\t\t  \"Language\": \"en-US\"\n\t\t\t}\n\t\tcontentType: json\n")
w(os.path.join(SM, "definition.pbism"), json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.0", "settings": {}}, indent=2))
_sid = stable_logical_id(os.path.join(SM, ".platform"))
w(os.path.join(SM, ".platform"), json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "SemanticModel", "displayName": "SPG Operational Dashboard"}, "config": {"version": "2.0", "logicalId": _sid}}, indent=2))
w(os.path.join(SM, "diagramLayout.json"), json.dumps({"version": "1.1.0", "diagrams": [{"ordinal": 0, "scrollPosition": {"x": 0, "y": 0}, "nodes": [], "name": "All tables", "zoomValue": 100, "pinKeyFieldsToTop": False, "showExtraHeaderInfo": False, "hideKeyFieldsWhenCollapsed": False, "tablesLocked": False}], "selectedDiagram": "All tables", "defaultDiagram": "All tables"}, indent=2))
print("model written:", len(M), "measures,", len(T), "tables")
