# Motion Matching, Control Operators, Rotation Representations

Sources: Daniel Holden, "Learned Motion Matching" (SIGGRAPH 2020),
2020-08-01, https://theorangeduck.com/page/learned-motion-matching - code at
https://github.com/orangeduck/Motion-Matching. "Control Operators for
Interactive Character Animation" (SIGGRAPH Asia), with Ruiyu Gou,
2025-10-02,
https://theorangeduck.com/page/control-operators-interactive-character-animation
and https://theorangeduck.com/page/implementing-control-operators - code at
https://github.com/gouruiyu/ControlOperators. "Unrolling Rotations",
2024-03-26, https://theorangeduck.com/page/unrolling-rotations.

## Motion matching

Each frame, search an animation database for the clip whose future
trajectory best matches the desired future trajectory of the simulation
object, expressed relative to the character entity's current transform.
That desired trajectory is produced analytically from a critically damped
spring evaluated at several future `dt` values (see `springs.md`), and
animation switching uses inertialization.

Consequences the author states:

- Fluid and **interruptible at any point**.
- By default it **does not blend**, so hitting an exact desired velocity or
  turn angle needs a correction pass.
- But with a lot of data, a realistic clip that already does what you want
  is more likely to exist, needing minimal adjustment.
- Industry appeal: flexibility, predictability, low preprocessing time,
  visual quality.
- The cost that motivates the learned version: **memory scales linearly
  with data**, forcing a permanent trade between movement diversity and
  memory budget.

## Learned Motion Matching

Break motion matching into its steps and replace each with a learned,
scalable alternative. Three networks; once trained the controller "almost
perfectly emulates the original Motion Matching system it was trained on,
but ... does not rely on keeping any animation data in memory" - only
weights, so memory stays small as data grows. **Emulation, not improvement**
- that is the stated success criterion.

| Network | Artifact | Trained by |
|---|---|---|
| **Decompressor** | `decompressor.bin` + `latent.bin` (extra per-frame features it learns) | `train_decompressor.py`, first, from `database.bin` + `features.bin` |
| **Stepper** | `stepper.bin` | `train_stepper.py`, after the decompressor, using `latent.bin` |
| **Projector** | `projector.bin` | `train_projector.py`, at the same time as the stepper |

### The reference implementation

C++, MIT, created 2021-10-19, last push 2025-02-06. It is the source for
both Learned Motion Matching and the displacement demos.

| Path | Role |
|---|---|
| `controller.cpp` (~90 KB) | Nearly all logic and the demo app |
| `database.h` (~25 KB) | The motion matching search |
| `lmm.h`, `nnet.h` | LMM wiring and the network runtime |
| `spring.h`, `quat.h`, `vec.h`, `array.h`, `character.h` | Support headers |
| `resources/train_*.py` | Training, in the order above |
| `resources/generate_database.py`, `bvh.py`, `quat.py` | Database generation from BVH |
| `resources/database.bin` (~64 MB), `features.bin` (~5.8 MB) | Animation database and matching features |
| `shell.html`, `wasm-server.py` | Emscripten web build |

Build: install raylib and raygui first, then compile `controller.cpp`. The
bundled Makefile assumes raylib on Windows at default paths. Web build:
install emscripten, `emsdk_env`, `make PLATFORM=PLATFORM_WEB`, serve with
`wasm-server.py`.

**Licence split - the trap.** Code is MIT. The animation data needed to
regenerate the database is from
https://github.com/ubisoft/ubisoft-laforge-animation-dataset under
**CC BY-NC-ND 4.0** - non-commercial, no derivatives, explicitly "unlike
the code". Anything built on that data inherits the restriction.

**Stated divergences from the paper:** the repo is "very similar ... but not
identical" - it omits some animation-database storage optimizations and
uses **no tags to disambiguate walking from running**.

**Regeneration order:** `features.bin` rebuilds every run. If the database
is regenerated, or matching weights change, the database must be rebuilt
**and the networks retrained**.

## Control Operators

A compositional way to **differentiably encode arbitrarily structured,
ragged, partly-missing input** into a fixed-size tensor. The problem: game
control input varies frame to frame - a target location, sometimes with a
time-until-arrival, sometimes a facing direction, sometimes a path with a
style, sometimes a varying number of nearby objects. Normally each variant
needs custom feature engineering, a bespoke architecture and its own
training procedure, which puts it out of reach of non-technical designers.

One contract: declare output width `D`, map a list of `N` inputs to `(N, D)`.

```python
class ControlOperator(torch.nn.Module):
    def output_size(self) -> int: pass
    def forward(self, x: List[Any]) -> torch.FloatTensor: pass
```

| Operator | C-like alias | Mechanism | Output width |
|---|---|---|---|
| `Vector(size)` | | stack | `size` |
| `Location`, `Direction` | | typed `Vector(3)` - same encoding, meaningful name | 3 |
| `Rotation` | | quaternion to two-axis (6D) format | 6 |
| `And(ops)` | `Struct` | concatenate children | sum of children |
| `Or(ops, encoding_size)` | `Union` | per-type `Linear` into a shared width + one-hot branch tag | `encoding_size + len(ops)` |
| `FixedArray(op, num)` | | concatenate | `num * child` |
| `OneOf(choices)` | `Enum` | one-hot | `len(choices)` |
| `SomeOf(choices)` | `Flags` | multi-hot | `len(choices)` |
| `Index(encoding_size)` | | sinusoidal positional encoding | `2 * encoding_size` |
| `String()` | | any text embedding (CLIP in the example) | embedding width |
| `Null()` | | the empty vector | 0 |
| `Optional(op)` | `Maybe` | `Or({null: Null(), valid: op})` | as `Or` |
| `Set(op)` | | multi-head self-attention summarises members | `head_num * encoding_size` |
| `Array(op)` | | `Set(And({index: Index(), value: op}))` - order matters | as `Set` |
| `Dictionary(k, v)` | | `Set(And({key, value}))` | as `Set` |
| `Encoded(op, size)` | | `Linear` + activation (ELU) to remap width | `size` |

Two derivations that show the algebra working: **`Optional` is just `Or`
with a `Null` branch**, and **`Array` is just a `Set` of `(index, value)`
pairs**. For an untrained network a missing `Optional` comes out as the
`Or` layer's bias, which is zero.

The schema reads as a type declaration for the control input:

```python
encoder = Set(Encoded(Struct({
    'name': String(),
    'class': Enum(['enemy', 'prop', 'weapon']),
    'location': Location(),
    'rotation': Rotation(),
    'aiming': Optional(Direction()),
    'state': Flags(['allocated', 'alive'])
})))
```

### Stated limitations

- **Performance.** The clarity-first implementation loops over the batch
  dimension in Python and gets slow. Doing it performantly is possible but
  "the code can start to get pretty hairy".
- **Encoder only.** It encodes structured data, it does not *produce* it.
  Training an auto-encoder over structured data is difficult; the author
  calls structured output "largely an open problem".
- **Normalization and statistics** over structured data are difficult in a
  way they never are for flat vectors.

### Where it is used

Demonstrated on a Flow-Matching auto-regressive model (Ruiyu Gou's) and a
variation of Learned Motion Matching. Validated by a **user study with
industry practitioners** - note: designer usability, not player experience.
The paper's implementation uses Unreal Blueprint visual scripting, which is
what makes it accessible, at the cost of much more complex C++. Control
Operators are "essentially already used" in **Learning Agents**, Unreal's
reinforcement-learning plugin - far broader than animation. The author
states the idea is not limited to animation.

## Rotation representations and unrolling

**Unroll rotation data before feeding it to anything statistical.** Two
nearly identical poses with wildly different numbers will defeat learning,
and naive interpolation across a discontinuity takes the long way round.
The author believes artefacts in his own earlier PFNN work came from not
unrolling properly - a real bug class.

The problem: a joint's rotation jumps instantly from +180 to -180 degrees.
Nothing moved - +181 and -179 are the same orientation, and the data was
normalised into `[-180, +180]`, discontinuities included.

| Representation | Discontinuous? | Unrollable? | Values grow unbounded? | Beyond +/-180? |
|---|---|---|---|---|
| **Euler angles** | Yes, at +/-180 | Yes, integrate differences | **Yes** | Yes, unboundedly |
| **Rotation matrix** | **No, never** | N/A | No | No - +180 and -180 are the same value |
| **Quaternion** | Yes | Yes, by hemisphere choice | No - loops at 720 degrees | Yes, to +/-360 |
| **Exponential map** | Yes | **No** - author knows of no way | No | Partially, then jumps |

```c
// Euler: integrate consecutive differences
void euler_unroll_inplace(slice1d<vec3> rotations)
{
    rotations(0) = angle_normalize(rotations(0));
    for (int i = 1; i < rotations.size; i++)
        rotations(i) = rotations(i-1) + angle_sub(rotations(i), rotations(i-1));
}

// Quaternion: pick the hemisphere nearest the previous frame
void quat_unroll_inplace(slice1d<quat> rotations)
{
    rotations(0) = quat_abs(rotations(0));
    for (int i = 1; i < rotations.size; i++)
        if (quat_dot(rotations(i), rotations(i - 1)) < 0.0f)
            rotations(i) = -rotations(i);
}
```

Euler unrolling faithfully captures multiple revolutions at the cost of
arbitrarily large values - a wheel that turned 100 times carries "a memory"
of that. Quaternions stay bounded (they rise then loop back), because +360
and -360 degrees are the same quaternion.

**Why 6D for networks.** Convert to matrices and plot the nine values: no
discontinuities ever, because +180 and -180 are literally the same matrix
for any configuration. Hence feeding **two columns of the rotation matrix**
to networks - "pretty much fool-proof: it always produces continuous values
which are within a fixed range whatever you throw at it". The third column
is dropped because the cross product recovers it, so including it wastes
capacity. Comparison paper: https://arxiv.org/abs/1812.07035

**Open problem:** the exponential map cannot be unrolled, as far as the
author knows - the outer "shells" reach an unstable configuration similar
to gimbal lock. He could find nothing written on it and asks to be
corrected. Note the tension: scaled-angle-axis *is* the right space for
small offsets, differences and angular velocities (springs,
inertialization), because it behaves like a vector - just do not carry that
over to storing or learning absolute rotations spanning revolutions.

### Rule of thumb

- **Network input/output:** two columns of the rotation matrix (6D).
- **Offsets, differences, angular velocities, spring state:**
  scaled-angle-axis / exponential map.
- **Storage and interpolation:** quaternions, unrolled.
- **Authoring and curve editing:** Euler, unrolled, accepting large values.
- **Anything destined for a statistical model:** unroll first, whatever the
  representation.
