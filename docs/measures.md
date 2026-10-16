# DAX measures (table `_Measures`)

| Folder | Measure | DAX | Format |
|---|---|---|---|
| Work on hand | `Open items (all)` | `COUNTROWS ( OpenTasks )` | #,0 |
| Work on hand | `Work on hand` | `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = FALSE () )` | #,0 |
| Work on hand | `Scheduled (not yet available)` | `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Scheduled] = TRUE () )` | #,0 |
| Work on hand | `Files on hand` | `CALCULATE ( DISTINCTCOUNT ( OpenTasks[File number] ), OpenTasks[Scheduled] = FALSE () )` | #,0 |
| Work on hand | `Out of service` | `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Out of service] = TRUE () )` | #,0 |
| Work on hand | `Within service` | `[Work on hand] - [Out of service]` | #,0 |
| Work on hand | `Out of service %` | `DIVIDE ( [Out of service], [Work on hand] )` | 0.0%;-0.0%;0.0% |
| Work on hand | `Oldest item (days)` | `CALCULATE ( MAX ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )` | 0 |
| Work on hand | `Median age (days)` | `CALCULATE ( MEDIAN ( OpenTasks[Age (days)] ), OpenTasks[Scheduled] = FALSE () )` | 0.0 |
| Work on hand | `Over 30 days` | `CALCULATE ( [Work on hand], OpenTasks[Over 30 days] = TRUE () )` | #,0 |
| Work on hand | `Over 90 days` | `CALCULATE ( [Work on hand], OpenTasks[Over 90 days] = TRUE () )` | #,0 |
| Work on hand | `Over 90 days %` | `DIVIDE ( [Over 90 days], [Work on hand] )` | 0.0%;-0.0%;0.0% |
| Work on hand | `Share of work on hand` | `DIVIDE ( [Work on hand], CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Aging Band' ), REMOVEFILTERS ( OpenTasks[Aging band] ) ) )` | 0.0%;-0.0%;0.0% |
| Work on hand | `Received yesterday` | `CALCULATE ( COUNTROWS ( OpenTasks ), OpenTasks[Received yesterday] = TRUE () )` | #,0 |
| Status | `Service status` | `SWITCH ( TRUE (), ISBLANK ( [Out of service %] ), BLANK (), [Out of service %] <= MAX ( Thresholds[Green max] ), "Green", [Out of service %] <= MAX ( Thresholds[Amber max] ), "Amber", "Red" )` |  |
| Status | `Service status colour` | `SWITCH ( [Service status], "Green", "#3EBD5E", "Amber", "#F3B921", "Red", "#D02D4F", "#8A949C" )` |  |
| Status | `Service status icon` | `SWITCH ( [Service status], "Green", UNICHAR ( 9679 ) & " Green", "Amber", UNICHAR ( 9679 ) & " Amber", "Red", UNICHAR ( 9679 ) & " Red", BLANK () )` |  |
| Status | `Work on hand subtitle` | `FORMAT ( [Files on hand], "#,0" ) & " files  |  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d  |  " & FORMAT ( [Over 30 days], "#,0" ) & " over 30 d"` |  |
| Status | `Out of service subtitle` | `FORMAT ( [Out of service], "#,0" ) & " of " & FORMAT ( [Work on hand], "#,0" ) & " available items past service level"` |  |
| Unassigned | `Unassigned items` | `CALCULATE ( [Work on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )` | #,0 |
| Unassigned | `Unassigned files` | `CALCULATE ( [Files on hand], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )` | #,0 |
| Unassigned | `Unassigned over 30 days` | `CALCULATE ( [Over 30 days], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )` | #,0 |
| Unassigned | `Unassigned out of service` | `CALCULATE ( [Out of service], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )` | #,0 |
| Unassigned | `Unassigned out of service %` | `DIVIDE ( [Unassigned out of service], [Unassigned items] )` | 0.0%;-0.0%;0.0% |
| Unassigned | `Unassigned oldest (days)` | `CALCULATE ( [Oldest item (days)], REMOVEFILTERS ( 'Dim Person' ), OpenTasks[Is unassigned] = TRUE () )` | 0 |
| Renewal pipeline | `Renewals in pipeline` | `CALCULATE ( [Work on hand], OpenTasks[In renewal pipeline] = TRUE () )` | #,0 |
| Renewal pipeline | `Share of renewals` | `DIVIDE ( [Renewals in pipeline], CALCULATE ( [Renewals in pipeline], REMOVEFILTERS ( OpenTasks[Renewal stage] ) ) )` | 0.0%;-0.0%;0.0% |
| Renewal pipeline | `Not yet quoted` | `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not yet quoted" )` | #,0 |
| Renewal pipeline | `Quoted - with agent` | `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Quoted - with agent" )` | #,0 |
| Renewal pipeline | `Bound - awaiting issue` | `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Bound - awaiting issue" )` | #,0 |
| Renewal pipeline | `Not renewing` | `CALCULATE ( [Renewals in pipeline], OpenTasks[Renewal stage] = "Not renewing" )` | #,0 |
| Renewal pipeline | `Not quoted %` | `DIVIDE ( [Not yet quoted], [Renewals in pipeline] )` | 0.0%;-0.0%;0.0% |
| Renewal pipeline | `Renewal stage subtitle` | `FORMAT ( [Share of renewals], "0%" ) & " of renewals  |  " & FORMAT ( [Out of service], "#,0" ) & " out of service  |  oldest " & FORMAT ( [Oldest item (days)], "0" ) & " d"` |  |
| Completed | `Completed yesterday` | `COUNTROWS ( Completed )` | #,0 |
| Completed | `Met SLA on completion` | `CALCULATE ( COUNTROWS ( Completed ), Completed[Met SLA] = TRUE () )` | #,0 |
| Completed | `Within SLA on completion %` | `DIVIDE ( [Met SLA on completion], [Completed yesterday] )` | 0.0%;-0.0%;0.0% |
| Completed | `Median turnaround (days)` | `MEDIAN ( Completed[Turnaround (days)] )` | 0.0 |
| Completed | `Average turnaround (days)` | `AVERAGE ( Completed[Turnaround (days)] )` | 0.0 |
| Completed | `Median hours in step` | `MEDIAN ( Completed[Hours in step] )` | 0.0 |
| Completed | `Median time in step` | `VAR h = [Median hours in step] RETURN IF ( ISBLANK ( h ), BLANK (), IF ( h < 24, FORMAT ( h, "0.0" ) & " h", FORMAT ( h / 24, "0.0" ) & " d" ) )` |  |
| Completed | `Rework released` | `CALCULATE ( COUNTROWS ( Completed ), Completed[Is rework] = TRUE () )` | #,0 |
| Completed | `Production released` | `[Completed yesterday] - [Rework released]` | #,0 |
| Completed | `Rework rate` | `DIVIDE ( [Rework released], [Completed yesterday] )` | 0.0%;-0.0%;0.0% |
| Completed | `Within hour target` | `SUMX ( Completed, IF ( Completed[Hours in step] <= RELATED ( 'Dim Step'[Hour target] ), 1, 0 ) )` | #,0 |
| Completed | `Within hour target %` | `DIVIDE ( [Within hour target], [Completed yesterday] )` | 0.0%;-0.0%;0.0% |
| Compliance | `Open filings` | `COUNTROWS ( Compliance )` | #,0 |
| Compliance | `Past due` | `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "past" )` | #,0 |
| Compliance | `Past due - fining states` | `CALCULATE ( [Past due], Compliance[Fining state] = TRUE () )` | #,0 |
| Compliance | `Past due and over 30 days (stuck)` | `CALCULATE ( [Past due], Compliance[Over 30 days] = TRUE () )` | #,0 |
| Compliance | `Due within 14 days` | `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "red" )` | #,0 |
| Compliance | `Due in 15-30 days` | `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "amber" )` | #,0 |
| Compliance | `On track` | `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Due band code] = "green" )` | #,0 |
| Compliance | `Filings over 30 days old` | `CALCULATE ( COUNTROWS ( Compliance ), Compliance[Over 30 days] = TRUE () )` | #,0 |
| Compliance | `Oldest past due (days)` | `CALCULATE ( MAX ( Compliance[Days past due] ), Compliance[Due band code] = "past" )` | +0;-0;0 |
| Compliance | `Compliance status` | `IF ( [Past due] > 0, "Past due", IF ( [Due within 14 days] > 0, "Due within 14 days", "On track" ) )` |  |
| Compliance | `Fining state flag` | `IF ( CALCULATE ( COUNTROWS ( Compliance ), Compliance[Fining state] = TRUE () ) > 0, "FINES", "" )` |  |
