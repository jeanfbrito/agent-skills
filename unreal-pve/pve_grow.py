"""pve_grow.py <spec.json>: grow a plant with the Procedural Vegetation Editor (PVE, UE 5.8) from a sample graph.

Run in the editor:  py "<abs path>/pve_grow.py" "<abs path>/spec.json"
Spec (JSON):
  {"sample": "/ProceduralVegetationEditor/SampleAssets/StarterContent/DeciduousTree_01/PVE_Sample_Deciduous_Tree_01",
   "out": "/Game/Trees/PVE_MyTree",           # copied from the sample on the first run
   "grower": "PVGrowerSettings_6",             # the node's settings object name; "" lists the growers and stops
   "cycles": 45,                               # optional: the CreateConstant node that feeds GrowthCycles
   "changes": {"PlantTargetLength": "16.000000", "Corymb": "1.000000", ...}}   # FPVGrowerParams text fields
Each run starts from the SAMPLE's grower text, so a field removed from "changes" goes back to the sample value.
It checks every changed field came back (import_text stops at the first field it cannot read), saves the asset,
opens the PVE editor, and logs PVE_GROW: start / done.
"""
import json
import re
import sys

import unreal

LOG = "PVE_GROW:"
unreal.log(f"{LOG} start")
# a field that is not in the sample text goes into the struct it belongs to (seen in PVGrowerParams.h)
PARENT = {"PlantTargetLength": "TrunkGrowth", "BranchTargetLength": "TrunkGrowth", "Corymb": "TrunkGrowth",
          "ApicalParentGrowth": "TrunkGrowth", "BranchScale": "TrunkGrowth", "AxillaryPriorityGradient": "TrunkGrowth",
          "GravitationalForce": "GravityParams"}


def set_field(text, key, value):
    """key=value in the exported struct text: replace a scalar or a balanced (...) group, else add it."""
    m = re.search(r"(?<![A-Za-z])" + key + r"=", text)
    if m:
        start = i = m.end()
        if text[start] == "(":
            depth = 0
            while True:
                depth += {"(": 1, ")": -1}.get(text[i], 0)
                i += 1
                if depth == 0:
                    break
        else:
            while text[i] not in ",)":
                i += 1
        return text[:start] + value + text[i:]
    parent = PARENT.get(key)
    if parent and parent + "=(" in text:
        at = text.index(parent + "=(") + len(parent) + 2
        return text[:at] + f"{key}={value}," + text[at:]
    return text[:1] + f"{key}={value}," + text[1:]


def graph_settings(asset):
    graph = unreal.find_object(None, asset.get_path_name() + ":ProceduralVegetationGraph")
    return {n.get_settings().get_name(): n.get_settings() for n in graph.get_editor_property("nodes")}


spec = json.load(open(sys.argv[1], encoding="utf-8"))
sample = graph_settings(unreal.load_asset(spec["sample"]))
growers = [k for k, s in sample.items() if s.get_class().get_name() == "PVGrowerSettings"]
if not spec.get("grower"):
    for k in growers:
        unreal.log(f"{LOG} grower {k}: {sample[k].get_editor_property('grower_params').export_text()[:160]}")
    unreal.log(f"{LOG} done")
    raise SystemExit
if not unreal.EditorAssetLibrary.does_asset_exist(spec["out"]):
    unreal.EditorAssetLibrary.duplicate_asset(spec["sample"], spec["out"])
asset = unreal.load_asset(spec["out"])
settings = graph_settings(asset)
text = sample[spec["grower"]].get_editor_property("grower_params").export_text()
changes = spec.get("changes", {})
for key, value in changes.items():
    text = set_field(text, key, value)
fresh = unreal.PVGrowerParams()
fresh.import_text(text)
settings[spec["grower"]].set_editor_property("grower_params", fresh)
back = settings[spec["grower"]].get_editor_property("grower_params").export_text()
lost = [k for k, v in changes.items() if f"{k}={v}" not in back and not (v.startswith("(") and f"{k}=(" in back)]
if lost or back.count("=") < text.count("=") * 0.95:
    unreal.log_error(f"{LOG} lost {lost}; sent {text.count('=')} fields, got {back.count('=')}\nSENT {text}\nGOT  {back}")
    raise RuntimeError(f"{LOG} the grower text did not import")
if "cycles" in spec:
    constant = next(s for s in settings.values() if s.get_class().get_name() == "PCGCreateAttributeSetSettings")
    values = constant.get_editor_property("attribute_types")
    values.set_editor_property("double_value", float(spec["cycles"]))
    constant.set_editor_property("attribute_types", values)
unreal.EditorAssetLibrary.save_asset(spec["out"], only_if_is_dirty=False)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([asset])
unreal.log(f"{LOG} {spec['out']}: {len(changes)} fields set")
unreal.log(f"{LOG} done")
