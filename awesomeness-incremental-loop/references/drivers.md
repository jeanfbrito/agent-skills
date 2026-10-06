# Drivers: how any harness repeats the cycle

The loop is one cycle, repeated. A cycle reads its state from the journal,
ships one thing, writes the state back, and ends (SKILL.md, "One cycle"). The
driver is the part that starts the next cycle. The skill does not depend on a
harness, because the cycle carries nothing in memory.

Choose the first driver that the harness can do. Write its name in the
journal, in Setup `Driver:`. Start it once, at the end of the Start steps.

| Driver | What the harness must do | Examples |
| --- | --- | --- |
| `in-session` | Start its next turn by itself, with no message from the human | Claude Code: `/loop /awesomeness-incremental-loop` with no interval. Codex: `/goal` |
| `scheduler` | Store a prompt and run it again on an interval, each time in a new agent | Grok: `scheduler_create`. Claude Code: `CronCreate` or a cloud routine |
| `shell` | Run one prompt headless from a terminal and exit | Any agent CLI: `grok`, `claude -p`, `codex exec` |
| `inline` | None of these | Any harness |

## in-session

Do one cycle per turn. At the end of the turn, start the next turn at the
minimum delay that the harness allows. A context compaction loses nothing,
because the next cycle reads `state.py brief`.

## scheduler

1. Fill `{project}` in `references/fire-prompt.md` and store that text as the
   scheduled prompt. Store it once. Do not edit it later.
2. Set the interval to about one normal cycle: 10 minutes is a good start.
   A run that starts while another cycle holds the lock exits in one call.
3. The runs must be new. Some schedulers carry the earlier runs into the next
   run (Grok writes "Earlier iterations, if any, appear above"). Then each run
   reads more, costs more, and at last fails at its start on a context or
   resume limit. When a run fails at its start, delete the task and create it
   again with the same prompt. That is the only schedule change that the
   loop makes. For a run that must last all night on such a harness, use the
   `shell` driver.

## shell

`tools/drive.sh` repeats the run prompt with any agent CLI. Each run is a new
process, so no transcript carries over. The human starts it in a terminal, or
the session starts it as a background command:

```bash
D=~/Github/agent-skills/awesomeness-incremental-loop/tools/drive.sh
$D --project ~/Github/game -- grok --prompt-file {prompt_file} --cwd {project} --always-approve
$D --project ~/Github/game -- claude -p {prompt} --permission-mode bypassPermissions
$D --project ~/Github/game -- codex exec --full-auto {prompt}
```

The agent needs permission to edit and run commands with no prompts. That is
the human's choice: say which flag gives it, and let the human start it. A run
that fails fast (auth, a bad flag) makes the driver wait longer each time. It
never stops by itself. The log is `.localdev/awesomeness/drive.log`.

## inline

Do the cycles back to back in the current turn. Do not end the turn. Before
the first cycle, print this line once: "This harness cannot restart me. The
loop stops when this turn ends. For an unattended run, start
tools/drive.sh." Then start the cycles.

## The session that starts a driver is a watcher

With `scheduler` or `shell`, other runs do the cycles. The session that started
them does this:

- It reads each status line. The run already did its own self-check, so the
  watcher does not run those checks again. It opens the evidence only when a
  status line has no commit or no evidence, or disagrees with the journal.
- It writes any change of plan in the journal as a human priority. The next run reads it there. The stored prompt stays the same.
- Before it edits the project by hand, it runs `state.py pause`. After the
  edit, it commits and runs `state.py resume`.
- It does not delete or pause the schedule on its own. Only the human stops
  the loop: Ctrl-C on the driver, `state.py pause`, or a request to delete
  the schedule.
