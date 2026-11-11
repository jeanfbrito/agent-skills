"""Set properties on every actor of a class in the Play world: the A/B switch for a before/after check.

py "<abs>/pie_set.py" <PythonClassName> <path>=<value> [<path>=<value> ...]

<path> is a property, or a property of a struct property, in snake_case: "hands.finger_reach", "hands.left_arm.upper_bone".
<value> is JSON (0.5, true, "Arm_Upper_L", null for an empty name). Only the Play world changes, not the asset.
Example: py ".../pie_set.py" ShooterWeapon hands.finger_reach=0 hands.left_arm.upper_bone=null
Logs "PIE_SET:" lines; read them with `ue.sh wait-log PIE_SET`.
"""
import json
import sys

import unreal

LOG = "PIE_SET:"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    raise RuntimeError(f"{LOG} no game world: start Play first")
cls = getattr(unreal, sys.argv[1], None)
if cls is None:
    raise RuntimeError(f"{LOG} no class unreal.{sys.argv[1]}")


def set_path(obj, parts, value):
    """struct properties are copies: change the copy, then write it back"""
    if len(parts) == 1:
        obj.set_editor_property(parts[0], value)
        return obj
    child = obj.get_editor_property(parts[0])
    obj.set_editor_property(parts[0], set_path(child, parts[1:], value))
    return obj


changes = []
for arg in sys.argv[2:]:
    path, text = arg.split("=", 1)
    value = json.loads(text)
    changes.append((path.split("."), "None" if value is None else value))

count = 0
for actor in unreal.GameplayStatics.get_all_actors_of_class(world, cls):
    for parts, value in changes:
        set_path(actor, parts, value)
    count += 1
    unreal.log(f"{LOG} {actor.get_name()} {' '.join(sys.argv[2:])}")
unreal.log(f"{LOG} done, {count} actors")
