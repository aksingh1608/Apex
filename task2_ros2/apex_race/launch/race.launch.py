"""Start Gazebo with the Apex circuit, spawn the cars, and start the race nodes.

Arguments:
  gui:=true|false        open the Gazebo window (default true)
  player:=true|false     spawn the second car for the keyboard (default false)
  drop_cone:=true|false  start drop_obstacle for the lap two cone (default true)
  runs_dir:=PATH         where the monitor writes runs/<timestamp>/
  slam:=true|false       build a 2D LiDAR map with slam_toolbox while the racer drives (default false)
  rviz:=true|false       open RViz with the live map, scan, racing line and racer trail;
                         needs slam:=true, which provides the map and odom frames (default false)
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, LogInfo,
                            OpaqueFunction, SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from apex_race.robot_model import coloured_burger

COLOURS = {"auto": (0.95, 0.35, 0.05), "player": (0.1, 0.45, 0.95)}


def spawn_cars(context):
    share = get_package_share_directory("apex_race")
    tb3 = get_package_share_directory("turtlebot3_gazebo")
    with open(os.path.join(tb3, "models", "turtlebot3_burger", "model.sdf")) as f:
        burger = f.read()
    with open(os.path.join(share, "config", "circuit.yaml")) as f:
        grid = yaml.safe_load(f)["grid"]
    slam = LaunchConfiguration("slam").perform(context).lower() == "true"
    cars = ["auto"]
    if LaunchConfiguration("player").perform(context).lower() == "true":
        cars.append("player")
    actions = []
    for car in cars:
        path = f"/tmp/apex_{car}.sdf"
        with open(path, "w") as f:
            # Only the racer publishes odom TF, and only when slam_toolbox needs it.
            f.write(coloured_burger(burger, car, COLOURS[car], odom_tf=slam and car == "auto"))
        g = grid[car]
        actions.append(Node(
            package="gazebo_ros", executable="spawn_entity.py", name=f"spawn_{car}",
            arguments=["-entity", car, "-file", path, "-robot_namespace", f"/{car}",
                       "-x", str(g["x"]), "-y", str(g["y"]), "-z", "0.01",
                       "-Y", str(g["yaw"])],
            output="screen"))
    return actions


def start_rviz(context):
    if LaunchConfiguration("rviz").perform(context).lower() != "true":
        return []
    if LaunchConfiguration("slam").perform(context).lower() != "true":
        return [LogInfo(msg="rviz:=true needs slam:=true for the map and odom frames. RViz not started.")]
    config = os.path.join(get_package_share_directory("apex_race"), "config", "apex_map.rviz")
    return [Node(package="rviz2", executable="rviz2", name="rviz2", arguments=["-d", config],
                 parameters=[{"use_sim_time": True}], output="log")]


def generate_launch_description():
    share = get_package_share_directory("apex_race")
    tb3 = get_package_share_directory("turtlebot3_gazebo")
    gazebo_ros = get_package_share_directory("gazebo_ros")
    params = os.path.join(share, "config", "params.yaml")
    world = os.path.join(share, "worlds", "apex_circuit.world")
    model_path = os.path.join(tb3, "models")
    old = os.environ.get("GAZEBO_MODEL_PATH", "")

    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("player", default_value="false"),
        DeclareLaunchArgument("drop_cone", default_value="true"),
        DeclareLaunchArgument("runs_dir", default_value=os.path.join(os.getcwd(), "runs")),
        DeclareLaunchArgument("slam", default_value="false"),
        DeclareLaunchArgument("rviz", default_value="false"),
        SetEnvironmentVariable("GAZEBO_MODEL_PATH", model_path + (":" + old if old else "")),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gazebo_ros, "launch", "gzserver.launch.py")),
            launch_arguments={"world": world, "verbose": "false"}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gazebo_ros, "launch", "gzclient.launch.py")),
            condition=IfCondition(LaunchConfiguration("gui"))),
        OpaqueFunction(function=spawn_cars),
        Node(package="apex_race", executable="race_controller_node", output="screen",
             parameters=[params]),
        Node(package="apex_race", executable="monitor_node", output="screen",
             parameters=[params, {"runs_dir": LaunchConfiguration("runs_dir")}]),
        Node(package="apex_race", executable="drop_obstacle", output="screen",
             parameters=[params],
             condition=IfCondition(LaunchConfiguration("drop_cone"))),
        # 2D mapping. The LiDAR sits 0.032 m behind and 0.181 m above base_footprint
        # (base_joint plus lidar_joint in the Burger SDF).
        Node(package="tf2_ros", executable="static_transform_publisher", name="scan_tf",
             arguments=["--x", "-0.032", "--z", "0.181",
                        "--frame-id", "base_footprint", "--child-frame-id", "base_scan"],
             parameters=[{"use_sim_time": True}],
             condition=IfCondition(LaunchConfiguration("slam"))),
        Node(package="slam_toolbox", executable="async_slam_toolbox_node", name="slam_toolbox",
             output="screen", parameters=[params],
             condition=IfCondition(LaunchConfiguration("slam"))),
        OpaqueFunction(function=start_rviz),
    ])
