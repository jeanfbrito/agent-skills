"""Run a list of Anim Lab commands during Play, with waits between them (unreal-anim-lab skill).

py "<abs>/anim_lab_run.py" "clip tactical; time 0.6; wait 3; shot tac_060; cam front; wait 2; shot tac_060_front"

- Commands are separated by ";". Each one is the text after "AnimLab" on the console.
- "wait <frames>" waits that many frames (default 3). The body pose follows the clock one frame later: wait 2 or
  more after a time change, before a shot.
- The engine writes a screenshot at the end of the next frame. A command after "shot" or "snap" in the same frame
  changes the picture, so the script waits SHOT_FRAMES frames after them.
- "!<console command>" runs a console command without the "AnimLab" prefix ("!stat fps").
The script returns at once. It logs "ANIM_LAB_RUN: done" when the last command ran.
"""
import os
import sys

import unreal

LOG = "ANIM_LAB_RUN:"
# the console verb of the lab (the reference lab registers "AnimLab")
PREFIX = os.environ.get("ANIM_LAB_PREFIX", "AnimLab")
SHOT_FRAMES = 2

steps = [step.strip() for step in " ".join(sys.argv[1:]).split(";") if step.strip()]
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    raise RuntimeError(f"{LOG} no game world: click Play first")

state = {"next": 0, "wait": 0, "handle": None}


def tick(_delta):
    if state["wait"] > 0:
        state["wait"] -= 1
        return
    while state["next"] < len(steps):
        step = steps[state["next"]]
        state["next"] += 1
        words = step.split()
        if words[0] == "wait":
            state["wait"] = int(words[1]) if len(words) > 1 else 3
            return
        command = step[1:] if step.startswith("!") else PREFIX + " " + step
        unreal.SystemLibrary.execute_console_command(world, command)
        if words[0] in ("shot", "snap"):
            state["wait"] = SHOT_FRAMES
            return
    unreal.unregister_slate_post_tick_callback(state["handle"])
    unreal.log(f"{LOG} done, {len(steps)} steps")


state["handle"] = unreal.register_slate_post_tick_callback(tick)
unreal.log(f"{LOG} {len(steps)} steps")
