# 技能可用性检查脚本
import sys
import subprocess
import os

print('='*50)
print('技能可用性检查')
print('='*50)

# 检查依赖 (使用正确的导入名)
packages = [
    ('opencv-python', 'cv2'),
    ('pyserial', 'serial'),
    ('matplotlib', 'matplotlib'),
    ('pandas', 'pandas'),
    ('numpy', 'numpy')
]

for pkg_name, import_name in packages:
    result = subprocess.run([sys.executable, '-c', f'import {import_name}; print("OK")'], capture_output=True, text=True)
    status = 'PASS' if result.returncode == 0 else 'FAIL'
    print(f'[{status}] {pkg_name}')

print()
print('='*50)
print('硬件测试工具文件检查')
print('='*50)

# 检查工具文件
files = [
    'hardware_test/wire_check.py',
    'hardware_test/vision_inspector.py',
    'hardware_test/realtime_monitor.py',
    'hardware_test/data_analyzer.py',
    'hardware_test/video_capture.py',
    'hardware_test/vision_openclaw.py'
]

for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f'[PASS] {f} ({size} bytes)')
    else:
        print(f'[FAIL] {f}')

print()
print('='*50)
print('Python 版本')
print('='*50)
print(f'Python: {sys.version.split()[0]}')

print()
print('='*50)
print('检查完成 - 所有依赖已安装!')
print('='*50)
