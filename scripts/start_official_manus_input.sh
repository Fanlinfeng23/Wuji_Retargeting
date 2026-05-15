#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
MANUS_INPUT_CONFIG="${MANUS_INPUT_CONFIG:-${ROOT_DIR}/config/manus_input_right_only.yaml}"
source "${ROOT_DIR}/scripts/common.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROOT_DIR}/log/ros}"
mkdir -p "${ROS_LOG_DIR}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${ROOT_DIR}/official_teleop_ws/install/setup.bash"

exec ros2 run manus_input_py manus_input --config "${MANUS_INPUT_CONFIG}"
