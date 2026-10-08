# Screenshots to take by hand

I cannot take these for you. Take each one during your own recorded run, at the moment given. Save them in `docs/screenshots/` with the file name shown.

## Task 1 (PyBullet notebook)

The notebook already saves its figures to `task1_pybullet/figures/`. Take these extra shots of Jupyter itself.

| File | When | What must be in the frame |
|---|---|---|
| `t1_restart_run_all.png` | Right after Kernel > Restart and Run All finishes | The top of the notebook and the kernel status showing idle, with no error cells |
| `t1_checks_passed.png` | After the run | The cell output that says "Check 1 passed" and "Check 2 passed" |
| `t1_queries.png` | After the run | The three query outputs: highlight, nearest object, role lookup |

## Task 2 (ROS 2 race)

Use three terminals side by side with the Gazebo window. Terminal 1 runs the launch file, terminal 2 runs `keyboard_node`, terminal 3 echoes `/apex/status`.

| File | When | What must be in the frame |
|---|---|---|
| `t2_docker_running.png` | After `docker/run.sh` starts the container | The terminal prompt inside the container |
| `t2_world_overview.png` | After Gazebo opens, before you press g | The whole circuit: walls, gantry, pit lane, grandstands, light tower, banners |
| `t2_grid.png` | Same moment, zoomed in | The orange racer (and the blue player car in phase 3) on the start grid |
| `t2_lidar.png` | Any time during the race | The racer with its LiDAR rays visible (View > Transparent, or the blue ray fan) |
| `t2_countdown.png` | Right after you press g | Terminal 1 showing "Countdown 3." to "Go." |
| `t2_cone_drop.png` | When the log says "Cone dropped" on lap 2 | The cone on the back straight in Gazebo |
| `t2_avoid_replan.png` | When the racer reaches the cone | Gazebo with the racer beside the cone, and terminal 1 showing the RACING to AVOID and AVOID to REPLAN lines |
| `t2_pause.png` | After you press p | Terminal 2 showing "Sent p", terminal 1 showing the PAUSED line, terminal 3 showing state PAUSED |
| `t2_resume.png` | After you press p again | Terminal 1 showing the PAUSED to RACING line |
| `t2_status.png` | Any time while racing | Terminal 3 with a few `/apex/status` messages |
| `t2_summary.png` | When the race ends | Terminal 1 showing the full APEX RACE SUMMARY block |
| `t2_run_folder.png` | After the race | A file browser or `ls` showing `runs/<timestamp>/` with events.csv, ticks.csv and summary.json |
| `t2_rqt_graph.png` | During the race, from a second container shell: `rqt_graph` | The nodes and topics |
| `t2_player_car.png` | Phase 3 run, while you drive the blue car in front of the racer | Gazebo with both cars, and terminal 1 showing the racer go to AVOID because of your car |
| `t2_rviz_map.png` | During a run started with `slam:=true rviz:=true`, on lap 2 or 3 | The RViz window with the live map, the red LiDAR points, and the green racing line bent around the cone |
