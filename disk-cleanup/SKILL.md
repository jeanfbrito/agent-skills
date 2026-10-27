---
name: disk-cleanup
description: Frees disk space on a macOS dev machine. Measures the known large spots first. Deletes data that rebuilds itself without asking. Asks before it touches the user's own files (Downloads, chat media, repos). Restarts a hung Docker Desktop and prunes it. Reports free space before and after, measured with df. Triggered by "/disk-cleanup", "clean the disk", "clean the machine", "free disk space", "disk is full", "limpa o disco", "libera espaço", "what can we delete".
---

# Disk cleanup (macOS)

Let `D` = `~/Github/agent-skills/disk-cleanup/scripts`.

This skill came from 3 sessions (Oct 2026) that found the same steps again
each time. Use these steps. Do not search old transcripts for the method.

## Rules

- Measure free space with `df -h /System/Volumes/Data` at the start, after
  each step and at the end. Report the `df` numbers, not the sum of `du`.
- Delete without asking only data that a tool makes again by itself: package
  manager caches, build caches, `~/Library/Caches`, old agent session logs.
- Ask before you delete anything else. Ask once, as one list with sizes.
  Examples: `~/Downloads`, chat app media (WhatsApp, Telegram), repos, VM
  images, ML model caches (slow to download again).
- Move user files to the Trash (`mv` into `~/.Trash`). Do not `rm` them. The
  user empties the Trash.
- Never delete a git worktree or clone with uncommitted changes or unpushed
  commits. Use the `worktree-gc` skill for worktrees.
- Before you delete inside an app's data folder, quit the app. Delete only
  media files, never the app's database.

## Steps

1. **Measure.** Run `$D/survey.sh`. It prints `df` and the size of each known
   large spot, and each `du` has a time limit (`SURVEY_LIMIT`, default 60 s).
   It took 2 min on this machine, so run it in the background. A `timeout`
   line means the folder is large: measure its subfolders. Do not run a full `du ~`
   in the foreground: it takes more than 10 minutes on this machine. Run
   it in the background if the survey does not explain the used space.
2. **Caches (no ask).** Use the tool's own clean command first:
   `yarn cache clean --all`, `npm cache clean --force`,
   `brew cleanup -s --prune=all`, `uv cache clean --force`
   (without `--force`, uv fails while a uv process runs), `pip cache purge`,
   `pnpm store prune`. Then delete the contents of `~/Library/Caches/*` and
   `~/Library/Developer/Xcode/DerivedData/*`. Delete `~/.cache/*`, but keep
   `huggingface`, `torch`, `whisper` and other model caches. Also delete the
   Electron, Playwright and Puppeteer download caches. Delete `node_modules`
   in worktrees older than 14 days.
3. **Agent data (no ask).** Delete `~/.codex/sessions` and `~/.grok/sessions`
   files older than 30 days. Delete `~/.codex/.tmp/marketplaces/.staging/*`
   entries older than 1 day (in one run this held 30 GB of copies).
4. **Docker.** Run `$D/docker-revive.sh`. Docker Desktop hung in 2 of 3
   runs. A backend from an earlier start stayed alive. `docker info` hung
   or returned EOF, and a quit request did nothing. The script checks the
   socket with a time limit, kills the stale backend and starts Docker
   again. Then run `docker system prune -a -f` and `docker builder prune -a -f`.
   Ask before `--volumes`: volumes can hold database data.
5. **Ask for the rest.** Show one table of the user's own items, largest
   first, with what each one is and whether it can come back. Delete only
   what the user names.
6. **If `df` does not move** after a large delete, check local snapshots
   (`tmutil listlocalsnapshots /`) and the Trash. Do not `sleep` to wait:
   the Bash tool blocks a leading `sleep`. Run `df` again in a later call.
7. **Report.** Free space before and after (from `df`), a table of what each
   step freed, and the numbered list of items that wait for the user.

## Parallel work

When the user asks for speed ("fan out"), give one subagent each to caches,
Docker and the survey. Give each one this file's rules. Two agents must not
work on the same folder.
