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
    if isinstance(v, float): return {"expr": {"Literal": {"Value": f"{v}D"}}}
    if isinstance(v, int): return {"expr": {"Literal": {"Value": f"{v}L"}}}
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
                   "Values": [[{"Literal": {"Value": ("'" + v.replace("'", "''") + "'") if isinstance(v, str) else ("true" if v is True else "false" if v is False else "null" if v is None else str(v))}}] for v in values]}}
    if exclude: cond = {"Not": {"Expression": cond}}
    return {"name": nid(), "field": fexpr(f), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "s", "Entity": ent, "Type": 0}], "Where": [{"Condition": cond}]}}
def filterconfig(filters): return {"filters": filters}
def pane_filter(f, display=None):
    """A page-level filter card with no condition: shows in the Filters pane as a slicer (the mockup's slide-out filter pane)."""
    d = {"name": nid(), "field": fexpr(f), "type": "Categorical"}
    if display: d["displayName"] = display
    return d
def meas_filter_gt(measure_name, value):
    """Visual-level filter: measure > value (e.g. hide workflows with fewer than 20 items)."""
    return {"name": nid(), "field": fexpr(Mx(measure_name)), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "m", "Entity": MEAS, "Type": 0}],
                       "Where": [{"Condition": {"Comparison": {"ComparisonKind": 1, "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": measure_name}}, "Right": {"Literal": {"Value": f"{value}L"}}}}}]}}

# ---- visual container
def title_obj(text, size=10, color=NAVY, show=True):
    return {"title": [{"properties": {"show": lit(show), "text": lit(text), "fontSize": lit(size), "fontColor": col_solid(color), "bold": lit(True), "fontFamily": lit("Segoe UI Semibold")}}],
            "subTitle": [{"properties": {"show": lit(False)}}],
            "visualHeader": [{"properties": {"showPinButton": lit(False), "showFocusModeButton": lit(True), "showCopyVisualImageButton": lit(False), "showFilterRestatementButton": lit(False)}}]}

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
    c = {"$schema": f"{SCHEMA}/visualContainer/2.14.0/schema.json", "name": nid(),
         "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": v}
    if filters: c["filterConfig"] = filterconfig(filters)
    return c

# ---- visual builders
def textbox(x, y, w, h, z, runs, size=16, color=NAVY, bold=True, background=False, sizes=None, colors=None, bolds=None):
    """runs: list of strings (one paragraph). Optional per-run sizes / colors / bolds."""
    tr = []
    for i, r in enumerate(runs):
        tr.append({"value": r, "textStyle": {"fontWeight": "bold" if (bolds[i] if bolds else bold) else "normal",
                                             "fontSize": f"{(sizes[i] if sizes else size)}pt", "color": (colors[i] if colors else color), "fontFamily": "Segoe UI"}})
    paras = [{"textRuns": tr}]
    vco = {} if background else {"background": [{"properties": {"show": lit(False)}}], "dropShadow": [{"properties": {"show": lit(False)}}]}
    return container("textbox", x, y, w, h, z, objects={"general": [{"properties": {"paragraphs": paras}}]}, drill=False, vco=vco)

def shape(x, y, w, h, z, fill="#FFFFFF", line=None):
    obj = {"shape": [{"properties": {"tileShape": lit("rectangle")}}],
           "fill": [{"properties": {"show": lit(True), "fillColor": col_solid(fill), "transparency": lit(0)}}],
           "outline": [{"properties": {"show": lit(bool(line)), "lineColor": col_solid(line or "#E5E7EB"), "weight": lit(1)}}]}
    return container("shape", x, y, w, h, z, objects=obj, drill=False,
                     vco={"background": [{"properties": {"show": lit(False)}}], "dropShadow": [{"properties": {"show": lit(False)}}], "title": [{"properties": {"show": lit(False)}}]})

def button(x, y, w, h, z, text, target=None, back=False, current=False, size=10):
    """Blank action button. target = page name -> page navigation; back=True -> Back action."""
    fill = "#EEF2FF" if current else "#FFFFFF"
    obj = {"text": [{"properties": {"show": lit(True), "text": lit(text), "fontColor": col_solid("#111827" if current else "#374151"), "fontSize": lit(size),
                                    "bold": lit(current), "horizontalAlignment": lit("left"), "fontFamily": lit("Segoe UI")}}],
           "fill": [{"properties": {"show": lit(True), "fillColor": col_solid(fill), "transparency": lit(0)}}],
           "outline": [{"properties": {"show": lit(False)}}]}
    if back:
        link = {"show": lit(True), "type": lit("Back")}
    else:
        link = {"show": lit(True), "type": lit("PageNavigation"), "navigationSection": lit(target)}
    vco = {"visualLink": [{"properties": link}], "background": [{"properties": {"show": lit(False)}}], "dropShadow": [{"properties": {"show": lit(False)}}]}
    return container("actionButton", x, y, w, h, z, objects=obj, drill=False, vco=vco)

def card(x, y, w, h, z, measure, title, color=NAVY, size=None, color_measure=None, filters=None, label_size=9, value_color=None):
    """KPI card in the service's native multiRowCard form: accent bar on the left, title above, value below.
    color_measure: a measure returning a hex colour -> field-value conditional formatting of the number (RAG)."""
    if size is None or size > (h - 40) * 0.55:
        size = max(12, int(min(size or 99, (h - 40) * 0.55)))
    vcol = col_measure(color_measure) if color_measure else col_solid(value_color or color)
    obj = {"card": [{"properties": {"barColor": col_solid(color), "barWeight": lit(4), "outlineWeight": lit(0)}}],
           "dataLabels": [{"properties": {"fontFamily": lit("Segoe UI Semibold"), "fontSize": lit(size), "color": vcol}}],
           "categoryLabels": [{"properties": {"show": lit(False)}}]}
    vco = {"title": [{"properties": {"show": lit(True), "text": lit(title.upper()), "fontSize": lit(label_size), "fontColor": col_solid(SUB), "bold": lit(True)}}]}
    return container("multiRowCard", x, y, w, h, z, roles={"Values": [measure]}, objects=obj, vco=vco, filters=filters)

def kpi(x, y, w, h, z, measure, title, sub=None, color=NAVY, size=None, color_measure=None, filters=None, sub_text=None):
    """Mockup KPI tile = card (label + big number) with a small grey subtitle line laid over its bottom edge.
    sub: a measure for a dynamic subtitle; sub_text: a static string."""
    has_sub = sub is not None or bool(sub_text)
    if size is None or (has_sub and size > (h - 56) * 0.6):
        size = max(12, int(min(size or 99, (h - 56) * 0.6)))   # title ~22 px + subtitle 30 px: the number must fit between them
    out = [card(x, y, w, h, z, measure, title, color=color, size=size, color_measure=color_measure, filters=filters)]
    if sub is not None:
        out.append(cardtext(x + 6, y + h - 30, w - 12, 30, z + 50, sub, None, size=8, filters=filters, transparent=True))
    elif sub_text:
        out.append(textbox(x + 2, y + h - 28, w - 8, 26, z + 50, [sub_text], size=8, color=SUB, bold=False))
    return out

def cardtext(x, y, w, h, z, measure, title, size=9, color=SUB, filters=None, transparent=False, color_measure=None, bold=False):
    obj = {"card": [{"properties": {"outline": lit("None"), "barShow": lit(False), "barWeight": lit(0), "outlineWeight": lit(0), "cardPadding": lit(0)}}],
           "dataLabels": [{"properties": {"fontSize": lit(size), "color": col_measure(color_measure) if color_measure else col_solid(color), "fontFamily": lit("Segoe UI Semibold" if bold else "Segoe UI")}}],
           "categoryLabels": [{"properties": {"show": lit(False)}}]}
    vco = {"title": [{"properties": {"show": lit(bool(title)), "text": lit(title or ""), "fontSize": lit(9), "fontColor": col_solid(SUB)}}]}
    if transparent:
        vco["background"] = [{"properties": {"show": lit(False)}}]
        vco["dropShadow"] = [{"properties": {"show": lit(False)}}]
    return container("multiRowCard", x, y, w, h, z, roles={"Values": [measure]}, objects=obj, vco=vco, filters=filters, drill=False)

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
             filters=None, horizontal=True, labels=True, extra_cats=None, legend=True, color_measure=None):
    vtype = ("barChart" if stacked else "clusteredBarChart") if horizontal else ("columnChart" if stacked else "clusteredColumnChart")
    cats = [category] + (extra_cats or [])
    roles = {"Category": cats, "Y": values}
    if series: roles["Series"] = [series]
    obj = {"dataPoint": [{"properties": {"fill": col_solid(color)}}] if not series else [],
           "labels": [{"properties": {"show": lit(labels), "fontSize": lit(8), "color": col_solid(NAVY)}}],
           "categoryAxis": [{"properties": {"fontSize": lit(8), "labelColor": col_solid(SUB), "preferredCategoryWidth": lit(16), "maxMarginFactor": lit(38), "concatenateLabels": lit(False)}}],
           "valueAxis": [{"properties": {"show": lit(False), "fontSize": lit(8), "gridlineShow": lit(False)}}],
           "legend": [{"properties": {"show": lit(bool(series) and legend), "position": lit("Top"), "fontSize": lit(8), "showTitle": lit(False)}}]}
    if series and colmap: obj["dataPoint"] = datapoint_colors(series, colmap)
    elif colmap and not series: obj["dataPoint"] = datapoint_colors(category, colmap)
    if color_measure: obj["dataPoint"] = [{"properties": {"fill": col_measure(color_measure)}}]
    sort = sortdef(sort_by, desc) if sort_by else None
    c = container(vtype, x, y, w, h, z, roles=roles, objects=obj, title=title, sort=sort, filters=filters)
    if extra_cats:
        c["visual"]["query"]["queryState"]["Category"]["projections"][0]["active"] = True
    return c

def table_vis(x, y, w, h, z, fields, title, sort_by=None, desc=True, filters=None, bold_cols=None, color_cols=None, totals=False):
    obj = {"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": col_solid("#EEF1F4"), "rowPadding": lit(2), "textSize": lit(8)}}],
           "columnHeaders": [{"properties": {"fontColor": col_solid("#FFFFFF"), "backColor": col_solid(ELEC), "fontSize": lit(8), "bold": lit(True), "wordWrap": lit(True)}}],
           "values": [{"properties": {"fontSize": lit(8), "fontColorPrimary": col_solid("#1E2A33"), "backColorSecondary": col_solid("#F8F9FA")}}],
           "total": [{"properties": {"totals": lit(totals), "fontSize": lit(8), "bold": lit(True), "backColor": col_solid("#EEF4FA")}}]}
    for f in (bold_cols or []):
        obj["values"].append({"selector": {"metadata": f"{f[1]}.{f[2]}"}, "properties": {"fontColorPrimary": col_solid(RED), "bold": lit(True)}})
    for f, measure in (color_cols or []):
        obj["values"].append({"selector": {"metadata": f"{f[1]}.{f[2]}"}, "properties": {"fontColorPrimary": col_measure(measure), "bold": lit(True)}})
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
def page(name, display, visuals, filters=None, order=0, width=1440, height=820, drillthrough=None):
    pid = name or nid()
    pdir = os.path.join(PAGES, pid); os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)
    pj = {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": pid, "displayName": display, "displayOption": "FitToPage",
          "height": height, "width": width,
          "objects": {"background": [{"properties": {"color": col_solid("#EEF1F4"), "transparency": lit(0)}}]}}
    pf = list(filters or [])
    if drillthrough:
        params = []
        for f in drillthrough:
            fname = nid()
            pf.append({"name": fname, "field": fexpr(f), "type": "Categorical", "howCreated": "Drillthrough"})
            params.append({"name": nid(), "boundFilter": fname, "fieldExpr": fexpr(f)})
        pj["pageBinding"] = {"name": nid(), "type": "Drillthrough", "parameters": params}
    if pf: pj["filterConfig"] = filterconfig(pf)
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
SCOPE = C("Dim Person", "Staff scope")
BAND_ORDER = C("Dim Aging Band", "Band order")

# ================================================================= LAYOUT (mockup shell: left page nav + page header + content grid)
PAGE_W, PAGE_H = 1440, 820
X0, CW = 14, PAGE_W - 28      # content area x / width
Y0 = 54
GAP = 10
CANVAS = "#EEF1F4"

def cols(fracs, x=X0, w=CW, gap=GAP):
    """Split a width into columns by fractions -> [(x, w), ...]."""
    tot = sum(fracs); free = w - gap * (len(fracs) - 1); out = []; cx = x
    for f in fracs:
        cw = int(round(free * f / tot)); out.append((cx, cw)); cx += cw + gap
    return out

bandmap = {"0-7 days": BAND_COL["0-7"], "8-15 days": BAND_COL["8-15"], "16-30 days": BAND_COL["16-30"], "31-60 days": BAND_COL["31-60"], "61-90 days": BAND_COL["61-90"], "Over 90 days": BAND_COL["90+"], "Unknown": MUTE}
bandmap6 = {k: v for k, v in bandmap.items() if k != "Unknown"}

# Pages: (id, display name, mockup subtitle). Fixed ids so page navigation buttons can target them.
import hashlib
def page_id(name): return hashlib.md5(("SPG page " + name).encode()).hexdigest()[:20]   # stable per page name, PBIR-style 20-hex id
PAGE_DEFS = [(page_id(n), n, sub) for n, sub in [("Service Overview", "Enterprise"), ("Work On Hand", "Drill to the individual"), ("Renewal Pipeline", "All divisions"),
                                                 ("Team Scorecard", "By individual"), ("Management", "Unassigned · quality"), ("Compliance", "Due date and state"), ("Task list", "Detail")]]
PID = {d[1]: d[0] for d in PAGE_DEFS}

def shell(display, subtitle, z=0):
    """Page header (the service shows the page list itself)."""
    return [textbox(X0, 10, 680, 34, z + 5, [display.upper(), "    " + subtitle], sizes=[14, 9], colors=[NAVY, SUB], bolds=[True, False]),
            textbox(X0 + CW - 540, 14, 540, 28, z + 6, ["Filters: open the Filters pane (☰) for the page slicers  ·  click a bar to cross-highlight  ·  right-click → Drill through → Task list"], size=7, color=SUB, bold=False)]

def kpi_row(y, h, items, z, x=X0, w=CW):
    """items: list of dicts(measure, title, sub|sub_text, color, color_measure, filters, size)"""
    out = []
    for (cx, cw), it in zip(cols([1] * len(items), x, w), items):
        out += kpi(cx, y, cw, h, z, it["measure"], it["title"], sub=it.get("sub"), sub_text=it.get("sub_text"), color=it.get("color", NAVY),
                   size=it.get("size"), color_measure=it.get("color_measure"), filters=it.get("filters"))
        z += 2
    return out

# Common pane filters (the mockup's slide-out filter pane, per page)
PF_DIV, PF_TEAM, PF_LINE, PF_WF, PF_STEP = pane_filter(OT("Division")), pane_filter(TEAM), pane_filter(OT("Line of business")), pane_filter(WF), pane_filter(STEP, "Process step")
PF_BAND, PF_DI, PF_AV = pane_filter(BAND, "Aging bucket"), pane_filter(OT("Date initiated")), pane_filter(OT("Available date"))
PF_WHO, PF_AE, PF_CSR, PF_AGENT, PF_SCOPE = pane_filter(PERSON_KEY, "Assigned to"), pane_filter(OT("Account executive")), pane_filter(OT("CSR")), pane_filter(OT("Agent name")), pane_filter(SCOPE)

pages = []
# ----------------------------------------------------------------- 1. Service Overview
V = shell("Service Overview", "Enterprise")
z = 10
(hx, hw), (kx, kw) = cols([1, 3])
# hero: Work on hand out of service
HY, HH = Y0, 190
V += [card(hx, HY, hw, HH, z, Mx("Out of service %"), "Work on hand out of service", color=ELEC, size=42, color_measure="Service status colour"),
      cardtext(hx + 6, HY + 96, 140, 30, z + 1, Mx("Service status icon"), None, size=11, transparent=True, color_measure="Service status colour", bold=True),
      cardtext(hx + 6, HY + 128, hw - 12, 30, z + 2, Mx("Out of service subtitle"), None, size=8, transparent=True, color="#1E2A33"),
      cardtext(hx + 6, HY + 158, hw - 12, 30, z + 3, Mx("Work on hand subtitle"), None, size=8, transparent=True)]
z = 20
KH = (HH - GAP) // 2
V += kpi_row(HY, KH, [dict(measure=Mx("Completed yesterday"), title="Completed yesterday", sub=Mx("Sub: completed tasks"), color=OK),
                      dict(measure=Mx("Within SLA on completion %"), title="Within SLA on completion", sub_text="of released", color=NAVY),
                      dict(measure=Mx("Median turnaround (days)"), title="Median turnaround", sub_text="start to finish (days)", color=NAVY)], z, x=kx, w=kw)
z = 30
V += kpi_row(HY + KH + GAP, KH, [dict(measure=Mx("Scheduled (not yet available)"), title="Scheduled — not yet available", sub_text="created ahead · not on hand, not out of service", color=MUTE),
                                 dict(measure=Mx("Over 90 days"), title="Over 90 days — fire drill", sub=Mx("Sub: over 90"), color="#8B1E3F"),
                                 dict(measure=Mx("Unassigned items"), title="Unassigned", sub=Mx("Sub: unassigned"), color=RED)], z, x=kx, w=kw)
# row 2: service by process | out-of-service drill | work on hand by age
R2Y, R2H = HY + HH + GAP, 262
(ax, aw), (bx, bw), (cx, cw) = cols([1.5, 1, 1])
z = 40
V += [table_vis(ax, R2Y, aw, R2H, z, [proj(WF), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"), proj(Mx("Service status icon"), "Status")],
                "Service by process", sort_by=Mx("Out of service %"), color_cols=[(Mx("Service status icon"), "Service status colour")], filters=[meas_filter_gt("Work on hand", 19)]),
      barchart(bx, R2Y, bw, R2H, z + 1, TEAM, [Mx("Out of service %")], "Out of service — drill Team › Workflow › Step › Individual",
               extra_cats=[WF, STEP, PERSON], sort_by=Mx("Out of service %"), color_measure="Service status colour"),
      barchart(cx, R2Y, cw, R2H, z + 2, BAND, [Mx("Work on hand")], "Work on hand by age — from date initiated", colmap=bandmap,
               sort_by=BAND_ORDER, desc=False)]
# row 3: top out-of-service steps | turnaround by process | intake steps in hours
R3Y = R2Y + R2H + GAP; R3H = PAGE_H - 14 - R3Y
(ax, aw), (bx, bw), (cx, cw) = cols([1.9, 0.85, 0.85])
z = 50
V += [table_vis(ax, R3Y, aw, R3H, z, [proj(STEP), proj(WF), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"),
                                      proj(Mx("Oldest item (days)"), "Oldest"), proj(Mx("Median time in step"), "Time in step"), proj(Mx("Service status icon"), "Status")],
                "Top out-of-service steps — where the work is stuck", sort_by=Mx("Out of service"), bold_cols=[Mx("Out of service")], color_cols=[(Mx("Service status icon"), "Service status colour")],
                filters=[meas_filter_gt("Out of service", 0)]),
      barchart(bx, R3Y, bw, R3H, z + 1, WF, [Mx("Median turnaround (days)")], "Turnaround by process — median days", sort_by=Mx("Median turnaround (days)"), color=ELEC, filters=[cat_filter(WF, [None], exclude=True), meas_filter_gt("Completed yesterday", 9)]),
      barchart(cx, R3Y, cw, R3H, z + 2, STEP, [Mx("Completed yesterday")], "Intake and set-up steps — measured in hours", series=CP("Hours band"), stacked=True,
               colmap=HOURS_COL, filters=[cat_filter(C("Dim Step", "Intake step"), [True])], sort_by=Mx("Completed yesterday"))]
pages.append((PID["Service Overview"], "Service Overview", V, [PF_DIV, PF_TEAM, PF_LINE, PF_WF, PF_STEP, PF_BAND, PF_DI]))

# ----------------------------------------------------------------- 2. Work on hand
V = shell("Work On Hand", "Drill to the individual")
z = 10
(ax, aw), (bx, bw), (cx, cw) = cols([1, 1, 4.6])
R1Y, R1H = Y0, 150
V += kpi(ax, R1Y, aw, R1H, z, Mx("Work on hand"), "Work on hand", sub=Mx("Sub: files and scheduled"), color=NAVY, size=30)
V += kpi(bx, R1Y, bw, R1H, z + 2, Mx("Out of service %"), "Out of service", sub=Mx("Sub: out of service items"), color=RED, size=30, color_measure="Service status colour")
# aging band strip: six band tiles (click a band -> cross-filters the page)
V.append(shape(cx, R1Y, cw, R1H, z + 4, fill="#FFFFFF"))
V.append(textbox(cx + 8, R1Y + 4, cw - 16, 20, z + 5, ["Work on hand by aging band — click a band to see its items"], size=9, color=NAVY))
z = 20
bands = [("0-7 days", "0–7 days"), ("8-15 days", "8–15 days"), ("16-30 days", "16–30 days"), ("31-60 days", "31–60 days"), ("61-90 days", "61–90 days"), ("Over 90 days", "Over 90 days")]
for (tx, tw), (bk, bl) in zip(cols([1] * 6, cx + 8, cw - 16, 6), bands):
    V += kpi(tx, R1Y + 28, tw, R1H - 34, z, Mx("Work on hand"), bl, sub=Mx("Sub: band share"), color=bandmap[bk], size=20, filters=[cat_filter(BAND, [bk])])
    z += 2
# row 2: decomposition tree | by individual
R2Y, R2H = R1Y + R1H + GAP, 290
(ax, aw), (bx, bw) = cols([1.45, 1])
z = 40
V += [decomp_tree(ax, R2Y, aw, R2H, z, Mx("Work on hand"), [OT("Division"), TEAM, WF, STEP, PERSON], "Decomposition — Division › Team › Workflow › Step › Individual"),
      barchart(bx, R2Y, bw, R2H, z + 1, PERSON, [Mx("Work on hand")], "Work on hand by individual", series=BAND, stacked=True, colmap=bandmap6,
               sort_by=Mx("Work on hand"), labels=False)]
# row 3: matrix | oldest first
R3Y = R2Y + R2H + GAP; R3H = PAGE_H - 14 - R3Y
(ax, aw), (bx, bw) = cols([1, 1])
z = 50
V += [matrix_vis(ax, R3Y, aw, R3H, z, [TEAM, WF, STEP, PERSON], [], [proj(Mx("Work on hand"), "On hand"), proj(Mx("On hand 0-7"), "0–7"), proj(Mx("On hand 8-15"), "8–15"), proj(Mx("On hand 16-30"), "16–30"),
                                                               proj(Mx("On hand 31-60"), "31–60"), proj(Mx("On hand 61-90"), "61–90"), proj(Mx("On hand 90+"), "90+"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%")],
                 "Matrix — next level with aging buckets"),
      table_vis(bx, R3Y, bw, R3H, z + 1, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Assigned to")), proj(OT("Step"))],
                "Oldest first", sort_by=OT("Age (days)"), filters=[cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")])]
pages.append((PID["Work On Hand"], "Work On Hand", V, [PF_TEAM, PF_LINE, PF_WF, PF_STEP, PF_WHO, PF_AE, PF_CSR, PF_AGENT, PF_DI, PF_AV, PF_BAND, PF_SCOPE]))

# ----------------------------------------------------------------- 3. Renewal pipeline
V = shell("Renewal Pipeline", "All divisions")
z = 10
stage_cards = [("Not yet quoted", RED), ("Quoted - with agent", "#FF8A00"), ("Bound - awaiting issue", OK), ("Not renewing", MUTE)]
R1Y, R1H = Y0, 100
for (xx, ww), (nm, colr) in zip(cols([1] * 4), stage_cards):
    V += kpi(xx, R1Y, ww, R1H, z, Mx(nm), nm, sub=Mx("Renewal stage subtitle"), color=colr, size=24, filters=[cat_filter(OT("Renewal stage"), [nm])])
    z += 2
R2Y, R2H = R1Y + R1H + GAP, 220
(ax, aw), (bx, bw) = cols([1, 1])
z = 20
V += [barchart(ax, R2Y, aw, R2H, z, TEAM, [Mx("Renewals in pipeline")], "Pipeline by team — stage mix", series=OT("Renewal stage"), stacked=True, colmap=STAGE_COL, sort_by=Mx("Renewals in pipeline")),
      barchart(bx, R2Y, bw, R2H, z + 1, OT("Account executive"), [Mx("Renewals in pipeline")], "Pipeline by account executive", series=OT("Renewal stage"), stacked=True, colmap=STAGE_COL, sort_by=Mx("Renewals in pipeline"), labels=False)]
R3Y, R3H = R2Y + R2H + GAP, 196
z = 30
V += [barchart(ax, R3Y, aw, R3H, z, OT("Renewal stage"), [Mx("Renewals in pipeline")], "Stage by aging bucket — from date initiated", series=BAND, stacked=True, colmap=bandmap6,
               sort_by=OT("Renewal stage order"), desc=False),
      barchart(bx, R3Y, bw, R3H, z + 1, STEP, [Mx("Renewals in pipeline"), Mx("Out of service")], "Not yet quoted — by step", color=RED,
               filters=[cat_filter(OT("Renewal stage"), ["Not yet quoted"])], sort_by=Mx("Renewals in pipeline"))]
R4Y = R3Y + R3H + GAP; R4H = PAGE_H - 14 - R4Y - 20
z = 40
V += [table_vis(X0, R4Y, CW, R4H, z, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Account executive"), "Account exec"), proj(OT("Assigned to")), proj(OT("Step")), proj(OT("Date initiated"), "Initiated")],
                "Not yet quoted — oldest first", sort_by=OT("Age (days)"), filters=[cat_filter(OT("Renewal stage"), ["Not yet quoted"]), cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")]),
      textbox(X0, PAGE_H - 32, CW, 20, z + 1, ["Stages are derived from the renewal steps. Quotes go out ~45 days before the effective date. An “expiring” stage needs the policy expiration date, which the current export does not carry."], size=7, color=SUB, bold=False)]
pages.append((PID["Renewal Pipeline"], "Renewal Pipeline", V, [cat_filter(WF, ["Renewal"]), PF_TEAM, PF_LINE, PF_AE, PF_WHO, PF_BAND, PF_DI, PF_AV]))

# ----------------------------------------------------------------- 4. Team scorecard
V = shell("Team Scorecard", "By individual")
z = 5
V += [slicer(X0, Y0, 230, 40, z, SCOPE, "Staff scope — all staff · internal · vendor (RPRO) · shared queues"),
      slicer(X0 + 240, Y0, 300, 40, z + 1, PERSON_KEY, "Individual / queue", single=True),
      textbox(X0 + 550, Y0 + 8, 660, 26, z + 2, ["Pick one individual to score; the Team table at the bottom ranks everyone in the selected scope."], size=8, color=SUB, bold=False)]
R1Y, R1H = Y0 + 48, 100
z = 10
V += kpi_row(R1Y, R1H, [dict(measure=Mx("Work on hand"), title="Items on hand", sub=Mx("Sub: files"), color=NAVY, size=22),
                        dict(measure=Mx("Out of service %"), title="Out of service", sub=Mx("Sub: out of service vs team"), color=RED, size=22, color_measure="Service status colour"),
                        dict(measure=Mx("Oldest item (days)"), title="Oldest item (days)", sub_text="from date initiated", color=RED, size=22),
                        dict(measure=Mx("Received yesterday"), title="Received yesterday", sub_text="inbound — became available", color=NAVY, size=22),
                        dict(measure=Mx("Completed yesterday"), title="Released yesterday", sub_text="outbound — release = completed", color=OK, size=22),
                        dict(measure=Mx("Within SLA on completion %"), title="Within SLA on completion", sub_text="of released", color=NAVY, size=22),
                        dict(measure=Mx("Service status icon"), title="Status", sub_text="against service level", color=NAVY, size=14, color_measure="Service status colour")], z)
R2Y, R2H = R1Y + R1H + GAP, 236
(ax, aw), (bx, bw), (cx, cw) = cols([1, 1, 1])
z = 30
V += [barchart(ax, R2Y, aw, R2H, z, STEP, [Mx("Work on hand")], "On hand by step", series=OT("Service"), stacked=True, colmap={"Within service": ELEC, "Out of service": RED}, sort_by=Mx("Work on hand"),
               filters=[cat_filter(OT("Scheduled"), [False])]),
      barchart(bx, R2Y, bw, R2H, z + 1, BAND, [Mx("Work on hand")], "Age profile", colmap=bandmap, sort_by=BAND_ORDER, desc=False),
      table_vis(cx, R2Y, cw, R2H, z + 2, [proj(CP("Step")), proj(CP("Turnaround (days)"), "Time in step (d)"), proj(CP("SLA (days)"), "SLA"), proj(CP("Met SLA"), "Met")], "Completed yesterday", sort_by=CP("Turnaround (days)"))]
R3Y = R2Y + R2H + GAP; R3H = PAGE_H - 14 - R3Y
(ax, aw), (bx, bw) = cols([2, 1])
z = 40
V += [table_vis(ax, R3Y, aw, R3H, z, [proj(PERSON, "Individual"), proj(Mx("Work on hand"), "On hand"), proj(Mx("Out of service"), "Out of svc"), proj(Mx("Out of service %"), "%"), proj(Mx("Oldest item (days)"), "Oldest"), proj(Mx("Service status icon"), "Status")],
                "Team — ranked by out of service", sort_by=Mx("Out of service %"), color_cols=[(Mx("Service status icon"), "Service status colour")], totals=True),
      barchart(bx, R3Y, bw, R3H, z + 1, PERSON, [Mx("Completed yesterday")], "Released yesterday by person", color=OK, sort_by=Mx("Completed yesterday"))]
pages.append((PID["Team Scorecard"], "Team Scorecard", V, [PF_TEAM, PF_LINE, PF_WF, PF_BAND, PF_DI, PF_AV]))

# ----------------------------------------------------------------- 5. Management
V = shell("Management", "Unassigned · quality")
R1Y, R1H = Y0, 100
z = 10
V += kpi_row(R1Y, R1H, [dict(measure=Mx("Unassigned items"), title="Unassigned items", sub=Mx("Sub: unassigned files"), color=RED, size=24),
                        dict(measure=Mx("Unassigned over 30 days"), title="Unassigned over 30 days", sub=Mx("Sub: unassigned oldest"), color=RED, size=24),
                        dict(measure=Mx("Unassigned out of service %"), title="Unassigned out of service", sub=Mx("Sub: unassigned out of service"), color=NAVY, size=24),
                        dict(measure=Mx("Rework released"), title="Rework released yesterday", sub_text="correction steps", color=NAVY, size=24),
                        dict(measure=Mx("Rework rate"), title="Rework rate", sub_text="of all releases", color=NAVY, size=24),
                        dict(measure=Mx("Production released"), title="Production released", sub_text="releases excluding rework", color=OK, size=24)], z)
UNA = [cat_filter(OT("Is unassigned"), [True])]
R2Y, R2H = R1Y + R1H + GAP, 210
(ax, aw), (bx, bw) = cols([1, 1])
z = 30
V += [barchart(ax, R2Y, aw, R2H, z, WF, [Mx("Work on hand")], "Unassigned by workflow", series=BAND, stacked=True, colmap=bandmap, sort_by=Mx("Work on hand"), filters=UNA),
      barchart(bx, R2Y, bw, R2H, z + 1, TEAM, [Mx("Work on hand")], "Unassigned by team", series=BAND, stacked=True, colmap=bandmap, sort_by=Mx("Work on hand"), filters=UNA)]
R3Y, R3H = R2Y + R2H + GAP, 196
z = 40
V += [barchart(ax, R3Y, aw, R3H, z, WF, [Mx("Completed yesterday")], "Production vs rework — released yesterday by workflow", series=CP("Release type"), stacked=True, colmap={"Production": OK, "Rework": AMBER}, sort_by=Mx("Completed yesterday")),
      barchart(bx, R3Y, bw, R3H, z + 1, STEP, [Mx("Rework released")], "Rework by step", color=AMBER, filters=[cat_filter(CP("Is rework"), [True])], sort_by=Mx("Rework released"))]
R4Y = R3Y + R3H + GAP; R4H = PAGE_H - 14 - R4Y
z = 50
V += [table_vis(X0, R4Y, CW, R4H, z, [proj(OT("Age (days)"), "Age"), proj(OT("SLA (days)"), "SLA"), proj(OT("File number"), "File"), proj(OT("Insured")), proj(OT("Workflow")), proj(OT("Step")), proj(OT("Team")), proj(OT("Date initiated"), "Initiated")],
                "Unassigned — oldest first", sort_by=OT("Age (days)"), filters=UNA + [cat_filter(OT("Scheduled"), [False])], bold_cols=[OT("Age (days)")])]
pages.append((PID["Management"], "Management", V, [PF_TEAM, PF_LINE, PF_WF, PF_BAND, PF_DI]))

# ----------------------------------------------------------------- 6. Compliance
V = shell("Compliance", "Due date and state")
R1Y, R1H = Y0, 100
z = 10
V += kpi_row(R1Y, R1H, [dict(measure=Mx("Past due"), title="Past due date", sub=Mx("Sub: past due stuck"), color=DRED, size=24),
                        dict(measure=Mx("Past due - fining states"), title="Past due — fining states", sub_text="NY only until the state list arrives", color=DRED, size=24),
                        dict(measure=Mx("Due within 14 days"), title="Due within 14 days", sub_text="red — needs hand-off", color=RED, size=24),
                        dict(measure=Mx("Due in 15-30 days"), title="Due in 15–30 days", sub_text="amber", color=AMBER, size=24),
                        dict(measure=Mx("On track"), title="On track", sub_text="due beyond 30 days", color=OK, size=24),
                        dict(measure=Mx("Open filings"), title="Open items", sub=Mx("Sub: open filings"), color=NAVY, size=24)], z)
R2Y, R2H = R1Y + R1H + GAP, 270
(ax, aw), (bx, bw), (cx, cw) = cols([1.35, 1, 0.8])
z = 30
V += [table_vis(ax, R2Y, aw, R2H, z, [proj(CM("Filing state"), "State"), proj(Mx("Fining state flag"), "Fines"), proj(Mx("Past due")), proj(Mx("Due within 14 days"), "≤ 14 d"), proj(Mx("Due in 15-30 days"), "15–30 d"), proj(Mx("On track")), proj(Mx("Open filings"), "Open"), proj(Mx("Oldest past due (days)"), "Oldest past due")],
                "By state — fining states first, then past due", sort_by=Mx("Past due"), bold_cols=[Mx("Past due"), Mx("Fining state flag")]),
      barchart(bx, R2Y, bw, R2H, z + 1, PERSON, [Mx("Open filings")], "By associate — who has it", series=CM("Due band"), stacked=True, colmap=DUE_COL, sort_by=Mx("Open filings")),
      barchart(cx, R2Y, cw, R2H, z + 2, BAND, [Mx("Open filings")], "Age from date initiated", colmap=bandmap, sort_by=BAND_ORDER, desc=False)]
R3Y = R2Y + R2H + GAP; R3H = PAGE_H - 14 - R3Y
z = 40
V += [table_vis(X0, R3Y, CW, R3H, z, [proj(CM("Due band"), "Status"), proj(CM("Fining state"), "Fines"), proj(CM("Due date")), proj(CM("Days past due"), "Days"), proj(CM("File name"), "File name (key)"), proj(CM("State")), proj(CM("UA"), "Has it (UA)"), proj(CM("Assigned to")), proj(CM("Team")), proj(CM("Age (days)"), "Age"), proj(CM("Note"))],
                "Action list — past due first, then due within 14 days", sort_by=CM("Days past due"), filters=[cat_filter(CM("Due band code"), ["past", "red"])], bold_cols=[CM("Days past due")])]
pages.append((PID["Compliance"], "Compliance", V, [pane_filter(CM("Filing state"), "State"), pane_filter(CM("Team")), pane_filter(CM("UA"), "Has it"), pane_filter(CM("Fining state"), "Fines when late")]))

# ----------------------------------------------------------------- 7. Task list (drill-through target)
V = shell("Task list", "Detail")
z = 10
V += [button(X0, Y0, 90, 28, z, "←  Back", back=True),
      textbox(X0 + 100, Y0 + 4, 400, 24, z + 1, ["Drill-through:  ", "the rows below follow the selection you came from (Team · Workflow · Step · Individual · Stage · Age band)"], sizes=[9, 8], colors=[NAVY, SUB], bolds=[True, False])]
# context line (not cards): count · files | out of service | oldest | age mix
CY = Y0 + 36
V += [shape(X0, CY, CW, 36, z + 2, fill="#FFFFFF"),
      cardtext(X0 + 6, CY + 3, 200, 30, z + 3, Mx("Context: tasks and files"), None, size=9, transparent=True, color="#1E2A33", bold=True),
      cardtext(X0 + 210, CY + 3, 240, 30, z + 4, Mx("Context: out of service"), None, size=9, transparent=True, color_measure="Service status colour", bold=True),
      cardtext(X0 + 456, CY + 3, 130, 30, z + 5, Mx("Context: oldest"), None, size=9, transparent=True, color="#1E2A33", bold=True),
      cardtext(X0 + 590, CY + 3, CW - 596, 30, z + 6, Mx("Context: age mix"), None, size=8, transparent=True)]
cols_ = ["Age (days)", "Service", "SLA (days)", "Aging band", "Status", "File number", "Policy number", "Insured", "Brand", "Department", "Team", "Workflow", "Step", "Assigned to", "From user", "Account executive", "CSR", "Agent name", "Date initiated", "Available date"]
TY = CY + 44
V += [table_vis(X0, TY, CW, PAGE_H - 14 - TY, 20, [proj(OT(c)) for c in cols_], "Task list · 20 columns · scroll right for more · Export data from the visual header", sort_by=OT("Age (days)"), bold_cols=[OT("Age (days)")])]
pages.append((PID["Task list"], "Task list", V, [PF_TEAM, PF_WF, PF_STEP, PF_WHO, PF_AE, PF_CSR, PF_AGENT, PF_DI, PF_AV, PF_BAND], [TEAM, WF, STEP, PERSON_KEY, OT("Renewal stage"), BAND]))
# ================================================================= WRITE
import shutil as _sh
if os.path.isdir(PAGES): _sh.rmtree(PAGES)
os.makedirs(PAGES, exist_ok=True)
page_ids = []
for entry in pages:
    pid, disp, vis, pf = entry[0], entry[1], entry[2], entry[3]
    dt = entry[4] if len(entry) > 4 else None
    page_ids.append(page(pid, disp, vis, pf, drillthrough=dt))
with open(os.path.join(PAGES, "pages.json"), "w") as f:
    json.dump({"$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json", "pageOrder": page_ids, "activePageName": page_ids[0]}, f, indent=2)
with open(os.path.join(DEF, "version.json"), "w") as f:
    json.dump({"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, f, indent=2)

THEME = {
    "name": "SPGTheme", "dataColors": [ELEC, NAVY, OK, AMBER, "#FF8A00", RED, "#8B1E3F", MUTE, "#E8702A", SUB],
    "background": "#FFFFFF", "foreground": NAVY, "tableAccent": ELEC, "good": OK, "neutral": AMBER, "bad": RED,
    "textClasses": {"callout": {"fontSize": 26, "fontFace": "Segoe UI Semibold", "color": NAVY}, "title": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": NAVY},
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

THEME_NAME = "Fluent2-CY26SU10"
REPORT = {"$schema": f"{SCHEMA}/report/3.3.0/schema.json",
          "themeCollection": {"baseTheme": {"name": THEME_NAME, "reportVersionAtImport": {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}, "type": "SharedResources"}},
          "objects": {"section": [{"properties": {"verticalAlignment": lit("Top")}}], "outspacePane": [{"properties": {"expanded": lit(False)}}]},
          "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": THEME_NAME, "path": f"BaseThemes/{THEME_NAME}.json", "type": "BaseTheme"}]}],
          "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True, "allowInlineExploration": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}}
import shutil
_bt = os.path.join(RP, "StaticResources", "SharedResources", "BaseThemes"); os.makedirs(_bt, exist_ok=True)
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Fluent2-CY26SU10.json"), os.path.join(_bt, f"{THEME_NAME}.json"))
with open(os.path.join(DEF, "report.json"), "w") as f: json.dump(REPORT, f, indent=2)
with open(os.path.join(RP, "definition.pbir"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
               "datasetReference": {"byPath": {"path": "../SPG Operational Dashboard.SemanticModel"}}}, f, indent=2)
_rid = stable_logical_id(os.path.join(RP, ".platform"))
with open(os.path.join(RP, ".platform"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
               "metadata": {"type": "Report", "displayName": "SPG Operational Dashboard"}, "config": {"version": "2.0", "logicalId": _rid}}, f, indent=2)
with open(os.path.join(ROOT, "SPG Operational Dashboard.pbip"), "w") as f:
    json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
               "artifacts": [{"report": {"path": "SPG Operational Dashboard.Report"}}], "settings": {"enableAutoRecovery": True}}, f, indent=2)
print("report written:", len(pages), "pages,", sum(len(e[2]) for e in pages), "visuals")
