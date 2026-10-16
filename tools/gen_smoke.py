import os, json, uuid, sys
sys.argv = ["x"]
os.environ["PBIP_ROOT"] = "/home/claude/repo"
import importlib.util
spec = importlib.util.spec_from_file_location("gr", "/home/claude/gen/gen_report.py")
# load only helper definitions: exec the file up to the 'pages = []' marker
src = open("/home/claude/gen/gen_report.py").read().split("pages = []")[0]
g = {}
exec(src, g)
RP = os.path.join("/home/claude/repo", "SPG Smoke Test.Report")
PAGES = os.path.join(RP, "definition", "pages")
os.makedirs(PAGES, exist_ok=True)
g["PAGES"] = PAGES; g["RP"] = RP
V = [g["textbox"](8, 6, 620, 30, 0, ["SMOKE TEST", "   one page, four visuals"], size=14),
     g["slicer"](900, 4, 180, 42, 1, g["TEAM"], "Team"),
     g["card"](8, 52, 300, 120, 2, g["Mx"]("Work on hand"), "Work on hand"),
     g["barchart"](320, 52, 600, 300, 3, g["WF"], [g["Mx"]("Work on hand")], "Work on hand by workflow", sort_by=g["Mx"]("Work on hand"))]
pid = g["page"](None, "Smoke", V, None, 0)
json.dump({"$schema": f"{g['SCHEMA']}/pagesMetadata/1.1.0/schema.json", "pageOrder": [pid], "activePageName": pid}, open(os.path.join(PAGES, "pages.json"), "w"), indent=2)
json.dump({"$schema": f"{g['SCHEMA']}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, open(os.path.join(RP, "definition", "version.json"), "w"), indent=2)
import shutil
_bt = os.path.join(RP, "StaticResources", "SharedResources", "BaseThemes"); os.makedirs(_bt, exist_ok=True)
shutil.copy("/home/claude/gen/Fluent2-CY26SU10.json", os.path.join(_bt, "Fluent2-CY26SU10.json"))
json.dump({"$schema": f"{g['SCHEMA']}/report/3.3.0/schema.json",
           "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU10", "reportVersionAtImport": {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}, "type": "SharedResources"}},
           "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": "Fluent2-CY26SU10", "path": "BaseThemes/Fluent2-CY26SU10.json", "type": "BaseTheme"}]}],
           "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True}}, open(os.path.join(RP, "definition", "report.json"), "w"), indent=2)
json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../SPG Operational Dashboard.SemanticModel"}}}, open(os.path.join(RP, "definition.pbir"), "w"), indent=2)
json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "Report", "displayName": "SPG Smoke Test"}, "config": {"version": "2.0", "logicalId": g["stable_logical_id"](os.path.join(RP, ".platform"))}}, open(os.path.join(RP, ".platform"), "w"), indent=2)
print("smoke report written")
