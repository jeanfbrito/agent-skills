# Foot Locking and Inverse Kinematics

Sources: Daniel Holden, "Inverse Kinematics and Foot Locking", 2026-07-30,
https://theorangeduck.com/page/inverse-kinematics-foot-locking - code at
https://github.com/orangeduck/GenoView-InverseKinematics (MIT, C, one
~85 KB `genoview.c`). Underlying solve: "Simple Two Joint IK", 2017-01-18,
https://theorangeduck.com/page/simple-two-joint.

The author's own framing: this is "much more of an art than a science",
these are recipes that served him well, **not** proven-best solutions.
Treat every threshold as a starting point to tune.

## Start here - the four philosophical points

These change how you approach the problem, so read them before the code.

**1. Foot sliding is about velocity, not position or friction.** Two
distinct causes: (a) the root moves in a way that does not match the
animation playing on the body - in which case *the whole character* is
sliding and the whole animation is wrong, you just notice it at the feet
because they are nearest the ground; (b) interpolating, blending or
modifying local joint rotations moves the end of the chain unnaturally. In
both cases runtime foot velocity no longer matches source foot velocity.
Labelling contacts by foot height treats it as a physics violation, which
is the wrong model. Constraining velocity only during contact is a
practical compromise, not the definition. Corollary: the flight phase is
wrong too, you just cannot see it.

**2. The toe is what needs locking.** About 90% of the time in locomotion
data the toe area is what contacts the floor; in athletic motion people
land far more front-footed than expected, so heel-without-toe contacts are
a small fraction and rarely a stable pose, while toe-without-heel is
extremely common (pivoting on the toe, lifting and dropping the heel).
Even if bad animation has the heel through the floor, **do not lock the
heel** - results improve the more freedom the heel has.

**3. Inverse kinematics is a modification, not a replacement.** The rigging
model (procedural rules plus a pole vector replacing three joints' pose) is
not the only one. Applied as a *minimal modification* that moves joints to
a target while preserving existing rotations as far as possible, it keeps
the heel-toe nuances and subtle twists the source animation already has.

**4. Avoid the dinosaur.** Over-applying foot locking leads to pulling the
hips down for extension room, which bends the knees into a t-rex walk. Real
animation data sits extremely close to hyper-extension - which is exactly
what makes foot locking hard. Pulling the hips down removes
hyper-extension and looks bad. Better to let the feet slide: limit
extension to what the input animation has.

Closing advice, verbatim: "a little bit of sliding is a lot better than
breaking the source animation just so the motion is mechanically correct.
In fact, stop thinking about it in terms of sliding ... and start thinking
about it in terms of input motion velocity preservation."

## Part 1 - solving the leg chain

Goal: modify local rotations so the pose is preserved as far as possible
but the toe lands on a target. Four steps:

1. Compute the heel target from the toe target - the toe-to-heel vector in
   the *existing* pose, added to the toe target. That is all.
2. Solve two-joint IK for hip and knee to put the heel on its target.
3. Rotate the heel joint to orient the toe toward the toe target (a look-at
   via `QuaternionBetween`).
4. Optionally rotate the toe-end to resolve ground collisions.

Once `SolveLegChain` exists, foot locking reduces to producing a
non-sliding toe target - it is "a kind of black box where we can input an
existing pose of the character and a new toe target, and always get
something relatively sane as output".

### The two-joint solve (2017 derivation)

Two rotations, no matrix algebra: extend/contract the chain so hip-to-heel
length equals hip-to-target length, then rotate the hip to swing the heel
onto the target.

```c
void two_joint_ik(
    vec3 a, vec3 b, vec3 c, vec3 t, float eps,   // hip, knee, heel, target
    quat a_gr, quat b_gr,                        // global rotations
    quat &a_lr, quat &b_lr) {                    // local rotations, modified

    float lab = length(b - a);
    float lcb = length(b - c);
    float lat = clamp(length(t - a), eps, lab + lcb - eps);

    float ac_ab_0 = acos(clamp(dot(normalize(c - a), normalize(b - a)), -1, 1));
    float ba_bc_0 = acos(clamp(dot(normalize(a - b), normalize(c - b)), -1, 1));
    float ac_at_0 = acos(clamp(dot(normalize(c - a), normalize(t - a)), -1, 1));

    float ac_ab_1 = acos(clamp((lcb*lcb-lab*lab-lat*lat) / (-2*lab*lat), -1, 1));
    float ba_bc_1 = acos(clamp((lat*lat-lab*lab-lcb*lcb) / (-2*lab*lcb), -1, 1));

    vec3 axis0 = normalize(cross(c - a, b - a));
    vec3 axis1 = normalize(cross(c - a, t - a));

    quat r0 = quat_angle_axis(ac_ab_1 - ac_ab_0, quat_mul(quat_inv(a_gr), axis0));
    quat r1 = quat_angle_axis(ba_bc_1 - ba_bc_0, quat_mul(quat_inv(b_gr), axis0));
    quat r2 = quat_angle_axis(ac_at_0, quat_mul(quat_inv(a_gr), axis1));

    a_lr = quat_mul(a_lr, quat_mul(r0, r2));
    b_lr = quat_mul(b_lr, r1);
}
```

Current interior angles come from dot products, desired ones from the
**cosine rule**; rotate by the difference. Rotations multiply on the
**right** of the existing locals, which is what makes this a modification
rather than a replacement.

**Always clamp before `acos`.** Floating-point error pushes the dot product
just outside `[-1, 1]` and `acos` returns NaN. This is the single most
common way this function breaks.

**The popping fix, and why no pole vector is needed.**
`normalize(cross(c - a, b - a))` is unstable when `c - a` and `b - a` point
nearly the same way - i.e. when the leg is nearly fully extended, which is
most of the time in real data. Symptom: small pops. Fix: derive the axis
from a separate control vector, usually the direction the knee points.

```c
vec3 d = quat_rotate(b_gr, vec3(0, 0, 1));    // if Z is forward
vec3 axis0 = normalize(cross(c - a, d));
```

In the 2026 code this is mandatory rather than optional, as
`kneeSideVector` / `axisRot`:

```c
Vector3 axisDwn = Vector3Normalize(
    Vector3Subtract(globalHeel.translation, globalHip.translation));
Vector3 axisFwd = Vector3Normalize(Vector3CrossProduct(axisDwn, sideVector));
Vector3 axisRot = Vector3Normalize(Vector3CrossProduct(axisDwn, axisFwd));
```

### Soft max-extension clamp (2026 addition)

So the limb only ever approaches `maxExtension` asymptotically:

```c
if (targetLength > maxExtension - softening)
{
    float saturation = 1.0f - expf(
        -Max(targetLength - maxExtension + softening, 0.0f) / softening);

    targetClamp = Vector3Add(
        globalHip.translation,
        Vector3Scale(Vector3Subtract(targetHeel, globalHip.translation),
            (maxExtension - softening + softening * saturation) / targetLength));
}
```

Values for the Geno character: `kneeSideVector = (1,0,0)`, `softening` about
`0.005f` metres, `maxExtension` = current hip-to-heel distance. Ground
clamping uses **bind-pose** heights of heel, toe and toe-end as minimums
(`targetToe->y = Max(targetToe->y, toeMinHeight)`). With dynamic terrain,
raycast instead of assuming the plane is at zero. The sample recomputes
full forward kinematics after each local update for clarity; only the
downstream bones are actually needed.

## Part 2 - runtime locking by inertialization

No contact: follow the toe position in the source animation. Contact:
follow a static floor position, where the toe was when the contact began.
Transition with **cubic** inertialization (see `springs.md`).

State per contact point: current position and velocity, input position and
velocity, inertialization offset position and velocity, time since
transition, contact location, `locked` flag.

- **Lock** when not locked, the input says contact, **and** the distance
  from current output to input position is below `lockDistance`. The
  contact point is the input toe position with `y` set to `contactHeight`.
- **Unlock** when locked and either the input says no contact **or** that
  distance exceeds `unlockDistance`.

Input velocity is a finite difference of input position. Then feed the
resulting position as the toe target into the leg solve. That is the whole
runtime path.

(The 2021 version of this recipe used an *exponential* inertializer keyed
on `halflife` and gated only on unlocking. The 2026 version above is the
one to implement from. Neither is retracted by the author.)

## Part 3 - annotating contact times automatically

Manual labelling is the only gold standard; heuristics get "about 90% of
the way there".

- Threshold the **global velocity magnitude of the toe joint**, not its
  height. Velocity is clearly low during contact; people barely lift their
  feet during locomotion and contact height wanders, so height is hard to
  threshold.
- Height remains a useful sanity check, to avoid labelling a foot that is
  stationary but held in the air. Combine both if you want.
- Starting values on high-quality data: velocity threshold **0.5 to
  0.1 m/s**, height threshold **0.1 m** - depends on where the toe sits on
  your skeleton.
- Post-process 1: **majority-vote filter** over a short window to kill
  single-frame flips. **5 frames at 60 Hz** is a good start. In numpy,
  `scipy.ndimage.median_filter` is equivalent for binary signals.
- Post-process 2: optional **Gaussian smoothing**, making the signal
  continuous so the runtime threshold becomes a sensitivity dial on how
  early or late contact kicks in.

**Failure mode: fast runs.** Shoe and foot deformation is large and
contacts are short - at 30 Hz a run contact can be **1 or 2 frames**, which
the majority-vote filter then eats. So **keep animation data at 60 Hz**,
and if up-sampling from 30 Hz compute velocities with cubic rather than
linear interpolation, because the result is easier to threshold.

## Part 4 - offline slide removal as a constraint solve

Better results than the runtime method when the whole clip is available.
Treat per-frame pelvis and left/right toe positions as connected particles
and relax constraints position-based-dynamics style, iterating the whole
animation repeatedly:

- **Inter-frame, contact active on both frames (hard):** move both toe
  positions toward their midpoint, `y` set to ground height. This bunches
  the toe particles together across the contact.
- **Inter-frame, otherwise (soft):** preserve each frame's toe offset
  relative to its neighbour as in the source, ground penetration removed.
- **Inter-frame pelvis (soft):** preserve the frame-to-frame pelvis delta.
- **In-frame (soft):** preserve the source hip-to-toe distance, moving
  pelvis and toe along their connecting direction.

Values demonstrated: `softFactor = 0.05f`, `hardFactor = 0.9f`,
`iterations = 25000`. The two factors trade constraint enforcement against
fidelity to the source; more iterations are better but slow. Feed the
resulting pelvis and toe arrays through the leg solve per frame.

Why it beats the runtime method: it has the whole clip, so it
**distributes the correction** rather than only reacting to contacts as
they arrive. Test setup for creating sliding on purpose: scale root motion
by `1.25`, and by `0.75`.

## The viewer is part of the method

GenoView is deliberately basic - a deferred renderer with shadow maps,
SSAO, and a procedural grid shader as texture - and its whole purpose is
**making artefacts visible**: foot sliding and penetration are obvious on a
skinned character even on low-end devices. Build the diagnostic before
claiming the fix. Pure-Python port:
https://github.com/orangeduck/GenoViewPython/

Thin prior art the author points to, as evidence the topic is
under-documented: https://www.gdcvault.com/play/1023316/Fitting-the-World-A-Biomechanical ,
https://research.cs.wisc.edu/graphics/Gallery/kovar.vol/Cleanup/cleanup.pdf ,
http://www.okanarikan.com/assets/Papers/FootSkate/paper.pdf
