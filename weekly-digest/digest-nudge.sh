#!/bin/bash
# SessionStart nudge: prints a reminder when the weekly digest is overdue.
# Reads last_run from local-config.yml next to this script (resolves through
# the ~/.claude/skills symlink). Silent no-op in every other case.

CONFIG="$(dirname "$0")/local-config.yml"
[ -f "$CONFIG" ] || exit 0

last=$(awk -F': ' '/^last_run:/{print $2}' "$CONFIG" | awk '{print $1}')
[ -n "$last" ] || exit 0

last_epoch=$(date -j -f "%Y-%m-%d" "$last" +%s 2>/dev/null || date -d "$last" +%s 2>/dev/null) || exit 0
now=$(date +%s)
days=$(((now - last_epoch) / 86400))

if [ "$days" -ge 7 ]; then
  echo "📣 Weekly digest overdue — last one covered through $last (${days}d ago). Run /weekly-digest."
fi
exit 0
