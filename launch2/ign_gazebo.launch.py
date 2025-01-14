import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_context import LaunchContext
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def launch_setup(context: LaunchContext):

    filename = 'robot.urdf.xacro'
    pkg_name = 'osprey_ros'
    pkg_path = os.path.join(get_package_share_directory(pkg_name))
    slam_params_file = os.path.join(pkg_path, 'config', 'slam_toolbox.yaml')
    world_file = context.perform_substitution(LaunchConfiguration('world')) + '.world'
    year = context.perform_substitution(LaunchConfiguration('year')).title()
    world = os.path.join(pkg_path,'worlds', world_file)
    xacro_file = os.path.join(pkg_path,'description',filename)

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            xacro_file,
            " ",
            "use_hardware:=ign_gazebo",
            " ",
            "year:=",
            year,
        ]
    )
    robot_description = {'robot_description': robot_description_content}

    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
                    launch_arguments={
                        'pause' : 'true',
                        'gz_args' : world,
                    }.items(),
                )

    create_entity = Node(package='ros_gz_sim',
                        executable='create',
                        arguments=['-topic', '/robot_description',
                                    '-entity', 'robot'],
                        output='screen')
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/depth_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ],
    )

    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/depth_camera'],
    )

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    autonomy_spawner = Node(
        package="osprey_ros",
        executable="autonomy_node",
    )

    remapper_spawner = Node(
        package="osprey_ros",
        executable="remapper_node",
    )

    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller", "-c", "/controller_manager"],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
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

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        output='screen',
        parameters=[ slam_params_file, {'use_sim_time': True} ],
        remappings=[('/map', '/slam_toolbox/map'),],
    )

    static_transform_publisher_depth_camera = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments= ["--frame-id", "base_link",
                        "--child-frame-id", "opsrey_ros/base_link/depth_camera"]
    )

    parent = "guide_frame"
    if year == "24":
        parent = "base_link"

    static_transform_publisher_lidar = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments= ["--frame-id", "base_link",
                        "--child-frame-id", "opsrey_ros/" + parent + "/lidar_sensor"]
    )

    static_transform_publisher_odom = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments= ["--frame-id", "base_link",
                        "--child-frame-id", "opsrey_ros/odom"]
    )

    delayed_joint_broad_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[joint_state_broadcaster],
        )
    )

    delayed_static_transform_publisher_depth_camera = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[static_transform_publisher_depth_camera],
        )
    )

    delayed_static_transform_publisher_lidar = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[static_transform_publisher_lidar],
        )
    )

    delayed_static_transform_publisher_odom = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[static_transform_publisher_odom],
        )
    )

    delayed_slam_toolbox_node_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[slam_toolbox_node],
        )
    )

    delayed_autonomy_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[autonomy_spawner],
        )
    )

    delayed_remapper_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=create_entity,
            on_exit=[remapper_spawner],
        )
    )

    delayed_diff_drive_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[diff_drive_spawner],
        )
    )

    delayed_position_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[position_spawner],
        )
    )

    delayed_velocity_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[velocity_spawner],
        )
    )

    nodes = [
        gazebo,
        create_entity,
        bridge,
        image_bridge,
        node_robot_state_publisher,
        delayed_joint_broad_spawner,
        delayed_static_transform_publisher_depth_camera,
        delayed_static_transform_publisher_lidar,
        delayed_static_transform_publisher_odom,
        delayed_slam_toolbox_node_spawner,
        delayed_remapper_spawner,
        delayed_autonomy_spawner,
        delayed_diff_drive_spawner,
        delayed_position_spawner,
    ]

    if year == "":
        nodes += [delayed_velocity_spawner,]


    return nodes

def generate_launch_description():
    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "world",
            default_value="empty",
            description="The world the robot will be spawned within.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "year",
            default_value="",
            description="Year of robot to start",
        )
    )

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
