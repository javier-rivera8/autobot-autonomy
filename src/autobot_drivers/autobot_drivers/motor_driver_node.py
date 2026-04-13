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


import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray


# ---------------------------------------------------------------------------
# Hardware abstraction — Yahboom MCU over I2C
# ---------------------------------------------------------------------------
class MotorHardware:
    """
    Sends left/right speed commands to the Yahboom MCU coprocessor.

    Speed convention (internal): signed float in [-100.0, 100.0]
      positive = forward, negative = backward
    """

    I2C_BUS  = 1
    I2C_ADDR = 0x16
    REG_MOVE = 0x01
    REG_STOP = 0x02

    def __init__(self, logger):
        self._logger = logger
        self._bus = None
        try:
            import smbus2
            self._bus = smbus2.SMBus(self.I2C_BUS)
            self._logger.info(
                f'MotorHardware: I2C-{self.I2C_BUS} @ 0x{self.I2C_ADDR:02X} open OK'
            )
        except Exception as e:
            self._logger.warn(
                f'MotorHardware: could not open I2C bus — DRY-RUN mode. ({e})'
            )

    # ------------------------------------------------------------------
    def set_speeds(self, left: float, right: float) -> None:
        """
        :param left:  signed speed [-100, 100] for left  wheels (M1+M3)
        :param right: signed speed [-100, 100] for right wheels (M2+M4)
        """
        l_dir   = 1 if left  >= 0 else 0
        r_dir   = 1 if right >= 0 else 0
        l_speed = min(100, int(math.fabs(left)))
        r_speed = min(100, int(math.fabs(right)))

        self._logger.debug(
            f'motors → L:{l_speed}{"fwd" if l_dir else "rev"} '
            f'R:{r_speed}{"fwd" if r_dir else "rev"}'
        )

        if self._bus is None:
            self._logger.info(f'[DRY-RUN] L={left:.1f} R={right:.1f}')
            return

        try:
            self._bus.write_i2c_block_data(
                self.I2C_ADDR,
                self.REG_MOVE,
                [l_dir, l_speed, r_dir, r_speed],
            )
        except Exception as e:
            self._logger.error(f'MotorHardware.set_speeds I2C error: {e}')

    def stop(self) -> None:
        self._logger.debug('motors → STOP')
        if self._bus is None:
            return
        try:
            self._bus.write_byte_data(self.I2C_ADDR, self.REG_STOP, 0x00)
        except Exception as e:
            self._logger.error(f'MotorHardware.stop I2C error: {e}')

    def close(self) -> None:
        self.stop()
        if self._bus is not None:
            self._bus.close()


# ---------------------------------------------------------------------------
# ROS 2 node
# ---------------------------------------------------------------------------
class MotorDriverNode(Node):

    def __init__(self):
        super().__init__('motor_driver')

        # Parameters — override from launch file or CLI as needed
        self.declare_parameter('wheel_base', 0.14)   # metres L-R wheel distance
        self.declare_parameter('max_speed',  100.0)  # MCU speed units (0-100)

        self._wheel_base = self.get_parameter('wheel_base').value
        self._max_speed  = self.get_parameter('max_speed').value

        self._hw = MotorHardware(self.get_logger())

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

        # Scale to [-max_speed, max_speed], preserving the ratio
        scale = max(abs(v_left), abs(v_right))
        if scale > 1e-6:
            ratio = self._max_speed / max(scale, 1.0)
            left  = v_left  * ratio
            right = v_right * ratio
        else:
            left = right = 0.0

        self._hw.set_speeds(left, right)

        out = Float32MultiArray()
        out.data = [float(left), float(right)]
        self._pub.publish(out)

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
