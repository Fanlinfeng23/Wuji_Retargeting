#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
HAND_NAME="${HAND_NAME:-hand_0}"
HAND_CONFIG="${HAND_CONFIG:-${ROOT_DIR}/config/wujihand_ik_right_hand0.yaml}"
source "${ROOT_DIR}/scripts/common.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export PYTHONPATH="${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROOT_DIR}/log/ros}"
mkdir -p "${ROS_LOG_DIR}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${ROOT_DIR}/wuji_ros2_ws/install/setup.bash"
source_ros_setup "${ROOT_DIR}/official_teleop_ws/install/setup.bash"

exec ros2 run controller wujihand_controller \
  -c "${HAND_CONFIG}" \
  -i manus \
  --right-hand "${HAND_NAME}"
