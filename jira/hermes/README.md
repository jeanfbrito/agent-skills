# Jira CLI Skill — Hermes Edition

Atlassian Jira workflow via `jira-cli` (ankitpokhrel/jira-cli), adapted for Linux/Hermes (no macOS Keychain, no Homebrew).

## Structure

```
jira/
├── README.md                          ← this file
├── SKILL.md                           ← skill definition for Hermes
├── setup.sh                           ← one-shot installer
├── jira-env.sh                        ← source this to export env vars
├── hermes/
│   ├── SKILL.md                       ← Hermes-adapted skill (same content)
│   ├── setup.sh                       ← Hermes-adapted installer
│   ├── jira-env.sh                    ← Hermes-adapted env helper
│   ├── local-config.yml               ← YOUR secrets (gitignored)
│   ├── local-config.yml.example       ← template for manual setup
│   └── scripts/                       ← support scripts (if any)
├── .gitignore
└── (original Claude Code files)
```

## Quick install (Hermes)

Run the interactive installer:

```bash
~/.hermes-icarus/skills/atlassian/jira/setup.sh
```

It will:
1. Detect your architecture (x86_64/arm64)
2. Download `jira-cli` Linux binary from GitHub Releases
3. Prompt for credentials (email, site, API token)
4. Test auth with `jira me`
5. Fetch issue types from your project via REST API
6. Write `local-config.yml` (secrets, gitignored)

### Prerequisites

- `curl` — binary download
- `jq` — JSON parsing (`apt install jq`)
- `python3 + pyyaml` — YAML writing for config (`pip3 install pyyaml` or `apt install python3-yaml`)

## Manual install

If you prefer not to run the interactive script:

1. **Install jira-cli:**
   ```bash
   # x86_64
   curl -sSL https://github.com/ankitpokhrel/jira-cli/releases/latest/download/jira_$(curl -sSL https://api.github.com/repos/ankitpokhrel/jira-cli/releases/latest | jq -r '.tag_name')_linux_x86_64.tar.gz | tar xz -C /tmp/jira-cli --strip-components=1
   cp /tmp/jira-cli/bin/jira ~/.local/bin/
   rm -rf /tmp/jira-cli
   ```
   Or for arm64: replace `x86_64` with `arm64`.

2. **Configure jira-cli:**
   ```bash
   mkdir -p ~/.config/.jira
   cat > ~/.config/.jira/.config.yml << 'EOF'
   installation: cloud
   auth_type: basic
   server: https://yourcompany.atlassian.net
   login: you@company.com
   issue:
     types:
       - id: "10001"
         name: Bug
         handle: Bug
         subtask: false
       # ... more types
   EOF
   ```

3. **Set up your local config:**
   ```bash
   cp hermes/local-config.yml.example hermes/local-config.yml
   # Edit with your real credentials
   ```

4. **Set the API token as env var** (or it's read from `local-config.yml` by `jira-env.sh`):
   ```bash
   export JIRA_API_TOKEN="your_token"
   ```

## Per-session usage

```bash
source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh
```

Or add to your `~/.bashrc` for automatic loading.

## Test that it works

```bash
source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh
jira me
```

## Authentication

- **API token:** Generate at https://id.atlassian.com/manage-profile/security/api-tokens
- Stored in `local-config.yml` (plain text, `chmod 600`)
- Read by `jira-env.sh` at runtime and exported as `JIRA_API_TOKEN`

If `jira me` returns a 401, your token is stale — generate a new one and update `local-config.yml`.

## OS support

| Feature | Claude Code original | Hermes |
|---------|--------------------|--------|
| Token storage | macOS Keychain | `local-config.yml` (plain text) |
| jira-cli install | Homebrew | Direct binary download |
| Issue types config | `jira init` (interactive) | REST API (non-interactive) |
| Shell env | `~/.zshrc` with Keychain | `jira-env.sh` sourcing |

## Upgrade jira-cli

```bash
# Re-run setup (idempotent)
~/.hermes-icarus/skills/atlassian/jira/setup.sh
```
