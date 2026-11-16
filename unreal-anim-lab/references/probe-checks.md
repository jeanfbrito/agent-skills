# Probe validity

Use the existing lab runner and project adapters. Do not build another private runner for each check.

## Startup and state

`~/Github/agent-skills/unreal-anim-lab/scripts/anim_lab_run.py` waits for the actor's `IsStartupReady(Pawn)` signal before issuing commands.
The reference actor reports readiness only after all startup commands succeed.
Older ports use the configured startup delay plus two completed game frames, with a warning. This fallback cannot prove command success.

The runner stops on pawn death or replacement, world loss, clock reversal, and timeout.
Set explicit expectations for the conditions that affect the measurement:

- `expect physics 1`: both limb simulation and the physical-gun load must be active.
- `expect physics 0`: both must be inactive.
- `expect view fp`: the pawn must own the view target.
- `expect view external`: another actor must own the view target. This does not prove a specific orbit angle.
- `expect movement 20`: require speed of at least 20 cm/s before completion.

Expectations stay active until replaced. Apply them after a settle wait, before the capture.
Use `expect clear` to finish the current checks before changing modes.
The console API does not return command success. Use expectations and inspect the log before treating a command as successful.
The physics check uses the reference project's `active_ragdoll` adapter. Port it with the rest of the lab bindings.
A movement request is not proof of movement. Walls, input guards or a dead pawn can prevent it.
Do not teleport a simulated pawn to prepare a measurement without a deliberate reset and settle procedure.

The runner counts a frame only when game time advances. Multiple Slate callbacks at one game time do not consume waits.
The game clock is a fallback frame identity. A paused game therefore does not complete frame waits.
The wall-clock timeout stops a stalled sequence without pretending that a pose advanced.

## Firing checks

A physical-shot counter counts successful physical impulses, not necessarily every bullet.
Check the physical-gun state throughout the measured phase. Let chamber events finish before reconciling ammunition.

`~/Github/agent-skills/unreal-anim-lab/scripts/probe_guard.py` provides `check_firing` for project probes.
Supply actual shot times, the required interval, its tolerance, ammunition before/after, and the physical-shot count.
The check rejects duplicate times, disagreeing counters and a mean interval outside tolerance.
Record frame timing separately. Frame-rounded intervals can alternate while the mean meets the intended rate.
A minimum shot count alone cannot prove cadence.

This helper checks the supplied observations. It does not prove that a probe observed projectiles or that its timestamp source is valid.
For release/cancellation checks, record the trigger-release time and the allowed pending-shot boundary separately.

## Focused tests

Run `python -X utf8 -I -B -m unittest discover -s ~/Github/agent-skills/unreal-anim-lab/tests -v`.
The synthetic checks cover delayed readiness, repeated callbacks, physical-mode reset, actor loss, wrong views, blocked movement and incorrect cadence.
They do not prove the C++ reference compiles in a new project or that the rendered view matches the requested camera.
Port the reference, build it, and inspect a real capture before claiming those results.
