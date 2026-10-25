#!/usr/bin/env bash
# branch-audit.sh [--remote origin] [--base main] [--delete-merged] [--keep <pattern>]...
#
# Lists the branches of a remote against its base branch, in two groups:
#   MERGED  every commit is in the base (an ancestor, or each patch is in the base: git cherry)
#   OPEN    commits ahead of the base, with ahead/behind counts, the last commit date, author and subject
# With --delete-merged it deletes the MERGED remote branches, except the base and any --keep pattern
# (a shell glob on the branch name). Run it once without the flag, show the list, and delete only
# what the user confirms.
#
# Output: one line per branch, tab-separated:  GROUP  branch  ahead  behind  date  author  subject
# Exit code: 0; 2 on a usage error.
set -euo pipefail

remote=origin
base=main
delete=0
keep=()
while [ $# -gt 0 ]; do
  case "$1" in
    --remote) remote=$2; shift 2 ;;
    --base) base=$2; shift 2 ;;
    --delete-merged) delete=1; shift ;;
    --keep) keep+=("$2"); shift 2 ;;
    -h|--help) sed -n 2,12p "$0"; exit 0 ;;
    *) echo "usage: $0 [--remote R] [--base B] [--delete-merged] [--keep GLOB]..." >&2; exit 2 ;;
  esac
done

git fetch --prune --quiet "$remote"
base_ref="$remote/$base"
git rev-parse --verify --quiet "$base_ref" >/dev/null || { echo "no branch $base_ref" >&2; exit 2; }

kept() {
  local b=$1 p
  [ "$b" = "$base" ] && return 0
  for p in "${keep[@]:-}"; do
    [ -z "$p" ] && continue
    # shellcheck disable=SC2254
    case "$b" in $p) return 0 ;; esac
  done
  return 1
}

merged_list=()
while IFS=$'\t' read -r ref date author subject; do
  b=${ref#refs/remotes/"$remote"/}
  [ "$b" = "HEAD" ] && continue
  ref=$b
  counts=$(git rev-list --left-right --count "$base_ref...$remote/$ref")
  behind=${counts%%	*}
  ahead=${counts##*	}
  group=OPEN
  if [ "$ahead" = 0 ]; then
    group=MERGED
  elif ! git cherry "$base_ref" "$remote/$ref" | grep -q '^+'; then
    group=MERGED   # every patch is in the base (a squash or a rebase merge)
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$group" "$b" "$ahead" "$behind" "$date" "$author" "$subject"
  if [ "$group" = MERGED ] && ! kept "$b"; then
    merged_list+=("$b")
  fi
done < <(git for-each-ref "refs/remotes/$remote" --sort=-committerdate \
          --format='%(refname)%09%(committerdate:short)%09%(authorname)%09%(subject)')

echo "merged and not kept: ${#merged_list[@]}" >&2
if [ "$delete" = 1 ] && [ "${#merged_list[@]}" -gt 0 ]; then
  git push "$remote" --delete "${merged_list[@]}"
  echo "deleted ${#merged_list[@]} branches on $remote" >&2
fi
