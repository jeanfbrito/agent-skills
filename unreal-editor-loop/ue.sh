#!/usr/bin/env bash
# Unreal editor loop helpers for any project (Git Bash on Windows, bash on macOS). See SKILL.md next to this file.
#   ue.sh info                       project, engine, target, log, MCP port that the script found
#   ue.sh build [Target] [Config]    build (default <Project>Editor Development). The editor must be closed
#   ue.sh running                    editor processes; exit 1 when none
#   ue.sh launch [/Game/Map]         start the editor on the project (and a map)
#   ue.sh wait-mcp [seconds]         wait until the Unreal MCP server answers
#   ue.sh wait-log <regex> [seconds] wait for a NEW log line that matches (counts lines at the start)
#   ue.sh log <regex> [n]            last n matching log lines, timestamps cut
#   ue.sh live-result [seconds]      wait for the result of LiveCoding.Compile
# Overrides: UE_PROJECT (.uproject path), UE_ENGINE (engine root, the folder that has Engine/), UE_MCP_PORT (8000).
set -u

find_uproject() {
  if [ -n "${UE_PROJECT:-}" ]; then echo "$UE_PROJECT"; return; fi
  local dir="$PWD"
  while [ -n "$dir" ] && [ "$dir" != "/" ]; do
    local hit; hit=$(ls "$dir"/*.uproject 2>/dev/null | head -1)
    if [ -n "$hit" ]; then echo "$hit"; return; fi
    dir=$(dirname "$dir")
  done
}

find_engine() {
  if [ -n "${UE_ENGINE:-}" ]; then echo "$UE_ENGINE"; return; fi
  local assoc; assoc=$(sed -n 's/.*"EngineAssociation" *: *"\([^"]*\)".*/\1/p' "$UPROJECT" | head -1)
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      # a GUID (or any custom name) is a registered build; a version is a Launcher install
      local reg; reg=$(reg query "HKCU\\Software\\Epic Games\\Unreal Engine\\Builds" 2>/dev/null | tr -d '\r' \
        | grep -F -- "$assoc" | sed -n 's/.*REG_SZ *//p' | head -1)
      if [ -n "$reg" ]; then echo "$reg"; return; fi
      local dat="C:/ProgramData/Epic/UnrealEngineLauncher/LauncherInstalled.dat"
      if [ -f "$dat" ]; then
        local loc; loc=$(python -c "import json,sys;d=json.load(open(sys.argv[1]));print(next((i['InstallLocation'] for i in d['InstallationList'] if i['AppName']=='UE_'+sys.argv[2]),''))" "$dat" "$assoc" 2>/dev/null)
        if [ -n "$loc" ]; then echo "$loc"; return; fi
      fi
      echo "C:/Program Files/Epic Games/UE_$assoc" ;;
    Darwin)
      local plist="$HOME/Library/Application Support/Epic/UnrealEngine/Install.ini"
      if [ -f "$plist" ] && grep -q "^$assoc=" "$plist"; then grep "^$assoc=" "$plist" | cut -d= -f2-; return; fi
      echo "/Users/Shared/Epic Games/UE_$assoc" ;;
    *) echo "$HOME/UnrealEngine" ;;
  esac
}

UPROJECT=$(find_uproject)
if [ -z "$UPROJECT" ]; then echo "no .uproject in this folder or above (set UE_PROJECT)"; exit 2; fi
# the Windows form (C:/...) on Git Bash: the engine tools take Windows paths
PROJECT_DIR=$(cd "$(dirname "$UPROJECT")" && { pwd -W 2>/dev/null || pwd; })
NAME=$(basename "$UPROJECT" .uproject)
UPROJECT="$PROJECT_DIR/$NAME.uproject"
ENGINE=$(find_engine)
LOG="$PROJECT_DIR/Saved/Logs/$NAME.log"
PORT="${UE_MCP_PORT:-8000}"
case "$(uname -s)" in
  Darwin) PLATFORM=Mac; BUILD="$ENGINE/Engine/Build/BatchFiles/Mac/Build.sh"
          EDITOR="$ENGINE/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor" ;;
  MINGW*|MSYS*|CYGWIN*) PLATFORM=Win64; BUILD="$ENGINE/Engine/Build/BatchFiles/Build.bat"
          EDITOR="$ENGINE/Engine/Binaries/Win64/UnrealEditor.exe" ;;
  *) PLATFORM=Linux; BUILD="$ENGINE/Engine/Build/BatchFiles/Linux/Build.sh"
     EDITOR="$ENGINE/Engine/Binaries/Linux/UnrealEditor" ;;
esac
cut_ts() { sed 's/^\[[^]]*\]\[[^]]*\]//'; }

case "${1:-}" in
  info)
    printf 'project  %s\nengine   %s\ntarget   %sEditor %s\nlog      %s\nmcp      http://127.0.0.1:%s/mcp\n' \
      "$UPROJECT" "$ENGINE" "$NAME" "$PLATFORM" "$LOG" "$PORT"
    [ -f "$BUILD" ] || echo "WARNING: no build script at $BUILD (set UE_ENGINE)"
    ;;
  build)
    "$BUILD" "${2:-${NAME}Editor}" "$PLATFORM" "${3:-Development}" "-Project=$UPROJECT" -WaitMutex 2>&1 \
      | grep -E "error|warning C|Result:|Total execution|BUILD (SUCCESSFUL|FAILED)" | tail -40
    ;;
  running)
    if [ "$PLATFORM" = Win64 ]; then tasklist //FI "IMAGENAME eq UnrealEditor.exe" //FO CSV //NH | grep -i unrealeditor || exit 1
    else pgrep -fl UnrealEditor || exit 1; fi
    ;;
  launch)
    if [ "$PLATFORM" = Win64 ]; then
      # Start-Process detaches the editor from this shell. Its working folder is Engine/Binaries/Win64:
      # give py commands absolute paths
      powershell.exe -NoProfile -Command "Start-Process '$EDITOR' -ArgumentList '\"$UPROJECT\"'${2:+,'$2'}" \
        && echo "launched $NAME ${2:-}"
    else
      nohup "$EDITOR" "$UPROJECT" ${2:+"$2"} >/dev/null 2>&1 & echo "launched $NAME ${2:-}"
    fi
    ;;
  wait-mcp)
    LIMIT="${2:-450}"
    for ((t = 0; t < LIMIT; t += 5)); do
      if curl -s -m 3 -X POST "http://127.0.0.1:$PORT/mcp" -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}' \
        | grep -q '"result"'; then echo "MCP up after ${t}s"; exit 0; fi
      sleep 5
    done
    echo "MCP timeout after ${LIMIT}s"; exit 1
    ;;
  wait-log)
    PATTERN="$2"; LIMIT="${3:-300}"
    START=$(grep -acE "$PATTERN" "$LOG" 2>/dev/null); START=${START:-0}
    for ((t = 0; t < LIMIT; t += 3)); do
      NOW=$(grep -acE "$PATTERN" "$LOG" 2>/dev/null); NOW=${NOW:-0}
      # a new log file (editor restart) has fewer lines: take every match
      if [ "$NOW" -lt "$START" ]; then START=0; fi
      if [ "$NOW" -gt "$START" ]; then grep -aE "$PATTERN" "$LOG" | tail -n $((NOW - START)) | cut_ts; exit 0; fi
      sleep 3
    done
    echo "timeout: no new line for /$PATTERN/ in ${LIMIT}s"; exit 1
    ;;
  log)
    grep -aE "$2" "$LOG" | tail -n "${3:-20}" | cut_ts
    ;;
  live-result)
    "$0" wait-log "Live coding succeeded|Live coding failed|error C[0-9]+|No changes" "${2:-240}"
    ;;
  *)
    sed -n '2,12p' "$0"; exit 2
    ;;
esac
