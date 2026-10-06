#!/usr/bin/env bash
# Watch one PR until it reaches a final state, then print one JSON digest, a
# last line `action=<next step>`, and exit with the state's code. The babysit
# loop runs it directly with the Bash tool's run_in_background; the harness
# re-invokes the agent when it exits. No LLM poller sits in between.
#
# Exit codes (JSON "reason" in parentheses), checked in this order:
#   6  closed / merged (closed | merged)    PR is no longer OPEN
#   6  sha moved (sha_moved)                headRefOid differs from --sha
#   3  human feedback (human)               new comment/review/inline item from a non-bot, non-author
#   2  conflict (conflict)                  mergeable CONFLICTING or mergeStateStatus DIRTY;
#                                           CI never runs on a conflicted PR, so do not wait
#   8  bot feedback (bot_feedback)          new review-bot items only; triage them
#   4  checks failed (checks_failed)        every check concluded, at least one did not pass;
#                                           each failed Actions job carries 40 lines of --log-failed
#   6  changes requested (changes_requested) checks pass but reviewDecision is CHANGES_REQUESTED
#   0  green (green)                        every check concluded SUCCESS/SKIPPED/NEUTRAL, mergeable
#                                           is MERGEABLE, and every configured review bot that reviewed
#                                           this PR has a non-pending status on the head commit
#   5  deadline (deadline)                  nothing final within --timeout; rerun with the same cursors
#   7  query error (query_error)            GitHub query error budget exhausted, or a non-retryable
#                                           error (bad PR number, auth, gh missing)
#   9  pending (pending)                    --once only: no final state yet
#  64  usage error or missing dependency    stderr only, no JSON
# mergeStateStatus BEHIND never blocks green; it sets merge.stale_base in the digest.
# Unrecognized enum values (state, mergeable, mergeStateStatus, reviewDecision)
# count as a failed query: retried, never read as green.
#
# Usage:
#   watch-pr.sh --pr 123 [--sha OID] [--since-comment ID] [--since-review ID] [--since-inline ID] \
#               [--bots "coderabbitai,sonarcloud"] [--interval 120] [--timeout 2700] \
#               [--max-errors 5] [--once]
#
# Cursors are REST numeric ids (issue comments, reviews, inline comments are three
# separate id spaces). Pass the highest id seen of each kind to skip old items.
# A failed gh call is retried with backoff min(max(interval,60) * 2^(n-1), 300)s;
# --max-errors consecutive failures exit 7.
set -uo pipefail

pr="" since_comment=0 since_review=0 since_inline=0 sha="" bots="" interval=120 timeout=2700
max_errors=5 once=false
while [ $# -gt 0 ]; do
  case "$1" in
    --once) once=true; shift; continue ;;
    --pr|--since-comment|--since-review|--since-inline|--sha|--bots|--interval|--timeout|--max-errors) ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  [ $# -ge 2 ] || { echo "$1 needs a value" >&2; exit 64; }
  case "$1" in
    --pr) pr="$2" ;;
    --since-comment) since_comment="$2" ;;
    --since-review) since_review="$2" ;;
    --since-inline) since_inline="$2" ;;
    --sha) sha="$2" ;;
    --bots) bots="$2" ;;
    --interval) interval="$2" ;;
    --timeout) timeout="$2" ;;
    --max-errors) max_errors="$2" ;;
  esac
  shift 2
done
[ -n "$pr" ] || { echo "--pr is required" >&2; exit 64; }
for n in "$pr" "$since_comment" "$since_review" "$since_inline" "$interval" "$timeout" "$max_errors"; do
  case "$n" in ''|*[!0-9]*) echo "expected a non-negative integer, got '$n'" >&2; exit 64 ;; esac
done
[ "$max_errors" -ge 1 ] || { echo "--max-errors must be >= 1" >&2; exit 64; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 64; }

tmp=$(mktemp -d "${TMPDIR:-/tmp}/watch-pr.XXXXXX") || { echo "mktemp failed" >&2; exit 64; }
trap 'rm -rf "$tmp"' EXIT
: >"$tmp/last"
repo="" query_detail="" query_retryable=true

# Run gh with stdout to $1. On failure record why and whether a retry can help.
gh_q() {
  local out=$1 rc
  shift
  gh "$@" >"$out" 2>"$tmp/err"
  rc=$?
  [ "$rc" -eq 0 ] && return 0
  query_detail="gh ${1:-} ${2:-} exited $rc: $(tr '\n' ' ' <"$tmp/err" | cut -c1-300 | sed 's/ *$//')"
  query_retryable=true
  if [ "$rc" -eq 127 ] || [ "$rc" -eq 4 ] ||
     grep -Eq 'HTTP 40[14]|HTTP 422|Could not resolve to a|no pull requests found|not a git repository|none of the git remotes' "$tmp/err"; then
    query_retryable=false
  fi
  return 1
}

snapshot() {
  if [ -z "$repo" ]; then
    gh_q "$tmp/repo" repo view --json nameWithOwner -q .nameWithOwner || return 1
    repo=$(cat "$tmp/repo")
  fi
  gh_q "$tmp/view" pr view "$pr" -R "$repo" \
    --json state,headRefOid,author,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup || return 1
  gh_q "$tmp/ic" api "repos/$repo/issues/$pr/comments" --paginate -q '.[]' || return 1
  gh_q "$tmp/rv" api "repos/$repo/pulls/$pr/reviews"   --paginate -q '.[]' || return 1
  gh_q "$tmp/il" api "repos/$repo/pulls/$pr/comments"  --paginate -q '.[]' || return 1
  if ! jq -n --slurpfile vs "$tmp/view" --slurpfile ic "$tmp/ic" --slurpfile rv "$tmp/rv" --slurpfile il "$tmp/il" \
        --arg pr "$pr" --arg sha "$sha" --arg bots "$bots" \
        --argjson sc "$since_comment" --argjson sr "$since_review" --argjson si "$since_inline" '
    $vs[0] as $v |
    ($v.author.login // "") as $author |
    ($bots | split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length > 0))) as $extra_bots |
    def is_bot: .user.type == "Bot" or (.user.login | endswith("[bot]")) or (.user.login | IN($extra_bots[]));
    def configured_bot: .user.login as $l | any($extra_bots[]; . == $l or (. + "[bot]") == $l);
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
    # CodeRabbit posts a commit status on the head commit: "pending: Review in
    # progress", then "success: Review completed" (or success on a skipped review).
    # While that status is pending, $pending already holds green back. A configured
    # bot that reviewed this PR before but has no status on the head yet has not
    # started; it owes a review. Matching: bot login (minus [bot]) and status
    # context share a prefix, case-insensitive ("coderabbitai" / "CodeRabbit").
    ($checks | map(select(.__typename == "StatusContext") | (.context // "") | ascii_downcase)
             | map(select(length > 0))) as $ctx |
    ($rv | map(select(configured_bot) | .user.login) | unique
         | map(select((ascii_downcase | sub("\\[bot\\]$"; "")) as $b
                      | any($ctx[]; . as $c | ($b | startswith($c)) or ($c | startswith($b))) | not))) as $owing |
    ($rv | map(select(.user.login != $author and (.state | IN("APPROVED","CHANGES_REQUESTED","DISMISSED"))))
         | group_by(.user.login) | map(max_by(.id))
         | map(select(.state == "CHANGES_REQUESTED") | {login: .user.login, bot: is_bot})) as $cr |
    ([$nc[], $nr[], $ni[]]) as $all_new |
    {
      pr: ($pr | tonumber),
      state: $v.state,
      headRefOid: $v.headRefOid,
      sha_moved: ($sha != "" and $sha != $v.headRefOid),
      author: $author,
      humans: ($all_new | map(select(is_bot | not) | .user.login) | unique),
      bots:   ($all_new | map(select(is_bot) | .user.login) | unique),
      feedback_counts: {
        human: ($all_new | map(select(is_bot | not)) | length),
        bot:   ($all_new | map(select(is_bot)) | length)
      },
      cursors: {
        comment: ([$sc, ($ic | map(.id) | max // 0)] | max),
        review:  ([$sr, ($rv | map(.id) | max // 0)] | max),
        inline:  ([$si, ($il | map(.id) | max // 0)] | max)
      },
      merge: {
        mergeable: $v.mergeable,
        mergeStateStatus: $v.mergeStateStatus,
        reviewDecision: ($v.reviewDecision // ""),
        conflict: ($v.mergeable == "CONFLICTING" or $v.mergeStateStatus == "DIRTY"),
        stale_base: ($v.mergeStateStatus == "BEHIND"),
        changes_requested_by: $cr
      },
      review_bots_owing: $owing,
      new_issue_comments:  ($nc | map({id, login: .user.login, bot: is_bot, body})),
      new_reviews:         ($nr | map({id, login: .user.login, bot: is_bot, state, body})),
      new_inline_comments: ($ni | map({id, login: .user.login, bot: is_bot, path, line: (.line // .original_line), body})),
      checks: {
        total: ($checks | length),
        pending: ($pending | length),
        pending_names: ($pending | map(.name // .context)),
        failed: ($failed | map(
          ((.detailsUrl // .targetUrl // "") | capture("/actions/runs/(?<run>[0-9]+)/job/(?<job>[0-9]+)")? // {}) as $ids |
          {name: (.name // .context), conclusion: (.conclusion // .state),
           url: (.detailsUrl // .targetUrl // ""), run_id: $ids.run, job_id: $ids.job})),
        green: (($checks | length) > 0 and ($pending | length) == 0 and ($failed | length) == 0)
      },
      unrecognized: [
        (if ($v.state | IN("OPEN","CLOSED","MERGED")) then empty else "state=\($v.state)" end),
        (if ($v.mergeable | IN("MERGEABLE","CONFLICTING","UNKNOWN")) then empty else "mergeable=\($v.mergeable)" end),
        (if ($v.mergeStateStatus | IN("BEHIND","BLOCKED","CLEAN","DIRTY","DRAFT","HAS_HOOKS","UNKNOWN","UNSTABLE"))
           then empty else "mergeStateStatus=\($v.mergeStateStatus)" end),
        (if (($v.reviewDecision // "") | IN("","APPROVED","CHANGES_REQUESTED","REVIEW_REQUIRED"))
           then empty else "reviewDecision=\($v.reviewDecision)" end)
      ]
    }' >"$tmp/snap" 2>"$tmp/err"; then
    query_detail="could not parse GitHub responses: $(tr '\n' ' ' <"$tmp/err" | cut -c1-300)"
    query_retryable=true
    return 1
  fi
  local bad
  bad=$(jq -r '.unrecognized | join(", ")' "$tmp/snap")
  if [ -n "$bad" ]; then
    query_detail="unrecognized GitHub enum value(s): $bad"
    query_retryable=true
    cp "$tmp/snap" "$tmp/last"
    return 1
  fi
  cp "$tmp/snap" "$tmp/last"
}

# shellcheck disable=SC2016  # jq program, not shell
classify='
  ((.new_issue_comments | length) + (.new_reviews | length) + (.new_inline_comments | length)) as $nfb |
  (.checks.total > 0 and .checks.pending == 0) as $concluded |
  if .state == "MERGED" then {reason: "merged", exit_code: 6}
  elif .state != "OPEN" then {reason: "closed", exit_code: 6}
  elif .sha_moved then {reason: "sha_moved", exit_code: 6}
  elif (.humans | length) > 0 then {reason: "human", exit_code: 3}
  elif .merge.conflict then {reason: "conflict", exit_code: 2}
  elif $nfb > 0 then {reason: "bot_feedback", exit_code: 8}
  elif $concluded and (.checks.failed | length) > 0 then {reason: "checks_failed", exit_code: 4}
  elif .checks.total == 0 then {waiting_on: "no checks reported yet"}
  elif .checks.pending > 0 then {waiting_on: "\(.checks.pending) check(s) pending"}
  elif (.review_bots_owing | length) > 0 then {waiting_on: "review bot(s) \(.review_bots_owing | join(", ")) have not posted a status on the head commit yet"}
  elif .merge.reviewDecision == "CHANGES_REQUESTED" then {reason: "changes_requested", exit_code: 6}
  elif .merge.mergeable != "MERGEABLE" or .merge.mergeStateStatus == "UNKNOWN" then {waiting_on: "GitHub is still computing mergeability"}
  else {reason: "green", exit_code: 0} end'

# shellcheck disable=SC2016  # jq program, not shell
action='
  (if .merge.stale_base == true then " Base moved ahead (BEHIND): suspect a stale base before the code." else "" end) as $stale |
  if .reason == "green" then "finish: PR is green; confirm every Act row is pushed, then SKILL.md section 7." + $stale
  elif .reason == "conflict" then "hand back: PR conflicts with its base (\(.merge.mergeable)/\(.merge.mergeStateStatus)); the owner rebases or merges the base, the babysit does not."
  elif .reason == "human" then "stop and hand back: human feedback from \(.humans | join(", "))."
  elif .reason == "checks_failed" then "triage \(.checks.failed | length) failed check(s) from checks.failed[].log; a failure outside the diff means suspect a stale base first." + $stale
  elif .reason == "deadline" and (.review_bots_owing | length) > 0 and .checks.green == true then "checks are green but \(.review_bots_owing | join(", ")) never posted a status on the head commit; check the bot is still installed on the repo, then rerun with the same --sha and cursors."
  elif .reason == "deadline" then "rerun with the same --sha and cursors; still waiting on: \(.waiting_on // "query errors"). A check past ~2x its usual duration is hung (SKILL.md section 5)."
  elif .reason == "sha_moved" then "stop and hand back: head moved to \(.headRefOid); someone else pushed."
  elif .reason == "changes_requested" then "hand back: reviewDecision is CHANGES_REQUESTED by \(.merge.changes_requested_by | map(.login) | join(", "))."
  elif .reason == "closed" then "stop: PR is closed; nothing to babysit."
  elif .reason == "merged" then "stop: PR is merged; nothing to babysit."
  elif .reason == "query_error" then "check the PR number, gh auth status and GitHub availability, then rerun: \(.query_error.detail)"
  elif .reason == "bot_feedback" then "triage \(.feedback_counts.bot) new bot item(s) per SKILL.md section 5, push, rerun with the new cursors and --sha."
  elif .reason == "pending" then "nothing final yet (\(.waiting_on)); run without --once to wait."
  else "unknown state; read the digest." end'

attach_logs() {
  local idx run job log
  : >"$tmp/logs"
  jq -r '.checks.failed | to_entries[] | select(.value.job_id != null) | [.key, .value.run_id, .value.job_id] | @tsv' "$tmp/final" |
  while IFS=$'\t' read -r idx run job; do
    if gh run view "$run" --job "$job" --log-failed -R "$repo" >"$tmp/log" 2>"$tmp/err"; then
      # Lines are "job<TAB>step<TAB>timestamp text". The window ends at the last
      # ##[error] marker; a plain tail lands in post-job cleanup output.
      log=$(cut -f3- "$tmp/log" | LC_ALL=C sed -E $'s/\033\\[[0-9;]*[A-Za-z]//g; s/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z //' |
            awk '{ l[NR] = $0 } /##\[error\]/ { e = NR } END { n = e ? e : NR; for (i = (n > 40 ? n - 39 : 1); i <= n; i++) print l[i] }')
      [ -n "$log" ] || log="no failed-step log (cancelled or failed before any step ran)"
    else
      log="log unavailable: $(tr '\n' ' ' <"$tmp/err" | cut -c1-200)"
    fi
    jq -nc --argjson i "$idx" --arg log "$log" '{i: $i, log: $log}' >>"$tmp/logs"
  done
  jq --slurpfile L "$tmp/logs" 'reduce $L[] as $l (.; .checks.failed[$l.i].log = $l.log)' "$tmp/final" >"$tmp/final.logs" &&
    mv "$tmp/final.logs" "$tmp/final"
}

# $1 = JSON object merged over the snapshot (reason, exit_code, ...).
finish() {
  if [ -s "$tmp/last" ]; then
    jq --argjson extra "$1" '. + $extra' "$tmp/last" >"$tmp/final"
  else
    jq -n --argjson extra "$1" --arg pr "$pr" '{pr: ($pr | tonumber)} + $extra' >"$tmp/final"
  fi
  if [ "$(jq -r .reason "$tmp/final")" = "checks_failed" ]; then attach_logs; fi
  jq 'del(.unrecognized | select(length == 0))' "$tmp/final"
  printf 'action=%s\n' "$(jq -r "$action" "$tmp/final")"
  exit "$(jq -r .exit_code "$tmp/final")"
}

query_error_json() { # $1 = reason, $2 = exit code
  jq -nc --arg r "$1" --argjson c "$2" --argjson f "$failures" --argjson rt "$query_retryable" --arg d "$query_detail" \
    '{reason: $r, exit_code: $c, query_error: {failures: $f, retryable: $rt, detail: $d}}'
}

started=$(date +%s)
deadline=$(( started + timeout ))
failures=0
while :; do
  if snapshot; then
    failures=0
    verdict=$(jq -c "$classify" "$tmp/snap")
    if [ "$(jq -r '.reason // empty' <<<"$verdict")" != "" ]; then finish "$verdict"; fi
    if $once; then finish "$(jq -c '{reason: "pending", exit_code: 9} + .' <<<"$verdict")"; fi
    if [ "$(date +%s)" -ge "$deadline" ]; then finish "$(jq -c '{reason: "deadline", exit_code: 5} + .' <<<"$verdict")"; fi
    sleep "$interval"
  else
    failures=$(( failures + 1 ))
    if ! $query_retryable || [ "$failures" -ge "$max_errors" ]; then finish "$(query_error_json query_error 7)"; fi
    if ! $once && [ "$(date +%s)" -ge "$deadline" ]; then finish "$(query_error_json deadline 5)"; fi
    backoff=$(( interval > 60 ? interval : 60 ))
    backoff=$(( backoff * (1 << (failures - 1)) ))
    [ "$backoff" -gt 300 ] && backoff=300
    echo "watch-pr: query failed ($failures/$max_errors), retrying in ${backoff}s: $query_detail" >&2
    sleep "$backoff"
  fi
done
