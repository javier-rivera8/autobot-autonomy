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

        # ---- Bottle detector (publishes /image_annotated with bboxes) ------
        # Node(
        #     package='autobot_drivers',
        #     executable='bottle_detector',
        #     name='bottle_detector',
        #     output='screen',
        # ),

    ])
