"""Drop one cone on the track mid race, at the same place every run.

It waits until the racer is on the chosen lap and past trigger_x on the
front straight, then spawns a cone that falls onto the back straight.
Settings come from the drop_obstacle section of params.yaml:
    ros2 run apex_race drop_obstacle --ros-args --params-file config/params.yaml
"""

import json
import signal

import rclpy
from gazebo_msgs.srv import SpawnEntity
from rclpy.node import Node
from std_msgs.msg import String

from apex_race.props import drop_cone_sdf


class Dropper(Node):
    def __init__(self):
        super().__init__("drop_obstacle")
        p = self.declare_parameters("", [
            ("lap", 2), ("trigger_x", 1.0), ("cone_x", 0.0), ("cone_y", 1.3),
            ("drop_height", 0.25),
        ])
        self.cfg = cfg = {x.name: x.value for x in p}
        self.done = False
        self.pending = None
        self.cli = self.create_client(SpawnEntity, "/spawn_entity")
        self.event_pub = self.create_publisher(String, "/apex/events", 50)
        self.create_subscription(String, "/apex/telemetry", self.on_telem, 10)
        self.get_logger().info(
            f"Waiting for lap {cfg['lap']} and x > {cfg['trigger_x']} on the front straight.")

    def on_telem(self, msg):
        if self.pending is not None or self.done:
            return
        t = json.loads(msg.data)
        if t["lap"] == self.cfg["lap"] and t["x"] > self.cfg["trigger_x"] and t["y"] < 0:
            self.drop(t)

    def drop(self, t):
        c = self.cfg
        if not self.cli.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("/spawn_entity is not available.")
            self.done = True
            return
        req = SpawnEntity.Request()
        req.name = "race_cone"
        req.xml = drop_cone_sdf("race_cone")
        req.initial_pose.position.x = float(c["cone_x"])
        req.initial_pose.position.y = float(c["cone_y"])
        req.initial_pose.position.z = float(c["drop_height"])
        req.reference_frame = "world"
        self.trigger = t
        self.pending = self.cli.call_async(req)
        self.pending.add_done_callback(self.on_spawned)

    def on_spawned(self, fut):
        c = self.cfg
        t = self.trigger
        ok = fut.result() is not None and fut.result().success
        text = (f"Cone dropped at ({c['cone_x']:.2f}, {c['cone_y']:.2f}) on lap {t['lap']}."
                if ok else "Cone drop failed.")
        self.event_pub.publish(String(data=json.dumps({
            "t": t["t"], "race_t": t["race_t"], "kind": "obstacle", "state": t["state"],
            "lap": t["lap"], "text": text})))
        self.get_logger().info(text)
        self.done = True


def main():
    rclpy.init()
    node = Dropper()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        # A second Ctrl+C (ros2 launch forwards one) must not cut the cleanup short.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
