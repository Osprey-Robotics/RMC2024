import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node

import xacro


def generate_launch_description():

    pkg_name = 'osprey_ros'
    filename = 'robot.urdf.xacro'

    pkg_path = os.path.join(get_package_share_directory(pkg_name))
    controller_params = os.path.join(pkg_path, 'config', 'robot_controllers.yaml')
    xacro_file = os.path.join(pkg_path,'description',filename)
    robot_description_config = xacro.process_file(xacro_file)
    robot_description = {'robot_description': robot_description_config.toxml()}

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_description, controller_params],
        output='both',
        remappings=[
            ("/diff_drive_controller/cmd_vel_unstamped", "/cmd_vel"),
            ("/diff_drive_controller/odom", "/odom"),
        ],
    )

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller", "-c", "/controller_manager"],
    )

    position_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["position_controllers", "-c", "/controller_manager"],
    )

    velocity_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["velocity_controllers", "-c", "/controller_manager"],
    )

    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
    )

    delayed_joint_broad_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[joint_broad_spawner],
        )
    )

    delayed_diff_drive_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_broad_spawner,
            on_exit=[diff_drive_spawner],
        )
    )

    delayed_position_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_broad_spawner,
            on_exit=[position_spawner],
        )
    )

    delayed_velocity_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_broad_spawner,
            on_exit=[velocity_spawner],
        )
    )

    return LaunchDescription([
        controller_manager,
        node_robot_state_publisher,
        delayed_joint_broad_spawner,
        delayed_diff_drive_spawner,
        delayed_position_spawner,
        delayed_velocity_spawner,
    ])
