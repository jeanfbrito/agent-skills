# Critic brief template

Use this brief for each blind critic round at the gate
(`references/checks.md`). Send it to a separate sub-agent that did not build
the work. Fill the parts in angle brackets. Send nothing else about the work.

## Before you send it

1. For each pair, put the reference image and our image at the same size,
   with no labels and no metadata drawn on them.
2. Choose left and right at random for each pair. Write the key (which side is
   ours) in the round file only after the critic answers.
3. Crop to the region of interest and use critic mode (all gizmos off, nothing
   that is not measured in view).
4. Do not tell the critic which side is ours, what changed, or what you hope.

## The brief

```text
You are a harsh visual critic. You compare pairs of images. Each pair shows the
same <subject> from the same view. One image in each pair is a reference from
<reference description>. You do not know which one.

For each pair, look at <what to judge, for example: contact with the ground,
shape, motion blur, material>. Ignore <what to ignore, for example: background,
colour grading>.

Images:
<pair 1: left = <path>, right = <path>, question: <one question>>
<pair 2: ...>

For each pair, answer in this JSON format and nothing else:
{"pair": 1, "better": "left" | "right" | "tie",
 "margin": "slight" | "clear" | "large",
 "deficits_of_worse": ["<specific, visible, located deficit>", ...]}

A deficit must name what is wrong and where. "Looks fake" is not a deficit.
"The left tyre does not flatten where it touches the ground" is a deficit.
Do not be polite. If the two are the same, say "tie".
```

## After the answer

1. Add the key to each pair. A pair where `better` is our side, or `tie`,
   is a win or a tie.
2. Write the round file in the format in `references/schemas.md`.
3. Rows that win or tie: set `matches` or `exceeds`. Rows that lose: set
   `below`, and turn each deficit into a sense check where one can catch it
   (`references/checks.md`).
