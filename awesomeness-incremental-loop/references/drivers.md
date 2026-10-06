# Drivers: how any harness repeats the cycle

The loop is one cycle, repeated. A cycle reads its state from the journal and
the trail, ships one thing, writes each step as it happens, and ends
(SKILL.md, "One cycle"). The driver is the part that starts the next cycle.
The skill does not depend on a harness, because the cycle keeps nothing in
memory.

The human types only the skill command. The agent starts the driver itself,
at the end of the Start steps. Use the first driver that works here, and
write its name in the journal, in Setup `Driver:`.

| Driver | Use it when | How |
| --- | --- | --- |
| `shell` (default) | The agent's own CLI can run one prompt headless | `tools/drive.sh --agent <cli> --detach` |
| `scheduler` | No headless CLI, but the harness can run a stored prompt on an interval | The harness scheduler, with the prompt in `fire-prompt.md` |
| `in-session` | Neither, but the harness can start its next turn by itself | Claude Code `/loop` with no interval, Codex `/goal` |
| `inline` | None of these | Cycles back to back in the current turn |

## shell (the default)

```bash
~/Github/agent-skills/awesomeness-incremental-loop/tools/drive.sh --project <repo> --agent grok --detach
```

- `--agent` picks the preset for the CLI that runs you: `grok`, `claude` or
  `codex`. For another CLI, give its headless command after `--`, with
  `{prompt_file}` or `{prompt}` in it (`drive.sh --help`).
- `--detach` starts the driver in its own session. It keeps running when the
  agent session or the terminal closes. It prints its pid, its log
  (`.localdev/awesomeness/drive.log`) and the stop command.
- Each cycle is a new process of the agent CLI, so no transcript carries
  over. No run gets slower or dearer than the run before it.
- One driver per project. A second start reports the running driver and
  exits, so it is safe to run the skill command again.
- The presets run the agent with no permission prompts (`--always-approve`,
  `bypassPermissions`, Codex's bypass flag). The human asked for unattended
  cycles when they started the loop. The loop rules still forbid push, pull
  requests and messages.
- A run that fails fast (auth, a bad flag) makes the driver wait longer each
  time. It never stops by itself.
- Brake: `drive.sh --project <repo> --stop` stops the driver and the cycle in
  progress. The next start continues that cycle from the trail.
  `state.py pause` makes the driver wait until `state.py resume`.
  `drive.sh --project <repo> --status` shows if it runs.

## scheduler

1. Fill `{project}` in `references/fire-prompt.md` and store that text as the
   scheduled prompt. Store it once. Do not edit it later.
2. Set the interval to about one normal cycle: 10 minutes is a good start.
   A run that starts while another cycle holds the lock exits in one call.
3. Some schedulers carry the earlier runs into the next run (Grok writes
   "Earlier iterations, if any, appear above"). Then each run reads more,
   costs more, and at last fails at its start on a context or resume limit.
   On such a scheduler, after every 5 runs, delete the task and create it
   again with the same prompt. Do the same at once when a run fails at its
   start. These are the only schedule changes that the loop makes.

## in-session

Do one cycle per turn. At the end of the turn, start the next turn at the
minimum delay that the harness allows. A context compaction loses nothing,
because the next cycle reads `state.py brief`.

## inline

Do the cycles back to back in the current turn. Do not end the turn. Before
the first cycle, print this line once: "This harness cannot restart me. The
loop stops when this turn ends."

## The session that starts a driver is a watcher

With `shell` or `scheduler`, other runs do the cycles. The session that started
them does this:

- It does not do cycles itself. It can end its turn. The driver goes on.
- When it reads a status line, it does not run that run's checks again. It
  opens the evidence only when a status line has no commit or no evidence, or
  disagrees with the journal. The live report shows the same facts.
- It writes any change of plan in the journal as a human priority. The next
  run reads it there. The run prompt stays the same.
- Before it edits the project by hand, it runs `state.py pause`. After the
  edit, it commits and runs `state.py resume`.
- It does not stop the driver or the schedule on its own. Only the human stops
  the loop.
