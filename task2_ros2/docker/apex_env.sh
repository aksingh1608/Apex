#!/bin/bash
# Sourced by the container entrypoint and by docker/exec.sh.
# Humble setup reads AMENT_TRACE_SETUP_FILES before it exists.
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"
export APEX_WS="${APEX_WS:-/ws}"
export HOME="${HOME:-/tmp/apex-home}"
mkdir -p "$HOME"
set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source /usr/share/gazebo/setup.sh
if [ -f /ws/install/setup.bash ]; then
  # shellcheck disable=SC1091
  source /ws/install/setup.bash
fi
set -u
