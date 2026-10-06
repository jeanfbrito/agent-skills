# Awesomeness loop: the prompt and example fills

## The prompt

```text
I want [PROJECT] to reach the level of [REFERENCE], and then go past it.
Read every reference and priority doc in the repo. Find the most important
thing that is missing, broken or below the reference. Do the human's set
priorities first. When there are none, take the quick wins with the highest
visible effect.

Fan out sub-agents. Give each sub-agent one item. Check every change yourself
with cheap senses: metrics, gizmos and one clean capture. Do not repeat a check
when nothing it measures changed. Only when a row is about to be called done,
have a separate sub-agent check it [CHECK] against [REFERENCE]. That critic
must be really harsh. It compares the two side by side, blind, and says which
one is better. If ours is not better, turn each deficit into a sense check and
a next item. Keep going.

When nothing is missing, do not stop. Invent what would make [PROJECT] more
awesome than [REFERENCE]. Put every invention behind a toggle until a human
says keep or kill. Repeat the cycle until the human stops you.
```

`PROJECT` and `REFERENCE` come from the repo docs. `CHECK` is `visually` for
visual work, `by running it` for behavior, `against the spec` for contracts.

The cycle in `SKILL.md` carries out this prompt. Each fill below states it for one project.

## Game: platformer against a genre classic (Godot)

```text
I want our 2D platformer to reach the level of Celeste, and then go past it.
Read every reference and priority doc in the repo. Find the most important
thing that is missing, broken or below the reference. Do the human's set
priorities first. When there are none, take the quick wins with the highest
visible effect.

Fan out sub-agents. Give each sub-agent one item. Check every change yourself
with cheap senses: metrics, gizmos and one clean capture. Do not repeat a check
when nothing it measures changed. Only when a row is about to be called done,
have a separate sub-agent check it visually against Celeste. That critic
must be really harsh. It compares the two side by side, blind, and says which
one is better. If ours is not better, turn each deficit into a sense check and
a next item. Keep going.

When nothing is missing, do not stop. Invent what would make our platformer
more awesome than Celeste. Put every invention behind a toggle until a human
says keep or kill. Repeat the cycle until the human stops you.
```

Typical sources the loop finds in a repo like this: `AGENTS.md` (product focus
and capture rules), `docs/roadmap.md` (priorities), `docs/references/`
(reference clips, screenshots and a feature list), and
`docs/KNOWN_ISSUES.md`.

## Web app against a named product

```text
I want our issue tracker to reach the level of Linear, and then go past it.
Read every reference and priority doc in the repo. Find the most important
thing that is missing, broken or below the reference. Do the human's set
priorities first. When there are none, take the quick wins with the highest
visible effect.

Fan out sub-agents. Give each sub-agent one item. Check every change yourself
with cheap senses: metrics, gizmos and one clean capture. Do not repeat a check
when nothing it measures changed. Only when a row is about to be called done,
have a separate sub-agent check it by running it against Linear. That critic
must be really harsh. It compares the two side by side, blind, and says which
one is better. If ours is not better, turn each deficit into a sense check and
a next item. Keep going.

When nothing is missing, do not stop. Invent what would make our issue tracker
more awesome than Linear. Put every invention behind a toggle until a human
says keep or kill. Repeat the cycle until the human stops you.
```

## Spec-driven library against a standard

Use `CHECK` = `against the spec`. The critic runs the conformance cases and
reads the spec section for each item. "Blind" here means the critic gets the
spec text and the behavior it sees. It does not get the builder's summary.
