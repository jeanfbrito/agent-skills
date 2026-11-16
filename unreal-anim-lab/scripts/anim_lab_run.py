#!/usr/bin/env python3
"""Run lab commands after startup. Count game frames and stop on invalid probe state.

py "<absolute>/anim_lab_run.py" "physics 1; wait 4; expect physics 1; cam fp; wait 4; expect view fp; shot hold"
The existing command syntax stays valid. Optional expectations remain active until replaced.
"""
import argparse
import os
from pathlib import Path
import runpy
import time
import unreal

LOG = "ANIM_LAB_RUN:"
PREFIX = os.environ.get("ANIM_LAB_PREFIX", "AnimLab")
SHOT_FRAMES = 2
ProbeGuard = runpy.run_path(str(Path(__file__).with_name("probe_guard.py")))["ProbeGuard"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commands", nargs="+")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--ready-timeout", type=float, default=10.0)
    args = parser.parse_args()
    if args.timeout <= 0 or args.ready_timeout <= 0:
        raise ValueError("Timeouts must be positive.")
    steps = [step.strip() for step in " ".join(args.commands).split(";") if step.strip()]
    if not steps:
        raise ValueError("Supply at least one lab command.")
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_game_world()
    if not world:
        raise RuntimeError("Start Play before the lab runner.")
    guard = ProbeGuard()
    state = {"next": 0, "wait": 0, "handle": None, "start": time.monotonic(),
             "candidate": None, "ready_frames": 0, "ready_time": None, "fallback": False}

    def finish(error=None):
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        if error:
            unreal.log_error(f"{LOG} failed: {error}")
        else:
            unreal.log(f"{LOG} done, {len(steps)} steps")

    def ready(pawn, game_time):
        labs = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AnimLabActor)
        if len(labs) != 1:
            raise RuntimeError("Require one active lab actor.")
        lab = labs[0]
        if hasattr(lab, "is_startup_ready"):
            return lab.is_startup_ready(pawn)
        # Older project ports need a conservative completed-frame wait.
        # State expectations still check what the script actually measures.
        if not state["fallback"]:
            unreal.log_warning(f"{LOG} no startup-ready API. Using startup delay plus two game frames.")
            state["fallback"] = True
        if pawn != state["candidate"]:
            state.update(candidate=pawn, ready_frames=0, ready_time=game_time)
        elif game_time != state["ready_time"]:
            state["ready_frames"] += 1
            state["ready_time"] = game_time
        return state["ready_frames"] >= lab.get_editor_property("startup_delay_frames") + 2

    def tick(_delta):
        try:
            elapsed = time.monotonic() - state["start"]
            if elapsed > args.timeout:
                raise RuntimeError("The lab sequence exceeded its time limit.")
            if editor.get_game_world() != world:
                raise RuntimeError("The measured Play world ended.")
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            alive = bool(pawn and unreal.SystemLibrary.is_valid(pawn)
                         and (not hasattr(pawn, "is_dead") or not pawn.is_dead()))
            game_time = unreal.GameplayStatics.get_time_seconds(world)
            is_ready = ready(pawn, game_time) if alive else False
            if not guard.started and elapsed > args.ready_timeout:
                raise RuntimeError("The lab did not finish startup within the readiness timeout.")
            physics = view = None
            speed = pawn.get_velocity().length() if alive else 0.0
            if guard.physics is not None and alive:
                ragdoll = pawn.get_editor_property("active_ragdoll")
                limbs = ragdoll.get_editor_property("limb_physics")
                physical_gun = ragdoll.has_physical_gun()
                physics = limbs if limbs == physical_gun else None
            if guard.view is not None and alive:
                view = "fp" if pawn.get_controller().get_view_target() == pawn else "external"
            if not guard.sample(game_time, pawn, alive, is_ready, physics, view, speed):
                return
            if state["wait"] > 0:
                state["wait"] -= 1
                return
            while state["next"] < len(steps):
                step = steps[state["next"]]
                state["next"] += 1
                words = step.split()
                if words[0] == "wait":
                    state["wait"] = int(words[1]) if len(words) > 1 else 3
                    if state["wait"] < 0:
                        raise ValueError("Frame waits cannot be negative.")
                    return
                if words == ["expect", "clear"]:
                    guard.finish()
                    guard.physics = guard.view = guard.motion_min = None
                    guard.moved = False
                    continue
                if words[0] == "expect":
                    if len(words) != 3:
                        raise ValueError("Use expect physics 0|1, expect view fp|external, or expect movement <cm/s>.")
                    if words[1] == "physics" and words[2] in ("0", "1"):
                        guard.physics = words[2] == "1"
                    elif words[1] == "view" and words[2] in ("fp", "external"):
                        guard.view = words[2]
                    elif words[1] == "movement":
                        guard.motion_min = float(words[2])
                        if not 0 < guard.motion_min < float("inf"):
                            raise ValueError("The movement threshold must be finite and positive.")
                        guard.moved = False
                    else:
                        raise ValueError("Unknown probe expectation.")
                    return # Check the observed state before another command or capture.
                command = step[1:] if step.startswith("!") else PREFIX + " " + step
                unreal.SystemLibrary.execute_console_command(world, command)
                if words[0] in ("shot", "snap"):
                    state["wait"] = SHOT_FRAMES
                    return
            guard.finish()
            finish()
        except Exception as error:
            finish(str(error))

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    unreal.log(f"{LOG} started, {len(steps)} steps")


if __name__ == "__main__":
    main()
