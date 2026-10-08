#!/usr/bin/env bash
# Run one full mission with no GUI and the scripted key presses.
# Use it inside the container from task2_ros2/:  scripts/headless_run.sh [player]
# With "player" it also spawns the blue car and parks it on the front straight.
# It starts the launch file, presses g, pauses and resumes once on lap 3,
# waits for the race to end, then stops everything. Logs go to runs/.

set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PLAYER=false
[ "${1:-}" = "player" ] && PLAYER=true

LOG=/tmp/apex_launch.log
# Job control gives the launch its own process group and keeps SIGINT
# working for it. Without it, bash starts background jobs with SIGINT ignored.
set -m
rm -f "$LOG"
ros2 launch apex_race race.launch.py gui:=false player:=$PLAYER > "$LOG" 2>&1 &
LAUNCH=$!
stop_launch() {
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
if [ "$PLAYER" = true ]; then
  python3 scripts/mission_driver.py --park 1.0 -1.2
else
  python3 scripts/mission_driver.py
fi
sleep 2
grep -a -A 14 "APEX RACE SUMMARY" "$LOG" | sed 's/^.*\] //'
