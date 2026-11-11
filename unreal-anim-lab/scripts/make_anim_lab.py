"""Anim Lab level: a light level to test a character body, its props and animations (unreal-anim-lab skill).

py "<abs>/make_anim_lab.py" [--level /Game/Dev/AnimLab/Lvl_AnimLab] [--game-mode /Game/Path/BP_GameMode.BP_GameMode_C]
                            [--lab-class AnimLabActor]

It makes the level (not World Partition): a 60 m floor with the world grid (1 m squares help to read sizes), a wall
10 m ahead (an aim trace target), a sun, a sky, a sky light, a player start, the lab actor (unreal.<lab-class>, skipped
when the class does not exist yet), and the game mode. No AI, no streaming: it runs fast in the background.
It can run again: it opens the level and puts back the actors it owns (label prefix "AnimLab_").
"""
import argparse
import sys

import unreal

parser = argparse.ArgumentParser()
parser.add_argument("--level", default="/Game/Dev/AnimLab/Lvl_AnimLab")
parser.add_argument("--game-mode", default="")
parser.add_argument("--lab-class", default="AnimLabActor")
args = parser.parse_args(sys.argv[1:])

LEVEL = args.level
GAME_MODE = args.game_mode
FLOOR_MESH = "/Engine/BasicShapes/Plane.Plane"
FLOOR_MATERIAL = "/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"
TARGET_MESH = "/Engine/BasicShapes/Cube.Cube"
PREFIX = "AnimLab_"
LOG = "ANIM_LAB_LEVEL:"

level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    level_editor.load_level(LEVEL)
else:
    if not level_editor.new_level(LEVEL, False):
        raise RuntimeError(f"{LOG} cannot make {LEVEL}")

# remove the actors of an earlier run
for actor in actors.get_all_level_actors():
    if actor.get_actor_label().startswith(PREFIX):
        actors.destroy_actor(actor)


def spawn(cls, label, location=(0, 0, 0), rotation=(0, 0, 0)):
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator(*rotation))
    actor.set_actor_label(PREFIX + label)
    return actor


def mesh_actor(label, mesh, location, scale, material=None):
    actor = spawn(unreal.StaticMeshActor, label, location)
    component = actor.static_mesh_component
    component.set_static_mesh(unreal.load_asset(mesh))
    if material:
        component.set_material(0, unreal.load_asset(material))
    actor.set_actor_scale3d(unreal.Vector(*scale))
    return actor


# a 60 m floor with the world grid (1 m squares help to read sizes), and a wall 10 m ahead for the aim trace
mesh_actor("Floor", FLOOR_MESH, (0, 0, 0), (60, 60, 1), FLOOR_MATERIAL)
mesh_actor("Wall", TARGET_MESH, (1000, 0, 150), (0.2, 6, 3), FLOOR_MATERIAL)

# light: a sun, a sky (for the sky light capture) and a sky light
sun = spawn(unreal.DirectionalLight, "Sun", (0, 0, 500), (0, -50, -30))  # (roll, pitch, yaw)
sun.light_component.set_editor_property("atmosphere_sun_light", True)
spawn(unreal.SkyAtmosphere, "Sky")
sky = spawn(unreal.SkyLight, "SkyLight", (0, 0, 300))
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)

spawn(unreal.PlayerStart, "PlayerStart", (0, 0, 100))
lab_class = getattr(unreal, args.lab_class, None)
if lab_class:
    spawn(lab_class, "Lab", (0, 0, 20))
else:
    unreal.log_warning(f"{LOG} no class unreal.{args.lab_class} (build the lab C++ first); level made without it")

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
settings = world.get_world_settings()
if GAME_MODE:
    settings.set_editor_property("default_game_mode", unreal.load_class(None, GAME_MODE))

level_editor.save_current_level()
mode = settings.get_editor_property("default_game_mode")
unreal.log(f"{LOG} {LEVEL} saved, {len(actors.get_all_level_actors())} actors, game mode "
           f"{mode.get_name() if mode else 'project default'}")
