#!/usr/bin/env bash
# Read-only: print free space and the size of the known large spots.
# The du calls of a section run in parallel, each with a time limit, so a slow folder cannot hang the survey.
set -u
LIMIT=${SURVEY_LIMIT:-60}

size() {
  local p=$1 out
  [ -e "$p" ] || return 0
  out=$( (command du -sk "$p" 2>/dev/null & pid=$!; (sleep "$LIMIT"; kill "$pid" 2>/dev/null) & w=$!; wait "$pid" 2>/dev/null; kill "$w" 2>/dev/null) | cut -f1)
  if [ -n "$out" ]; then
    awk -v k="$out" -v p="$p" 'BEGIN { printf "%8.1f GiB  %s\n", k/1048576, p }'
  else
    printf "%8s      %s\n" "timeout" "$p"
  fi
}

echo "== df"
df -h /System/Volumes/Data | tail -1

echo "== caches (safe to clean)"
for p in ~/Library/Caches ~/.cache ~/.npm ~/.yarn/berry/cache ~/Library/Caches/Yarn \
  ~/Library/pnpm ~/.gradle/caches ~/Library/Developer/Xcode/DerivedData \
  ~/Library/Developer/CoreSimulator/Caches ~/Library/Caches/ms-playwright \
  ~/.cache/puppeteer ~/Library/Caches/electron ~/.cache/uv; do size "$p" & done; wait

echo "== agent data"
for p in ~/.codex/sessions ~/.codex/.tmp ~/.grok/sessions ~/.grok/worktrees ~/.claude/projects; do size "$p" & done; wait

echo "== docker and VMs"
for p in ~/Library/Containers/com.docker.docker ~/.rd ~/Library/Application\ Support/rancher-desktop ~/.colima; do size "$p" & done; wait

echo "== user data (ask first)"
for p in ~/Downloads ~/Desktop ~/Movies ~/Github ~/.Trash \
  ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared \
  ~/Library/Group\ Containers/6N38VWS5BX.ru.keepcoder.Telegram; do size "$p" & done; wait

echo "== local snapshots"
tmutil listlocalsnapshots / 2>/dev/null | tail -n +2 | wc -l | awk '{print $1 " snapshots"}'
