"""
bottle_detector_node.py
-----------------------
Detects water bottles via camera + YOLOv8n and controls the LED light bar.

Uses ultralytics YOLOv8 nano (COCO) — COCO class 39 = "bottle".
  - Bottle detected  → LED bar GREEN
  - Bottle lost       → LED bar OFF

The model (~6 MB) is auto-downloaded on first run by ultralytics.

Requires:
  1.  v4l2_camera_node running and publishing /image_raw

Topics:
  Subscribed : /image_raw         (sensor_msgs/Image)
  Published  : /bottle_detected   (std_msgs/Bool)
               /image_annotated   (sensor_msgs/Image)  ← bounding boxes
"""

import cv2
from ultralytics import YOLO

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from cv_bridge import CvBridge

from autobot_drivers.yahboom_mcu import YahboomMCU

_COCO_BOTTLE_CLASS = 39  # COCO class ID for "bottle"


class BottleDetectorNode(Node):

    def __init__(self):
        super().__init__('bottle_detector')

        # ----- Parameters ---------------------------------------------------
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.40)
        self.declare_parameter('img_size', 320)

        model_name = self.get_parameter('model').value
        self._conf = self.get_parameter('confidence').value
        self._imgsz = self.get_parameter('img_size').value

        # ----- YOLO model ---------------------------------------------------
        self._model = YOLO(model_name)
        self.get_logger().info(f'YOLO model "{model_name}" loaded OK')

        # ----- MCU (LED control) --------------------------------------------
        try:
            self._mcu = YahboomMCU()
            self.get_logger().info('YahboomMCU: I2C open OK')
        except Exception as e:
            self._mcu = None
            self.get_logger().warn(
                f'YahboomMCU unavailable ({e}), LED control disabled')

        # ----- ROS plumbing -------------------------------------------------
        self._bridge = CvBridge()
        self._bottle_visible = False

        self._sub = self.create_subscription(
            Image, '/image_raw', self._image_cb,
            qos_profile_sensor_data)

        self._pub = self.create_publisher(Bool, '/bottle_detected', 10)
        self._img_pub = self.create_publisher(Image, '/image_annotated', 10)

        self.get_logger().info('bottle_detector node ready  '
                               f'(confidence ≥ {self._conf})'
                               '  →  stream: /image_annotated')

    # ------------------------------------------------------------------
    def _image_cb(self, msg: Image) -> None:
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        results = self._model.predict(
            frame, imgsz=self._imgsz, conf=self._conf,
            classes=[_COCO_BOTTLE_CLASS], verbose=False)

        found = False
        best_conf = 0.0
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    found = True
                # Draw bounding box on frame
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f'bottle {conf:.0%}',
                            (x1, max(y1 - 8, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Publish annotated image (always, so the stream stays active)
        ann_msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        ann_msg.header = msg.header
        self._img_pub.publish(ann_msg)

        # Publish detection flag
        det_msg = Bool()
        det_msg.data = found
        self._pub.publish(det_msg)

        # Update LED only on state change
        if found != self._bottle_visible:
            self._bottle_visible = found
            if self._mcu:
                if found:
                    self._mcu.led_all(1, YahboomMCU.GREEN)
                    self.get_logger().info(
                        f'Bottle detected ({best_conf:.0%}) → LED GREEN')
                else:
                    self._mcu.led_off()
                    self.get_logger().info('Bottle lost → LED OFF')

    # ------------------------------------------------------------------
    def destroy_node(self) -> None:
        if self._mcu:
            self._mcu.led_off()
            self._mcu.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BottleDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
