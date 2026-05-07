#!/usr/bin/env bash
# Hermes-adapted installer for the jira skill.
# Linux-compatible: no macOS Keychain, no Homebrew.
#
# - Downloads jira-cli binary for Linux
# - Prompts for Atlassian credentials
# - Writes local-config.yml (gitignored) with everything the skill needs
# - Runs jira init interactively to populate issue types
# - Verifies with jira me
#
# Idempotent. Safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

prompt_if_missing() {
  local var="$1"
  local prompt_text="$2"
  local secret="${3:-no}"
  if [[ -z "${!var:-}" ]]; then
    if [[ "$secret" == "yes" ]]; then
      read -r -s -p "$prompt_text: " value; echo
    else
      read -r -p "$prompt_text: " value
    fi
    declare -g "$var=$value"
  fi
}

prompt_optional() {
  local var="$1"
  local prompt_text="$2"
  if [[ -z "${!var:-}" ]]; then
    read -r -p "$prompt_text (optional, press Enter to skip): " value
    declare -g "$var=$value"
  fi
}

echo "=== Atlassian credentials ==="
prompt_if_missing ATLASSIAN_EMAIL  "Atlassian email"
prompt_if_missing ATLASSIAN_SITE   "Atlassian site host (e.g. yourcompany.atlassian.net)"
prompt_if_missing ATLASSIAN_API_TOKEN "Atlassian API token (input hidden)" yes

for v in ATLASSIAN_API_TOKEN ATLASSIAN_EMAIL ATLASSIAN_SITE; do
  if [[ -z "${!v}" ]]; then
    echo "ERROR: $v is empty" >&2
    exit 1
  fi
done

echo ""
echo "=== Workflow defaults ==="
prompt_optional JIRA_PRIMARY_PROJECT  "Primary project key (e.g. CORE)"
prompt_optional JIRA_DEFAULT_COMPONENT "Default component for primary-project tickets"
prompt_optional JIRA_DEFAULT_ASSIGNEE  "Default assignee email (leave blank for currentUser())"

# 1. Install jira-cli (Linux binary download)
if ! command -v jira >/dev/null 2>&1; then
  echo ""
  echo "==> Installing jira-cli for Linux..."

  # Detect arch and resolve actual asset name via GitHub API
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64)  ARCH_SUFFIX="x86_64" ;;
    aarch64|arm64) ARCH_SUFFIX="arm64" ;;
    *) echo "ERROR: unsupported arch $ARCH" >&2; exit 1 ;;
  esac

  echo "==> Resolving latest jira-cli release..."
  ASSET_URL=$(curl -sSL \
    "https://api.github.com/repos/ankitpokhrel/jira-cli/releases/latest" \
    | jq -r '.assets[] | select(.name | test("linux_'${ARCH_SUFFIX}'.tar.gz")) | .browser_download_url' \
    | head -1)

  if [[ -z "$ASSET_URL" ]]; then
    echo "ERROR: Could not find a Linux ${ARCH_SUFFIX} asset for jira-cli" >&2
    exit 1
  fi

  DEST="/tmp/jira-cli-install"
  mkdir -p "$DEST"
  curl -sSL "$ASSET_URL" | tar xz -C "$DEST" --strip-components=1
  chmod +x "$DEST/bin/jira"

  # Install to local bin
  mkdir -p "$HOME/.local/bin"
  cp "$DEST/bin/jira" "$HOME/.local/bin/jira"
  rm -rf "$DEST"

  echo "==> Installed to ~/.local/bin/jira"
  # Add to PATH for this session
  export PATH="$HOME/.local/bin:$PATH"
else
  echo ""
  echo "==> jira-cli already installed: $(jira version 2>/dev/null | head -1)"
fi

# 2. Write jira-cli config stub
CONFIG_DIR="$HOME/.config/.jira"
CONFIG_FILE="$CONFIG_DIR/.config.yml"
mkdir -p "$CONFIG_DIR"
if [[ -f "$CONFIG_FILE" ]]; then
  echo "==> Backing up existing config to $CONFIG_FILE.bak.$(date +%s)"
  cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%s)"
fi
cat > "$CONFIG_FILE" <<YAML
installation: cloud
auth_type: basic
server: https://${ATLASSIAN_SITE}
login: ${ATLASSIAN_EMAIL}
YAML
chmod 600 "$CONFIG_FILE"
echo "==> Wrote $CONFIG_FILE (stub)"

# 3. Smoke test
echo ""
echo "==> Verifying with 'jira me'..."
JIRA_API_TOKEN="$ATLASSIAN_API_TOKEN" jira me

# 4. Populate issue.types via REST (avoids interactive jira init)
echo ""
echo "==> Fetching issue types via REST..."
JIRA_PROJECT_META=$(curl -sS -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://${ATLASSIAN_SITE}/rest/api/3/issue/createmeta?projectKeys=${JIRA_PRIMARY_PROJECT:-CORE}" 2>/dev/null)

ISSUE_TYPES_JSON=$(echo "$JIRA_PROJECT_META" | jq -r '
  .projects[0].issuetypes[] | {id: .id, name: .name, handle: .name, subtask: (.subtask // false)}
' 2>/dev/null)

# Parse into YAML
echo "$JIRA_PROJECT_META" | python3 -c "
import json, sys, yaml

data = json.load(sys.stdin)
project = data.get('projects', [{}])[0]
types = project.get('issuetypes', [])

result = []
for t in types:
    result.append({
        'id': t['id'],
        'name': t['name'],
        'handle': t['name'],
        'subtask': t.get('subtask', False)
    })

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f) or {}

config['issue'] = {'types': result}

with open('$CONFIG_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f'Populated {len(result)} issue types for {project.get(\"key\", \"?\")}:')
for t in result:
    print(f'  - {t[\"name\"]} (id={t[\"id\"]})')
" 2>/dev/null || {
  echo "WARN: REST failed, falling back to jira init..."
  echo "y" | JIRA_API_TOKEN="$ATLASSIAN_API_TOKEN" jira init
}

echo "==> Config written to $CONFIG_FILE"

# 5. Write local-config.yml (gitignored)
LOCAL_CONFIG="$SCRIPT_DIR/local-config.yml"
{
  echo "# Generated by setup.sh — gitignored, safe to edit by hand."
  echo "# Read by jira-env.sh and used by SKILL.md to apply your defaults."
  echo ""
  echo "atlassian:"
  echo "  email: \"${ATLASSIAN_EMAIL}\""
  echo "  site: \"${ATLASSIAN_SITE}\""
  echo "  api_token: \"${ATLASSIAN_API_TOKEN}\""
  echo ""
  echo "defaults:"
  if [[ -n "${JIRA_PRIMARY_PROJECT:-}" ]]; then
    echo "  primary_project: \"${JIRA_PRIMARY_PROJECT}\""
  else
    echo "  primary_project: \"\""
  fi
  if [[ -n "${JIRA_DEFAULT_COMPONENT:-}" ]]; then
    echo "  default_component: \"${JIRA_DEFAULT_COMPONENT}\""
  else
    echo "  default_component: \"\""
  fi
  if [[ -n "${JIRA_DEFAULT_ASSIGNEE:-}" ]]; then
    echo "  default_assignee: \"${JIRA_DEFAULT_ASSIGNEE}\""
  else
    echo "  default_assignee: \"\"   # empty = use \$(jira me) / currentUser()"
  fi
  echo ""
  echo "workflow_statuses: []"
} > "$LOCAL_CONFIG"
chmod 600 "$LOCAL_CONFIG"
echo "==> Wrote $LOCAL_CONFIG (gitignored)"

# 6. Add .gitignore entry for local-config.yml if missing
GITIGNORE="$SCRIPT_DIR/.gitignore"
if [[ -f "$GITIGNORE" ]]; then
  grep -q "local-config.yml" "$GITIGNORE" 2>/dev/null || echo "local-config.yml" >> "$GITIGNORE"
fi

echo ""
echo "Setup complete."
echo ""
echo "Per-session usage:"
echo "    source $SCRIPT_DIR/jira-env.sh"
echo ""
echo "Or add to your ~/.bashrc:"
echo "    source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh"
