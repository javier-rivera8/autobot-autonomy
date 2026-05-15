from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # ---- Camera -------------------------------------------------------
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera',
            output='screen',
            parameters=[{
                'video_device': '/dev/video0',
                'image_size': [640, 480],
                'pixel_format': 'YUYV',
            }],
        ),

        # ---- Video web stream (http://<IP>:8080/stream?topic=/image_raw) --
        Node(
            package='web_video_server',
            executable='web_video_server',
            name='web_video_server',
            output='screen',
        ),

        # ---- Motor driver -------------------------------------------------
        Node(
            package='autobot_drivers',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
        ),

        # ---- Web teleop (iPhone / browser control) -------------------------
        # Opens http://<pi-ip>:8888/ — virtual joystick for /cmd_vel
        Node(
            package='autobot_drivers',
            executable='web_teleop',
            name='web_teleop',
            output='screen',
            parameters=[{'http_port': 8888}],
        ),

        # ---- rosbridge (WebSocket → ROS 2) --------------------------------
        # Browser connects to ws://<pi-ip>:9090
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            output='screen',
            parameters=[{
                'address': '0.0.0.0',
                'port': 9090,
            }],
        ),

        # ---- Bottle detector (publishes /image_annotated with bboxes) ------
        # Node(
        #     package='autobot_drivers',
        #     executable='bottle_detector',
        #     name='bottle_detector',
        #     output='screen',
        # ),

    ])
