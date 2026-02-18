# 硬件参数导出使用说明

## 概述

将演化训练的NCA网络参数导出为ESP32固件格式。

## 文件清单

```
hardware_export/
├── nca_params.h      # 网络参数头文件（最重要）
├── nca_agent.c      # ESP32 NCA实现
├── platformio.ini   # PlatformIO配置
├── robot_sketch.ino # Arduino草图
└── test_hardware.c  # 硬件测试套件
```

## 使用方法

### 1. 运行导出
```bash
python hardware_export.py [checkpoint.json] [output_dir]
```

### 2. 编译到ESP32

#### PlatformIO方式
```bash
cd hardware_export
pio run -e esp32dev -t upload
```

#### Arduino方式
1. 打开 `robot_sketch.ino`
2. 选择工具 → ESP32 Dev Module
3. 上传

## 硬件接口

### 引脚定义
| 功能 | 引脚 |
|------|------|
| 左电机A | GPIO12 |
| 左电机B | GPIO13 |
| 右电机A | GPIO14 |
| 右电机B | GPIO15 |
| 超声波TRIG | GPIO5 |
| 超声波ECHO | GPIO18 |

### 网络输入格式 (6维)
```
[position_x, position_y, target_x, target_y, neighbor_count, avg_rssi]
```

### 网络输出格式 (2维)
```
[dx, dy]  # 移动方向
```

## 测试

```bash
# 编译测试
gcc -o test test_hardware.c -lm
./test

# 预期输出
Running hardware tests...
Activation test: PASSED
Forward pass test: PASSED
RSSI test: PASSED
Motor output test: PASSED
All tests PASSED!
```

## 下一步

1. **刷写到v5底盘**
2. **ESP-NOW通信测试**
3. **真实环境验证**

## 已知问题

- 偏差值(b1, b2)未正确保存（需要修复导出脚本）
- 需手动调整引脚定义
