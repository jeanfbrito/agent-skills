#!/usr/bin/env bash
# Bring Docker Desktop to a state where the engine answers, then print `docker system df`.
# A stale com.docker.backend from an earlier start blocks a new start, and `docker info` can hang,
# so every check uses the socket with a time limit.
set -u
SOCK=~/.docker/run/docker.sock

ping_engine() { [ "$(curl -s -m 5 --unix-socket "$SOCK" http://localhost/_ping 2>/dev/null)" = OK ]; }

wait_engine() {
  for _ in $(seq 1 "$1"); do ping_engine && return 0; sleep 3; done
  return 1
}

if ping_engine; then
  echo "engine: up"
else
  echo "engine: not answering, starting Docker"
  open -a Docker
  if ! wait_engine 20; then
    echo "engine: still down, stopping stale backend processes"
    osascript -e 'quit app "Docker"' 2>/dev/null
    sleep 8
    pkill -f com.docker.backend
    sleep 3
    pkill -9 -f com.docker.backend
    pgrep -lf com.docker | head -5
    open -a Docker
    if ! wait_engine 50; then
      echo "engine: down after restart. Read ~/Library/Containers/com.docker.docker/Data/log/host/docker-desktop.log" >&2
      exit 1
    fi
  fi
  echo "engine: up"
fi

docker system df
