#!/usr/bin/env bash
# Stops embargoed work from leaving the machine.
#
# Usage:
#   embargo-guard.sh pre-push <remote> [url]   (git pre-push hook: reads refs on stdin)
#   embargo-guard.sh text <file>...            (PR body, ticket or post text)
#
# The denylist is private and lives outside every repo (default
# ~/.config/embargo/denylist, override with EMBARGO_DENYLIST). One rule per line:
#   ref <glob>      a branch name that is never pushed (matches local and remote ref)
#   branch <name>   commits that only this local branch has are never pushed
#   text <string>   a string that never appears in a pushed commit message or a checked text
# Lines that start with # are comments. A missing denylist allows everything.
# A human can override one push with EMBARGO_OK=1. An agent never sets it.
set -u
LIST=${EMBARGO_DENYLIST:-$HOME/.config/embargo/denylist}
[ -f "$LIST" ] || exit 0

rules() { awk -v k="$1" '$1 == k { $1 = ""; sub(/^ /, ""); print }' "$LIST"; }
fail=0
block() { echo "embargo-guard: BLOCKED: $*" >&2; fail=1; }

check_text() { # $1 label, stdin text
  local body t
  body=$(cat)
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    printf '%s' "$body" | command grep -qiF -- "$t" && block "$1 contains an embargoed string ($LIST)"
  done < <(rules text)
}

case "${1:-}" in
text)
  shift
  for f in "$@"; do check_text "$f" < "$f"; done
  ;;
pre-push)
  [ "${EMBARGO_OK:-}" = 1 ] && { echo "embargo-guard: override EMBARGO_OK=1" >&2; exit 0; }
  remote=${2:-origin}
  zero=0000000000000000000000000000000000000000
  # Commits that only an embargoed branch has: on the branch, not on any remote.
  embargoed=$(mktemp)
  trap 'rm -f "$embargoed"' EXIT
  while IFS= read -r b; do
    [ -n "$b" ] || continue
    git rev-parse -q --verify "refs/heads/$b" >/dev/null || continue
    git rev-list "refs/heads/$b" --not --remotes >> "$embargoed"
  done < <(rules branch)
  sort -u -o "$embargoed" "$embargoed"

  while read -r lref lsha rref _; do
    [ -n "${lref:-}" ] || continue
    names=("${lref#refs/heads/}")
    [ "${rref#refs/heads/}" = "${names[0]}" ] || names+=("${rref#refs/heads/}")
    for name in "${names[@]}"; do
      while IFS= read -r g; do
        [ -n "$g" ] || continue
        # shellcheck disable=SC2053
        [[ $name == $g ]] && block "ref '$name' matches 'ref $g'"
      done < <(rules ref)
    done
    [ "$lsha" = "$zero" ] && continue # a delete pushes no commits
    pushed=$(git rev-list "$lsha" --not --remotes="$remote")
    [ -n "$pushed" ] || continue
    if [ -s "$embargoed" ]; then
      hit=$(printf '%s\n' "$pushed" | sort -u | comm -12 - "$embargoed" | head -1)
      [ -n "$hit" ] && block "$rref would publish embargoed commit $(git log -1 --format='%h %s' "$hit")"
    fi
    msgs=$(printf '%s\n' "$pushed" | while read -r c; do git log -1 --format=%B "$c"; done)
    check_text "commit messages for $rref" <<< "$msgs"
  done
  ;;
*)
  sed -n '2,16p' "$0" >&2
  exit 2
  ;;
esac
exit "$fail"
