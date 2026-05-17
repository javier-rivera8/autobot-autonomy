#!/usr/bin/env python3
"""
web_teleop_node.py
------------------
Serves the web teleop HTML page (port 8888) and handles the
simple command topics published by the browser:

  /web_teleop/buzzer      (std_msgs/Bool)   → buzzer on/off
  /web_teleop/led         (std_msgs/String) → colour name: red/blue/green/white/purple/off
  /web_teleop/servo_tilt  (std_msgs/Float32)→ incremental tilt delta (degrees/tick)

Drive control goes directly through /cmd_vel → motor_driver_node.
"""

import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String

from autobot_drivers.yahboom_mcu import YahboomMCU


# ---------------------------------------------------------------------------
# Static file server (restricted to the web/ dir in this package)
# ---------------------------------------------------------------------------
_WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')


class _QuietHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler locked to _WEB_DIR with suppressed access logs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_WEB_DIR, **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path in ('', '/'):
            self.path = '/teleop.html'
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, 'File not found')
        return None

    def log_message(self, fmt, *args):  # silence request logs
        pass

    def log_error(self, fmt, *args):
        pass


class _TeleopHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


# ---------------------------------------------------------------------------
# ROS 2 node
# ---------------------------------------------------------------------------
class WebTeleopNode(Node):

    TILT_MIN, TILT_MAX = 0, 100
    TILT_CENTER = 40

    _LED_MAP = {
        'red':    (255, 0, 0),
        'green':  (0, 255, 0),
        'blue':   (0, 0, 255),
        'white':  (255, 255, 255),
        'purple': (128, 0, 128),
        'off':    (0, 0, 0),
    }

    def __init__(self):
        super().__init__('web_teleop')

        self.declare_parameter('http_port', 8888)
        port = self.get_parameter('http_port').value

        try:
            self._mcu = YahboomMCU()
            self.get_logger().info('YahboomMCU: I2C open OK')
        except Exception as e:
            self._mcu = None
            self.get_logger().warn(f'YahboomMCU unavailable: {e} — running without hardware')

        self._tilt = self.TILT_CENTER
        if self._mcu:
            self._mcu.set_servo(2, int(self._tilt))

        # Subscriptions
        self.create_subscription(Bool,    '/web_teleop/buzzer',     self._buzzer_cb,     10)
        self.create_subscription(String,  '/web_teleop/led',        self._led_cb,        10)
        self.create_subscription(Float32, '/web_teleop/servo_tilt', self._servo_tilt_cb, 10)

        # HTTP server (runs in a daemon thread — lifecycle tied to the node)
        self._start_http_server(port)

        self.get_logger().info(
            f'web_teleop ready — open http://<pi-ip>:{port}/ on your iPhone')

    # ------------------------------------------------------------------
    def _start_http_server(self, port: int) -> None:
        self._http_server = _TeleopHTTPServer(('0.0.0.0', port), _QuietHandler)
        t = threading.Thread(
            target=self._http_server.serve_forever,
            daemon=True,
            name='web-teleop-http',
        )
        t.start()

    # ------------------------------------------------------------------
    def _buzzer_cb(self, msg: Bool) -> None:
        if self._mcu:
            self._mcu.buzzer(1 if msg.data else 0)

    def _led_cb(self, msg: String) -> None:
        colour = msg.data.lower().strip()
        rgb = self._LED_MAP.get(colour)
        if rgb is None:
            self.get_logger().warn(f'Unknown LED colour: {colour!r}')
            return
        if self._mcu:
            self._mcu.led_rgb_all(*rgb)

    def _servo_tilt_cb(self, msg: Float32) -> None:
        self._tilt = max(self.TILT_MIN,
                         min(self.TILT_MAX, self._tilt + msg.data))
        if self._mcu:
            self._mcu.set_servo(2, int(self._tilt))


# ---------------------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = WebTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
