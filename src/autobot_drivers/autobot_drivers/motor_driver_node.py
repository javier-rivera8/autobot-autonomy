"""
motor_driver_node.py
--------------------
ROS 2 node that translates geometry_msgs/Twist → motor commands.

Hardware: Yahboom Raspbot MCU coprocessor (I2C-1, 0x2B)
All low-level I2C calls are in yahboom_mcu.YahboomMCU.

Physical layout (verified by hardware probing):
    FL(ID=0)   FR(ID=2)
    RL(ID=1)   RR(ID=3)

Topics:
  Subscribed : /cmd_vel  (geometry_msgs/Twist)
  Published  : /motor_speeds (std_msgs/Float32MultiArray)  [left, right] debug
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

from autobot_drivers.yahboom_mcu import YahboomMCU


# ---------------------------------------------------------------------------
# ROS 2 node
# ---------------------------------------------------------------------------
class MotorDriverNode(Node):

    def __init__(self):
        super().__init__('motor_driver')

        self.declare_parameter('wheel_base', 0.14)   # L-R wheel distance (m)
        self.declare_parameter('max_speed',  255.0)  # MCU speed units (0-255)

        self._wheel_base = self.get_parameter('wheel_base').value
        self._max_speed  = self.get_parameter('max_speed').value

        try:
            self._mcu = YahboomMCU()
            self.get_logger().info('YahboomMCU: I2C open OK')
        except Exception as e:
            self._mcu = None
            self.get_logger().warn(f'YahboomMCU: DRY-RUN mode ({e})')

        self._sub = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_cb, 10)

        self._pub = self.create_publisher(
            Float32MultiArray, '/motor_speeds', 10)

        self.get_logger().info('motor_driver node ready')

    # ------------------------------------------------------------------
    def _cmd_vel_cb(self, msg: Twist) -> None:
        vx = msg.linear.x    # m/s  forward (+) / backward (-)
        wz = msg.angular.z   # rad/s CCW (+) / CW (-)

        # Differential drive mixing
        v_left  = vx - wz * self._wheel_base / 2.0
        v_right = vx + wz * self._wheel_base / 2.0

        # Scale to [-max_speed, max_speed] preserving L/R ratio
        scale = max(abs(v_left), abs(v_right))
        if scale > 1e-6:
            factor = self._max_speed / max(scale, 1.0)
            left   = v_left  * factor
            right  = v_right * factor
        else:
            left = right = 0.0

        self._set_drive(left, right)

        out = Float32MultiArray()
        out.data = [float(left), float(right)]
        self._pub.publish(out)

    def _set_drive(self, left: float, right: float) -> None:
        """Send left/right signed speed [-255, 255] to the 4 motors."""
        self.get_logger().debug(f'drive L={left:.1f}  R={right:.1f}')

        if self._mcu is None:
            self.get_logger().info(f'[DRY-RUN] L={left:.1f}  R={right:.1f}')
            return

        l = int(round(left))
        r = int(round(right))
        self._mcu.set_motor(YahboomMCU.MOTOR_FL, l)
        self._mcu.set_motor(YahboomMCU.MOTOR_RL, l)
        self._mcu.set_motor(YahboomMCU.MOTOR_FR, r)
        self._mcu.set_motor(YahboomMCU.MOTOR_RR, r)

    # ------------------------------------------------------------------
    def destroy_node(self) -> None:
        if self._mcu:
            self._mcu.stop_all_motors()
            self._mcu.close()
        super().destroy_node()


# ---------------------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = MotorDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

    # ------------------------------------------------------------------
    def destroy_node(self) -> None:
        self._hw.close()
        super().destroy_node()


# ---------------------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = MotorDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
