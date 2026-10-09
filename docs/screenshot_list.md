# Screenshots

Evidence images live in `docs/screenshots/`. They match a full GUI run of Task 2
(Gazebo, keyboard, status, optional RViz) and the Task 1 notebook outputs.
See `README.md` for how to reproduce the runs.

## Task 1 (PyBullet notebook)

The notebook also saves figures to `task1_pybullet/figures/`. These are the Jupyter evidence shots:

| File | When | What is in the frame |
|---|---|---|
| `t1_restart_run_all.png` | After Kernel → Restart and Run All finishes | Top of the notebook and idle kernel, with no error cells |
| `t1_checks_passed.png` | After the run | Cell output with “Check 1 passed” and “Check 2 passed” |
| `t1_queries.png` | After the run | The three query outputs: highlight, nearest object, role lookup |

## Task 2 (ROS 2 race)

Captured with three terminals and the Gazebo window. Terminal 1 runs the launch file, terminal 2 runs `keyboard_node`, terminal 3 echoes `/apex/status`.

| File | When | What is in the frame |
|---|---|---|
| `t2_docker_running.png` | After `docker/run.sh` starts the container | The terminal prompt inside the container |
| `t2_world_overview.png` | After Gazebo opens, before `g` | The whole circuit: walls, gantry, pit lane, grandstands, light tower, banners |
| `t2_grid.png` | Same moment, zoomed in | The orange racer (and the blue player car when `player:=true`) on the start grid |
| `t2_lidar.png` | During the race | The racer with its LiDAR rays visible |
| `t2_countdown.png` | Right after `g` | Terminal 1 showing “Countdown 3.” to “Go.” |
| `t2_cone_drop.png` | When the log says “Cone dropped” on lap 2 | The cone on the back straight in Gazebo |
| `t2_avoid_replan.png` | When the racer reaches the cone | Gazebo with the racer beside the cone, and Terminal 1 showing RACING→AVOID and AVOID→REPLAN |
| `t2_pause.png` | After `p` | Pause acknowledged; Terminal 1 shows PAUSED; status shows state PAUSED |
| `t2_resume.png` | After `p` again | Terminal 1 showing PAUSED→RACING |
| `t2_status.png` | While racing | Terminal 3 with a few `/apex/status` messages |
| `t2_summary.png` | When the race ends | Terminal 1 showing the full APEX RACE SUMMARY block |
| `t2_run_folder.png` | After the race | `ls` of `runs/<timestamp>/` with `events.csv`, `ticks.csv` and `summary.json` |
| `t2_rqt_graph.png` | During the race (`rqt_graph` in another shell) | The nodes and topics |
| `t2_player_car.png` | Two-car run, player car on the line | Gazebo with both cars; Terminal 1 shows AVOID because of the player car |
| `t2_rviz_map.png` | Run with `slam:=true rviz:=true`, lap 2 or 3 | RViz with the live map, red LiDAR points, and green racing line bent around the cone |

To regenerate the Task 2 set inside the container after a build, from `task2_ros2/`:

```bash
scripts/capture_screenshots.sh
```
