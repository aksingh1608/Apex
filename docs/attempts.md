# Attempts log

Each entry records an approach that failed, what broke, and what came next.

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
