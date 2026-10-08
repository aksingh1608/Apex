#!/usr/bin/env bash
# Run one full mission with no GUI and the scripted key presses.
# Use it inside the container from task2_ros2/:  scripts/headless_run.sh [player] [slam]
# With "player" it also spawns the blue car and parks it on the front straight.
# With "slam" it also builds a 2D LiDAR map and saves it as runs/<timestamp>/map.pgm and map.yaml.
# It starts the launch file, presses g, pauses and resumes once on lap 3,
# waits for the race to end, then stops everything. Logs go to runs/.

set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PLAYER=false
SLAM=false
for arg in "$@"; do
  case "$arg" in
    player) PLAYER=true ;;
    slam) SLAM=true ;;
    *) echo "usage: $0 [player] [slam]"; exit 1 ;;
  esac
done

LOG=/tmp/apex_launch.log
# Job control gives the launch its own process group and keeps SIGINT
# working for it. Without it, bash starts background jobs with SIGINT ignored.
set -m
rm -f "$LOG"
ros2 launch apex_race race.launch.py gui:=false player:=$PLAYER slam:=$SLAM > "$LOG" 2>&1 &
LAUNCH=$!
OFFSET=""
stop_launch() {
  # An if, not &&: under set -e a failed kill at the end of && would end the
  # trap here and leave the launch running.
  if [ -n "$OFFSET" ]; then kill -INT "$OFFSET" 2>/dev/null || true; fi
  kill -INT -- -"$LAUNCH" 2>/dev/null || true
  for _ in $(seq 20); do kill -0 "$LAUNCH" 2>/dev/null || return 0; sleep 1; done
  kill -KILL -- -"$LAUNCH" 2>/dev/null || true
}
trap stop_launch EXIT

until grep -aq "Press g to start" "$LOG"; do sleep 1; done
until grep -aq "Successfully spawned entity \[auto\]" "$LOG"; do
  if grep -aq "Spawn service failed" "$LOG"; then
    echo "Spawning a car failed. Is an old gzserver still running?"; exit 1
  fi
  sleep 1
done
echo "Launch is up. Driving the mission."
if [ "$SLAM" = true ]; then
  # Records slam_toolbox's map to odom correction, which is its pose error here.
  python3 scripts/slam_offset.py /tmp/apex_slam_offset.csv &
  OFFSET=$!
fi
if [ "$PLAYER" = true ]; then
  python3 scripts/mission_driver.py --park 1.0 -1.2
else
  python3 scripts/mission_driver.py
fi
sleep 2
grep -a -A 14 "APEX RACE SUMMARY" "$LOG" | sed 's/^.*\] //'
if [ "$SLAM" = true ]; then
  RUN="runs/$(ls runs | tail -1)"
  ros2 run nav2_map_server map_saver_cli -f "$RUN/map" \
    --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0 > /tmp/apex_map_saver.log 2>&1 \
    && echo "Saved the map to $RUN/map.pgm and $RUN/map.yaml" \
    || { echo "Saving the map failed:"; cat /tmp/apex_map_saver.log; }
  kill -INT "$OFFSET" 2>/dev/null || true
  wait "$OFFSET" 2>/dev/null || true
  cp /tmp/apex_slam_offset.csv "$RUN/slam_offset.csv"
fi
