#!/usr/bin/env bash
# Repeat awesomeness-loop cycles with an agent CLI that runs headless.
# Each cycle is a new process, so no transcript carries over between cycles.
# The skill starts this itself (SKILL.md, Start step 6). A human can too.
#
# Usage:
#   drive.sh --project DIR --agent grok|claude|codex [--detach] [--gap SEC] [--max N]
#   drive.sh --project DIR [--detach] -- <agent command ...>
#   drive.sh --project DIR --status
#   drive.sh --project DIR --stop
#
# --agent uses a preset command for that CLI. With `--`, give your own command:
# {prompt_file} becomes the path of the filled run prompt, {prompt} its text,
# and {project} the project path. Without either, the text is the last argument.
# --detach starts the driver in its own session, so it keeps running after the
# agent session or the terminal that started it closes.
# One driver per project: a second start reports the running one and exits.
#
# Stop: drive.sh --stop, Ctrl-C in the foreground, or `state.py pause`
# (the driver then waits until `state.py resume`).
# --max N stops after N cycles (for a test). The default is no limit.
set -u
shopt -u patsub_replacement 2>/dev/null || true

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$PWD"
GAP=30
MAX=0
AGENT=""
DETACH=0
ACTION=run
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$(cd "$2" && pwd)" || exit 2; shift 2 ;;
    --gap) GAP="$2"; shift 2 ;;
    --max) MAX="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --detach) DETACH=1; shift ;;
    --status) ACTION=status; shift ;;
    --stop) ACTION=stop; shift ;;
    --) shift; break ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "drive.sh: unknown option $1 (put a custom agent command after --)" >&2; exit 2 ;;
  esac
done

ROOT="$PROJECT/.localdev/awesomeness"
mkdir -p "$ROOT"
PIDFILE="$ROOT/driver.pid"
LOG="$ROOT/drive.log"
PROMPT_FILE="$ROOT/run-prompt.txt"

running_pid() {
  local pid
  [ -f "$PIDFILE" ] || return 1
  pid="$(cat "$PIDFILE" 2>/dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && { echo "$pid"; return 0; }
  return 1
}

case "$ACTION" in
  status)
    if pid="$(running_pid)"; then
      echo "DRIVER RUNNING: pid $pid. Log: $LOG"
      grep '^run [0-9]*:' "$LOG" 2>/dev/null | tail -n 1
    else
      echo "DRIVER NOT RUNNING for $PROJECT"
    fi
    exit 0 ;;
  stop)
    if pid="$(running_pid)"; then
      # A detached driver leads its own process group: stop the group, so the
      # agent run in progress stops too. A foreground driver: stop it and its children.
      kill -TERM -- "-$pid" 2>/dev/null || { pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; }
      rm -f "$PIDFILE"
      echo "DRIVER STOPPED: pid $pid. A cycle that was running stops too. The next start continues it from the trail."
    else
      echo "DRIVER NOT RUNNING for $PROJECT"
    fi
    exit 0 ;;
esac

if [ -n "$AGENT" ]; then
  case "$AGENT" in
    grok) set -- grok --prompt-file "{prompt_file}" --cwd "{project}" --always-approve --output-format plain ;;
    claude) set -- claude -p "{prompt}" --permission-mode bypassPermissions ;;
    codex) set -- codex exec --dangerously-bypass-approvals-and-sandbox -C "{project}" "{prompt}" ;;
    *) echo "drive.sh: no preset for --agent $AGENT. Use grok, claude or codex, or give the command after --" >&2; exit 2 ;;
  esac
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "drive.sh: the $1 CLI is not on PATH" >&2
    exit 2
  fi
fi
if [ $# -eq 0 ]; then
  echo "drive.sh: give --agent grok|claude|codex, or the agent command after --" >&2
  exit 2
fi

if pid="$(running_pid)"; then
  echo "DRIVER ALREADY RUNNING: pid $pid. Log: $LOG. Stop: $SELF --project \"$PROJECT\" --stop"
  exit 0
fi

if [ "$DETACH" -eq 1 ]; then
  # A new session (setsid) leaves the caller's process group, so the harness
  # that ran this command cannot stop the driver when its command ends.
  AWESOME_DRIVER_DETACHED=1 python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
    nohup "$SELF" --project "$PROJECT" --gap "$GAP" --max "$MAX" -- "$@" >> "$LOG" 2>&1 < /dev/null &
  sleep 1
  if pid="$(running_pid)"; then
    echo "DRIVER STARTED: pid $pid, project $PROJECT. Log: $LOG"
    echo "Stop: $SELF --project \"$PROJECT\" --stop   Pause: state.py pause --project \"$PROJECT\""
    exit 0
  fi
  echo "drive.sh: the detached driver did not start. Read $LOG" >&2
  exit 1
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT
trap 'exit 130' INT TERM

# The run prompt is the first ```text block of references/fire-prompt.md.
TEMPLATE="$(awk '/^```text/{on=1; next} /^```/{if(on){exit}} on{print}' "$SKILL_DIR/references/fire-prompt.md")"
printf '%s\n' "${TEMPLATE//\{project\}/$PROJECT}" > "$PROMPT_FILE"
if [ ! -s "$PROMPT_FILE" ]; then
  echo "drive.sh: no run prompt found in $SKILL_DIR/references/fire-prompt.md" >&2
  exit 2
fi
PROMPT_TEXT="$(cat "$PROMPT_FILE")"

n=0
fails=0
echo "drive.sh: pid $$, project $PROJECT. Log: $LOG. Stop with --stop, Ctrl-C or state.py pause."
while :; do
  if [ -e "$ROOT/PAUSE" ]; then
    sleep 60
    continue
  fi
  n=$((n + 1))
  args=()
  used=0
  for a in "$@"; do
    case "$a" in
      *"{prompt_file}"*) a="${a//\{prompt_file\}/$PROMPT_FILE}"; used=1 ;;
    esac
    case "$a" in
      *"{prompt}"*) a="${a//\{prompt\}/$PROMPT_TEXT}"; used=1 ;;
    esac
    a="${a//\{project\}/$PROJECT}"
    args+=("$a")
  done
  [ "$used" -eq 1 ] || args+=("$PROMPT_TEXT")

  start=$(date +%s)
  echo "=== cycle run $n $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  (cd "$PROJECT" && "${args[@]}") >> "$LOG" 2>&1 < /dev/null
  code=$?
  secs=$(( $(date +%s) - start ))
  last="$(tail -n 1 "$LOG")"
  echo "=== exit $code after ${secs}s" >> "$LOG"
  # A detached driver's output already goes to the log. A foreground one also writes it there.
  echo "run $n: exit $code, ${secs}s: ${last:0:200}"
  [ "${AWESOME_DRIVER_DETACHED:-0}" -eq 1 ] || echo "run $n: exit $code, ${secs}s: ${last:0:200}" >> "$LOG"
  if [ "$MAX" -gt 0 ] && [ "$n" -ge "$MAX" ]; then
    echo "drive.sh: --max $MAX reached."
    exit 0
  fi

  # A run that fails fast (auth, a bad flag, a crash) waits longer each time.
  # The driver never stops on its own: only the human stops the loop.
  if [ "$code" -ne 0 ] && [ "$secs" -lt 60 ]; then
    fails=$((fails + 1))
    wait_s=$(( GAP * (2 ** (fails < 6 ? fails : 6)) ))
    echo "drive.sh: fast failure $fails. Next run in ${wait_s}s. Read $LOG."
    sleep "$wait_s"
  else
    fails=0
    sleep "$GAP"
  fi
done
