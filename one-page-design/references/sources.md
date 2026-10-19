# Sources

## Stone Librande, "One Page Designs", GDC 2010

- URL: https://www.youtube.com/watch?v=E9_wLks1kAg (re-upload by circache, 51:59)
- Transcript: `yt2txt` cache, `~/.local/share/yt-transcripts/E9_wLks1kAg-*.md`
- Frames: `yt2frame <url> 23:30 26:30 28:00 28:45 31:50 32:15 33:05 34:15 38:10 42:50 45:40`

Timestamped takeaways. The skill body is the procedure; this list
says where each rule came from.

| Stamp | What the talk shows | Rule in the skill |
| --- | --- | --- |
| 11:18 | Architect drawings: one building, one sheet for the client (elevation) and another for the contractor (stud spacing). | Step 1: a second audience is a second file. |
| 13:00 | Napoleon's march chart: army width, path, temperature and dates on one figure. | Time + space frame. |
| 14:05 | Diablo UI flowchart on legal paper; a programmer hung it on his wall unasked. | The wall test. |
| 15:10 | Early prototype sheet with hand notes from meetings, then a new print. | Step 6: the marked sheet is the input of the next dated file. |
| 16:00 | Act one as a "musical score": every waypoint and monster, expected player level, time marks like "Level 13: 20 minutes (1:30-1:50)". | Score frame. |
| 18:10 | Combat drawn as X's and O's with arrows: the atomic moves of the game. | Abstract a physical system into marks before adding art. |
| 23:30 | The template slide: title and date top-left, "lots of whitespace", main illustration centre, callouts with leader lines, sidebar of bullets, a detail illustration with notes, a description under the figure. | Step 4 skeleton. |
| 23:13 | "If you can't fill in the title, stop." Date every print. | Step 1, Step 4. |
| 26:30 | Flowchart first when new to a system: player acts, system answers, feedback loops. | Loop frame, drawn first. |
| 28:00 | Storyboard of the key moments in play order, with timing marks; the sheet to hand to marketing or an executive. | Storyboard frame. |
| 28:45 | Spore continent: the path across islands with a time and power axis along the bottom. "Decide the intended duration first, then make content match." | Time + space frame; score rule. |
| 31:50 | Relationships between modules: every area and the path from one to the next, around one central drawing. | Modules frame. |
| 32:15 | Rock-paper-scissors triangle with one faction per corner. | Units frame, bad shape. |
| 33:05 | Same triangle with factions on the sides as sliders: "mostly scissors with a little rock". | Units frame: redraw corners as ranges. |
| 34:15 | Matrix: name the two axes first, fill cells top-down; Excel is fine; the filled grid is the programmer's checklist. | Matrix frame. |
| 36:10 | A four-dimension spreadsheet nobody can read. | Matrix frame: more than two dimensions collapses to a rule or stops. |
| 38:10 | The "dreamcatcher": beautiful, symmetric, wrong (adjacent on the circle but not adjacent in the design). | Step 3: redraw a finished picture that misstates a relationship. |
| 41:20 | The fix: a vector rule, 36 reachable states in place of a 256-row table. | Matrix frame: collapse to a rule. |
| 42:50 | Plotting every vector from one origin revealed the real shape. | Draw the space to discover it. |
| 43:33 | Print it and hand it over yourself; bring pencils; it is a working copy, not a museum piece. | Step 6. |
| 45:40 | The sheet back from a level designer covered in pencil. | Step 6: ask what to mark. |
| 46:34 | Below about four-point type, stop: decide tier one, two, three of what must be seen. | Three reading tiers; never shrink the type. |
| 49:36 | Updating one sheet can be the whole week's job. Once it is on the wall the design is near final. | Step 6: the file is a working copy until it goes up. |
| 50:37 | "A subtractive art": decide what to leave out, then spend the time helping people unpack it. | Step 6: the Cut list. |

## cathrynlavery/diagram-design

- URL: https://github.com/cathrynlavery/diagram-design
- Taken, in our own words: the six connector rules (orthogonal elbows,
  labels off the stroke on a mask, no stacked strokes, spaced attach
  points, no transit behind a non-endpoint box, no label under a later
  node), the one-focal-path rule, a complexity budget with a split
  above it, no rotated text on arrows, a `<title>` and `<desc>` on the
  figure, and the idea of a geometry gate. Our gate is our own script,
  keyed to our markup; theirs did not see our arrows at all when run on
  a sheet (measured 2026-10-09).
- Also taken, as our own tokens with system fonts: paper with a dot
  grid, slate ink, muted lines, one accent, grey zones, sans names
  with mono sublabels and uppercase mono edge labels, type-tag chips,
  an ink-filled centre node. The first attempt kept their rules and
  refused their look, and the sheets read as web pages from 2000.
- Not taken: Google Fonts, size presets, the many diagram types.

## archify (tt-a1i, from Cocoon-AI/architecture-diagram-generator)

- Installed at `~/.claude/skills/archify`.
- Taken, in our own words: write the file first and never plan
  coordinates in prose; a bounded repair loop (one diagnosed fix per
  round, stop after two rounds with no improvement and report); labels
  are facts (move, reroute, shorten, delete only when both ends say it,
  never to pass a check); an automated pass is not a visual review.
- Not taken: the JSON specification, the renderer and viewer runtime,
  brand marks, legends as a separate strip.
