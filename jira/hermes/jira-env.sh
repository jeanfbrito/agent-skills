#!/usr/bin/env bash
# Hermes-adapted env helper for the jira skill.
# Linux-compatible: reads JIRA_API_TOKEN from local-config.yml instead of macOS Keychain.
#
# Source this before any `jira` invocation:
#   source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CONFIG="$SCRIPT_DIR/local-config.yml"

read_local_config() {
  local key="$1"
  if [[ -f "$LOCAL_CONFIG" ]]; then
    awk -v k="$key" '
      $0 ~ "^[[:space:]]*"k":" {
        sub("^[[:space:]]*"k":[[:space:]]*", "", $0)
        gsub(/^"|"$/, "", $0)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
        print
        exit
      }' "$LOCAL_CONFIG"
  fi
}

# Read from local-config.yml
ATLASSIAN_EMAIL="$(read_local_config email)"
ATLASSIAN_SITE="$(read_local_config site)"
JIRA_API_TOKEN="$(read_local_config api_token)"

export ATLASSIAN_EMAIL
export ATLASSIAN_SITE
export JIRA_API_TOKEN

if [[ -z "$JIRA_API_TOKEN" ]]; then
  echo "WARN: jira skill: no JIRA_API_TOKEN found in $LOCAL_CONFIG" >&2
  echo "      Run: $SCRIPT_DIR/setup.sh" >&2
fi

if [[ -z "$ATLASSIAN_EMAIL" ]]; then
  echo "WARN: jira skill: no Atlassian email configured." >&2
  echo "      Run: $SCRIPT_DIR/setup.sh" >&2
  return 0 2>/dev/null || exit 0
fi
