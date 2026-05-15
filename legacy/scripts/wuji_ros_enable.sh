#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WUJI_WS="${ROOT_DIR}/wuji_ros2_ws"
ROS_DISTRO="${ROS_DISTRO:-humble}"
source "${ROOT_DIR}/scripts/common.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/roslog_wuji_enable}"
mkdir -p "${ROS_LOG_DIR}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${WUJI_WS}/install/setup.bash"

ENABLED="${1:-true}"
exec ros2 service call /"${HAND_NAME:-hand_0}"/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: ${ENABLED}}"
