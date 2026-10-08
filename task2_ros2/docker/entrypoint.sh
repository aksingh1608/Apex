#!/bin/bash
# shellcheck disable=SC1091
source /opt/apex_env.sh
if [ -d /ws/src/apex/task2_ros2 ]; then
  cd /ws/src/apex/task2_ros2
fi
exec "$@"
