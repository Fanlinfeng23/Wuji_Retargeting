#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TELEOP_WS="${ROOT_DIR}/official_teleop_ws"
ROS_DISTRO="${ROS_DISTRO:-humble}"
OFFICIAL_SRC="${OFFICIAL_SRC:-${ROOT_DIR}/wuji-hand-teleop/src}"
source "${ROOT_DIR}/scripts/common.bash"

if [ "${WUJI_CLEAN_ENV:-0}" != "1" ]; then
  exec env -i \
    HOME="${HOME}" \
    USER="${USER:-user}" \
    LOGNAME="${LOGNAME:-${USER:-user}}" \
    SHELL=/bin/bash \
    TERM="${TERM:-xterm}" \
    LANG="${LANG:-C.UTF-8}" \
    LC_ALL="${LC_ALL:-C.UTF-8}" \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    ROS_DISTRO="${ROS_DISTRO}" \
    WUJI_CLEAN_ENV=1 \
    bash --noprofile --norc "$0" "$@"
fi

mkdir -p "${TELEOP_WS}/src"
link_pkg() {
  local name="$1"
  local target="$2"
  if [ -L "${TELEOP_WS}/src/${name}" ] || [ ! -e "${TELEOP_WS}/src/${name}" ]; then
    rm -f "${TELEOP_WS}/src/${name}"
    ln -s "${target}" "${TELEOP_WS}/src/${name}"
    return
  fi
  echo "[error] ${TELEOP_WS}/src/${name} exists and is not a symlink" >&2
  exit 1
}

MANUS_SDK_LIB="${OFFICIAL_SRC}/input_devices/manus_input/manus_ros2/ManusSDK/lib/libManusSDK_Integrated.so"
if ! is_real_elf_shared_object "${MANUS_SDK_LIB}"; then
  cat >&2 <<EOF
[error] MANUS SDK library is missing or still a Git LFS pointer:
        ${MANUS_SDK_LIB}

Run one of:
  ./scripts/prepare_manus_sdk.sh
  git lfs install && git lfs pull

The official MANUS ROS2 publisher cannot build until libManusSDK_Integrated.so
is a real ELF shared object.
EOF
  exit 1
fi

link_pkg controller "${OFFICIAL_SRC}/controller"
link_pkg manus_ros2_msgs "${OFFICIAL_SRC}/input_devices/manus_input/manus_ros2_msgs"
link_pkg manus_ros2 "${OFFICIAL_SRC}/input_devices/manus_input/manus_ros2"
link_pkg wuji_teleop_bringup "${OFFICIAL_SRC}/wuji_teleop_bringup"
link_pkg wujihand_output "${OFFICIAL_SRC}/output_devices/wujihand_output"
link_pkg manus_input_py "${OFFICIAL_SRC}/input_devices/manus_input/manus_input_py"
link_pkg tianji_output "${OFFICIAL_SRC}/output_devices/tianji_output"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${ROOT_DIR}/wuji_ros2_ws/install/setup.bash"
export PYTHONPATH="${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
export PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-/usr/bin/python3}"
export Python3_EXECUTABLE="${Python3_EXECUTABLE:-/usr/bin/python3}"

cd "${TELEOP_WS}"
exec colcon build --symlink-install --cmake-args -DPython3_EXECUTABLE="${Python3_EXECUTABLE}"
