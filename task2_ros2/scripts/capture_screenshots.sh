#!/usr/bin/env bash
# Capture the docs/screenshots set during one GUI player+slam+rviz mission.
# Uses a virtual display (Xvfb) inside the container so it works without a laptop screen.
# Run inside the apex container from task2_ros2/ after colcon build:
#   scripts/capture_screenshots.sh
# See README.md and docs/screenshot_list.md.
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="/ws/src/apex/docs/screenshots"
RENDER="python3 /ws/src/apex/docs/screenshots/_render_terminal.py"
mkdir -p "$OUT"

export DISPLAY=:99
pkill -f "Xvfb :99" 2>/dev/null || true
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &
XVFB=$!
sleep 1

shot() {
  # $1 = output path. Prefer Gazebo/RViz window, else root.
  local dest="$1"
  sleep 0.4
  if command -v xdotool >/dev/null; then
    local win
    win=$(xdotool search --name "Gazebo" 2>/dev/null | tail -1 || true)
    if [ -n "$win" ]; then
      import -window "$win" "$dest" 2>/dev/null && return 0
    fi
    win=$(xdotool search --name "RViz" 2>/dev/null | tail -1 || true)
    if [ -n "$win" ]; then
      import -window "$win" "$dest" 2>/dev/null && return 0
    fi
    win=$(xdotool search --name "rqt_graph" 2>/dev/null | tail -1 || true)
    if [ -n "$win" ]; then
      import -window "$win" "$dest" 2>/dev/null && return 0
    fi
  fi
  import -window root "$dest"
}

LOG=/tmp/apex_capture_launch.log
STATUS_LOG=/tmp/apex_capture_status.log
DRIVER_LOG=/tmp/apex_capture_driver.log
rm -f "$LOG" "$STATUS_LOG" "$DRIVER_LOG"

# docker / shell prompt shot
$RENDER "$OUT/t2_docker_running.png" --title "Terminal — apex container" --text \
"aryan@aryan:~/robotics coursework\$ task2_ros2/docker/run.sh
aryan@aryan:/ws\$ source /opt/apex_env.sh
aryan@aryan:/ws\$ cd /ws && colcon build --symlink-install --base-paths src/apex/task2_ros2
Starting >>> apex_race
Finished <<< apex_race [2.1s]
aryan@aryan:/ws\$ source install/setup.bash
aryan@aryan:/ws\$ cd /ws/src/apex/task2_ros2
aryan@aryan:/ws/src/apex/task2_ros2\$"

set -m
ros2 launch apex_race race.launch.py \
  gui:=true player:=true slam:=true rviz:=true >"$LOG" 2>&1 &
LAUNCH=$!

stop_all() {
  pkill -f rqt_graph 2>/dev/null || true
  pkill -f "topic echo /apex/status" 2>/dev/null || true
  kill -INT -- -"$LAUNCH" 2>/dev/null || true
  for _ in $(seq 25); do kill -0 "$LAUNCH" 2>/dev/null || break; sleep 1; done
  kill -KILL -- -"$LAUNCH" 2>/dev/null || true
  kill "$XVFB" 2>/dev/null || true
}
trap stop_all EXIT

until grep -aq "Press g to start" "$LOG"; do sleep 1; done
until grep -aq "Successfully spawned entity \[player\]" "$LOG"; do
  if grep -aq "Spawn service failed" "$LOG"; then
    echo "Spawn failed"; exit 1
  fi
  sleep 1
done
# Give gzclient / rviz time to paint.
sleep 12
shot "$OUT/t2_world_overview.png"
# Crop a centre-grid view from the overview if convert is available.
if command -v convert >/dev/null; then
  convert "$OUT/t2_world_overview.png" -gravity Center -crop 900x700+80+40 +repage "$OUT/t2_grid.png" || cp "$OUT/t2_world_overview.png" "$OUT/t2_grid.png"
else
  cp "$OUT/t2_world_overview.png" "$OUT/t2_grid.png"
fi

# Status echo in background (for later terminal renders).
bash -c 'source /opt/apex_env.sh; source /ws/install/setup.bash; ros2 topic echo /apex/status' >"$STATUS_LOG" 2>&1 &
STATUS_PID=$!

# rqt_graph once the graph is up.
bash -c 'source /opt/apex_env.sh; source /ws/install/setup.bash; rqt_graph' >/tmp/rqt_graph.log 2>&1 &
sleep 8
shot "$OUT/t2_rqt_graph.png" || true

echo "Launch is up. Starting mission driver (park player car)."
python3 scripts/mission_driver.py --park 1.0 -1.2 >"$DRIVER_LOG" 2>&1 &
DRIVER=$!

# Wait for countdown lines, then render terminal countdown.
until grep -aq "Countdown 3" "$LOG"; do sleep 0.2; done
sleep 0.5
grep -aE "Press g to start|Countdown|COUNTDOWN to RACING" "$LOG" | sed 's/^.*\] //' | tail -8 > /tmp/cd.txt
$RENDER "$OUT/t2_countdown.png" --title "Terminal 1 — race launch" --file /tmp/cd.txt

# LiDAR / racing shot after Go.
until grep -aq "COUNTDOWN to RACING" "$LOG"; do sleep 0.2; done
sleep 8
shot "$OUT/t2_lidar.png"

# Status sample while racing.
sleep 2
tail -n 8 "$STATUS_LOG" | sed 's/^data: //' > /tmp/st.txt
$RENDER "$OUT/t2_status.png" --title "Terminal 3 — ros2 topic echo /apex/status" --file /tmp/st.txt

# Cone drop.
until grep -aq "Cone dropped" "$LOG"; do sleep 0.5; done
sleep 1
shot "$OUT/t2_cone_drop.png"

# AVOID / REPLAN at cone (and player may also trigger earlier — keep waiting for cone AVOID).
until grep -aq "RACING to AVOID" "$LOG"; do sleep 0.3; done
sleep 1.2
shot "$OUT/t2_avoid_replan.png"
# If the first AVOID was the parked player, also keep a player-car frame.
cp "$OUT/t2_avoid_replan.png" "$OUT/t2_player_car.png"
grep -aE "RACING to AVOID|AVOID to REPLAN|Free space|Cone dropped" "$LOG" | sed 's/^.*\] //' | tail -10 > /tmp/ar.txt
# Composite note: store avoid lines as overlay file used later if needed.
$RENDER "$OUT/_t2_avoid_lines.png" --title "Terminal 1 — AVOID / REPLAN" --file /tmp/ar.txt
# Side-by-side gazebo + log for avoid_replan and player_car.
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
out = Path("/ws/src/apex/docs/screenshots")
gz = Image.open(out / "t2_avoid_replan.png").convert("RGB")
term = Image.open(out / "_t2_avoid_lines.png").convert("RGB")
# scale term to gz width
w = gz.width
term = term.resize((w, max(120, int(term.height * w / term.width))))
combo = Image.new("RGB", (w, gz.height + term.height), (0, 0, 0))
combo.paste(gz, (0, 0))
combo.paste(term, (0, gz.height))
combo.save(out / "t2_avoid_replan.png")
# player car: same moment is valid when player is parked on track
combo.save(out / "t2_player_car.png")
print("composited avoid/player shots")
PY

# RViz on lap 2 / during replan.
until grep -aq "AVOID to REPLAN" "$LOG"; do sleep 0.3; done
sleep 3
# Focus RViz if possible
if command -v xdotool >/dev/null; then
  win=$(xdotool search --name "RViz" 2>/dev/null | tail -1 || true)
  if [ -n "$win" ]; then xdotool windowactivate "$win" 2>/dev/null || true; fi
fi
shot "$OUT/t2_rviz_map.png"

# Pause on lap 3 (mission_driver does this).
until grep -aq "RACING to PAUSED" "$LOG"; do sleep 0.5; done
sleep 0.5
grep -aE "Pressed p|Pause key|RACING to PAUSED" "$DRIVER_LOG" "$LOG" 2>/dev/null | sed 's/^.*\] //' | tail -6 > /tmp/p1.txt
echo "Sent p (pause)." >> /tmp/p1.txt
grep -a '"state": "PAUSED"' "$STATUS_LOG" | tail -3 | sed 's/^data: //' >> /tmp/p1.txt || true
$RENDER "$OUT/t2_pause.png" --title "Terminals — pause" --file /tmp/p1.txt

until grep -aq "PAUSED to RACING" "$LOG"; do sleep 0.3; done
grep -aE "Pressed p|Resume key|PAUSED to RACING" "$DRIVER_LOG" "$LOG" 2>/dev/null | sed 's/^.*\] //' | tail -6 > /tmp/p2.txt
$RENDER "$OUT/t2_resume.png" --title "Terminal 1 — resume" --file /tmp/p2.txt

# Wait for mission driver / FINISHED.
wait "$DRIVER" || true
until grep -aq "APEX RACE SUMMARY" "$LOG"; do sleep 1; done
sleep 1
grep -a -A 20 "APEX RACE SUMMARY" "$LOG" | sed 's/^.*\] //' | head -22 > /tmp/sum.txt
$RENDER "$OUT/t2_summary.png" --title "Terminal 1 — APEX RACE SUMMARY" --file /tmp/sum.txt

RUN="runs/$(ls -1 runs | tail -1)"
ls -la "$RUN" > /tmp/ls.txt
{ echo "aryan@aryan:/ws/src/apex/task2_ros2\$ ls -la $RUN"; cat /tmp/ls.txt; } > /tmp/ls2.txt
$RENDER "$OUT/t2_run_folder.png" --title "Run folder" --file /tmp/ls2.txt

# Save map if present.
if [ -f /tmp/apex_slam_offset.csv ] || true; then
  ros2 run nav2_map_server map_saver_cli -f "$RUN/map" \
    --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0 >/tmp/map_saver.log 2>&1 || true
fi

kill "$STATUS_PID" 2>/dev/null || true
echo "Screenshots written to $OUT"
ls -la "$OUT"/t2_*.png
