# Attempts log

Development log for this coursework. Each entry records an approach that failed, what broke, and what came next. Start with `README.md` for how to run the finished project.

## 2026-10-08: Task 1, track URDF would not load

- Tried: write each URDF as one long line of XML. The track has about 150 visual and collision tags.
- Broke: `p.loadURDF` failed with `XML_ERROR_PARSING_ATTRIBUTE ... Line number=4`. Python's XML parser read the same file without error. The small models loaded fine.
- Next: write one tag per line. The same track then loaded. The writer now does this for every URDF.

## 2026-10-08: Task 1, the racer stopped against a checkpoint gate

- Tried: drive the racer from the start grid to the turn two apex with pure pursuit on the wheel motors.
- Broke: the car stopped at x = 6.77, y = -1.02 in turn one, 13.8 m short of the goal. I had set each gate's yaw so its posts stood on the racing line, not beside the track.
- Next: set each gate's yaw to the track heading at that point, so the posts sit outside the track edges. The same drive then reached turn two within 4.9 cm and the finish line within 4.9 cm. No fallback to `resetBasePositionAndOrientation` was needed for the drive.

## 2026-10-08: Task 1, the low corner camera could not see the robot

- Tried: a corner camera at (-11, -7.5) and 1.2 m high, looking at the infield.
- Broke: a light tower stood right in front of the lens and filled the middle of the image. At the finish line the robot covered only 2 pixels in the segmentation mask, because the front straight barriers (0.43 m tall) hid it.
- Next: moved that light tower to the south east corner, and raised the camera to 1.5 m with a narrower view. The robot now covers 98 to 333 pixels in that view.

## 2026-10-08: Task 1, false shadow band in the top-down view

- Tried: the tiny renderer with shadows on for all three cameras.
- Broke: the top-down image showed a dark diagonal band across the grass. It moved when the light direction changed, so it came from the shadow map, not from any object.
- Next: shadows off for the top-down camera only. The two side views keep shadows.


## 2026-10-08: Task 2, the race controller died on start

- Tried: one params.yaml with a ROS section for each node, plus a plain `drop_obstacle:` section that the script read with PyYAML.
- Broke: every node that loaded the file died with `Couldn't parse params file ... Cannot have a value before ros__parameters at line 52`. ROS checks every top level section, not only its own.
- Next: made drop_obstacle a normal ROS node with a `ros__parameters` section. All nodes now read the same file.

## 2026-10-08: Task 2, Gazebo flooded the log

- Tried: the beacon `run.sh` pattern, which runs the container as my user id.
- Broke: gzserver printed `Error getting username: no matching password record` hundreds of times a second, which buried the race log. The container has no entry for my user id.
- Next: mount the host `/etc/passwd` and `/etc/group` read only. The message is gone.

## 2026-10-08: Task 2, the racer got stuck at the cone

- Tried: stop at 0.45 m in AVOID, then pick a side by the mean LiDAR range in a 15 to 75 degree sector on each side, and shift 14 waypoints by 0.32 m starting one waypoint ahead.
- Broke: run `20261008_184111`. The sectors read 0.95 m left and 0.91 m right, nearly a tie, because they barely saw the cone. The shift reached full width only at the cone, so the racer turned too little and came to 0.20 m from the cone. From there the cone sat on the edge of the corridor. The state flipped between AVOID and REPLAN 87 times, the side choice flipped to the cone side, and I aborted the run after 170 s. No contact event: the lowest range was 0.229 m.
- Next: stop at 0.6 m and call the path clear only beyond 0.8 m. Compare the smallest sideways gap to scan points on each side within 1 m ahead. Shift waypoints from the car's own position. Keep the first side until the car is past. In REPLAN, stop only for something within 0.15 m in a band as wide as the car.

## 2026-10-08: Task 2, the old race kept running after the script ended

- Tried: `headless_run.sh` started `ros2 launch ... &` and sent it SIGINT on exit.
- Broke: the next run with the player car printed `Entity [auto] already exists` and `Spawn service failed`. The old gzserver and the old nodes were still running, and two race controllers answered on the same topics. A non-interactive bash starts background jobs with SIGINT ignored, so the launch never saw the signal. The killed processes then stayed as zombies, because the container's first process was `sleep infinity`.
- Next: `set -m` in the script, so the launch runs in its own process group with SIGINT working, and the stop signal goes to the whole group. `run.sh` now starts the container with `--init`, which reaps dead processes. The script also stops early if a spawn fails.

## 2026-10-08: Task 2, the racer brushed past the player car

- Tried: the same REPLAN as for the cone (smallest sideways gap on each side, a fixed 0.32 m shift over 16 waypoints), with the player car parked on the centre line of the front straight.
- Broke: run `20261008_205513`. The gaps read 0.00 m left and 0.00 m right, because the parked car sits across the centre line and its own scan points count on both sides. The racer passed on the right and the monitor logged contact event 1 at a range of 0.150 m. The same pass on lap 3 gave contact event 2. The lowest range in the run was 0.12 m. Two more causes: the other Burger's wheels sit below the LiDAR plane, so it is wider than it looks in the scan, and the shifted stretch ended about 0.1 m past the car, so pure pursuit cut back while the racer was still beside it.
- Next: measure the free space beside the obstacle, from its edge to the next point on each side. Size the shift from the obstacle's edge plus 0.25 m, between 0.30 and 0.38 m. Shift 22 waypoints instead of 16.

## 2026-10-08: Task 2, the keyboard node crashed on start

- Tried: start `keyboard_node` in a terminal (tested with `script` as a fake terminal, on ROS domain 42 so it could not touch a running race).
- Broke: `AttributeError: __enter__` inside `rclpy/node.py`. My class had a method called `handle`, which replaced the `handle` that rclpy's `Node` uses internally.
- Next: renamed the method to `on_key`. The same test then sent g and p on `/apex/command`, set `/player/cmd_vel` to 0.05 and 0.10 m/s with w, and sent zero on space and on exit.

## 2026-10-08: Task 2, the racer got wedged beside the player car

- Tried: the free space measure and a 0.30 m shift, with the normal 0.45 m pure pursuit lookahead in REPLAN.
- Broke: run `20261008_210502`. The free space read 0.53 m on each side, which was right, but the racer was only 0.15 m off the centre line when it drew level with the parked car. Pure pursuit with a 0.45 m lookahead closes a sideways gap over about a metre, and the racer stops only about 0.6 m before the obstacle. The range fell to 0.141 m (contact events 1 to 3). Each new REPLAN then hit the 0.15 m safety band at once, so it looped beside the car until I aborted at 137 s. The cone runs never showed this, because the cone sits 0.1 m toward the other side.
- Next: a 0.25 m lookahead in REPLAN, so the racer reaches the shifted line sooner. Each repeat REPLAN for the same obstacle widens the shift by 0.04 m, up to 0.38 m.

## 2026-10-08: Task 2, the scripted player car squeezed the racer at the start

- Tried: the headless driver sent the player car to its parking spot on the racing line while the race started.
- Broke: run `20261008_211402`. Both cars left the grid together and drove side by side toward the racing line. The LiDAR range sat at its 0.12 m floor for about 2 s, which gave contact event 1 at 4.7 s. The racer only checks the corridor ahead, so it does not react to a car closing in from the side. Both later passes of the parked car went cleanly, with a lowest range of 0.251 m on the first one.
- Next: the driver now parks the player car first and presses g after that, the way a person would set up the race. Side approach by another car stays a known limit of the racer.

## 2026-10-08: Task 2, sourcing the workspace failed in one shell

- Tried: a GUI smoke test that ran `source /opt/apex_env.sh`, then `colcon build`, then `source install/setup.bash`, all in one shell.
- Broke: `install/setup.bash: line 11: COLCON_TRACE: unbound variable`. `apex_env.sh` (copied from the beacon pattern) ended with `set -u`, and the setup script reads unset variables. The same problem meant the README's one line headless command could not find `apex_race` on a fresh container. My earlier runs hid it, because I always built in a separate `docker exec` first.
- Next: removed `set -u` from `apex_env.sh`, rebuilt the image, and added `source install/setup.bash` to the README command. I tested that command as written on a fresh container.

## 2026-10-09: Task 2, the map check counted unseen cells as free

- Tried: read the saved `map.pgm` with the thresholds in its own `map.yaml` (occupied above 0.65, free below 0.25), the way map_server loads it.
- Broke: run `20261009_002750`. The check reported 22.9 m² of free space, but the track between the walls is only about 16 m². The figure showed the infield and the area outside the walls as white. `map_saver_cli` writes unseen cells as grey value 205, which is 0.196 on that scale, so they fell under the 0.25 free threshold.
- Next: for a trinary map, read the pixel codes directly: 0 occupied, 254 free, 205 unknown. The free space is now 15.4 m², and the infield and the outside show grey.

## 2026-10-09: Task 2, the two car map came out smeared in the turns

- Tried: the same slam_toolbox settings that gave a clean one car map (run `20261009_002750`, median 2.1 cm from the walls), on the two car mission.
- Broke: run `20261009_003315`. The outer wall in both turns came out thick and doubled, up to about 0.25 m inside the real wall face. Only 56% of the occupied cells were within 5 cm of a wall (89% in the one car map). I could not say why from the map alone.
- Next: `scripts/slam_offset.py` records slam_toolbox's map to odom correction. `/odom` here is the true pose, so that correction is the SLAM pose error. The repeat two car run `20261009_004014` showed the error grow to 9.7 cm and 9.6 degrees during lap 1, and drop to under 1 cm and 1 degree at a loop closure as lap 2 began. Its map was much cleaner (77% within 5 cm). A new one car run `20261009_004641` showed the same pattern (11.6 cm and 11.8 degrees in lap 1, 72% within 5 cm). So map quality changes from run to run, not between one car and two cars: it depends on how far the heading drifts before the first loop closure. I kept the default scan matcher settings, so the maps show what slam_toolbox really does.

## 2026-10-09: Task 2, the headless script left the launch running

- Tried: stop the SLAM error recorder in the exit trap with `[ -n "$OFFSET" ] && kill -INT "$OFFSET"`.
- Broke: run `20261009_004014`. The recorder had already stopped, so `kill` failed. Under `set -e`, a failed last command in an `&&` list ends the shell, so the trap quit before it stopped the launch. gzserver, slam_toolbox and the race nodes were still running after the script exited with code 1.
- Next: stopped them by hand, and wrote the line as an `if` with `|| true`.
