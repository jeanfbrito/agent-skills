# Code vs Data Driven Displacement, and Movement Models

Sources: Daniel Holden, "Code vs Data Driven Displacement", 2021-09-23,
https://theorangeduck.com/page/code-vs-data-driven-displacement - code at
https://github.com/orangeduck/Motion-Matching (MIT, C++, raylib + raygui).
"New Movement Model", 2026-01-07,
https://theorangeduck.com/page/new-movement-model - code at
https://github.com/orangeduck/MovementModel.

## The problem

How do you move a character around a game world in a way that is both
realistic and responsive? The two halves pull against each other and the
conflict is unavoidable whatever controller you build.

## The vocabulary - get this right first

| Object | What it is | Moved by |
|---|---|---|
| **Simulation object** | A simple physical proxy, usually a capsule or circle, that collides with walls and slides along floors | Gameplay code: stick to desired velocity, smoothed by a critically damped spring. "Code driven displacement" |
| **Character entity** | The position and rotation of the visible character | The animation data, so the feet do not slide. "Data driven displacement" |
| **Simulation bone** | An extra bone in the animation data marking where an imaginary simulation object would be relative to the character. Made the **root** bone, which simplifies downstream code | Authored, derived, or both. It is what makes the two comparable |

Key constraint: for minimal disconnect, the simulation bone and the
simulation object must have **similar styles of movement** - similar
speeds, and similar rates of acceleration, deceleration and turning.

## Generating the simulation bone procedurally

1. Project an upper spine bone onto the ground; smooth the position with a
   Savitzky-Golay filter. That is the position.
2. Take the hip bone forward direction, project onto the ground, smooth the
   same way, convert to a rotation about the vertical axis. That is the
   rotation.

Smoothing removes the small oscillations from hip sway, which is what makes
the result resemble a critically damped spring's output.

Stated caveats: it "will often not produce good results" on looping
animations or clips already cut small - it wants long takes starting and
ending in a standing pose. Always keep the ability to hand-edit the result.

## Check whether the data can even do it

Before building anything: plot the simulation bone's one-second
trajectories plus histograms of velocity, acceleration and angular
velocity; then record the simulation object driven the same way and overlay
the same plots. **Overlapping plots mean a good visual match is achievable**
with that data and those spring settings. Max acceleration and max angular
velocity are the measure of how responsive the data is.

Measured coverage of the mocap set used in the article (Ubisoft La Forge
dataset):

| Gait | Forward | Sideways strafe | Backward |
|---|---|---|---|
| Running | just over 4 m/s | just under 3 m/s | around 2 m/s |
| Walking | about 1.75 m/s | around 1.5 m/s | around 1.25 m/s |

## The strategies, weakest to strongest

1. **Do nothing.** With motion matching this partly self-corrects, because
   matching the simulation object's future trajectory *relative to the
   character's current transform* picks a clip that catches up. Verdict:
   not enough control - the character drifts far, clips walls, moves
   unpredictably.
2. **Sync character to simulation** (fully code driven). Direct one-to-one
   control; floaty and artificial with foot sliding and sudden spinning
   unless the data matches closely. The trap: you end up de-tuning the
   simulation object to make the animation tolerable, defeating the point.
3. **Sync simulation to character** (fully data driven). Almost no sliding,
   real weight; sluggish unless the data is quick and snappy.
4. **Blend the two.** Works, but trades one constraint for the other rather
   than satisfying both.
5. **Adjustment** - recommended. Let each move freely, damp the character
   toward the simulation over time.
6. **Clamping**, on top of adjustment, to bound worst-case deviation.

## Adjustment - the recommended approach

Damp the difference and add it back. The damper restarts from zero each
frame, because the result is applied directly to the thing being adjusted:

```c
#define LN2f 0.69314718056f

vec3 damp_adjustment_exact(vec3 g, float halflife, float dt, float eps=1e-8f)
{
    return g * (1.0f - fast_negexpf((LN2f * dt) / (halflife + eps)));
}

quat damp_adjustment_exact(quat g, float halflife, float dt, float eps=1e-8f)
{
    return quat_slerp_shortest_approx(quat(), g,
        1.0f - fast_negexpf((LN2f * dt) / (halflife + eps)));
}
```

Position: `damp_adjustment_exact(sim_pos - char_pos, halflife, dt) + char_pos`.
Rotation: the same on `quat_abs(quat_normalize(quat_mul_inv(sim_rot, char_rot)))`
- `quat_abs` forces the shortest path, and the normalize is there because
the difference of two very similar rotations is numerically unstable. Slerp
approximation: https://zeux.io/2015/07/23/approximating-slerp/

**Velocity-limited adjustment is the refinement that matters.** Clamp the
adjustment to a ratio of the character's own speed, so position is only
adjusted while actually moving and rotation only while actually turning:

```c
float max_length = max_adjustment_ratio * length(character_velocity) * dt;
if (length(adjustment_position) > max_length)
{
    adjustment_position = max_length * normalize(adjustment_position);
}
```

`max_adjustment_ratio = 0.5` is the demonstrated value. For rotation, apply
the same clamp in scaled-angle-axis space (convert, rescale, convert back).
This visibly removes sliding during plant-and-turns and start-and-stops.

## Clamping

Hard-bound the deviation in distance and angle - which is what network code
and collision detection actually need.

```c
float quat_angle_between(quat q, quat p)
{
    quat diff = quat_abs(quat_mul_inv(q, p));
    return 2.0f * acosf(clampf(diff.w, -1.0f, 1.0f));
}
```

Position clamp pushes the character back onto the sphere of `max_distance`
around the simulation; rotation clamp decomposes the difference into angle
and axis, clamps to `max_angle`, reapplies. Cost: the character can feel
dragged along while pressed against the bound.

## Practical rules

- **Position and rotation responsiveness are separate controls.** A common
  shipped-game mistake is setting desired-rotation responsiveness too high:
  the character spins unrealistically on the spot and gains no positional
  control.
- Rotational adjustment should be applied **much more slowly** than
  positional - it matters less for perceived responsiveness and looks worse
  when aggressive.
- Edit the data, not only the simulation. The demo speeds up the mocap
  ~10% to raise max speed and responsiveness, and mirrors it to widen
  coverage.
- Part of the mismatch is unfixable: game characters move at superhuman
  speed, and a real person anticipates their own stop while a player moves
  the stick at the instant they want a reaction.
- Prefer letting animators and designers **label regions of the animation
  data** with the displacement behaviour they want, over embedding it in
  states or modes. It scales better.
- Cheap perceived responsiveness: procedural look-at so the head turns
  toward the desired travel direction with no delay.
- Last resort, genuinely used: move the camera over the shoulder so the
  feet are not visible.

## The movement model (UE 5.7 Mover "Smooth Walking Mode")

Replaces the Character Movement Component's default Walking Mode. Four
stated goals: much easier to understand with a clear per-parameter mental
model; a large range of behaviours from old-Walking-Mode to spring-based;
**no runtime parameter adjustment** needed; and realistic movement
profiles.

How the old CMC behaves, simplified: request a speed **slower** than
current and it decelerates at a constant rate; request **faster or equal**
and it adds some proportion of desired velocity to current velocity then
clamps the magnitude. That asymmetry is what `directional_acceleration`
interpolates against.

The four-layer parameter ladder:

1. **Constant acceleration / deceleration.** `vel_diff = desired - vel`,
   pick `acceleration` or `deceleration` by whether the desired speed
   exceeds current, take the smaller of the full step and `acc_mag * dt`,
   integrate. The plain baseline - and *not* what UE did by default.
2. **`directional_acceleration` (0..1).** Splits the budget between a
   **lateral** part (toward `vel_diff`) and a **directional** part (along
   `normalize(desired_vel)`), then clamps speed to
   `max(previous_speed, |desired_vel|)`. 0 gives layer 1; 1 gives the old
   Walking Mode. High values give slide/drift and let the character change
   direction without losing much speed. Analogy: low is a **quad-copter**,
   high is a **swamp airboat**.
3. **`turn_strength`.** A damper pulling the velocity *direction* toward
   the desired direction at constant magnitude, applied first:
   `damper_exact(vel, length(vel) * normalize(desired_vel), 1/turn_strength, dt)`.
   It exists because the lower layers cannot turn sharply without either
   slowing down or needing excessive acceleration.
4. **A velocity spring on top.** Layers 1-3 produce an *intermediate*
   velocity (`vel_imm`); real velocity tracks it through a velocity spring
   aiming `lag = dt + compensation * halflife_to_lag(halflife)` ahead so it
   does not lag. Separate half-lives and compensations for acceleration and
   deceleration.

Why the spring: plotting velocity and acceleration over many start/stop
mocap clips, the shape is a spring-damper-like ramp up and a more linear
ramp down with small lead-in and lead-out. Layers 1-3 are too linear and
not smooth enough. (The author is candid that the data is hard to read -
large variance plus a smoothing bias from simulation-bone generation.)

**Rotation is modelled entirely separately.** In mocap, character rotation
follows an **S-shape and takes about the same time regardless of how many
degrees it turns**, which fits a double spring. Hence `rotation_halflife`
plus a `rotation_double_spring` toggle falling back to a single spring.

```c
struct movementparams
{
    float acceleration = 800.0f;  // pixels/second^2 (2-D web demo units)
    float deceleration = 1400.0f;

    float directional_acceleration = 0.0f;
    float turn_strength = 1.0f;

    float acceleration_halflife = 0.1f;
    float deceleration_halflife = 0.05f;
    float acceleration_compensation = 1.0f;
    float deceleration_compensation = 0.0f;

    float rotation_halflife = 0.15f;
    bool rotation_double_spring = true;
};
```

State: `pos`, `vel`, `acc`, `vel_imm`, plus `rot`, `ang`, `rot_imm`,
`ang_imm`. Emulation recipes: high `directional_acceleration` reproduces the
old Walking Mode; very large acceleration and deceleration make it snap to
target velocity, degenerating into a pure spring-based model.

### Caveats to read before shipping

- **Not delta-time invariant.** Sub-step for accuracy at larger timesteps.
- **No physical interpretation.** Neither `directional_acceleration` nor
  `turn_strength` has a real-world parallel. Fine for games, but both let
  the character change direction very fast, meaning large acceleration
  spikes and large forces - be careful where this meets a physics engine.
- **The spring never quite arrives.** Reaching exactly zero velocity on a
  stop, or exactly the target velocity, can take a long time. Add an
  epsilon and snap within a threshold.
- **External forces need care.** Collisions, pushes and moving platforms
  must affect **both** the character velocity **and** the intermediate
  velocity of the velocity spring.
