# 硬件调试终极工具箱使用说明

## 概述

集成所有硬件调试模块的统一工具箱。

## 模块列表

| 模块 | 文件 | 功能 | 优先级 |
|------|------|------|--------|
| 连线检测 | `wire_check.py` | 通电前检测连线 | P0 |
| 视觉检测 | `vision_inspector.py` | LED/电机状态识别 | P0 |
| 电流监控 | `ina219_monitor.py` | 实时功耗监控 | P0 |
| GDB 调试 | `gdb_controller.py` | 暂停/单步/变量查看 | P0 |
| 无线 OTA | `ota_updater.py` | 远程无线烧录 | P1 |
| 自动回归测试 | `regression_test.py` | CI/CD 自动化 | P1 |
| 多机调试 | `multi_robot_debug.py` | 多机器人协同 | P1 |
| 实时示波器 | `realtime_oscope.py` | 波形显示 | P2 |
| AI 故障预测 | `ai_predictor.py` | 异常检测 | P2 |

## 快速开始

### 方式 1: 终极工具箱

```bash
# 全功能模式
python hardware_toolkit.py --mode all

# 指定模式
python hardware_toolkit.py --mode check   # 连线检测
python hardware_toolkit.py --mode monitor # 实时监控
python hardware_toolkit.py --mode debug   # 调试信息
python hardware_toolkit.py --mode test    # 回归测试
python hardware_toolkit.py --mode analyze # AI 分析
```

### 方式 2: 单独使用

```bash
# 1. 连线检测
python wire_check.py --port COM3 --auto-fix

# 2. 视觉检测
python vision_inspector.py --camera 0

# 3. 电流监控
python ina219_monitor.py

# 4. GDB 调试
python gdb_controller.py --connect

# 5. 无线 OTA
python ota_updater.py --wifi "ssid" --password "pass"

# 6. 回归测试
python regression_test.py --full

# 7. 多机调试
python multi_robot_debug.py --broker localhost

# 8. 实时示波器
python realtime_oscope.py --port COM3

# 9. AI 预测
python ai_predictor.py --predict once
```

## 硬件需求

### 必需
- USB 摄像头 (¥30-100)

### P0 功能需要
- INA219 电流传感器 ($2)
- USB 转串口

### P1 功能需要
- WiFi 网络
- MQTT 服务器

### P2 功能需要
- 无特殊硬件需求

## 目录结构

```
hardware_test/
├── hardware_toolkit.py      # 终极工具箱 (14KB)
├── wire_check.py          # 连线检测 (34KB)
├── vision_inspector.py    # 视觉检测 (19KB)
├── ina219_monitor.py      # 电流监控 (15KB)
├── gdb_controller.py     # GDB 调试 (26KB)
├── ota_updater.py         # 无线 OTA (34KB)
├── regression_test.py     # 自动回归 (21KB)
├── multi_robot_debug.py   # 多机调试 (26KB)
├── realtime_oscope.py     # 实时示波器 (12KB)
├── ai_predictor.py         # AI 预测 (13KB)
└── ...
```

## 配置文件

创建 `config.json`:

```json
{
  "stm32_port": "COM3",
  "esp32_port": "COM4",
  "camera_id": 0,
  "mqtt_broker": "localhost",
  "wifi_ssid": "your_wifi",
  "wifi_password": "your_password"
}
```

## 常见问题

### Q: 模块导入失败

```bash
# 检查依赖
pip install pyserial pandas matplotlib opencv-python numpy paho-mqtt

# 重新导入
python -c "import hardware_toolkit; print('OK')"
```

### Q: 串口无法打开

```bash
# 查看可用端口
python -c "import serial; print(serial.tools.list_ports.comports())"
```

### Q: 摄像头无法打开

```bash
# 查看摄像头ID
python -c "import cv2; [print(f'{i}: OK' if cv2.VideoCapture(i).isOpened() else f'{i}: FAIL') for i in range(5)]"
```

## OpenClaw 集成

```python
from hardware_toolkit import HardwareToolkit, HardwareConfig

# 创建工具箱
config = HardwareConfig(
    stm32_port="COM3",
    camera_id=0
)
toolkit = HardwareToolkit(config)

# 初始化
toolkit.init_all()

# 运行检测
results = toolkit.run_check()
```

## 下一步

1. 安装缺失依赖
2. 连接硬件
3. 运行 `python hardware_toolkit.py --mode all`
4. 根据结果进行调试

---

最后更新: 2026-02-18
