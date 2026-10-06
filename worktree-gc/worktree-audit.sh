#!/usr/bin/env bash
# Read-only worktree audit. Classifies every worktree of the repo it runs in.
# Never deletes, removes, or modifies anything.
#
# Usage: worktree-audit.sh [repo-path]   (defaults to the current repo)
#
# Buckets (first match wins):
#   keep-tracked-changes   tracked uncommitted changes
#   keep-open-pr           branch has an open PR
#   keep-recent-session    a Claude Code session touched the path in the last 7 days
#   safe-merged            clean, and merged PR, or HEAD is an ancestor of the default
#                          branch and the branch reflog shows commits of its own
#   deletable-untracked    merged, and the only changes are untracked files (listed below)
#   review                 none of the above (includes CLOSED-not-merged PRs)
#
# Adapted from cursor/plugins pstack worktree-audit.sh (MIT License).
set -u

repo="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$repo" ] && { echo "not in a git repo; pass a repo path" >&2; exit 1; }
cd "$repo" || exit 1

main_wt=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')

default_ref=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
if [ -z "$default_ref" ]; then
	echo "error: refs/remotes/origin/HEAD not set; run: git remote set-head origin -a" >&2
	exit 1
fi

# PR state by branch, fetched once. Empty list if gh is unavailable.
prs=$(mktemp)
trap 'rm -f "$prs"' EXIT
if ! gh pr list --state all --limit 1000 \
	--json number,state,headRefName 2>/dev/null > "$prs" || [ ! -s "$prs" ]; then
	echo "warn: gh pr list failed; PR column is unknown" >&2
	echo "[]" > "$prs"
	gh_ok=no
else
	gh_ok=yes
fi

# Claude Code names project dirs by replacing every non-alphanumeric char with '-'.
slugify() { printf '%s' "$1" | sed 's/[^A-Za-z0-9]/-/g'; }
projects="$HOME/.claude/projects"
main_slug=$(slugify "$main_wt")
now=$(date +%s)

# Echo the newest mtime (epoch) of a session file in the last 7 days that
# references path $1, or nothing.
recent_session() {
	local wt="$1" own newest=0 f m
	own="$projects/$(slugify "$wt")"
	# Sessions started inside the worktree live in its own slug dir.
	for f in "$own"/*.jsonl; do
		[ -f "$f" ] || continue
		m=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null) || continue
		[ $(( now - m )) -le 604800 ] && [ "$m" -gt "$newest" ] && newest=$m
	done
	# Sessions started elsewhere (main checkout) that mention the path.
	if [ -d "$projects/$main_slug" ]; then
		while IFS= read -r f; do
			m=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null) || continue
			[ "$m" -gt "$newest" ] && newest=$m
		done < <(find "$projects/$main_slug" -maxdepth 3 -name '*.jsonl' -mtime -7 \
			-exec grep -lF -e "$wt/" -e "$wt\"" {} + 2>/dev/null)
	fi
	[ "$newest" -gt 0 ] && echo "$newest"
}

untracked_report=""
printf "BUCKET\tAGE\tPR\tCHANGES\tLAST_SESSION\tBRANCH\tWORKTREE\n"

while read -r wt; do
	[ "$wt" = "$main_wt" ] && continue

	head=$(git -C "$wt" rev-parse HEAD 2>/dev/null)
	head_ts=$(git -C "$wt" log -1 --format='%ct' HEAD 2>/dev/null || echo 0)
	age=$([ "${head_ts:-0}" -gt 0 ] && echo "$(( (now - head_ts) / 86400 ))d" || echo "?")
	branch=$(git -C "$wt" symbolic-ref --quiet --short HEAD 2>/dev/null || echo "")

	git merge-base --is-ancestor "$head" "$default_ref" 2>/dev/null && ancestor=yes || ancestor=no
	# A branch created from the default branch and never committed on is also an
	# ancestor; only a branch whose reflog shows its own commits counts as merged.
	own_commits=no
	if [ -n "$branch" ] && git reflog show --format=%gs "refs/heads/$branch" 2>/dev/null |
		grep -qvE '^(branch: (Created|Renamed)|reset: )'; then
		own_commits=yes
	fi

	porcelain=$(git -C "$wt" status --porcelain 2>/dev/null)
	if [ -z "$porcelain" ]; then changes=clean
	elif printf '%s\n' "$porcelain" | grep -qv '^??'; then
		changes="tracked:$(printf '%s\n' "$porcelain" | grep -cv '^??')"
	else changes="untracked:$(printf '%s\n' "$porcelain" | grep -c '^??')"; fi

	# PR state: OPEN wins, then MERGED, then CLOSED. Only MERGED counts as merged.
	pr="-"
	if [ -n "$branch" ]; then
		states=$(jq -r --arg b "$branch" '.[] | select(.headRefName==$b) | "\(.state) #\(.number)"' "$prs" 2>/dev/null)
		for s in OPEN MERGED CLOSED; do
			hit=$(printf '%s\n' "$states" | grep -m1 "^$s ")
			[ -n "$hit" ] && { pr="$hit"; break; }
		done
	fi
	[ "$gh_ok" = no ] && pr="unknown"

	last_ts=$(recent_session "$wt")
	last=$([ -n "$last_ts" ] && date -r "$last_ts" '+%Y-%m-%d' 2>/dev/null || echo "-")

	case "$changes" in
	tracked:*) bucket=keep-tracked-changes ;;
	*)
		case "$pr" in
		OPEN*) bucket=keep-open-pr ;;
		*)
			if [ -n "$last_ts" ]; then bucket=keep-recent-session
			elif [ "${pr#MERGED}" != "$pr" ] || { [ "$ancestor" = yes ] && [ "$own_commits" = yes ]; }; then
				case "$changes" in
				untracked:*) bucket=deletable-untracked ;;
				*) bucket=safe-merged ;;
				esac
			else bucket=review; fi ;;
		esac ;;
	esac

	if [ "$bucket" = deletable-untracked ]; then
		untracked_report="${untracked_report}
== $wt (branch ${branch:-detached}, PR $pr)
$(printf '%s\n' "$porcelain" | sed 's/^?? /   /')"
	fi

	printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
		"$bucket" "$age" "$pr" "$changes" "$last" "${branch:-detached}" "$wt"
done < <(git worktree list --porcelain | awk '/^worktree /{print $2}')

if [ -n "$untracked_report" ]; then
	printf '\nUntracked files in deletable-untracked worktrees:%s\n' "$untracked_report"
fi
