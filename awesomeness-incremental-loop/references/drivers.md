# The orchestrator: how the session repeats the cycle

The loop is one cycle, repeated. A cycle reads its state from the journal and
the trail, ships one thing, writes each step as it happens, and ends
(SKILL.md, "One cycle"). The session that the human started with the skill
command runs the loop. It stays in that session, where the human sees it and
stops it.

## Subagents (the default)

The session is the **orchestrator**. It does no cycle work itself:

1. Spawn one new subagent. Give it the prompt in `references/fire-prompt.md`,
   with `{project}` filled. Give it nothing else: its state is on disk.
2. Wait for it to end. Read only its last line, the status line.
3. Print that status line for the human. Then spawn the next new subagent.
   Repeat without end.

Rules:

- **A new subagent for each cycle.** Do not resume or continue an earlier
  subagent. A resumed subagent carries the history of every cycle before it.
  Each run then costs more, and at last fails at its start on a context
  limit (lessons 24 and 25).
- **The prompt never changes.** Do not add the next item, the commit or
  "do not retry" notes to it. The subagent reads them from the trail
  (`state.py brief`). A plan change from the human goes in the journal as a
  human priority.
- **One cycle at a time.** Spawn the next subagent only after the last one
  ends. The cycle lock also refuses a second cycle.
- **A lock left behind.** When a cycle subagent has ended and the lock is still
  there, its run died before it could unlock. Run `state.py unlock --orphan`,
  then spawn the next cycle. That cycle continues the open cycle from the trail.
- **Trust the status line.** The subagent did its own self-check. The
  orchestrator does not run those checks again. It opens the evidence only
  when a status line has no commit or no evidence, or disagrees with the
  journal. The live report shows the same facts.
- **The loop does not stop itself.** A status line that says "nothing left"
  is not a stop: the next cycle reads the `EXHAUSTED` signal and continues.
- **Waiting.** If the harness wakes the session when a background subagent
  ends (Grok and Claude Code do), spawn it in the background and end the
  turn. The completion message starts the next turn: spawn the next cycle
  then. If the harness does not wake the session, wait for the subagent in
  the same turn and do not end the turn.
- **Hand work.** If the human asks this session for other work while the loop
  runs, run `state.py pause`, do the work, commit, and run `state.py resume`.

## A harness with no subagents

- If the harness can start its next turn by itself (Claude Code `/loop` with
  no interval, Codex `/goal`), do one cycle per turn in the session.
- If it cannot, do the cycles back to back in the current turn. Before the
  first cycle, print once: "This harness cannot restart me. The loop stops
  when this turn ends."

A context compaction loses nothing, because each cycle reads `state.py brief`.

## Outside the session (only when the human asks)

`tools/drive.sh` runs the same cycle prompt with an agent CLI. Each cycle is
a new process. Use it, for example, on a machine with no open agent session.
The skill never starts it by itself, and it refuses to start without
`--human-asked`. `drive.sh --help` gives the presets
(`--agent grok|claude|codex`), `--detach`, `--status` and `--stop`.
