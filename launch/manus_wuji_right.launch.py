"""Right-hand Manus -> Wuji launch wrapper around Wuji's official nodes."""

from __future__ import annotations

from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import LaunchConfigurationEquals
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from wuji_teleop_bringup.hand_defaults import (
    DRIVER_DIAGNOSTICS_RATE,
    DRIVER_FILTER_CUTOFF_FREQ,
    DRIVER_PUBLISH_RATE,
)


def _default_config(path: str) -> str:
    root = Path(__file__).resolve().parents[1]
    return str(root / path)


def generate_launch_description() -> LaunchDescription:
    hand_input_arg = DeclareLaunchArgument("hand_input", default_value="manus")
    hand_config_arg = DeclareLaunchArgument(
        "hand_config",
        default_value=_default_config("config/wujihand_ik_right_hand0.yaml"),
    )
    manus_config_arg = DeclareLaunchArgument(
        "manus_config",
        default_value=_default_config("config/manus_input_right_only.yaml"),
    )
    right_serial_arg = DeclareLaunchArgument("right_serial", default_value="")
    right_hand_name_arg = DeclareLaunchArgument("right_hand_name", default_value="hand_0")

    hand_input = LaunchConfiguration("hand_input")
    hand_config = LaunchConfiguration("hand_config")
    manus_config = LaunchConfiguration("manus_config")
    right_hand_name = LaunchConfiguration("right_hand_name")
    right_serial = ParameterValue(LaunchConfiguration("right_serial"), value_type=str)

    return LaunchDescription([
        hand_input_arg,
        hand_config_arg,
        manus_config_arg,
        right_serial_arg,
        right_hand_name_arg,

        Node(
            package="wujihand_driver",
            executable="wujihand_driver_node",
            name="wujihand_driver",
            namespace=right_hand_name,
            parameters=[{
                "serial_number": right_serial,
                "publish_rate": DRIVER_PUBLISH_RATE,
                "filter_cutoff_freq": DRIVER_FILTER_CUTOFF_FREQ,
                "diagnostics_rate": DRIVER_DIAGNOSTICS_RATE,
            }],
            output="screen",
            emulate_tty=True,
        ),
        Node(
            package="manus_ros2",
            executable="manus_data_publisher",
            name="manus_data_publisher",
            output="screen",
            emulate_tty=True,
            condition=LaunchConfigurationEquals("hand_input", "manus"),
        ),
        Node(
            package="manus_input_py",
            executable="manus_input",
            name="manus_input",
            output="screen",
            emulate_tty=True,
            arguments=["--config", manus_config],
            condition=LaunchConfigurationEquals("hand_input", "manus"),
        ),
        Node(
            package="controller",
            executable="wujihand_controller",
            name="wujihand_controller",
            output="screen",
            emulate_tty=True,
            arguments=[
                "-c", hand_config,
                "-i", hand_input,
                "--right-hand", right_hand_name,
            ],
        ),
    ])
