#!/usr/bin/env bash
# Repeat awesomeness-loop cycles with any agent CLI that runs headless.
# Each cycle is a new process, so no transcript carries over between cycles.
#
# Usage:
#   drive.sh [--project DIR] [--gap SEC] [--max N] -- <agent command ...>
#
# In the agent command, {prompt_file} becomes the path of the filled run
# prompt, {prompt} becomes its text, and {project} becomes the project path.
# Without {prompt_file} or {prompt}, the prompt text is the last argument.
#
# Examples:
#   drive.sh --project ~/Github/game -- grok --prompt-file {prompt_file} --cwd {project} --always-approve
#   drive.sh --project ~/Github/game -- claude -p {prompt} --permission-mode bypassPermissions
#   drive.sh --project ~/Github/game -- codex exec --full-auto {prompt}
#
# Stop: Ctrl-C, or `state.py pause` (the driver waits until `state.py resume`).
# --max N stops after N cycles (for a test). The default is no limit.
set -u
shopt -u patsub_replacement 2>/dev/null || true

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$PWD"
GAP=30
MAX=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$(cd "$2" && pwd)"; shift 2 ;;
    --gap) GAP="$2"; shift 2 ;;
    --max) MAX="$2"; shift 2 ;;
    --) shift; break ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "drive.sh: unknown option $1 (put the agent command after --)" >&2; exit 2 ;;
  esac
done
if [ $# -eq 0 ]; then
  echo "drive.sh: give the agent command after --" >&2
  exit 2
fi

ROOT="$PROJECT/.localdev/awesomeness"
mkdir -p "$ROOT"
PROMPT_FILE="$ROOT/run-prompt.txt"
LOG="$ROOT/drive.log"

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
echo "drive.sh: project $PROJECT. Log: $LOG. Stop with Ctrl-C or state.py pause."
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
  echo "run $n: exit $code, ${secs}s: ${last:0:200}"
  echo "=== exit $code after ${secs}s" >> "$LOG"
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
