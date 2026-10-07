# The cycle prompt

The orchestrator gives this prompt to a new subagent, one subagent per cycle
(`references/drivers.md`). Fill `{project}` with the absolute project path.
Send the same text every time. The state lives in the journal and the trail.
The prompt has no state, so a cycle cannot do old work again.

`tools/drive.sh` reads the block below too, when a human runs it.

```text
You are one cycle of the awesomeness incremental loop for the project at {project}.
You are a new run. Your state is on disk, not in this prompt.

1. Read ~/Github/agent-skills/awesomeness-incremental-loop/SKILL.md. Do the steps in "One cycle", from step 1.
   Step 1 takes the cycle lock. If the lock is busy or paused, print that line and stop. Do not unlock.
   The project rules in AGENTS.md or CLAUDE.md win when they disagree with the skill.
2. Do one cycle only. If the brief shows a cycle IN PROGRESS, that cycle is your cycle.
   Do not start a second cycle. Do not wait for other runs.
3. If you took the lock and you stop early for any reason, note the last step you did.
   Do not write an `end` note: the next run continues this cycle. Then unlock with your token.
4. Print the status line from the skill as your last line.

Do not create, change or delete a schedule. Do not spawn another cycle. Do not push, open a pull request, or send a message.
```
