#!/usr/bin/env bash
# Start the Apex container with the repo mounted and the display forwarded.
#
# Usage: task2_ros2/docker/run.sh
#        task2_ros2/docker/run.sh --gpu
#        task2_ros2/docker/run.sh --headless
#
# The repo appears at /ws/src/apex. Files written there are owned by
# the user who starts this script.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GPU=()
HEADLESS=0
case "${1:-}" in
  "") ;;
  --gpu) GPU=(--gpus all --env NVIDIA_VISIBLE_DEVICES=all --env NVIDIA_DRIVER_CAPABILITIES=all) ;;
  --headless) HEADLESS=1 ;;
  *) echo "usage: $0 [--gpu | --headless]"; exit 1 ;;
esac

if docker ps -a --format '{{.Names}}' | grep -qx apex; then
  echo "A container named apex already exists."
  echo "Enter it with task2_ros2/docker/exec.sh, or remove it with: docker rm -f apex"
  exit 1
fi

args=(
  docker run --name apex
  --user "$(id -u):$(id -g)"
  --network host
  --env HOME=/tmp/apex-home
  --volume /etc/passwd:/etc/passwd:ro
  --volume /etc/group:/etc/group:ro
  --volume /etc/localtime:/etc/localtime:ro
  --volume "$ROOT:/ws/src/apex"
)

if [ "$HEADLESS" -eq 1 ]; then
  args+=(-d apex:humble sleep infinity)
else
  if [ -z "${DISPLAY:-}" ]; then
    echo "DISPLAY is empty. Start this from a desktop session so Gazebo can open."
    exit 1
  fi
  xhost +local:root >/dev/null
  xhost +SI:localuser:"$(id -un)" >/dev/null || true
  args+=(-it
    --env DISPLAY="$DISPLAY"
    --env QT_X11_NO_MITSHM=1
    --volume /tmp/.X11-unix:/tmp/.X11-unix)
  if [ "${#GPU[@]}" -gt 0 ]; then
    args+=("${GPU[@]}")
  fi
  args+=(apex:humble bash)
fi
exec "${args[@]}"
