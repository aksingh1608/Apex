# Apex

Robotics coursework with one racing theme across two tasks.

- Task 1: `task1_pybullet/apex_track.ipynb`, a PyBullet race circuit notebook. Done in phase 1.
- Task 2: `task2_ros2/`, a ROS 2 time trial in Docker. Coming in phase 2.

## Task 1 quick start

```
curl -LsSf https://astral.sh/uv/install.sh | sh        # once, if uv is missing
uv venv --python 3.11 task1_pybullet/.venv
VIRTUAL_ENV=task1_pybullet/.venv uv pip install -r task1_pybullet/requirements.txt
cd task1_pybullet
.venv/bin/jupyter nbconvert --to notebook --execute --inplace apex_track.ipynb
```

Or open it with `.venv/bin/jupyter lab` and use Restart and Run All.

Failed attempts are logged in `docs/attempts.md`.
