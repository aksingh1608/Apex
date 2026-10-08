#!/usr/bin/env bash
# Open a second shell in the running apex container, with Humble sourced.
set -euo pipefail
exec docker exec -it apex bash -c 'source /opt/apex_env.sh; cd /ws/src/apex/task2_ros2; exec bash'
