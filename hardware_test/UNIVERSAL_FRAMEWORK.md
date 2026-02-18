# 通用设备框架

## 概述

让所有调试工具适配任何设备，通过配置文件管理设备差异。

## 快速开始

```bash
# 列出已注册设备
python universal_tool.py --list

# 使用指定设备运行检测
python universal_tool.py --use v5_robot --check

# 添加新设备
python universal_tool.py --add my_robot --port COM10

# 查看设备信息
python universal_tool.py --info v5_robot

# 运行所有工具
python universal_tool.py --use v5_robot --all
```

## 代码使用

```python
from universal_tool import UniversalTool, status, check

# 使用设备
tool = UniversalTool("v5_robot")

# 查看状态
print(status())

# 运行检测
check()
```

## 内置设备模板

| 设备 | 说明 | 默认串口 |
|------|------|----------|
| v5_robot | NCA-Mesh v5 机器人 | COM3 |
| esp32_devkit | ESP32 DevKit | COM4 |
| stm32_nucleo | STM32 Nucleo | COM5 |

## 添加自定义设备

### 方式1: 命令行

```bash
python universal_tool.py --add my_robot --port COM10 --baud 9600
```

### 方式2: 代码

```python
from device_config import register_generic_robot

register_generic_robot(
    name="my_robot",
    serial_port="COM10",
    baud_rate=9600,
    max_current_ma=1500,
    description="我的自定义机器人"
)
```

### 方式3: JSON 文件

创建 `my_robot.json`:

```json
{
    "name": "my_robot",
    "type": "robot",
    "description": "我的机器人",
    "serial_port": "COM10",
    "baud_rate": 9600,
    "max_current_ma": 2000,
    "voltage_range": [3.0, 4.2],
    "temp_limit_c": 80.0,
    "components": [
        {
            "name": "controller",
            "type": "controller",
            "protocol": "uart"
        },
        {
            "name": "imu",
            "type": "imu",
            "protocol": "i2c",
            "address": "0x68"
        }
    ]
}
```

加载:

```python
from device_config import create_device_from_json

adapter = create_device_from_json("my_robot.json")
```

## 设备类型

| 类型 | 说明 |
|------|------|
| robot | 机器人 |
| sensor | 传感器 |
| controller | 控制器 |
| actuator | 执行器 |
| custom | 自定义 |

## 通信协议

| 协议 | 说明 |
|------|------|
| uart | 串口 |
| i2c | I2C |
| spi | SPI |
| can | CAN |
| ble | 蓝牙 |
| wifi | WiFi |

## 工具适配

所有工具会自动适配当前设备：

| 工具 | 自动适配 |
|------|----------|
| wire_check.py | 串口、波特率、组件 |
| vision_inspector.py | 检测目标 |
| ina219_monitor.py | 电流限制 |
| realtime_monitor.py | 监控通道 |

## 文件结构

```
hardware_test/
├── device_config.py        # 设备配置框架
├── universal_tool.py       # 通用工具
└── devices/               # 设备配置文件
    ├── v5_robot.json
    ├── esp32_devkit.json
    └── my_robot.json
```

---

最后更新: 2026-02-18
