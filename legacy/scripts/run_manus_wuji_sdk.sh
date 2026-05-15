#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
MANUS_WS="${MANUS_WS:-/home/user/ros2_ws}"
source "${ROOT_DIR}/scripts/common.bash"

export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/roslog_manus_wuji_sdk}"
mkdir -p "${ROS_LOG_DIR}"

GLOVE_ID="${GLOVE_ID:-0}"
HAND="${HAND:-right}"
SOURCE="${SOURCE:-manus-glove}"
INPUT_TOPIC="${INPUT_TOPIC:-}"
PRINT_EVERY="${PRINT_EVERY:-30}"
MAX_RUNTIME_S="${MAX_RUNTIME_S:-0}"
SDK_BLEND="${SDK_BLEND:-1.0}"
SDK_CUTOFF_HZ="${SDK_CUTOFF_HZ:-10.0}"
REQUIRE_SIDE="${REQUIRE_SIDE:-0}"
MANUS_BEST_EFFORT="${MANUS_BEST_EFFORT:-1}"
LOG_COST="${LOG_COST:-0}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${MANUS_WS}/install/setup.bash"

ARGS=(
  --input ros
  --ros-source "${SOURCE}"
  --glove-id "${GLOVE_ID}"
  --hand "${HAND}"
  --output-mode sdk
  --print-every "${PRINT_EVERY}"
  --max-runtime-s "${MAX_RUNTIME_S}"
  --sdk-command-blend "${SDK_BLEND}"
  --sdk-cutoff-hz "${SDK_CUTOFF_HZ}"
)

if [ -n "${INPUT_TOPIC}" ]; then
  ARGS+=(--ros-input-topic "${INPUT_TOPIC}")
fi
if [ "${REQUIRE_SIDE}" = "1" ]; then
  ARGS+=(--require-side)
fi
if [ "${MANUS_BEST_EFFORT}" != "1" ]; then
  ARGS+=(--no-manus-best-effort)
fi
if [ "${LOG_COST}" = "1" ]; then
  ARGS+=(--log-cost)
fi

exec /usr/bin/python3 "${ROOT_DIR}/src/manus_wuji_retarget.py" "${ARGS[@]}"
