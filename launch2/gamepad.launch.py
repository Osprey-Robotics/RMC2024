
from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node

def generate_launch_description():

    spawn_joy_linux_node = Node(package='joy_linux',
                                executable='joy_linux_node',
                                name='joy_linux_node',
                                parameters=[])

    spawn_teleop_manual_joy_node = Node(package='osprey_ros',
                                        executable='teleop_manual_joy_node',
                                        name='teleop_manual_joy_node',
                                        parameters=[])

    delayed_teleop_manual_joy_node_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=spawn_joy_linux_node,
            on_start=[spawn_teleop_manual_joy_node],
        )
    )

    return LaunchDescription([
        spawn_joy_linux_node,
        delayed_teleop_manual_joy_node_spawner,
    ])
