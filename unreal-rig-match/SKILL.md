---
name: unreal-rig-match
description: Makes an Unreal character body follow a reference rig animation of another skeleton and size - first person arms rigged to a weapon or tool, a mocap or game rig - by moving the prop as the rig moves, putting hands with knuckle-frame offsets and two bone IK, matching finger directions then fingertip reach, and copying the elbow or knee bend side, then proves it in the Anim Lab. Use when a body must hold, reload or use a prop like a reference animation, or when hands, fingers, elbows or contacts do not match the reference. Triggered by "use the arms animation as reference", "the rig already has the arms animated", "retarget the hands to the gun", "hands on the new weapon", "fingers don't match the rig", "the elbow is glued to the body", "match the body to the reference animation".
---

# Match a body to a reference rig

Tools: `unreal-editor-loop` (editor, builds, logs) and `unreal-anim-lab` (measure and prove). Worked example and
numbers: `~/Github/agent-skills/unreal-rig-match/references/example-rifle-reload.md`.

## Principles (do not re-derive)

1. **The prop is the shared frame.** Sample the reference rig without a mesh (component space). Express each rig
   bone in prop space: `X_prop = X_rig · Prop(t)⁻¹ · Prop(hold)`. The prop moves on the body by
   `delta = Prop(hold)⁻¹ · Prop(t)`. The body never needs the rig's camera or shoulders.
2. **One hand holds the prop** (fixed grip transform from the hold pose). The other hand follows the rig with
   two-bone IK. Choose the holding hand by what the action does (a reload: the trigger hand holds).
3. **Align hands by a knuckle frame, not by the wrist**: origin on the middle knuckle, X wrist → that knuckle, Y little
   → index knuckle. Body and rig palms differ (a game mannequin palm can be ~1.3–1.85× a first person rig palm).
4. **Fingers in two passes.** Pass 1: turn each segment parallel to the rig segment, from the knuckle to the tip.
   Pass 2 (reach): bend the middle joints by one angle about the rig finger plane normal (bisection on the
   knuckle-to-tip distance). Then turn the knuckle so the tip is on the rig tip. Search the angle from the straightest finger, or an unreachable finger
   bends backwards. A body bone chain with no tip bone: estimate the tip as last joint + ~0.85 × previous segment.
   **Reach fit**: after the knuckle-frame alignment, move the whole hand (no turn) by the smallest shift that puts
   every fingertip in reach (finger length × ~0.97). A short index otherwise cannot reach the trigger and the grip
   is not wrapped. Leave the thumb out of the fit when its base is far off: it pulls the palm off the grip.
5. **Elbows and knees: copy the side, not the position.** Side = rig elbow minus its projection on the rig
   shoulder-to-wrist line, in prop space. Pole = middle of the body shoulder-to-hand line + side × ~50 cm. Re-solve
   two-bone IK with the same hand transform. A fixed "elbow down" pole glues the elbow to the ribs.
6. **Order in the pose evaluation**: prop move → other hand IK → elbows → fingers → (aim, sights). The later
   steps use the moved elbow as their pole, so they keep the elbow side.

## Steps

1. **Inspect the source.** List the rig bones and parents (for a glb: the nodes of its JSON chunk). Find the
   clips (hold, actions), the prop bone, the wrists, the arms and the finger chains (with tip bones or not). Note the license: private reference assets stay out of git.
2. **Prepare and import.** Remove the rig-only meshes. Put the prop grip at the origin, like the other props. Give
   the final asset name before the import: a rename of a used asset breaks references. Use the project's import path
   (UE 5.8 Interchange: `InterchangeManager.import_asset` with `override_pipelines`, then save).
3. **Measure the action steps** in the rig clips (contact out/in, pouch low point, bolt) from bone curves.
4. **Data struct on the prop** (one place). It holds the clips, the prop bone, the hand bone and offset, and the
   grip. It also holds the finger chains (body bones ↔ rig bones), finger weight and reach, the arm bone triples
   and the step times. A setup script writes it, compiles the Blueprint and saves. It logs a unique prefix and can rerun.
5. **Anim code** in the body anim instance proxy (C++ `Evaluate_WithRoot` after the graph): the steps of principle 6.
   Expose diagnostics (`GetLast...`) for the lab.
6. **Prove it** with the lab. Use the hand and finger presets and sweep every clip. Take shots front, side, top and
   first person at each step time, and a before/after sheet per change. Targets:
   - free hand vs its target ≤ 1 cm
   - holding hand vs rig wrist: a few cm, by design (fixed grip)
   - reachable fingertips ≤ 1 cm mean
   - elbows on the rig side, and a clear first person view.
7. **Explain what stays out** with numbers (`get` knuckle bases and lengths). Proportion gaps need a hand scale or
   another body: ask the user, keep the current default, make a change opt-in.
8. **Document** the data source, numbers and limits in the project `AGENTS.md`.
