# Release Checklist

Run before publishing:

```bash
cd ~/ros2_ws/wuji_retargeting

bash -n scripts/*.sh
/usr/bin/python3 -m py_compile \
  launch/manus_wuji_right.launch.py \
  src/*.py \
  wuji-hand-teleop/src/controller/controller/*.py \
  wuji-hand-teleop/src/input_devices/manus_input/manus_input_py/manus_input_py/*.py \
  wuji-hand-teleop/src/output_devices/wujihand_output/wujihand_output/*.py

./scripts/prepare_manus_sdk.sh
./scripts/check_environment.sh
./scripts/build_wuji_ros2_driver.sh
./scripts/build_official_teleop.sh
./scripts/check_official_chain.sh
```

Hardware checks:

```bash
./scripts/check_devices.sh
./scripts/check_wuji_sdk.sh
./scripts/check_wuji_motion.sh --finger 1 --joint 0 --delta 0.08 --hold 0.8
timeout 12s ./scripts/start_official_manus_wuji.sh
```

Expected official launch signs:

```text
Connected to WujiHand (right)
WujiHand driver started
Right hand connected (via wujihandros2)
```

Before committing, make sure generated files are ignored or removed:

```text
log/
official_teleop_ws/build/
official_teleop_ws/install/
official_teleop_ws/log/
official_teleop_ws/src/
wuji_ros2_ws/build/
wuji_ros2_ws/install/
wuji_ros2_ws/log/
wuji_ros2_ws/src/
__pycache__/
*.pyc
log.txt
```

Also verify the official teleop source is vendored as normal files:

```bash
test ! -d wuji-hand-teleop/.git
test ! -d third_party/wuji-hand-teleop-src
```

If publishing to GitHub with MANUS SDK libraries included, enable Git LFS before
the first commit:

```bash
git lfs install
git lfs track "*.so"
git add .gitattributes wuji-hand-teleop/.gitattributes
```
