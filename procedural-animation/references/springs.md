# Springs, Dampers, Inertialization

Source: Daniel Holden, "Spring-It-On: The Game Developer's Spring-Roll-Call",
2021-03-04, https://theorangeduck.com/page/spring-roll-call - code at
https://github.com/orangeduck/Spring-It-On (MIT, raylib + raygui).
Looping and cubic inertialization: "Creating Looping Animations from Motion
Capture", 2022-09-19,
https://theorangeduck.com/page/creating-looping-animations-motion-capture -
code at https://github.com/orangeduck/Animation-Looping.

## Cheat sheet

| Need | Function | Parameters |
|---|---|---|
| Smooth to a goal, no velocity continuity | `damper_exact` | `halflife` |
| Smooth to a goal with velocity continuity | `simple_spring_damper_exact` | `halflife` |
| Decay an offset to zero | `decay_spring_damper_exact` | `halflife` |
| Full spring with a goal velocity | `critical_spring_damper_exact` | `halflife` |
| Spring where oscillation is wanted | `spring_damper_exact` | `frequency` or `damping_ratio` + `halflife` |
| S-shaped ease instead of steep-then-flat | `double_spring_damper_exact` | `halflife` |
| Arrive at a goal at a specific time | `timed_spring_damper_exact` | `t_goal`, `halflife` |
| Approach at a fixed speed without lagging | `velocity_spring_damper_exact` | `v_goal`, `halflife` |
| Spring a rotation | `simple_spring_damper_exact_quat` | `halflife` |
| Predict future position/velocity analytically | `spring_character_update` | `halflife`, any `dt` |
| Where a decelerating object ends up | `extrapolate` | `halflife` |
| Does a signal oscillate at frequency f | `spring_energy` + `resonant_frequency` | `frequency`, `halflife` |

The three most-used forms are inlined in SKILL.md. The rest follow.

## Bug 1 - the naive forms

- `lerp(x, g, factor)` each frame is **framerate dependent**: at 30 fps you
  call it half as often as at 60, so it converges slower.
- `lerp(x, g, damping * dt)` is **unstable**: once `damping * dt > 1` it
  explodes. Clamping papers over a real error - doubling `dt` is not the
  same as applying the damper twice (lerp 0.5 twice reaches 75%, lerp 1.0
  once reaches 100%).

The fix comes from the recurrence relation, which exposes the exponential:
`x_{t+n} = lerp(x_t, g, 1 - y^n)` with `y = 1 - damping * ft`. Then fix the
decay rate at 0.5 and scale the timestep - that is a half-life.

## Bug 2 - only handling the under-damped case

The exact spring solution needs `w = sqrt(s - d^2/4)`, and that goes
negative at high damping. There are **three regimes**, each with a
different closed form:

| Condition | Regime | Behaviour |
|---|---|---|
| `s - d^2/4 > 0` | under damped | oscillates toward the goal |
| `s - d^2/4 = 0` | critically damped | fastest arrival, no oscillation |
| `s - d^2/4 < 0` | over damped | returns slowly |

An implementation that handles only the under-damped branch **produces
NaNs at high damping**. This is the most likely porting bug.

```c
void spring_damper_exact(float& x, float& v, float x_goal, float v_goal,
                         float stiffness, float damping, float dt,
                         float eps = 1e-5f)
{
    float g = x_goal, q = v_goal, s = stiffness, d = damping;
    float c = g + (d*q) / (s + eps);
    float y = d / 2.0f;

    if (fabs(s - (d*d) / 4.0f) < eps)          // Critically Damped
    {
        float j0 = x - c;
        float j1 = v + j0*y;
        float eydt = fast_negexp(y*dt);
        x = j0*eydt + dt*j1*eydt + c;
        v = -y*j0*eydt - y*dt*j1*eydt + j1*eydt;
    }
    else if (s - (d*d) / 4.0f > 0.0)           // Under Damped
    {
        float w = sqrtf(s - (d*d)/4.0f);
        float j = sqrtf(squaref(v + y*(x - c)) / (w*w + eps) + squaref(x - c));
        float p = fast_atan((v + (x - c) * y) / (-(x - c)*w + eps));
        j = (x - c) > 0.0f ? j : -j;
        float eydt = fast_negexp(y*dt);
        x = j*eydt*cosf(w*dt + p) + c;
        v = -y*j*eydt*cosf(w*dt + p) - w*j*eydt*sinf(w*dt + p);
    }
    else                                        // Over Damped
    {
        float y0 = (d + sqrtf(d*d - 4*s)) / 2.0f;
        float y1 = (d - sqrtf(d*d - 4*s)) / 2.0f;
        float j1 = (c*y0 - x*y0 - v) / (y1 - y0);
        float j0 = x - j1 - c;
        float ey0dt = fast_negexp(y0*dt), ey1dt = fast_negexp(y1*dt);
        x = j0*ey0dt + j1*ey1dt + c;
        v = -y0*j0*ey0dt - y1*j1*ey1dt;
    }
}
```

## Parameter conversions

```c
float halflife_to_damping(float h, float eps=1e-5f) { return (4.0f*0.69314718056f)/(h+eps); }
float damping_to_halflife(float d, float eps=1e-5f) { return (4.0f*0.69314718056f)/(d+eps); }
float frequency_to_stiffness(float f) { return squaref(2.0f * M_PI * f); }
float stiffness_to_frequency(float s) { return sqrtf(s) / (2.0f * M_PI); }
float halflife_to_lag(float h)   { return h / 0.69314718056f; }
float lag_to_halflife(float lag) { return lag * 0.69314718056f; }
```

Honesty notes the author states explicitly, worth repeating to users:

- The `4` in the half-life conversion is **a fudge factor** (roughly: one
  halving to get `y` from `d`, plus the spring being a sum of two
  exponentials). A less-fudged formulation:
  https://theorangeduck.com/page/fitting-code-driven-displacement-revisited#true-half-life
- Velocity continuity means the spring is **not** exactly halfway to the
  goal after one `halflife`.
- `frequency` is a pseudo-frequency; real oscillation rate also depends on
  `damping`.

**Damping ratio** is usually the best user-facing dial - it reads as "less
springy to more springy": `r = d / (2*sqrt(s))`, with `1` critical, `< 1`
under, `> 1` over damped.

`halflife_to_lag` is how far a critically damped spring trails a target
moving at constant velocity, and therefore how far ahead to aim to cancel
that lag. It is the lag-compensation term in the locomotion model.

## Predicting the future analytically

Because the solution is closed form, evaluating at a larger `dt` gives the
exact future state with no intermediate simulation. Integrating the
critical spring gives future *position*. Note the framing: **the spring's
position is the character's velocity**, so its velocity is acceleration.

```c
void spring_character_update(float& x, float& v, float& a, float v_goal,
                             float halflife, float dt)
{
    float y = halflife_to_damping(halflife) / 2.0f;
    float j0 = v - v_goal;
    float j1 = a + j0*y;
    float eydt = fast_negexp(y*dt);

    x = eydt*(((-j1)/(y*y)) + ((-j0 - j1*dt)/y)) +
        (j1/(y*y)) + j0/y + v_goal * dt + x;
    v = eydt*(j0 + j1*dt) + v_goal;
    a = eydt*(a - j1*y*dt);
}
```

Call it with an array of increasing `dt` to get a predicted trajectory in
one pass. This is how the future character trajectory is produced for
motion matching.

## Cubic inertialization

Reaches exactly zero by `blendtime`, unlike the exponential form. Use where
the end state must be exact.

```c
vec3 decayed_offset_cubic(const vec3 x, const vec3 v,
                          const float blendtime, const float dt,
                          const float eps=1e-8)
{
    float t = clampf(dt / (blendtime + eps), 0, 1);
    vec3 d = x;
    vec3 c = v * blendtime;
    vec3 b = -3*d - 2*c;
    vec3 a = 2*d + c;
    return a*t*t*t + b*t*t + c*t + d;
}

// Velocity-only sibling, when position is handled by a ramp
vec3 decayed_velocity_offset_cubic(const vec3 v, const float blendtime,
                                   const float dt, const float eps=1e-8f)
{
    float t = clampf(dt / (blendtime + eps), 0, 1);
    vec3 c = v * blendtime;
    vec3 b = -2*c;
    vec3 a = c;
    return a*t*t*t + b*t*t + c*t;
}
```

The running-state form used for foot locking (`InertializeCubicUpdate` /
`InertializeCubicTransition`) uses weights `w0 = 2t^3-3t^2+1`,
`w1 = (t^3-2t^2+t)*blendTime`, `w2 = (6t^2-6t)/blendTime`,
`w3 = 3t^2-4t+1` over `t = time/blendTime` clamped to `[0,1]`.

## Looping a clip - inertializing an animation against itself

Two requirements only: first and last frame equal, and start/end velocities
close enough to hide the discontinuity. Positions subtract directly;
rotations go through **scaled-angle-axis** space so offsets behave like
vectors and combine with angular velocity. Positional offsets are added;
rotational offsets convert back and multiply on the left.

Four offset shapes, each with its trap:

| Shape | Trap |
|---|---|
| Exponential at start and/or end | Residual offset never reaches zero - visible in slow motion |
| Cubic at start and/or end | None. This is the fix |
| Linear over the whole clip | Introduces a velocity discontinuity; needs a cubic velocity inertializer at each end. Also causes drift, and drift means foot sliding |
| Softfade (ramp limited to the ends, tunable knee) | Same velocity correction needed; more parameters |

```c
float softfade(const float x, const float alpha)
{
    return logf(1.0f + expf(alpha - 2.0f*alpha*x)) / alpha;
}
```

**The subtle trap:** a ramp adds velocity of its own, which must be
accounted for when setting the inertializer's initial velocity. With a pure
linear fade it is identical at both ends and cancels, so ignoring it works.
With softfade, where the two ends differ in duration or hardness, it does
**not** cancel.

**The root needs separate handling.** Usually you do not want the root to
loop in world space - you want the velocity discontinuity gone while
displacement accumulates. Compute offsets in **character space**, apply
them in the **world space of the first or last frame**, and inertialize out
only the velocity difference.

The design space in one sentence, from the source: produce an offset whose
total displacement accounts for the positional difference and whose
velocity offsets at either end account for the velocity difference -
everything in the middle is your choice.

## Other variants

- **Double spring** - `simple_spring_damper_exact` twice at
  `0.5 * halflife`, the first driving an intermediate target. Turns
  steep-then-flat into an S-curve.
- **Timed spring** - track a linear interpolation to the goal, aimed
  `halflife_to_lag(halflife)` ahead, to arrive near `t_goal`.
- **Velocity spring** - same trick for a fixed approach speed.
- **Quaternion spring** - convert differences to scaled-angle-axis so they
  combine with angular velocity. Counter-intuitive detail: it computes the
  rotation taking the **goal toward the initial state**, not the reverse.
- **Extrapolation** - assume exponential velocity decay and integrate:
  `x_t = (v0/y)*(1 - e^(-y*t)) + x0`.
- **Resonance** - drive springs at candidate frequencies, measure
  `spring_energy`; the one accumulating energy matches. Cheaper than an FFT
  for a single frequency. Long `halflife` gives narrow selectivity, short
  gives a broader band. Use `resonant_frequency(goal_frequency, halflife)`.
- **Interpolation** - springs over a curve parameter give a spline-like
  result the author himself calls odd and asymmetric, usually not reaching
  the last control point. An unresolved experiment, not a recommendation.
