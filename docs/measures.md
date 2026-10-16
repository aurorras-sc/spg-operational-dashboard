# Measures
Generated from `_Measures.tmdl` by `tools/gen_model.py`. Folder · name · DAX.

## Work on hand
- **Open items (all)** — Every open task row, including work scheduled ahead.
  `COUNTROWS ( OpenTasks )`  (format `#,0`)
- **Work on hand** — Open tasks available to be worked now (scheduled-ahead work excluded).
  `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = FALSE () )`  (format `#,0`)
- **Scheduled (not yet available)**
  `COALESCE ( CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = TRUE () ), 0 )`  (format `#,0`)
- **Files on hand**
  `CALCULATE ( DISTINCTCOUNT ( OpenTasks[File number] ), OpenTasks[Scheduled] = FALSE () )`  (format `#,0`)
- **Out of service** — Work on hand older than its step service level.
  `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Out of service] = TRUE () )`  (format `#,0`)
- **Within service**
  `[Work on hand] - [Out of service]`  (format `#,0`)
- **Out of service %**
  `DIVIDE ( [Out of service], [Work on hand] )`  (format `0.0%;-0.0%;0.0%`)
- **Oldest item (days)**
  `CALCULATE ( MAX ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )`  (format `0`)
- **Median age (days)**
  `CALCULATE ( MEDIAN ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )`  (format `0.0`)
- **Over 30 days**
  `CALCULATE ( [Work on hand], OpenTasks[Over 30 days] = TRUE () )`  (format `#,0`)
- **Over 90 days**
  `COALESCE ( CALCULATE ( [Work on hand], OpenTasks[Over 90 days] = TRUE () ), 0 )`  (format `#,0`)
- **Over 90 days %**
  `DIVIDE ( [Over 90 days], [Work on hand] )`  (format `0.0%;-0.0%;0.0%`)
- **Share of work on hand**
  `DIVIDE ( [Work on hand], CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Aging Band' ), REMOVEFILTERS ( OpenTasks[Aging band] ) ) )`  (format `0.0%;-0.0%;0.0%`)
- **Received yesterday**
  `COALESCE ( CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Received yesterday] = TRUE () ), 0 )`  (format `#,0`)

## Status
- **Service status** — Green <= 15% out of service, Amber <= 30%, otherwise Red (thresholds to be confirmed by the business).
  `VAR p = [Out of service %] RETURN IF ( ISBLANK ( p ), BLANK (), IF ( p <= 0.15, "Green", IF ( p <= 0.30, "Amber", "Red" ) ) )`
- **Service status colour**
  `SWITCH ( [Service status], "Green", "#3EBD5E", "Amber", "#F3B921", "Red", "#D02D4F", "#8A949C" )`
- **Service status icon**
  `SWITCH ( [Service status], "Green", UNICHAR ( 9679 ) & " Green", "Amber", UNICHAR ( 9679 ) & " Amber", "Red", UNICHAR ( 9679 ) & " Red", BLANK () )`
- **Work on hand subtitle**
  `FORMAT ( [Files on hand], "#,0" ) & " files  ·  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d  ·  " & FORMAT ( [Over 30 days], "#,0" ) & " over 30 d"`
- **Out of service subtitle**
  `FORMAT ( [Out of service], "#,0" ) & " of " & FORMAT ( [Work on hand], "#,0" ) & " available items past service level"`
- **Team out of service %** — Out of service share of the whole team, ignoring the individual selected.
  `CALCULATE ( [Out of service %], REMOVEFILTERS ( 'Dim Person' ), REMOVEFILTERS ( OpenTasks[Assigned to] ) )`  (format `0.0%;-0.0%;0.0%`)

## Subtitles
- **Sub: files**
  `FORMAT ( [Files on hand], "#,0" ) & " files"`
- **Sub: files and scheduled**
  `FORMAT ( [Files on hand], "#,0" ) & " files  ·  " & FORMAT ( [Scheduled (not yet available)], "#,0" ) & " scheduled (not yet available)"`
- **Sub: out of service items**
  `FORMAT ( [Out of service], "#,0" ) & " items"`
- **Sub: out of service vs team**
  `FORMAT ( [Out of service], "#,0" ) & " items  ·  team " & FORMAT ( [Team out of service %], "0%" )`
- **Sub: over 90**
  `FORMAT ( [Over 90 days %], "0%" ) & " of work on hand  ·  " & FORMAT ( [Over 30 days], "#,0" ) & " over 30"`
- **Sub: unassigned**
  `"oldest " & FORMAT ( [Unassigned oldest (days)], "0" ) & " d  ·  " & FORMAT ( [Unassigned over 30 days], "#,0" ) & " over 30"`
- **Sub: unassigned files**
  `FORMAT ( [Unassigned files], "#,0" ) & " files"`
- **Sub: unassigned oldest**
  `"oldest " & FORMAT ( [Unassigned oldest (days)], "0" ) & " d"`
- **Sub: unassigned out of service**
  `FORMAT ( [Unassigned out of service], "#,0" ) & " items"`
- **Sub: band share**
  `FORMAT ( [Share of work on hand], "0%" ) & " of on hand"`
- **Sub: completed tasks**
  `FORMAT ( [Completed yesterday], "#,0" ) & " tasks  ·  release = completed"`
- **Context: tasks and files**
  `FORMAT ( [Work on hand], "#,0" ) & " tasks  ·  " & FORMAT ( [Files on hand], "#,0" ) & " files"`
- **Context: out of service**
  `FORMAT ( [Out of service], "#,0" ) & " out of service  ·  " & FORMAT ( [Out of service %], "0%" )`
- **Context: oldest**
  `"oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d"`
- **Context: age mix**
  `VAR b = ADDCOLUMNS ( SUMMARIZE ( 'Dim Aging Band', 'Dim Aging Band'[Band label], 'Dim Aging Band'[Band order] ), "@n", [Work on hand] ) RETURN CONCATENATEX ( FILTER ( b, [@n] > 0 ), 'Dim Aging Band'[Band label] & " " & FORMAT ( [@n], "#,0" ), "  ·  ", 'Dim Aging Band'[Band order], ASC )`

## Unassigned
- **Unassigned items**
  `COALESCE ( CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () ), 0 )`  (format `#,0`)
- **Unassigned files**
  `CALCULATE ( [Files on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )`  (format `#,0`)
- **Unassigned over 30 days**
  `COALESCE ( CALCULATE ( [Over 30 days], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () ), 0 )`  (format `#,0`)
- **Unassigned out of service**
  `COALESCE ( CALCULATE ( [Out of service], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () ), 0 )`  (format `#,0`)
- **Unassigned out of service %**
  `DIVIDE ( [Unassigned out of service], [Unassigned items] )`  (format `0.0%;-0.0%;0.0%`)
- **Unassigned oldest (days)**
  `CALCULATE ( [Oldest item (days)], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )`  (format `0`)

## Renewal pipeline
- **Renewals in pipeline**
  `CALCULATE ( [Work on hand], OpenTasks[In renewal pipeline] = TRUE () )`  (format `#,0`)
- **Share of renewals**
  `DIVIDE ( [Renewals in pipeline], CALCULATE ( [Renewals in pipeline], REMOVEFILTERS ( OpenTasks[Renewal stage] ) ) )`  (format `0.0%;-0.0%;0.0%`)
- **Not yet quoted**
  `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not yet quoted" )`  (format `#,0`)
- **Quoted - with agent**
  `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Quoted - with agent" )`  (format `#,0`)
- **Bound - awaiting issue**
  `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Bound - awaiting issue" )`  (format `#,0`)
- **Not renewing**
  `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not renewing" )`  (format `#,0`)
- **Not quoted %**
  `DIVIDE ( [Not yet quoted], [Renewals in pipeline] )`  (format `0.0%;-0.0%;0.0%`)
- **Renewal stage subtitle**
  `FORMAT ( [Share of renewals], "0%" ) & " of renewals  |  " & FORMAT ( [Out of service], "#,0" ) & " out of service  |  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d"`

## Completed
- **Completed yesterday** — Release/Kill actions on the day before the snapshot. Release = completed.
  `COALESCE ( COUNTROWS ( Completed ), 0 )`  (format `#,0`)
- **Met SLA on completion**
  `CALCULATE ( COUNTROWS ( Completed ), Completed[Met SLA] = TRUE () )`  (format `#,0`)
- **Within SLA on completion %**
  `DIVIDE ( [Met SLA on completion], [Completed yesterday] )`  (format `0.0%;-0.0%;0.0%`)
- **Median turnaround (days)**
  `MEDIAN ( Completed[Turnaround (days)] )`  (format `0.0`)
- **Average turnaround (days)**
  `AVERAGE ( Completed[Turnaround (days)] )`  (format `0.0`)
- **Median hours in step**
  `MEDIAN ( Completed[Hours in step] )`  (format `0.0`)
- **Median time in step**
  `VAR h = [Median hours in step] RETURN IF ( ISBLANK ( h ), BLANK (), IF ( h < 24, FORMAT ( h, "0.0" ) & " h", FORMAT ( h / 24, "0.0" ) & " d" ) )`
- **Rework released**
  `COALESCE ( CALCULATE ( COUNTROWS ( Completed ), Completed[Is rework] = TRUE () ), 0 )`  (format `#,0`)
- **Production released**
  `[Completed yesterday] - [Rework released]`  (format `#,0`)
- **Rework rate**
  `DIVIDE ( [Rework released], [Completed yesterday] )`  (format `0.0%;-0.0%;0.0%`)
- **Within hour target**
  `SUMX ( Completed, IF ( Completed[Hours in step] <= RELATED ( 'Dim Step'[Hour target] ), 1, 0 ) )`  (format `#,0`)
- **Within hour target %**
  `DIVIDE ( [Within hour target], [Completed yesterday] )`  (format `0.0%;-0.0%;0.0%`)

## Compliance
- **Open filings**
  `COUNTROWS ( Compliance )`  (format `#,0`)
- **Past due**
  `COALESCE ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "past" ), 0 )`  (format `#,0`)
- **Past due - fining states**
  `COALESCE ( CALCULATE ( [Past due], Compliance[Fining state] = TRUE () ), 0 )`  (format `#,0`)
- **Past due and over 30 days (stuck)**
  `CALCULATE ( [Past due], Compliance[Over 30 days] = TRUE () )`  (format `#,0`)
- **Due within 14 days**
  `COALESCE ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "red" ), 0 )`  (format `#,0`)
- **Due in 15-30 days**
  `COALESCE ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "amber" ), 0 )`  (format `#,0`)
- **On track**
  `COALESCE ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "green" ), 0 )`  (format `#,0`)
- **Filings over 30 days old**
  `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Over 30 days] = TRUE () )`  (format `#,0`)
- **Oldest past due (days)**
  `CALCULATE ( MAX ( Compliance[Days past due] ), Compliance[Due band code] = "past" )`  (format `+0;-0;0`)
- **Compliance status**
  `IF ( [Past due] > 0, "Past due", IF ( [Due within 14 days] > 0, "Due within 14 days", "On track" ) )`
- **Fining state flag**
  `IF ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Fining state] = TRUE () ) > 0, "FINES", "" )`
- **Filings in processing**
  `COALESCE ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[State] = "Processing" ), 0 )`  (format `#,0`)

## Subtitles
- **Sub: past due stuck**
  `FORMAT ( [Past due and over 30 days (stuck)], "#,0" ) & " of them also over 30 days old  —  stuck"`
- **Sub: open filings**
  `FORMAT ( [Filings over 30 days old], "#,0" ) & " over 30 days old" & IF ( [Filings in processing] > 0, "  ·  " & FORMAT ( [Filings in processing], "#,0" ) & " in processing", "" )`
