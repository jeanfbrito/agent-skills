#!/usr/bin/env bash
# Self-contained env helper for the jira skill.
#
# Source this before any `jira` invocation to populate JIRA_API_TOKEN
# from the macOS Keychain (jira-cli reads it from the env var; on
# macOS it does not natively read Keychain — Linux libsecret only).
#
#   source ~/.claude/skills/jira/jira-env.sh
#
# Resolves the Keychain account in this priority order:
#   1. $JIRA_KEYCHAIN_ACCOUNT (env var override)
#   2. atlassian.keychain_account in ./local-config.yml (written by setup.sh)
#   3. atlassian.email in ./local-config.yml
#
# If none resolve, prints a hint to run setup.sh and exits the source quietly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CONFIG="$SCRIPT_DIR/local-config.yml"

read_local_config() {
  local key="$1"
  if [[ -f "$LOCAL_CONFIG" ]]; then
    awk -v k="$key" '
      $0 ~ "^[[:space:]]*"k":" {
        sub("^[[:space:]]*"k":[[:space:]]*","",$0)
        gsub(/^"|"$/,"",$0)
        gsub(/^[[:space:]]+|[[:space:]]+$/,"",$0)
        print
        exit
      }' "$LOCAL_CONFIG"
  fi
}

KEYCHAIN_SERVICE="${JIRA_KEYCHAIN_SERVICE:-jira-cli}"
KEYCHAIN_ACCOUNT="${JIRA_KEYCHAIN_ACCOUNT:-$(read_local_config keychain_account)}"
if [[ -z "$KEYCHAIN_ACCOUNT" ]]; then
  KEYCHAIN_ACCOUNT="$(read_local_config email)"
fi

if [[ -z "$KEYCHAIN_ACCOUNT" ]]; then
  echo "WARN: jira skill: no Atlassian account configured." >&2
  echo "      Run: $SCRIPT_DIR/setup.sh" >&2
  return 0 2>/dev/null || exit 0
fi

export JIRA_API_TOKEN="$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null)"
export ATLASSIAN_EMAIL="$KEYCHAIN_ACCOUNT"

if [[ -z "$JIRA_API_TOKEN" ]]; then
  echo "WARN: could not load JIRA_API_TOKEN from Keychain (service=$KEYCHAIN_SERVICE, account=$KEYCHAIN_ACCOUNT)" >&2
  echo "      Run: $SCRIPT_DIR/setup.sh" >&2
fi
