---
name: one-page-design
description: 'Draws one printable diagram of one design idea: a title, a date, one central figure, and callouts, using Stone Librande''s GDC 2010 one-page design tests. Triggered by "/one-page-design", "one page design", "one-page design", "put this on one page", "wall sheet", "relationship diagram of this system". Not a text one-pager, a GDD, or a proposal.'
---

# One-page design

Draw one sheet a person can print and mark up. The method is Stone
Librande, GDC 2010, "One Page Designs"
(https://www.youtube.com/watch?v=E9_wLks1kAg). This file is the
procedure. Do not reread the talk to run the skill. Where each rule
came from, with timestamps, is in
`~/Github/agent-skills/one-page-design/references/sources.md`. The
vault write-up with the examples is
`~/Github/mindness/Knowledge/One-Page Designs.md`.

## Not this skill

- A text one-pager (goals, problem, alternatives, priorities), a GDD,
  or a feature index. Those say where a decision is written. This
  sheet shows how the parts act on each other.
- A proposal. Use the `proposal` skill.
- A design bible, a wiki page, or a poster of prose. Shrinking a long
  document onto one page fails the method.
- A generated picture. Labels must be facts. Draw vector marks.

## 1. Title, or stop

Name the one idea in a short title. If you cannot, ask which idea
this sheet is and do not draw. A second idea is a second file.

Name the reader too. An architect draws the elevation for the client
and the stud spacing for the builder from the same house. A second
audience is a second file.

## 2. Read the system

Read the code, notes, or description the user pointed at. Every label
on the sheet comes from that reading or from the user. Leave an
unknown as an empty callout marked `unknown`. Do not invent counts,
names, timings, or links.

## 3. Pick one frame

Say which frame you are using before drawing.

- **Loop.** What the actor does, and what the system answers, until
  stop. Draw this first when you do not yet know the system.
- **Score.** Parts in time order with every named thing on them,
  like a musical score: each stop, what is there, what the actor
  should be by then. State the intended duration first, then place
  content on it. Do not measure the duration after the content is
  listed.
- **Storyboard.** The key moments in play order as small framed
  pictures with a caption each, and timing marks between them. No
  mechanics. This is the sheet for a reader outside the team.
- **Time + space.** A map with the path drawn across it and a time
  axis along the bottom, so where and when read as one figure.
- **Modules.** How areas connect, including the path from one to the
  next.
- **Units.** How entities relate. Three corners with one winner each
  (rock-paper-scissors) is a bad frame: redraw each entity as a range
  the actor can slide.
- **Matrix.** Name the two axes first. Fill cells after the axes are
  fixed. More than two dimensions does not get a grid. Collapse it
  to a rule the reader can apply, or stop and say the frame failed.

If the first picture looks finished and misstates a relationship,
redraw it. Say what the first picture got wrong. The usual case is a
symmetric shape, a circle or a wheel, that puts two things next to
each other that are not next to each other in the design.

A physical system can be drawn as marks before art: an actor as O,
a target as X, an arrow for each move. That sheet shows every atomic
action, and the real art comes later.

## 4. Write one print file

Create the file first, then draw in it. Do not plan coordinates in
prose.

```sh
~/Github/agent-skills/one-page-design/new-sheet.sh "<title>" <frame> designs
```

It copies `skeleton.html` from the skill folder (letter landscape, a
title, a date, one figure between two callout columns, a footer) to
`designs/YYYY-MM-DD - <title>.html` in the project you are working
in, with `screen-layer.js` inlined, and refuses to overwrite. Never
overwrite an older dated file. Do not commit, and do not write the
vault, unless the user asks.

Prefer the wide layout: `class="wide"` on the stage and the callouts
in `<aside class="notes">` under the figure in four short columns.
A figure across the page prints twice the size of one squeezed
between columns. Keep the two-column skeleton for a tall drawing.

The print page is the artifact. A scrolling browser window is not.
Keep it to one printed page: letter landscape unless the user names
another size. A bigger sheet (tabloid, A3) is allowed when the user
names it, by changing `@page`. Smaller type is not.

The screen layer runs only on screen: it traces relationships on
hover, shows the source of each label, zooms like walking closer, and
gives the reader a pencil. In print it does nothing. Mark the figure
and the callouts with `data-id`, `data-rel`, `data-for` and
`data-src` as `~/Github/agent-skills/one-page-design/references/screen-layer.md`
says. Read that file before writing the markup.

Rules for the sheet:

- White space stays. A callout under 9pt means cut the sheet, not the
  type.
- Three reading tiers. The title and the figure's shape read from
  across the room. The callouts read standing in front of it. The
  small notes read leaning in. Decide which tier each fact is in and
  drop what has no tier.
- One figure. Notes sit in callouts beside what they describe.
- Put time on a loop or a score.
- The skeleton's tokens are the look: paper with a dot grid, slate
  ink, muted lines, grey zones, sans names, mono sublabels, one
  accent. The accent goes on the focal path and at most one node.
  One node may be ink-filled as the centre. Black hairline boxes on
  white are not a design.
- Draw the thing, not a box with its name. Every node carries a
  pictogram of what it is, in the figure's own line weight, and a
  region gets a faint tint. Ornament that is not a design fact stays
  off. A sheet of labelled rectangles is a web page from 2000, not a
  drawing. Starter pictograms and the grid for new ones:
  `~/Github/agent-skills/one-page-design/references/pictograms.md`.
- Every label carries where it was read, in `data-src`, or is marked
  `unknown`. The reader can click any fact and check you.

Rules for the figure. The fit check measures each one:

- Draw regions, then edges, then nodes, so lines sit behind boxes.
- One focal path, drawn bold with `class="edge ring"`. Everything else
  thin. Wanting three bold paths means the idea is not chosen yet.
- Lines are horizontal or vertical and turn at right angles. No
  diagonals, no curves.
- A label sits beside its line, 4px or more off the stroke, never on
  it, never rotated, never under a box. The skeleton gives labels a
  white halo so they stay readable where lines cross.
- A line never passes behind a box it does not connect. Reroute it or
  cut the edge.
- Lines that share a box edge attach 10px or more apart.
- Dashed means a report back. The caption is the legend: say what
  solid, bold and dashed mean there.
- Budget: about 12 nodes and 18 edges. Above that, split into an
  overview sheet and a detail sheet, each dated.
- The svg starts with a `<title>` and a `<desc>`.
- A label is a fact. When it collides: move it, then reroute the
  line, then shorten the words. Delete it only when both ends already
  say it. Never delete a label to pass the check.

## 5. Fit test

Run the check. Do not report "one page" from reading the HTML.

```sh
~/Github/agent-skills/one-page-design/fit-check.sh "designs/YYYY-MM-DD - <title>.html" --keep
```

It renders the sheet with headless Chrome and prints: the page count,
each element whose content overflows its box, whether the print is the
same with and without the screen layer, labels with no `data-src`, the
geometry findings against the figure rules, the node and edge count,
and `FIT` or `DOES NOT FIT`. `--keep` leaves the PDF next to the HTML.
Quote the output in the reply. If Chrome is missing, say `UNVERIFIED`
and why.

Repair one finding at a time with the smallest change, then rerun.
After two rounds that do not lower the count, stop and report what
remains. Do not loosen the check, and do not add `overflow: hidden`:
hidden text is a cut nobody chose.

A passing check is not a visual review. Rasterize the PDF (on macOS:
`sips -s format png "<pdf>" --out <png>`), look at the image, and say
what you saw. Then check by eye:

- One idea, one date, one figure.
- You can still see margin on the printed page.
- Every arrow or cell is a relationship you read, not a guess.
- More than two dimensions were collapsed or refused.
- A rock-paper-scissors corner was redrawn as a range.

If it does not fit, the frame is wrong or the design is too big. Say
which, and either redraw or stop. Do not shrink the text until it fits.

## 6. Deliver

In the reply, give the file path, the frame you chose, and two lists:

- **On the sheet.** What a passerby must see.
- **Cut.** Facts you read that did not fit. The next dated file can
  pull one of them up.

The file is a working copy, not a museum piece. Ask what to mark. The
marked sheet is the input of the next dated file. Do not file a task,
open a ticket, or treat the sheet as a decision.
