#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
exec /usr/bin/python3 "${ROOT_DIR}/src/check_wuji_motion.py" "$@"
