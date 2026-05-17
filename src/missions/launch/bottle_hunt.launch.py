from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    start_detector = LaunchConfiguration('start_detector')
    use_ultrasonic = LaunchConfiguration('use_ultrasonic')

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
            }],
        ),
    ])
