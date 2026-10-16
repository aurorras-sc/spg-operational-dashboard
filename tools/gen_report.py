"""Generate the SPG Operational Dashboard report in PBIR (enhanced report format)."""
import os, json, uuid, re

def stable_logical_id(platform_path):
    """Keep the Fabric logicalId stable across regenerations: Fabric identifies items by it."""
    try:
        return json.load(open(platform_path))["config"]["logicalId"]
    except Exception:
        return str(uuid.uuid4())

ROOT = os.environ.get("PBIP_ROOT", "/home/claude/repo")
RP = os.path.join(ROOT, "SPG Operational Dashboard.Report")
DEF = os.path.join(RP, "definition")
PAGES = os.path.join(DEF, "pages")
RES = os.path.join(RP, "StaticResources", "RegisteredResources")
os.makedirs(PAGES, exist_ok=True)

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
MEAS = "_Measures"
NAVY, ELEC, OK, AMBER, RED, DRED, MUTE, SUB = "#253746", "#0077C8", "#3EBD5E", "#F3B921", "#D02D4F", "#8E1B33", "#8A949C", "#5A6670"
BAND_COL = {"0-7": "#3EBD5E", "8-15": "#F3B921", "16-30": "#FF8A00", "31-60": "#E8702A", "61-90": "#D02D4F", "90+": "#8B1E3F", "Unknown": MUTE}
STAGE_COL = {"Not yet quoted": RED, "Quoted - with agent": "#FF8A00", "Bound - awaiting issue": OK, "Not renewing": MUTE}
DUE_COL = {"Past due": DRED, "Due within 14 days": RED, "Due in 15-30 days": AMBER, "On track": OK, "No due date": MUTE}
HOURS_COL = {"<= 2 h": OK, "2-4 h": "#F3B921", "4-24 h": "#FF8A00", "Over a day": RED}

def nid(): return uuid.uuid4().hex[:20]
def lit(v):
    if isinstance(v, bool): return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)): return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}
def col_solid(hexv): return {"solid": {"color": lit(hexv)}}
def col_measure(name): return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": MEAS}}, "Property": name}}}}}

# ---- fields
def C(entity, prop): return ("col", entity, prop)
def Mx(prop): return ("meas", MEAS, prop)
def fexpr(f):
    kind, ent, prop = f
    key = "Column" if kind == "col" else "Measure"
    return {key: {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}
def proj(f, name=None):
    kind, ent, prop = f
    p = {"field": fexpr(f), "queryRef": f"{ent}.{prop}", "nativeQueryRef": name or prop}
    if name: p["displayName"] = name
    return p
def sortdef(f, desc=True):
    return {"sort": [{"field": fexpr(f), "direction": "Descending" if desc else "Ascending"}], "isDefaultSort": True}

# ---- filters (visual / page level)
def cat_filter(f, values, exclude=False):
    kind, ent, prop = f
    cond = {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": prop}}],
                   "Values": [[{"Literal": {"Value": ("'" + v.replace("'", "''") + "'") if isinstance(v, str) else ("true" if v is True else "false" if v is False else str(v))}}] for v in values]}}
    if exclude: cond = {"Not": {"Expression": cond}}
    return {"name": nid(), "field": fexpr(f), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "s", "Entity": ent, "Type": 0}], "Where": [{"Condition": cond}]}}
def filterconfig(filters): return {"filters": filters}

# ---- visual container
def title_obj(text, size=11, color=NAVY, show=True):
    return {"title": [{"properties": {"show": lit(show), "text": lit(text), "fontSize": lit(size), "fontColor": col_solid(color), "bold": lit(True)}}]}

def container(vtype, x, y, w, h, z, roles=None, objects=None, title=None, sort=None, filters=None, extra=None, drill=True, vco=None):
    v = {"visualType": vtype}
    if roles is not None:
        qs = {}
        for role, fields in roles.items():
            if not fields: continue
            lst = [f if isinstance(f, dict) else proj(f) for f in fields]
            qs[role] = {"projections": lst}
        q = {"queryState": qs}
        if sort: q["sortDefinition"] = sort
        v["query"] = q
    if objects: v["objects"] = objects
    vcos = {}
    if title: vcos.update(title_obj(title) if isinstance(title, str) else title)
    if vco: vcos.update(vco)
    if vcos: v["visualContainerObjects"] = vcos
    if extra: v.update(extra)
    v["drillFilterOtherVisuals"] = drill
    c = {"$schema": f"{SCHEMA}/visualContainer/1.0.0/schema.json", "name": nid(),
         "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": v}
    if filters: c["filterConfig"] = filterconfig(filters)
    return c

# ---- visual builders
def textbox(x, y, w, h, z, runs, size=16, color=NAVY, bold=True):
    paras = [{"textRuns": [{"value": r, "textStyle": {"fontWeight": "bold" if bold else "normal", "fontSize": f"{size}pt", "color": color}} for r in runs]}]
    return container("textbox", x, y, w, h, z, objects={"general": [{"properties": {"paragraphs": paras}}]}, drill=False,
                     vco={"background": [{"properties": {"show": lit(False)}}]})

def card(x, y, w, h, z, measure, title, color=NAVY, size=26, color_measure=None, filters=None, label_size=9):
    obj = {"labels": [{"properties": {"color": col_measure(color_measure) if color_measure else col_solid(color), "fontSize": lit(size), "bold": lit(True)}}],
           "categoryLabels": [{"properties": {"show": lit(True), "color": col_solid(SUB), "fontSize": lit(label_size)}}]}
    vco = {"title": [{"properties": {"show": lit(True), "text": lit(title), "fontSize": lit(9), "fontColor": col_solid(SUB), "bold": lit(True)}}],
           "border": [{"properties": {"show": lit(True), "color": col_solid(color), "radius": lit(0), "width": lit(2)}}]}
    return container("card", x, y, w, h, z, roles={"Values": [measure]}, objects=obj, vco=vco, filters=filters)

def cardtext(x, y, w, h, z, measure, title, size=12, color=SUB, filters=None):
    obj = {"labels": [{"properties": {"color": col_solid(color), "fontSize": lit(size), "bold": lit(False), "wordWrap": lit(True)}}],
           "categoryLabels": [{"properties": {"show": lit(False)}}]}
    vco = {"title": [{"properties": {"show": lit(bool(title)), "text": lit(title or ""), "fontSize": lit(9), "fontColor": col_solid(SUB)}}]}
    return container("card", x, y, w, h, z, roles={"Values": [measure]}, objects=obj, vco=vco, filters=filters)

def slicer(x, y, w, h, z, field, title, single=False, dropdown=True):
    obj = {"data": [{"properties": {"mode": lit("Dropdown" if dropdown else "Basic")}}],
           "selection": [{"properties": {"singleSelect": lit(single), "selectAllCheckboxEnabled": lit(not single)}}],
           "header": [{"properties": {"show": lit(True), "text": lit(title), "fontColor": col_solid(SUB), "fontSize": lit(9), "bold": lit(True)}}],
           "items": [{"properties": {"fontColor": col_solid(NAVY), "fontSize": lit(10), "bold": lit(True)}}]}
    return container("slicer", x, y, w, h, z, roles={"Values": [field]}, objects=obj, drill=False)

def datapoint_colors(series_field, colmap):
    kind, ent, prop = series_field
    out = []
    for val, hexv in colmap.items():
        out.append({"selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0,
                    "Left": {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}},
                    "Right": {"Literal": {"Value": "'" + val + "'"}}}}}]},
                    "properties": {"fill": col_solid(hexv)}})
    return out

def barchart(x, y, w, h, z, category, values, title, series=None, stacked=False, color=ELEC, colmap=None, sort_by=None, desc=True,
             filters=None, horizontal=True, labels=True, extra_cats=None, legend=True):
    vtype = ("barChart" if stacked else "clusteredBarChart") if horizontal else ("columnChart" if stacked else "clusteredColumnChart")
    cats = [category] + (extra_cats or [])
    roles = {"Category": cats, "Y": values}
    if series: roles["Series"] = [series]
    obj = {"dataPoint": [{"properties": {"fill": col_solid(color)}}] if not series else [],
           "labels": [{"properties": {"show": lit(labels), "fontSize": lit(8), "color": col_solid(NAVY)}}],
           "categoryAxis": [{"properties": {"fontSize": lit(8), "labelColor": col_solid(SUB), "preferredCategoryWidth": lit(16)}}],
           "valueAxis": [{"properties": {"show": lit(False), "fontSize": lit(8), "gridlineShow": lit(False)}}],
           "legend": [{"properties": {"show": lit(bool(series) and legend), "position": lit("Top"), "fontSize": lit(8), "showTitle": lit(False)}}]}
    if series and colmap: obj["dataPoint"] = datapoint_colors(series, colmap)
    elif colmap and not series: obj["dataPoint"] = datapoint_colors(category, colmap)
    sort = sortdef(sort_by, desc) if sort_by else None
    c = container(vtype, x, y, w, h, z, roles=roles, objects=obj, title=title, sort=sort, filters=filters)
    return c

def table_vis(x, y, w, h, z, fields, title, sort_by=None, desc=True, filters=None, bold_cols=None, color_cols=None):
    obj = {"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": col_solid("#EEF1F4"), "rowPadding": lit(2), "textSize": lit(8)}}],
           "columnHeaders": [{"properties": {"fontColor": col_solid("#FFFFFF"), "backColor": col_solid(ELEC), "fontSize": lit(8), "bold": lit(True), "wordWrap": lit(True)}}],
           "values": [{"properties": {"fontSize": lit(8), "fontColorPrimary": col_solid("#1E2A33"), "backColorSecondary": col_solid("#F8F9FA")}}],
           "total": [{"properties": {"totals": lit(False)}}]}
    for f in (bold_cols or []):
        obj["values"].append({"selector": {"metadata": f"{f[1]}.{f[2]}"}, "properties": {"fontColorPrimary": col_solid(RED), "bold": lit(True)}})
    for f, meas in (color_cols or []):
        obj["values"].append({"selector": {"metadata": f"{f[1]}.{f[2]}"}, "properties": {"fontColorPrimary": col_measure(meas)}})
    sort = sortdef(sort_by, desc) if sort_by else None
    return container("tableEx", x, y, w, h, z, roles={"Values": fields}, objects=obj, title=title, sort=sort, filters=filters)

def matrix_vis(x, y, w, h, z, rows, cols, values, title, filters=None):
    obj = {"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "rowPadding": lit(2), "textSize": lit(8)}}],
           "columnHeaders": [{"properties": {"fontColor": col_solid("#FFFFFF"), "backColor": col_solid(ELEC), "fontSize": lit(8), "bold": lit(True)}}],
           "rowHeaders": [{"properties": {"fontSize": lit(8), "stepped": lit(True), "steppedLayoutIndentation": lit(10)}}],
           "values": [{"properties": {"fontSize": lit(8), "backColorSecondary": col_solid("#F8F9FA")}}],
           "subTotals": [{"properties": {"rowSubtotals": lit(True), "columnSubtotals": lit(False)}}]}
    return container("pivotTable", x, y, w, h, z, roles={"Rows": rows, "Columns": cols, "Values": values}, objects=obj, title=title, filters=filters)

def decomp_tree(x, y, w, h, z, analyze, explain_by, title):
    obj = {"general": [{"properties": {"analyzeSort": lit("High value")}}],
           "tree": [{"properties": {"density": lit("Compact")}}]}
    return container("decompositionTreeVisual", x, y, w, h, z, roles={"Analyze": [analyze], "ExplainBy": explain_by}, objects=obj, title=title)

# ---- page
def page(name, display, visuals, filters=None, order=0, width=1280, height=720):
    pid = nid()
    pdir = os.path.join(PAGES, pid); os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)
    pj = {"$schema": f"{SCHEMA}/page/1.0.0/schema.json", "name": pid, "displayName": display, "displayOption": "FitToPage",
          "height": height, "width": width,
          "objects": {"background": [{"properties": {"color": col_solid("#EEF1F4"), "transparency": lit(0)}}]}}
    if filters: pj["filterConfig"] = filterconfig(filters)
    with open(os.path.join(pdir, "page.json"), "w") as f: json.dump(pj, f, indent=2)
    for v in visuals:
        vdir = os.path.join(pdir, "visuals", v["name"]); os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "visual.json"), "w") as f: json.dump(v, f, indent=2)
    return pid

# ================================================================= FIELDS
OT = lambda p: C("OpenTasks", p)
CP = lambda p: C("Completed", p)
CM = lambda p: C("Compliance", p)
TEAM, WF, STEP, PERSON, BAND = C("Dim Team", "Team"), C("Dim Workflow", "Workflow"), C("Dim Step", "Step"), C("Dim Person", "Display name"), C("Dim Aging Band", "Band label")
PERSON_KEY = C("Dim Person", "Person")

def header(title, subtitle, z=0):
    return [textbox(8, 6, 620, 30, z, [title.upper(), "   " + subtitle], size=14)]
def global_slicers(z, y=4):
    return [slicer(900, y, 180, 42, z, TEAM, "Team"), slicer(1090, y, 182, 42, z + 1, WF, "Workflow")]

bandmap = {"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"], "Unknown": MUTE}
pages = []
# ----------------------------------------------------------------- 1. Service Overview
V = header("Service Overview", "Enterprise") + global_slicers(1)
z = 10
V += [card(8, 52, 190, 150, z, Mx("Out of service %"), "Work on hand out of service", size=40, color_measure="Service status colour"),
      card(204, 52, 104, 150, z + 1, Mx("Service status"), "Status", size=16, color_measure="Service status colour"),
      cardtext(8, 206, 300, 40, z + 2, Mx("Out of service subtitle"), None, size=9),
      card(316, 52, 310, 70, z + 3, Mx("Completed yesterday"), "Completed yesterday", color=OK),
      card(634, 52, 310, 70, z + 4, Mx("Within SLA on completion %"), "Within SLA on completion", color=NAVY),
      card(952, 52, 320, 70, z + 5, Mx("Median turnaround (days)"), "Median turnaround (days)", color=NAVY),
      card(316, 128, 310, 70, z + 6, Mx("Scheduled (not yet available)"), "Scheduled - not yet available", color=MUTE),
      card(634, 128, 310, 70, z + 7, Mx("Over 90 days"), "Over 90 days - fire drill", color="#8B1E3F"),
      card(952, 128, 320, 70, z + 8, Mx("Unassigned items"), "Unassigned", color=RED),
      cardtext(316, 200, 956, 46, z + 9, Mx("Work on hand subtitle"), None, size=9)]
z = 30
V += [table_vis(8, 250, 480, 232, z, [proj(WF), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"), proj(Mx("Service status"), "Status")],
                "Service by process", sort_by=Mx("Out of service %"), color_cols=[(Mx("Service status"), "Service status colour")]),
      barchart(496, 250, 384, 232, z + 1, TEAM, [Mx("Out of service %")], "Out of service - drill Team > Workflow > Step > Individual",
               extra_cats=[WF, STEP, PERSON], sort_by=Mx("Out of service %"), color=RED),
      barchart(888, 250, 384, 232, z + 2, BAND, [Mx("Work on hand")], "Work on hand by age - from date initiated", colmap=bandmap,
               sort_by=C("Dim Aging Band", "Band order"), desc=False)]
z = 40
V += [table_vis(8, 490, 560, 222, z, [proj(STEP), proj(WF), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"),
                                      proj(Mx("Oldest item (days)"), "Oldest"), proj(Mx("Median time in step"), "Median time in step"), proj(Mx("Service status"), "Status")],
                "Top out-of-service steps - where the work is stuck", sort_by=Mx("Out of service"), bold_cols=[Mx("Out of service")], color_cols=[(Mx("Service status"), "Service status colour")]),
      barchart(576, 490, 344, 222, z + 1, WF, [Mx("Median turnaround (days)")], "Turnaround by process - median days", sort_by=Mx("Completed yesterday"), color=ELEC),
      barchart(928, 490, 344, 222, z + 2, STEP, [Mx("Completed yesterday")], "Intake and set-up steps - measured in hours", series=CP("Hours band"), stacked=True,
               colmap=HOURS_COL, filters=[cat_filter(C("Dim Step", "Intake step"), [True])], sort_by=Mx("Completed yesterday"))]
pages.append(("Service Overview", V, None))

# ----------------------------------------------------------------- 2. Work on hand
V = header("Work on hand", "Drill to the individual") + global_slicers(1)
z = 10
V += [card(8, 52, 200, 130, z, Mx("Work on hand"), "Work on hand", color=NAVY, size=30),
      card(216, 52, 200, 130, z + 1, Mx("Out of service %"), "Out of service", color_measure="Service status colour", size=30),
      barchart(424, 52, 848, 130, z + 2, BAND, [Mx("Work on hand")], "Work on hand by aging band - click a band to see its items", horizontal=False,
               colmap={"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"], "Unknown": MUTE},
               sort_by=C("Dim Aging Band", "Band order"), desc=False)]
z = 20
V += [decomp_tree(8, 190, 700, 260, z, Mx("Work on hand"), [TEAM, WF, STEP, PERSON], "Decomposition - Team > Workflow > Step > Individual"),
      barchart(716, 190, 556, 260, z + 1, PERSON, [Mx("Work on hand")], "Work on hand by individual", series=BAND, stacked=True,
               colmap={"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"]},
               sort_by=Mx("Work on hand"), labels=False)]
z = 30
V += [matrix_vis(8, 458, 700, 254, z, [TEAM, WF, STEP, PERSON], [BAND], [proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%")],
                 "Matrix - next level with aging buckets"),
      table_vis(716, 458, 556, 254, z + 1, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Assigned to")), proj(OT("Step"))],
                "Oldest first", sort_by=OT("Age (days)"), filters=[cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")])]
pages.append(("Work On Hand", V, None))

# ----------------------------------------------------------------- 3. Renewal pipeline
V = header("Renewal pipeline", "All divisions") + global_slicers(1)
z = 10
stage_cards = [("Not yet quoted", RED), ("Quoted - with agent", "#FF8A00"), ("Bound - awaiting issue", OK), ("Not renewing", MUTE)]
for i, (nm, colr) in enumerate(stage_cards):
    xx = 8 + i * 318
    V.append(card(xx, 52, 310, 72, z + i, Mx(nm), nm, color=colr, size=24))
    V.append(cardtext(xx, 126, 310, 26, z + 4 + i, Mx("Renewal stage subtitle"), None, size=8, filters=[cat_filter(OT("Renewal stage"), [nm])]))
z = 20
V += [barchart(8, 160, 632, 250, z, TEAM, [Mx("Renewals in pipeline")], "Pipeline by team - stage mix", series=OT("Renewal stage"), stacked=True, colmap=STAGE_COL, sort_by=Mx("Renewals in pipeline")),
      barchart(648, 160, 624, 250, z + 1, OT("Account executive"), [Mx("Renewals in pipeline")], "Pipeline by account executive", series=OT("Renewal stage"), stacked=True, colmap=STAGE_COL, sort_by=Mx("Renewals in pipeline"), labels=False)]
z = 30
V += [barchart(8, 418, 420, 294, z, OT("Renewal stage"), [Mx("Renewals in pipeline")], "Stage by aging bucket - from date initiated", series=BAND, stacked=True,
               colmap={"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"]},
               sort_by=OT("Renewal stage order"), desc=False),
      barchart(436, 418, 400, 294, z + 1, STEP, [Mx("Renewals in pipeline"), Mx("Out of service")], "Not yet quoted - by step", color=RED,
               filters=[cat_filter(OT("Renewal stage"), ["Not yet quoted"])], sort_by=Mx("Renewals in pipeline")),
      table_vis(844, 418, 428, 294, z + 2, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Account executive"), "Account exec"), proj(OT("Assigned to")), proj(OT("Step")), proj(OT("Date initiated"), "Initiated")],
                "Not yet quoted - oldest first", sort_by=OT("Age (days)"), filters=[cat_filter(OT("Renewal stage"), ["Not yet quoted"]), cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")])]
pages.append(("Renewal Pipeline", V, [cat_filter(WF, ["Renewal"])]))

# ----------------------------------------------------------------- 4. Team scorecard
V = header("Team scorecard", "By individual") + [slicer(700, 4, 190, 42, 1, C("Dim Person", "Staff scope"), "Scope"), slicer(900, 4, 180, 42, 2, PERSON_KEY, "Individual", single=True), slicer(1090, 4, 182, 42, 3, WF, "Workflow")]
z = 10
kp = [("Items on hand", Mx("Work on hand"), NAVY, None), ("Out of service", Mx("Out of service %"), None, "Service status colour"), ("Oldest item (days)", Mx("Oldest item (days)"), RED, None),
      ("Received yesterday", Mx("Received yesterday"), NAVY, None), ("Released yesterday", Mx("Completed yesterday"), OK, None), ("Within SLA on completion", Mx("Within SLA on completion %"), NAVY, None),
      ("Status", Mx("Service status"), None, "Service status colour")]
for i, (t, mm, colr, cm) in enumerate(kp):
    V.append(card(8 + i * 181, 52, 176, 90, z + i, mm, t, color=colr or NAVY, color_measure=cm, size=22 if t != "Status" else 16))
z = 20
V += [barchart(8, 150, 420, 250, z, STEP, [Mx("Work on hand")], "On hand by step", series=OT("Service"), stacked=True, colmap={"Within service": ELEC, "Out of service": RED}, sort_by=Mx("Work on hand"),
               filters=[cat_filter(OT("Scheduled"), [False])]),
      barchart(436, 150, 400, 250, z + 1, BAND, [Mx("Work on hand")], "Age profile",
               colmap={"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"]},
               sort_by=C("Dim Aging Band", "Band order"), desc=False),
      table_vis(844, 150, 428, 250, z + 2, [proj(CP("Step")), proj(CP("Turnaround (days)"), "Turnaround (d)"), proj(CP("SLA (days)"), "SLA"), proj(CP("Met SLA"), "Met")], "Completed yesterday", sort_by=CP("Turnaround (days)"))]
z = 30
V += [table_vis(8, 408, 840, 304, z, [proj(PERSON, "Individual"), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"), proj(Mx("Oldest item (days)"), "Oldest"), proj(Mx("Service status"), "Status")],
                "Team - ranked by out of service", sort_by=Mx("Out of service %"), color_cols=[(Mx("Service status"), "Service status colour")]),
      barchart(856, 408, 416, 304, z + 1, PERSON, [Mx("Completed yesterday")], "Released yesterday by person", color=OK, sort_by=Mx("Completed yesterday"))]
pages.append(("Team Scorecard", V, None))

# ----------------------------------------------------------------- 5. Management
V = header("Management", "Unassigned  |  quality") + global_slicers(1)
z = 10
kp = [("Unassigned items", Mx("Unassigned items"), RED, None), ("Unassigned over 30 days", Mx("Unassigned over 30 days"), RED, None), ("Unassigned out of service", Mx("Unassigned out of service %"), NAVY, None),
      ("Rework released yesterday", Mx("Rework released"), NAVY, None), ("Rework rate", Mx("Rework rate"), NAVY, None), ("Production released", Mx("Production released"), OK, None)]
for i, (t, mm, colr, cm) in enumerate(kp):
    V.append(card(8 + i * 211, 52, 206, 90, z + i, mm, t, color=colr, size=24))
z = 20
UNA = [cat_filter(OT("Is unassigned"), [True])]
V += [barchart(8, 150, 632, 220, z, WF, [Mx("Work on hand")], "Unassigned by workflow", series=BAND, stacked=True, colmap=bandmap, sort_by=Mx("Work on hand"), filters=UNA),
      barchart(648, 150, 624, 220, z + 1, TEAM, [Mx("Work on hand")], "Unassigned by team", series=BAND, stacked=True, colmap=bandmap, sort_by=Mx("Work on hand"), filters=UNA)]
z = 30
V += [barchart(8, 378, 632, 170, z, WF, [Mx("Completed yesterday")], "Production vs rework - released yesterday by workflow", series=CP("Release type"), stacked=True, colmap={"Production": OK, "Rework": AMBER}, sort_by=Mx("Completed yesterday")),
      barchart(648, 378, 624, 170, z + 1, STEP, [Mx("Rework released")], "Rework by step", color=AMBER, filters=[cat_filter(CP("Is rework"), [True])], sort_by=Mx("Rework released"))]
z = 40
V += [table_vis(8, 556, 1264, 156, z, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Workflow")), proj(OT("Step")), proj(OT("Team")), proj(OT("Date initiated"), "Initiated")],
                "Unassigned - oldest first", sort_by=OT("Age (days)"), filters=UNA + [cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")])]
pages.append(("Management", V, None))

# ----------------------------------------------------------------- 6. Compliance
V = header("Compliance", "Due date and state") + [slicer(700, 4, 190, 42, 1, CM("Filing state"), "State"), slicer(900, 4, 180, 42, 2, CM("Team"), "Team"), slicer(1090, 4, 182, 42, 3, CM("UA"), "UA")]
z = 10
kp = [("Past due date", Mx("Past due"), DRED), ("Past due - fining states", Mx("Past due - fining states"), DRED), ("Due within 14 days", Mx("Due within 14 days"), RED),
      ("Due in 15-30 days", Mx("Due in 15-30 days"), AMBER), ("On track", Mx("On track"), OK), ("Open items", Mx("Open filings"), NAVY)]
for i, (t, mm, colr) in enumerate(kp):
    V.append(card(8 + i * 211, 52, 206, 90, z + i, mm, t, color=colr, size=24))
z = 20
V += [table_vis(8, 150, 560, 250, z, [proj(CM("Filing state"), "State"), proj(Mx("Fining state flag"), "Fines"), proj(Mx("Past due")), proj(Mx("Due within 14 days"), "<= 14 d"), proj(Mx("Due in 15-30 days"), "15-30 d"), proj(Mx("On track")), proj(Mx("Open filings"), "Open"), proj(Mx("Oldest past due (days)"), "Oldest past due")],
                "By state - fining states first, then past due", sort_by=Mx("Past due"), bold_cols=[Mx("Past due")]),
      barchart(576, 150, 400, 250, z + 1, PERSON, [Mx("Open filings")], "By associate - who has it", series=CM("Due band"), stacked=True, colmap=DUE_COL, sort_by=Mx("Open filings")),
      barchart(984, 150, 288, 250, z + 2, BAND, [Mx("Open filings")], "Age from date initiated", colmap=bandmap, sort_by=C("Dim Aging Band", "Band order"), desc=False)]
z = 30
V += [table_vis(8, 408, 1264, 304, z, [proj(CM("Due band"), "Status"), proj(CM("Fining state"), "Fines"), proj(CM("Due date")), proj(CM("Days past due"), "Days"), proj(CM("File name"), "File name (key)"), proj(CM("State")), proj(CM("UA"), "Has it (UA)"), proj(CM("Assigned to")), proj(CM("Team")), proj(CM("Age (days)"), "Age"), proj(CM("Note"))],
                "Action list - past due first, then due within 14 days", sort_by=CM("Days past due"), filters=[cat_filter(CM("Due band code"), ["past", "red"])], bold_cols=[CM("Days past due")])]
pages.append(("Compliance", V, None))

# ----------------------------------------------------------------- 7. Task list
V = header("Task list", "Every column  |  detail") + [slicer(640, 4, 150, 42, 1, TEAM, "Team"), slicer(798, 4, 150, 42, 2, WF, "Workflow"), slicer(956, 4, 150, 42, 3, STEP, "Step"), slicer(1114, 4, 158, 42, 4, OT("Service"), "Service")]
z = 10
V += [card(8, 52, 200, 60, z, Mx("Work on hand"), "Tasks", size=18), card(216, 52, 200, 60, z + 1, Mx("Files on hand"), "Files", size=18),
      card(424, 52, 200, 60, z + 2, Mx("Out of service"), "Out of service", size=18, color=RED), card(632, 52, 200, 60, z + 3, Mx("Out of service %"), "Out of service %", size=18, color_measure="Service status colour"),
      card(840, 52, 200, 60, z + 4, Mx("Oldest item (days)"), "Oldest (days)", size=18), card(1048, 52, 224, 60, z + 5, Mx("Scheduled (not yet available)"), "Scheduled (not on hand)", size=18, color=MUTE)]
cols = ["Age (days)", "Service", "SLA (days)", "Aging band", "Status", "File number", "Policy number", "Insured", "Brand", "Department", "Team", "Workflow", "Step", "Assigned to", "From user", "Account executive", "CSR", "Agent name", "Date initiated", "Available date"]
V += [table_vis(8, 120, 1264, 592, 20, [proj(OT(c)) for c in cols], "Task list - 20 columns, scroll right for more; use Export data from the visual header", sort_by=OT("Age (days)"), bold_cols=[OT("Age (days)")])]
pages.append(("Task list", V, None))

# ================================================================= WRITE
page_ids = []
for i, (disp, vis, pf) in enumerate(pages):
    page_ids.append(page(None, disp, vis, pf, i))
with open(os.path.join(PAGES, "pages.json"), "w") as f:
    json.dump({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json", "pageOrder": page_ids, "activePageName": page_ids[0]}, f, indent=2)
with open(os.path.join(DEF, "version.json"), "w") as f:
    json.dump({"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "1.0.0"}, f, indent=2)

THEME = {
    "name": "SPGTheme", "dataColors": [ELEC, NAVY, OK, AMBER, "#FF8A00", RED, "#8B1E3F", MUTE, "#E8702A", SUB],
    "background": "#FFFFFF", "foreground": NAVY, "tableAccent": ELEC, "good": OK, "neutral": AMBER, "bad": RED,
    "textClasses": {"callout": {"fontSize": 26, "fontFace": "Segoe UI Semibold", "color": NAVY}, "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": NAVY},
                    "header": {"fontSize": 9, "fontFace": "Segoe UI Semibold", "color": "#FFFFFF"}, "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": "#1E2A33"}},
    "visualStyles": {"*": {"*": {
        "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
        "border": [{"show": False}],
        "visualHeader": [{"show": True}],
        "title": [{"show": True, "fontColor": {"solid": {"color": NAVY}}, "fontSize": 11, "fontFamily": "Segoe UI Semibold", "alignment": "left"}],
        "dropShadow": [{"show": True, "preset": "BottomRight", "color": {"solid": {"color": "#000000"}}, "transparency": 92}],
        "outspacePane": [{"backgroundColor": {"solid": {"color": "#FFFFFF"}}, "fontSize": 9}]}},
        "page": {"*": {"background": [{"color": {"solid": {"color": "#EEF1F4"}}, "transparency": 0}], "outspace": [{"color": {"solid": {"color": "#E3E7EB"}}}]}}}
}
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "SPGTheme.json"), "w") as f: json.dump(THEME, f, indent=2)

REPORT = {"$schema": f"{SCHEMA}/report/1.0.0/schema.json",
          "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.55", "type": "SharedResources"}},
          "layoutOptimization": "None",
          "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]}],
          "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True}}
with open(os.path.join(DEF, "report.json"), "w") as f: json.dump(REPORT, f, indent=2)
with open(os.path.join(RP, "definition.pbir"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json", "version": "4.0",
               "datasetReference": {"byPath": {"path": "../SPG Operational Dashboard.SemanticModel"}}}, f, indent=2)
_rid = stable_logical_id(os.path.join(RP, ".platform"))
with open(os.path.join(RP, ".platform"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
               "metadata": {"type": "Report", "displayName": "SPG Operational Dashboard"}, "config": {"version": "2.0", "logicalId": _rid}}, f, indent=2)
with open(os.path.join(ROOT, "SPG Operational Dashboard.pbip"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
               "artifacts": [{"report": {"path": "SPG Operational Dashboard.Report"}}], "settings": {"enableAutoRecovery": True}}, f, indent=2)
print("report written:", len(pages), "pages,", sum(len(v) for _, v, _ in pages), "visuals")
