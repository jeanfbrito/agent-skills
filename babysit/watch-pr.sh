#!/usr/bin/env bash
# Poll one PR until something the babysit loop must act on appears, then print
# a single JSON digest and exit. Meant to be run by the haiku watcher agent, in
# repeated calls (each bounded by --timeout), never by the main model.
#
# Exit reasons (JSON "reason"):
#   feedback   new comment / review / inline comment from someone other than the PR author
#   checks     every check has concluded (green or not) and there is no new feedback
#   sha_moved  headRefOid changed under us
#   closed     PR is no longer OPEN
#   timeout    nothing changed within --timeout; call again with the same cursors
#
# Usage:
#   watch-pr.sh --pr 123 [--since-comment ID] [--since-review ID] [--since-inline ID] \
#               [--sha OID] [--bots "dionisio-bot,sonarcloud"] [--interval 120] [--timeout 540]
#
# Cursors are REST numeric ids (issue comments, reviews, inline comments are three
# separate id spaces). Pass the highest id seen of each kind to skip old items.
set -euo pipefail

pr="" since_comment=0 since_review=0 since_inline=0 sha="" bots="" interval=120 timeout=540
while [ $# -gt 0 ]; do
  case "$1" in
    --pr) pr="$2"; shift 2 ;;
    --since-comment) since_comment="$2"; shift 2 ;;
    --since-review) since_review="$2"; shift 2 ;;
    --since-inline) since_inline="$2"; shift 2 ;;
    --sha) sha="$2"; shift 2 ;;
    --bots) bots="$2"; shift 2 ;;
    --interval) interval="$2"; shift 2 ;;
    --timeout) timeout="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$pr" ] || { echo "--pr is required" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 2; }

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
author=$(gh pr view "$pr" --json author -q .author.login)
deadline=$(( $(date +%s) + timeout ))

snapshot() {
  local view ic rv il
  view=$(gh pr view "$pr" --json state,headRefOid,statusCheckRollup)
  ic=$(gh api "repos/$repo/issues/$pr/comments" --paginate -q '.[]' | jq -s '.')
  rv=$(gh api "repos/$repo/pulls/$pr/reviews"   --paginate -q '.[]' | jq -s '.')
  il=$(gh api "repos/$repo/pulls/$pr/comments"  --paginate -q '.[]' | jq -s '.')
  jq -n --argjson v "$view" --argjson ic "$ic" --argjson rv "$rv" --argjson il "$il" \
        --arg author "$author" --arg sha "$sha" --arg bots "$bots" \
        --argjson sc "$since_comment" --argjson sr "$since_review" --argjson si "$since_inline" '
    ($bots | split(",") | map(select(length > 0))) as $extra_bots |
    def is_bot: .user.type == "Bot" or (.user.login | endswith("[bot]")) or (.user.login | IN($extra_bots[]));
    def fresh($cursor): .user.login != $author and .id > $cursor;
    ($ic | map(select(fresh($sc)))) as $nc |
    ($rv | map(select(fresh($sr) and (.body // "") != ""))) as $nr |
    ($il | map(select(fresh($si)))) as $ni |
    ($v.statusCheckRollup // []) as $checks |
    ($checks | map(select(
        (.__typename == "CheckRun"      and .status != "COMPLETED") or
        (.__typename == "StatusContext" and .state == "PENDING")))) as $pending |
    ($checks | map(select(
        (.__typename == "CheckRun"      and .status == "COMPLETED"
           and (.conclusion | IN("SUCCESS","SKIPPED","NEUTRAL") | not)) or
        (.__typename == "StatusContext" and (.state | IN("SUCCESS","PENDING") | not))))) as $failed |
    {
      state: $v.state,
      headRefOid: $v.headRefOid,
      sha_moved: ($sha != "" and $sha != $v.headRefOid),
      author: $author,
      humans: ([$nc[], $nr[], $ni[]] | map(select(is_bot | not) | .user.login) | unique),
      cursors: {
        comment: ([$sc, ($ic | map(.id) | max // 0)] | max),
        review:  ([$sr, ($rv | map(.id) | max // 0)] | max),
        inline:  ([$si, ($il | map(.id) | max // 0)] | max)
      },
      new_issue_comments:  ($nc | map({id, login: .user.login, bot: is_bot, body})),
      new_reviews:         ($nr | map({id, login: .user.login, bot: is_bot, state, body})),
      new_inline_comments: ($ni | map({id, login: .user.login, bot: is_bot, path, line: (.line // .original_line), body})),
      checks: {
        total: ($checks | length),
        pending: ($pending | length),
        failed: ($failed | map({name: (.name // .context), url: (.detailsUrl // .targetUrl // "")})),
        green: (($checks | length) > 0 and ($pending | length) == 0 and ($failed | length) == 0)
      }
    }'
}

while :; do
  snap=$(snapshot)
  reason=$(jq -r '
    if .state != "OPEN" then "closed"
    elif .sha_moved then "sha_moved"
    elif ((.new_issue_comments|length) + (.new_reviews|length) + (.new_inline_comments|length)) > 0 then "feedback"
    elif .checks.pending == 0 and .checks.total > 0 then "checks"
    else "" end' <<<"$snap")
  if [ -n "$reason" ]; then
    jq --arg r "$reason" '. + {reason: $r}' <<<"$snap"; exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    jq '. + {reason: "timeout"}' <<<"$snap"; exit 0
  fi
  sleep "$interval"
done
