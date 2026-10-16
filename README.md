# SPG Operational Dashboard — Power BI Project (PBIP / TMDL / PBIR)

Power BI implementation of the **SPG Operational Dashboard** mockup for Aurorras / Monarch. The semantic model is stored as
TMDL and the report in the enhanced PBIR format, so the whole project is source‑controllable and deploys to a Fabric
workspace through Git integration.

```
SPG Operational Dashboard.pbip                  ← open this in Power BI Desktop
SPG Operational Dashboard.SemanticModel/        ← TMDL semantic model (tables, M queries, relationships, 56 DAX measures)
SPG Operational Dashboard.Report/               ← PBIR report (7 pages, 101 visuals, SPG theme)
data/SPG_Dashboard_Mockup_Data.xlsx             ← source extract (16 Sep 2026 refresh)
docs/measures.md                                ← every measure with its DAX
tools/gen_model.py, tools/gen_report.py         ← generators used to build the project (optional, for regeneration)
```

## 1. Open in Power BI Desktop

1. Power BI Desktop (mid‑2025 or newer). Under **File → Options → Preview features** enable
   *Power BI Project (.pbip) save option* and *Store reports using enhanced metadata format (PBIR)*, then restart.
2. Clone the repo and open `SPG Operational Dashboard.pbip`.
3. Desktop will ask for the **DataPath** parameter the first time it refreshes. Point it at the Excel file
   (e.g. `C:\repos\spg-operational-dashboard\data\SPG_Dashboard_Mockup_Data.xlsx`) or a SharePoint/OneDrive URL to the
   same workbook — the query uses `Web.Contents` when the path starts with `http`, otherwise `File.Contents`.
4. **Home → Refresh**. The model loads 12,119 open tasks, 2,722 completed actions and 685 compliance filings.
5. Save. Desktop writes its own cache files under `.pbi/` — those are git‑ignored.

> The project was authored outside Desktop and has not yet been round‑tripped through it. On first open, Desktop may
> report a validation message on an individual visual; the fix is to open that visual and re‑save, which rewrites the
> container in Desktop's own canonical form. Commit the saved result so the repo becomes Desktop‑canonical.

## 2. Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `DataPath` | GitHub raw URL of `data/SPG_Dashboard_Mockup_Data.xlsx` (POC); move to Lakehouse for production | Local path or SharePoint/OneDrive URL of the workbook |
| `SnapshotDate` | 2026‑09‑16 | Date the extract was taken; dates are reconstructed from the age columns |
| `SLA_Cap_Days` | 60 | Placeholder SLA ceiling (matches the mockup) until the business SLA sheet arrives |
| `Fining_States` | `NY` | Comma‑separated list of states that fine for late filings |
| `Green_Max_OutOfService` | 0.15 | Out‑of‑service share up to which status is Green |
| `Amber_Max_OutOfService` | 0.30 | …up to which status is Amber; above is Red |

Change them in Desktop under **Transform data → Edit parameters**, or after publishing under
**Semantic model settings → Parameters** in the service.

## 3. Data model

Star schema with three facts and five shared dimensions, all built in Power Query from the workbook:

- **OpenTasks** — one row per open task. Adds `SLA (days)`, `Scheduled` (available date in the future), `Out of service`
  (age > SLA and not scheduled), `Service`, six‑band `Aging band`, `Renewal stage` (derived from the step name),
  `Staff scope` (Internal / Vendor / Shared queue), `Line of business`, reconstructed `Date initiated` / `Available date`.
- **Completed** — release/kill actions on the day before the snapshot. Adds `Is rework` (revision/re‑quote/re‑issue steps),
  `Release type`, `Hours band` for the intake‑step hour analysis.
- **Compliance** — compliance document reviews. Adds `Due band` (Past due / Due within 14 days / Due in 15–30 days / On track),
  `Fining state`, `Aging band`, reconstructed `Due date`.
- **Dim Team, Dim Workflow, Dim Step, Dim Person, Dim Aging Band** — conformed dimensions so that one slicer filters all facts.
  `Dim Step` carries the `Intake step` flag and `Hour target` used by the hours analysis. `Dim Person` carries `Staff scope`
  and the `Display name` (vendor prefix stripped).
- **_Measures** — all DAX, in display folders *Work on hand, Status, Unassigned, Renewal pipeline, Completed, Compliance*.
  See `docs/measures.md`. **Thresholds** is a hidden one‑row table exposing the RAG parameters to DAX.

Relationships: facts → dimensions, many‑to‑one, single direction.

## 4. Report pages (1440 × 820, built from mockup v15)

Every page carries the mockup's page title and subtitle and the content grid in the mockup's proportions (page navigation
is the service's own Pages list). Slicers are **not** on the canvas — as in
the mockup's slide-out pane, each page's slicer set lives in the **Filters pane** (page-level filter cards: Team, Workflow,
Process step, Aging bucket, Date initiated, Line of business, Division, Assigned to, Account executive, CSR, Agent, Staff scope …).
Every KPI tile is a card (label + number) with the mockup's small grey subtitle line (static text or a `Sub: …` measure).

| Page | What it shows (mirrors mockup v15) |
|---|---|
| **Service Overview** | Hero *Work on hand out of service* (number and ● status coloured by RAG via `Service status colour`); six KPI tiles with subtitles; Service by process (RAG status column, workflows with ≥ 20 items); out‑of‑service bar with drill Team › Workflow › Step › Individual, bars RAG‑coloured; work on hand by age; top out‑of‑service steps (with median time in step); turnaround by process; intake steps measured in hours |
| **Work On Hand** | Work on hand / out‑of‑service tiles; **aging‑band strip** of six tiles (count + share of on hand — click one to cross‑filter the page); decomposition tree Division › Team › Workflow › Step › Individual; work on hand by individual stacked by age; matrix with aging buckets; oldest‑first table |
| **Renewal Pipeline** | Page‑filtered to Renewal. Four stage tiles with *share · out of service · oldest* subtitles; stage mix by team and by account executive; stage by aging bucket; not‑yet‑quoted by step; oldest unquoted renewals; footnote on stage derivation |
| **Team Scorecard** | Staff‑scope and Individual slicers; seven person tiles (out‑of‑service tile shows *team* share, Status tile is RAG text); on hand by step; age profile; completed yesterday; Team ranked by out of service (with team total row); released yesterday by person |
| **Management** | Six unassigned / quality tiles; unassigned by workflow and by team (stacked by age); production vs rework; rework by step; unassigned oldest first |
| **Compliance** | Six deadline tiles (past‑due tile shows the *stuck* count); by state with FINES flag; by associate stacked by due band; age from date initiated; action list (past due and due within 14 days). Pane slicers: State, Team, Has it (UA), Fines when late |
| **Task list** | Drill‑through target: **Back** button, drill‑through context line (tasks · files / out of service / oldest / age mix), 20‑column table; *Export data* from the visual header |

Right‑click any Team, Workflow, Step, Individual, Renewal stage or Aging band → **Drill through → Task list**.

### Known gaps vs the mockup (data or platform)
- *Turnaround by process* uses yesterday's releases (`Completed`); the mockup's May‑2025 history is not in the extract.
- The *Division* filter has one value (Wholesale) — the extract covers the Monarch/Wholesale teams only.
- The *Compliance workflow* slicer needs a workflow column in the Compliance extract; not present yet.
- The data‑bar column in *Service by process* and the segmented scope buttons on the Scorecard are rendered as a sortable % column and a dropdown slicer respectively.

## 5. Publish to the Power BI service

**Option A — Desktop publish.** Open the .pbip, refresh, **Home → Publish**, choose the workspace. Both the semantic model
and the report are published. Set the `DataPath` parameter in the service to a SharePoint/OneDrive URL (or configure a
gateway for a local path) and schedule refresh.

**Option B — Fabric Git integration (recommended for this repo).**
1. Workspace must be on Fabric or Premium capacity. Open **Workspace settings → Git integration**.
2. Provider: GitHub. Connect with the GitHub account, select this repository and branch `main`, directory `/`.
3. Fabric detects the `SPG Operational Dashboard.SemanticModel` and `.Report` folders via their `.platform` files and
   creates both items in the workspace. Each commit to `main` shows as an incoming change; click **Update all**.
4. In the service, open the semantic model settings, set the `DataPath` parameter to the SharePoint/OneDrive URL of the
   workbook and set credentials; then refresh. Local `C:\` paths cannot be refreshed from the service without a gateway.

`data/`, `docs/` and `tools/` are ignored by Fabric (not Fabric items) and are safe to keep in the repo.

## 6. Regenerating from the generators

```
PBIP_ROOT=./ python3 tools/gen_model.py
PBIP_ROOT=./ python3 tools/gen_report.py
```
The generators are the source of truth for the initial build only; once the project has been saved from Power BI
Desktop, treat Desktop as the editor and retire the generators (or keep them only for the semantic model).
