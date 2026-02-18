# 硬件需求清单

## 视觉检测硬件需求

### 必需硬件

| 设备 | 用途 | 价格 | 备注 |
|------|------|------|------|
| **USB 摄像头** | 视觉检测 | ¥30-100 | 任何标准 USB 摄像头 |
| **现有开发板** | 串口通信 | 已拥有 | STM32 + ESP32 |
| **USB 延长线** | 摄像头布线 | ¥10-20 | 2-3米 |

### 可选硬件

| 设备 | 用途 | 价格 | 备注 |
|------|------|------|------|
| **USB Hub** | 多设备连接 | ¥20-50 | 带供电 |
| **摄像头支架** | 固定视角 | ¥15-30 | 淘宝搜索"摄像头支架" |
| **LED 指示灯** | 状态反馈 | ¥5-10 | 红/绿/黄 |

---

## 技能可用性检查

### 1. OpenCV 可用性

```bash
pip install opencv-python
python -c "import cv2; print(f'OpenCV 版本: {cv2.__version__}')"
```

预期输出: `OpenCV 版本: 4.x.x`

### 2. 摄像头可用性

```bash
python -c "import cv2; cap = cv2.VideoCapture(0); print('摄像头: OK' if cap.isOpened() else '摄像头: FAIL'); cap.release()"
```

### 3. 串口可用性

```bash
pip install pyserial
python -c "import serial; print(serial.tools.list_ports.comports())"
```

---

## 最小配置方案

### 方案 A: 仅串口 (基础版)

```
电脑 ← USB → STM32 ← UART → ESP32
                        ↓
                    电机+IMU
```

功能:
- 连线检测 (wire_check.py) ✅
- 串口监控 ✅
- 数据分析 ✅

**不需要摄像头**

### 方案 B: 串口 + 摄像头 (推荐)

```
电脑 ← USB → STM32 ← UART → ESP32
    ↑                    ↓
  摄像头              电机+IMU
```

功能:
- 所有功能 ✅
- LED 状态检测 ✅
- 电机转动检测 ✅
- 连线可视化 ✅

---

## 推荐配置

```
┌─────────────────────────────────────────┐
│  电脑                                    │
│  ┌──────────┐  ┌──────────┐            │
│  │ 摄像头    │  │  USB口   │            │
│  │ USB摄像头 │←│ STM32   │            │
│  └──────────┘  └────┬─────┘            │
└─────────────────────┼────────────────────┘
                      │
                      ▼
        ┌─────────────────────┐
        │ 电机 + IMU + ESP32  │
        └─────────────────────┘
```

---

## 快速开始指南

### 1. 检查环境

```bash
# 安装依赖
pip install pyserial pandas matplotlib opencv-python numpy

# 检查摄像头
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"

# 检查串口
python -c "import serial; print([p.device for p in serial.tools.list_ports.comports()])"
```

### 2. 测试连线检测

```bash
# 查看连线图
python wire_check.py --diagram

# 连线检测
python wire_check.py --port COM3
```

### 3. 测试视觉检测

```bash
# 交互模式
python vision_inspector.py --camera 0

# OpenClaw 模式
python vision_inspector.py --camera 0 --openclaw-mode
```

---

## 故障排除

### 摄像头无法打开

```bash
# 检查摄像头ID
python -c "import cv2; [print(f'{i}: OK' if cv2.VideoCapture(i).isOpened() else f'{i}: FAIL') for i in range(5)]"
```

### 串口无法识别

```bash
# Windows: 检查设备管理器
# Linux: ls /dev/ttyUSB*
# Mac: ls /dev/cu.*
```

---

最后更新: 2026-02-18
