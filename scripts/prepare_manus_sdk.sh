#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${ROOT_DIR}/wuji-hand-teleop/src/input_devices/manus_input/manus_ros2/ManusSDK"
LOCAL_SDK_DIR="${LOCAL_MANUS_SDK_DIR:-/home/user/ros2_ws/src/ROS2/ManusSDK}"
source "${ROOT_DIR}/scripts/common.bash"

copy_local_sdk() {
  if [ ! -d "${LOCAL_SDK_DIR}" ]; then
    return 1
  fi
  if ! is_real_elf_shared_object "${LOCAL_SDK_DIR}/lib/libManusSDK_Integrated.so"; then
    return 1
  fi

  mkdir -p "${SDK_DIR}/include" "${SDK_DIR}/lib"
  cp "${LOCAL_SDK_DIR}/include/"*.h "${SDK_DIR}/include/"
  cp "${LOCAL_SDK_DIR}/lib/libManusSDK.so" "${SDK_DIR}/lib/"
  cp "${LOCAL_SDK_DIR}/lib/libManusSDK_Integrated.so" "${SDK_DIR}/lib/"
  chmod 755 "${SDK_DIR}/lib/"*.so
  echo "[ok] copied MANUS SDK from ${LOCAL_SDK_DIR}"
}

pull_lfs() {
  if ! command -v git >/dev/null 2>&1; then
    return 1
  fi
  if ! git lfs version >/dev/null 2>&1; then
    return 1
  fi
  (
    cd "${ROOT_DIR}"
    git lfs install --local
    git lfs pull
  )
}

if is_real_elf_shared_object "${SDK_DIR}/lib/libManusSDK_Integrated.so"; then
  echo "[ok] MANUS SDK library already present"
  exit 0
fi

if copy_local_sdk; then
  exit 0
fi

if pull_lfs && is_real_elf_shared_object "${SDK_DIR}/lib/libManusSDK_Integrated.so"; then
  echo "[ok] MANUS SDK library downloaded with Git LFS"
  exit 0
fi

cat >&2 <<EOF
[error] Could not prepare MANUS SDK libraries.

Required file:
  ${SDK_DIR}/lib/libManusSDK_Integrated.so

Recommended fixes:
  1. Install Git LFS and pull the repository LFS assets:
       sudo apt install git-lfs
       cd ${ROOT_DIR}
       git lfs install
       git lfs pull

  2. Or point to an existing MANUS ROS2 SDK checkout:
       LOCAL_MANUS_SDK_DIR=/path/to/ManusSDK ./scripts/prepare_manus_sdk.sh

The official MANUS publisher cannot build while the .so files are 134-byte
Git LFS pointer files.
EOF
exit 1
