"""Keyboard: race commands and the player car.

Keys:  g start   p pause or resume   x abort   r reset
       w faster  s slower or reverse  a turn left  d turn right
       space stop the player car      q quit this node

Race keys go to /apex/command. Drive keys set /<player>/cmd_vel,
which is sent 10 times a second.
"""

import select
import signal
import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String

RACE_KEYS = {"g": "start", "p": "pause or resume", "x": "abort", "r": "reset"}


class Keyboard(Node):
    def __init__(self):
        super().__init__("keyboard_node")
        p = self.declare_parameters("", [
            ("player", "player"), ("lin_step", 0.05), ("ang_step", 0.3),
            ("lin_max", 0.22), ("ang_max", 1.5),
        ])
        self.cfg = {x.name: x.value for x in p}
        self.cmd_pub = self.create_publisher(String, "/apex/command", 10)
        self.vel_pub = self.create_publisher(Twist, f"/{self.cfg['player']}/cmd_vel", 10)
        self.v = 0.0
        self.w = 0.0
        self.create_timer(0.1, self.send_vel)

    def send_vel(self):
        t = Twist()
        t.linear.x = self.v
        t.angular.z = self.w
        self.vel_pub.publish(t)

    def on_key(self, key):
        c = self.cfg
        if key in RACE_KEYS:
            self.cmd_pub.publish(String(data=key))
            return f"Sent {key} ({RACE_KEYS[key]})."
        if key == "w":
            self.v = min(c["lin_max"], self.v + c["lin_step"])
        elif key == "s":
            self.v = max(-c["lin_max"], self.v - c["lin_step"])
        elif key == "a":
            self.w = min(c["ang_max"], self.w + c["ang_step"])
        elif key == "d":
            self.w = max(-c["ang_max"], self.w - c["ang_step"])
        elif key == " ":
            self.v = 0.0
            self.w = 0.0
        else:
            return None
        self.send_vel()
        return f"Player car: speed {self.v:+.2f} m/s, turn {self.w:+.2f} rad/s."

    def stop(self):
        self.v = 0.0
        self.w = 0.0
        for _ in range(3):
            self.send_vel()


def raise_interrupt(*_):
    raise KeyboardInterrupt


def main():
    if not sys.stdin.isatty():
        print("keyboard_node needs a terminal. Run it with: ros2 run apex_race keyboard_node")
        return
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, raise_interrupt)
    node = Keyboard()
    print(__doc__)
    old = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            ready, _, _ = select.select([sys.stdin], [], [], 0.0)
            if not ready:
                continue
            key = sys.stdin.read(1).lower()
            if key == "q":
                break
            text = node.on_key(key)
            if text:
                print(text, flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        node.stop()
        print("Keyboard node stopped. Sent zero velocity to the player car.")
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
