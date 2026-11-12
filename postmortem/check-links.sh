#!/usr/bin/env bash
# Checks that every http(s) URL in a markdown file resolves.
# GitHub repo links are checked with `gh repo view` (works for private repos
# you can read); other links with an HTTP HEAD/GET request.
# Usage: check-links.sh <file.md>   Exit 1 when any link fails.
set -u
file="${1:?usage: check-links.sh <file.md>}"
fail=0
while IFS= read -r url; do
  url="${url%%[).,;>\`\"\']}"
  if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/#?]+) ]]; then
    repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    if canonical=$(gh repo view "$repo" --json nameWithOwner -q .nameWithOwner 2>/dev/null); then
      lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
      if [[ "$(lower "$canonical")" == "$(lower "$repo")" ]]; then
        echo "ok    $url"
      else
        echo "MOVED $url (renamed to $canonical: use the current name)"; fail=1
      fi
    else
      echo "FAIL  $url (gh repo view $repo)"; fail=1
    fi
    continue
  fi
  code=$(curl -s -o /dev/null -L --max-time 15 -w '%{http_code}' "$url")
  if [[ "$code" =~ ^(2|3) ]]; then
    echo "ok    $url"
  elif [[ "$code" == 401 || "$code" == 403 ]]; then
    echo "AUTH  $url ($code: needs a login, check by hand)"
  else
    echo "FAIL  $url ($code)"; fail=1
  fi
done < <(grep -oE 'https?://[^ )>"`]+' "$file" | sort -u)
exit "$fail"
