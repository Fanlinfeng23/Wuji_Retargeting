#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WUJI_WS="${ROOT_DIR}/wuji_ros2_ws"
ROS_DISTRO="${ROS_DISTRO:-humble}"
source "${ROOT_DIR}/scripts/common.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/roslog_wuji_driver}"
mkdir -p "${ROS_LOG_DIR}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${WUJI_WS}/install/setup.bash"

exec ros2 launch wujihand_bringup wujihand.launch.py \
  hand_name:="${HAND_NAME:-hand_0}" \
  publish_rate:="${WUJI_PUBLISH_RATE:-200.0}" \
  diagnostics_rate:="${WUJI_DIAGNOSTICS_RATE:-5.0}"
