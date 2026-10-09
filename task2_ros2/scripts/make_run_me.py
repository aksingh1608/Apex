#!/usr/bin/env python3
"""Write task2_ros2/RUN_ME.ipynb from the steps below.

Step times live in run_me_times.json (measured on Ubuntu 24.04).
Run from the project root:
  python3 task2_ros2/scripts/make_run_me.py task2_ros2/scripts/run_me_times.json

See README.md for the short run guide.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "RUN_ME.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def build(times):
    t = times
    cells = [md(f"""
# Apex Task 2: run the ROS 2 race

Companion notebook to `README.md`. It lists every Task 2 command in order, with the time each
step took on Ubuntu 24.04 (12 cores, CPU rendering in Docker).

There are two ways to use it.

* **Headless check.** Run the code cells from top to bottom. They build the image, start the container,
  run one full mission with scripted key presses, and draw the figures. No window opens.
* **Recorded run with the GUI.** Follow the markdown steps in section 7. They need three terminals,
  because Gazebo and the keyboard node need a real screen and a real keyboard.

All paths are relative to the project root (the folder that contains `README.md`). The first code cell moves there.
"""),
             code("""
%cd ..
!pwd
"""),
             md(f"""
## 1. Build the Docker image (once)

Time: about {t['build']} the first time, with `osrf/ros:humble-desktop-full` already pulled.
Pulling that base image first adds a few minutes more (about 5.4 GB on disk).
"""),
             code("""
!docker pull osrf/ros:humble-desktop-full
!docker build -t apex:humble task2_ros2/docker
"""),
             md(f"""
## 2. Start the container and build the package

Time: container start {t['start']}, `colcon build` {t['colcon']}.

`run.sh --headless` starts the container in the background with no display.
For the GUI run in section 4 use `task2_ros2/docker/run.sh` with no flag instead.
If a container named `apex` already exists, remove it first with `docker rm -f apex`.
"""),
             code("""
!docker rm -f apex 2>/dev/null; task2_ros2/docker/run.sh --headless
!docker exec apex bash -c 'source /opt/apex_env.sh && cd /ws && colcon build --symlink-install --base-paths src/apex/task2_ros2'
"""),
             md(f"""
## 3. Unit tests and world generation

Time: tests {t['tests']}, world generation {t['world']}.

The world file is already in the repo. Regenerate it after you change `config/circuit.yaml`.
"""),
             code("""
!docker exec apex bash -c 'source /opt/apex_env.sh && cd /ws/src/apex/task2_ros2/apex_race && python3 -m pytest -q test'
!docker exec apex bash -c 'cd /ws/src/apex/task2_ros2 && python3 world_gen/generate_world.py'
"""),
             md(f"""
## 4. Headless mission (scripted keys)

Time: about {t['mission']} for the whole run. The race itself is 3 laps.

This starts Gazebo with no window, presses g, drops the cone on lap 2,
pauses and resumes once on lap 3, and prints the summary. Logs go to `task2_ros2/runs/<timestamp>/`.
"""),
             code("""
!docker exec apex bash -c 'source /opt/apex_env.sh && cd /ws/src/apex/task2_ros2 && scripts/headless_run.sh'
"""),
             md(f"""
Phase 3 version, with the blue player car. The script parks the player car on the front straight before it presses g,
so the racer has to pass it on every lap. Time: about {t['mission_player']}.
"""),
             code("""
!docker exec apex bash -c 'source /opt/apex_env.sh && cd /ws/src/apex/task2_ros2 && scripts/headless_run.sh player'
"""),
             md(f"""
## 5. Figures from the newest run

Time: {t['analyze']}.
"""),
             code("""
!docker exec apex bash -c 'cd /ws/src/apex/task2_ros2 && python3 scripts/analyze_run.py $(ls -d runs/*/ | tail -1)'
!ls task2_ros2/runs/$(ls task2_ros2/runs | tail -1)/figures
"""),
             md(f"""
## 6. 2D LiDAR map of the circuit

Time: about {t['mission_slam']} for the run, and about 2 s for the figures.

`slam` adds slam_toolbox to the launch. It builds a 2D map from the racer's LiDAR while the racer drives
the same mission. At the end the script saves the map as `map.pgm` and `map.yaml` in the run folder.
`plot_map.py` draws the map and checks it against the wall positions in `circuit.yaml`.
Add `player` before `slam` to map the two car mission.
"""),
             code("""
!docker exec apex bash -c 'source /opt/apex_env.sh && cd /ws/src/apex/task2_ros2 && scripts/headless_run.sh slam'
!docker exec apex bash -c 'cd /ws/src/apex/task2_ros2 && python3 scripts/plot_map.py $(ls -d runs/*/ | tail -1)'
"""),
             md("""
## 7. Recorded run with the GUI and your own key presses

Do this in three terminals, not in this notebook. Stop the headless container first:
`docker rm -f apex`.

**Terminal 1** (time to a ready racer with no window: about """ + t['gui_up'] + """; Gazebo with a display takes a little longer):
```
# from the project root (folder that contains README.md)
task2_ros2/docker/run.sh
cd /ws && colcon build --symlink-install --base-paths src/apex/task2_ros2 && source install/setup.bash
cd /ws/src/apex/task2_ros2
ros2 launch apex_race race.launch.py player:=true
```
Leave out `player:=true` for the one-car version. Add `slam:=true` to build the 2D map as well, and `slam:=true rviz:=true` to also open RViz with the live map, the scan and the racing line.

**Terminal 2**, the keyboard:
```
task2_ros2/docker/exec.sh
ros2 run apex_race keyboard_node --ros-args --params-file apex_race/config/params.yaml
```
Click into this terminal so it gets your keys.

**Terminal 3**, the status:
```
task2_ros2/docker/exec.sh
ros2 topic echo /apex/status
```

**The mission** (about """ + t['race'] + """ of race time):
1. Press `g`. The countdown runs 3, 2, 1, Go.
2. Drive the blue car with `w a s d` (space stops it). Park it on the racing line if you want the racer to pass it.
3. On lap 2 the cone drops on the back straight. Watch AVOID and REPLAN in terminal 1.
4. On lap 3 press `p` to pause. Wait a few seconds. Press `p` again to resume.
5. After lap 3 the racer stops and terminal 1 prints the summary.
6. Press `Ctrl+C` in terminal 1, then `q` in terminal 2. The Gazebo window takes about 5 s to close: it ignores the first signal, and the launch then stops it.

Other keys: `x` aborts the race, `r` resets it after it ends or while paused.

If you started with `slam:=true`, save the map before step 6, from terminal 3 (Ctrl+C the echo first):
```
ros2 run nav2_map_server map_saver_cli -f runs/<timestamp>/map --ros-args -p use_sim_time:=true
```

Then draw the figures for that run:
```
python3 scripts/analyze_run.py runs/<timestamp>
python3 scripts/plot_map.py runs/<timestamp>     # only if you saved a map
```
"""),
             md("""
## 8. Clean up

```
docker rm -f apex
```
The image stays. Remove it with `docker rmi apex:humble` if you need the space.
"""),
             ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3",
                                                       "language": "python", "name": "python3"},
                                        "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


if __name__ == "__main__":
    import sys
    times = json.loads(Path(sys.argv[1]).read_text())
    OUT.write_text(json.dumps(build(times), indent=1) + "\n")
    print(f"Wrote {OUT}")
