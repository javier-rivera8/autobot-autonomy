from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    start_detector = LaunchConfiguration('start_detector')
    use_ultrasonic = LaunchConfiguration('use_ultrasonic')
    search_angular_speed = LaunchConfiguration('search_angular_speed')
    search_rotate_seconds = LaunchConfiguration('search_rotate_seconds')
    search_pause_seconds = LaunchConfiguration('search_pause_seconds')
    max_linear_speed = LaunchConfiguration('max_linear_speed')
    max_angular_speed = LaunchConfiguration('max_angular_speed')
    camera_tilt_start = LaunchConfiguration('camera_tilt_start')

    return LaunchDescription([
        DeclareLaunchArgument(
            'start_detector',
            default_value='true',
            description='Start autobot_drivers/bottle_detector with mission',
        ),
        DeclareLaunchArgument(
            'use_ultrasonic',
            default_value='true',
            description='Use Yahboom ultrasonic range to stop near target',
        ),
        DeclareLaunchArgument(
            'search_angular_speed',
            default_value='2.00',
            description='Angular speed while scanning for the bottle',
        ),
        DeclareLaunchArgument(
            'search_rotate_seconds',
            default_value='0.45',
            description='Seconds to rotate during each scan step',
        ),
        DeclareLaunchArgument(
            'search_pause_seconds',
            default_value='1.35',
            description='Seconds to wait still for detector frames',
        ),
        DeclareLaunchArgument(
            'max_linear_speed',
            default_value='0.35',
            description='Maximum forward speed while approaching the bottle',
        ),
        DeclareLaunchArgument(
            'max_angular_speed',
            default_value='2.00',
            description='Maximum turn speed while tracking the bottle',
        ),
        DeclareLaunchArgument(
            'camera_tilt_start',
            default_value='25',
            description='Tilt servo angle to set when the mission starts',
        ),

        Node(
            package='autobot_drivers',
            executable='bottle_detector',
            name='bottle_detector',
            output='screen',
            condition=IfCondition(start_detector),
            parameters=[{
                'confidence': 0.40,
                'img_size': 320,
            }],
        ),

        Node(
            package='missions',
            executable='bottle_hunt_mission',
            name='bottle_hunt_mission',
            output='screen',
            parameters=[{
                'use_ultrasonic': ParameterValue(
                    use_ultrasonic,
                    value_type=bool,
                ),
                'search_angular_speed': ParameterValue(
                    search_angular_speed,
                    value_type=float,
                ),
                'search_rotate_seconds': ParameterValue(
                    search_rotate_seconds,
                    value_type=float,
                ),
                'search_pause_seconds': ParameterValue(
                    search_pause_seconds,
                    value_type=float,
                ),
                'max_linear_speed': ParameterValue(
                    max_linear_speed,
                    value_type=float,
                ),
                'max_angular_speed': ParameterValue(
                    max_angular_speed,
                    value_type=float,
                ),
                'camera_tilt_start': ParameterValue(
                    camera_tilt_start,
                    value_type=int,
                ),
            }],
        ),
    ])
