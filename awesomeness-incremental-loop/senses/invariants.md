# Sense guide: invariants (common-sense rules the harness watches)

## When to use it

Any project with a world, a body or a layout: games, simulations, 3D tools,
UI. Turn them on in labs and in the full project from the first cycle.

## The blocker

- **Sign:** the human finds the defect first. For example: wheels below the
  ground, a hand through the wall, a character that floats, text that runs
  off the button. Nobody asked for it, and any person would call it wrong.
- **Cause:** the harness checked only the item under work. Nothing watched
  the rules that are always true in the real world.

## The sense

An invariant is a rule that must hold on every frame, unless the project says
otherwise. The harness checks the invariants on every frame or every physics
step. It is cheap math, not a capture.

**Start set** (use the ones that apply):

| Area | Invariant |
| --- | --- |
| Ground | No wheel, foot or body part below the ground surface by more than a small tolerance |
| Contact | No penetration between solid bodies above a tolerance. A part that must touch (hand on grip, foot in stance) is within its contact tolerance |
| Support | Nothing floats: a body with no support and no upward force must be falling |
| Bodies | Bone lengths stay constant. Joints stay inside their limits. Scale stays positive |
| Numbers | No NaN or infinity. Speeds and accelerations stay below a physical limit. Energy does not grow with no input |
| World | Every object stays inside the world bounds. The camera is not inside geometry |
| Time | Frame time stays under the limit of the frame-rate target (`metrics.md`). No big jump in position between two frames (a pop) |
| UI | No text overflow or clipping. No element off-screen or under another element. Contrast is above its minimum |

**On a break:**

1. Write an event to `events.jsonl`: the invariant, the object, the value, the
   limit and the frame.
2. Save a snapshot at that frame: the standard views of the object that broke
   it, with its isolation set and the metadata (`capture-metadata.md`).
   Save only the first break of each invariant per object, and then a count.
   Do not fill the disk.
3. The digest lists the breaks first, grouped by invariant, with the first
   frame and the worst value.

A break is a failing check at level 0 (`references/checks.md`). The agent
fixes it before it goes to other work. If the agent thinks that the break is
intended, it writes the question in the "Pending verdicts" table. The break
stays a failing check until the human adds an exception.

**Exceptions:** keep the project's exceptions in one file next to the
invariants, with a reason for each. For example: "wheels sink up to 5 cm in
mud: suspension design". Only the human or a project doc can add an
exception. The agent must not add one to make a check pass.

**Watch, do not enforce.** An invariant reports. It does not push objects
back into place. A runtime fix that hides a break also hides its cause
(`references/lessons.md`, rule 10).

## Proof that it works

Break each invariant on purpose once in a lab. For example, push a wheel
10 cm into the ground, put a NaN in a velocity, or move a label off-screen.
Each must produce one event, one snapshot and one line in the digest.

## Cost and limits

Per-frame checks must stay cheap: use bounds and contact points, not mesh
against mesh tests, unless the item needs them. An invariant cannot judge
style or feel. It catches what any person calls wrong, so that the human and
the critic only judge what needs taste.

## Grow the set

Each time the human or the critic reports a defect that a rule could catch,
add that rule as an invariant. Then the same defect cannot reach the human
again.
