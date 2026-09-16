---
name: procedural-animation
description: Routes character and procedural animation problems to the technique that solves them - foot sliding and foot locking, leg-chain and two-bone IK, locomotion and movement models, springs/dampers/inertialization, motion matching, and rotation representations for neural networks. Use when implementing or debugging character movement, foot contact, animation blending, offset decay, or animation data fed to a model. Triggered by "foot sliding", "foot locking", "two-bone IK", "inverse kinematics", "locomotion model", "character feels floaty", "spring damper", "inertialization", "motion matching", "unroll rotations", "procedural animation".
---

# Procedural Animation

Reference corpus for character and procedural animation, distilled from
Daniel Holden's (orangeduck) body of work, 2017-2026. Self-contained: every
technique below is here or in `references/`, no vault or network needed.

**Provenance.** Derived from 12 sources (10 articles, 2 repos) captured
verbatim in the Obsidian vault at `/Users/jean/Github/mindness` under
`raw/articles/`, compiled into 10 `Knowledge/` notes. Entry point there:
`Projects/Character Animation - orangeduck.md`. The vault holds the full
text and the per-claim provenance; this skill holds the working answer.
Single-author corpus - weigh it as one very experienced practitioner's
position, not field consensus.

## Route the problem first

| Problem | Read | Key answer |
|---|---|---|
| Feet slide on the ground | `references/foot-locking.md` | It is a **velocity** error, not position or friction |
| Place a foot/end effector on a target | `references/foot-locking.md` | Solve toe target, derive heel, two-bone IK, orient toe |
| Two-bone IK from scratch, or a knee that pops | `references/foot-locking.md` | Cosine rule; clamp before `acos`; use a knee side vector, not a pole vector |
| Label foot contacts in animation data | `references/foot-locking.md` | Threshold toe **velocity** (0.5-0.1 m/s), not height |
| Remove slide from a whole clip offline | `references/foot-locking.md` | Constraint relaxation, PBD style |
| Character drifts from its capsule, or feels floaty | `references/displacement-and-movement.md` | Simulation object vs character entity; velocity-limited adjustment + clamping |
| Design or tune a locomotion model | `references/displacement-and-movement.md` | The four-layer parameter ladder |
| Any damper, spring, or inertializer | Below, then `references/springs.md` | `simple_spring_damper_exact` is the default |
| Spring NaNs, explodes, or is framerate dependent | `references/springs.md` | Two standard bugs; both listed there |
| Blend between two animation sources without a pop | Below, then `references/springs.md` | Inertialization: decay the offset, evaluate one stream |
| Make a mocap clip loop | `references/springs.md` | Inertialize the clip against itself |
| Select animation from a mocap database | `references/learning-based.md` | Motion matching, and its learned replacement |
| Feed varying/ragged input to a network | `references/learning-based.md` | Control Operators |
| Rotation data with jumps; rotations into a model | `references/learning-based.md` | Unroll first; 6D (two matrix columns) for networks |

Reference paths, absolute (this skill is symlink-installed, so relative
paths break):

- `~/Github/agent-skills/procedural-animation/references/springs.md`
- `~/Github/agent-skills/procedural-animation/references/foot-locking.md`
- `~/Github/agent-skills/procedural-animation/references/displacement-and-movement.md`
- `~/Github/agent-skills/procedural-animation/references/learning-based.md`

## Four principles that decide most designs

1. **Design in velocity, not position.** Foot sliding is a velocity error;
   locomotion models are expressed in velocity with position as a single
   final integration; matching data to a controller means matching velocity
   and acceleration *distributions*. Ask "what velocity am I preserving,
   and whose" before "where should this be".
2. **Two objects, and the gap between them is the problem.** A code-driven
   collision proxy (responsive) and a data-driven visible character
   (realistic) will disagree. Every technique manages that gap; none
   eliminates it. Get the vocabulary right before picking a fix.
3. **Reach for a second-order smoother before a learned model.** Damper,
   critically damped spring, velocity spring, double spring,
   inertialization, soft exponential clamp. In this corpus these answer
   five separate problems; the ML exists to remove a scaling cost, never to
   replace the hand-built control model.
4. **Every smoother needs an escape hatch.** Velocity-ratio limits, hard
   clamps, lock/unlock distances, soft max extension. The smoother handles
   the common case; a bound handles the case where it would look absurd.

Two corollaries worth applying by default: give position and rotation
**separate** dials and make rotation the gentler one (over-responsive
rotation makes a character spin on the spot for no control gain); and
prefer letting designers **label the data** over embedding behaviour in
states or modes.

## The code you will reach for most

Stable at any `dt`, parameterised by `halflife`. `fast_negexp` is a
polynomial approximation of `exp(-x)`; `halflife_to_damping` is
`(4 * ln2) / halflife`.

```c
float fast_negexp(float x)
{
    return 1.0f / (1.0f + x + 0.48f*x*x + 0.235f*x*x*x);
}

float halflife_to_damping(float halflife, float eps = 1e-5f)
{
    return (4.0f * 0.69314718056f) / (halflife + eps);
}

// Smooth toward a goal, no velocity continuity.
float damper_exact(float x, float g, float halflife, float dt, float eps=1e-5f)
{
    return lerp(x, g, 1.0f - fast_negexp((0.69314718056f * dt) / (halflife + eps)));
}

// Smooth toward a goal WITH velocity continuity. The default choice.
void simple_spring_damper_exact(float& x, float& v, float x_goal,
                                float halflife, float dt)
{
    float y = halflife_to_damping(halflife) / 2.0f;
    float j0 = x - x_goal;
    float j1 = v + j0*y;
    float eydt = fast_negexp(y*dt);

    x = eydt*(j0 + j1*dt) + x_goal;
    v = eydt*(v - j1*y*dt);
}

// Decay an offset to zero. The inertialization workhorse.
void decay_spring_damper_exact(float& x, float& v, float halflife, float dt)
{
    float y = halflife_to_damping(halflife) / 2.0f;
    float j1 = v + x*y;
    float eydt = fast_negexp(y*dt);

    x = eydt*(x + j1*dt);
    v = eydt*(v - j1*y*dt);
}

// Inertialization: blend between two animation streams by decaying their
// offset, so only one stream is ever evaluated.
void inertialize_transition(float& off_x, float& off_v,
                            float src_x, float src_v, float dst_x, float dst_v)
{
    off_x = (src_x + off_x) - dst_x;
    off_v = (src_v + off_v) - dst_v;
}

void inertialize_update(float& out_x, float& out_v, float& off_x, float& off_v,
                        float in_x, float in_v, float halflife, float dt)
{
    decay_spring_damper_exact(off_x, off_v, halflife, dt);
    out_x = in_x + off_x;
    out_v = in_v + off_v;
}
```

**Never** ship `lerp(x, g, factor)` per frame (framerate dependent) or
`lerp(x, g, damping * dt)` (explodes once `damping * dt > 1`). Precompute
`y` and `eydt` when many springs share a `halflife` and `dt`.

**Exponential vs cubic inertialization.** Exponential (above) needs no
memory of the transition time and is very fast, but leaves a small residual
offset that is visible in slow motion and can overshoot. Cubic reaches
exactly zero by `blendTime`. Prefer cubic where the end state must be exact
- offline clip work, and foot contact locking. Both are in
`references/springs.md`.

## Applying this

- Say which source claim a recommendation rests on, and its date. Marked
  `stated` claims are the author's; anything else is inference.
- Treat every "looks good" or "feels responsive" claim as one
  practitioner's judgement. The corpus contains **no player-perception
  measurement**; its one user study tested designer usability.
- Prefer the newest source when two conflict, and say that they conflict.
  The known case: 2021 foot locking used an exponential inertializer, 2026
  uses cubic plus a lock-distance gate and advises never locking the heel.
- Verify engine API names before relying on one. Unreal Mover and Character
  Movement Component names are version-specific (UE 5.7 as of 2026-01).
- **Licence trap:** the `orangeduck/Motion-Matching` code is MIT, but the
  animation data needed to regenerate its database is CC BY-NC-ND 4.0
  (non-commercial, no derivatives). The code licence does not cover the
  data.

## Not covered - say so instead of extrapolating

Physics-based animation and ragdolls; arm, hand, look-at, or full-body IK
(only the leg chain); facial animation; blend trees and state machines;
retargeting and skeleton mapping; cloth, hair, secondary motion; animation
compression, streaming, budgets; networked animation beyond "clamping
bounds worst-case deviation"; terrain adaptation past a single ground-plane
clamp (dynamic terrain needs a raycast).

Outside that range, answer from first principles and label it as such.
