#!/usr/bin/env python3
"""Record slam_toolbox's map to odom correction during a run.

Usage (inside the container, while a launch with slam:=true runs):
    python3 scripts/slam_offset.py OUT_CSV

/odom in this simulation is Gazebo's true pose, so the map frame should sit
exactly on the odom frame. Any map to odom offset that slam_toolbox
publishes is its own pose error. This writes one row per change:
sim time, x, y, yaw. It stops on Ctrl+C or SIGTERM.
"""

import csv
import math
import signal
import sys

import rclpy
from rclpy.parameter import Parameter
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from tf2_msgs.msg import TFMessage


class Recorder(Node):
    def __init__(self, path):
        super().__init__("slam_offset", parameter_overrides=[
            Parameter("use_sim_time", value=True)])
        self.f = open(path, "w", newline="")
        self.w = csv.writer(self.f)
        self.w.writerow(["t", "x", "y", "yaw"])
        self.last = None
        self.create_subscription(TFMessage, "/tf", self.on_tf, 100)

    def on_tf(self, msg):
        for tf in msg.transforms:
            if tf.header.frame_id != "map" or tf.child_frame_id != "odom":
                continue
            q = tf.transform.rotation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            row = (round(tf.transform.translation.x, 4), round(tf.transform.translation.y, 4),
                   round(yaw, 5))
            if row == self.last:
                continue
            self.last = row
            t = tf.header.stamp.sec + tf.header.stamp.nanosec * 1e-9
            self.w.writerow([round(t, 2), *row])
            self.f.flush()


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = Recorder(sys.argv[1])

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.f.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
