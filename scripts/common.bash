#!/usr/bin/env bash

source_ros_setup() {
  local setup_file="$1"
  if [ ! -f "${setup_file}" ]; then
    echo "[error] ROS setup file not found: ${setup_file}" >&2
    return 1
  fi
  set +u
  source "${setup_file}"
  set -u
}

is_real_elf_shared_object() {
  local lib_file="$1"
  [ -f "${lib_file}" ] && file "${lib_file}" | grep -q "ELF .* shared object"
}
