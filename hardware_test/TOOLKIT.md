# 硬件开发工具箱

## 概述

集成了实时监控、视频录制、数据分析、代码热修复建议的完整工具链。

## 工具列表

| 工具 | 文件 | 功能 |
|------|------|------|
| 自动化测试 | `hardware_auto_test.py` | 一键烧录+自检+报告 |
| 实时监控 | `realtime_monitor.py` | 串口数据实时显示+记录 |
| 视频录制 | `video_capture.py` | 摄像头录制+动作检测 |
| 数据分析 | `data_analyzer.py` | 统计+绘图+异常检测 |
| 完整工作流 | `run_full_dev_workflow.bat` | 一键执行所有步骤 |

## 快速开始

### 方式1: 完整工作流 (推荐)

```bash
# 双击或运行
run_full_dev_workflow.bat
```

自动执行：
1. 安装依赖
2. 编译固件
3. 烧录硬件
4. 启动实时监控
5. 启动视频录制
6. 等待30秒
7. 分析数据

### 方式2: 单独使用

```bash
# 1. 自动化测试
python hardware_test/hardware_auto_test.py --id 01

# 2. 实时监控 (新终端)
python hardware_test/realtime_monitor.py --port COM3 --log logs/data.csv

# 3. 视频录制 (新终端)
python hardware_test/video_capture.py --output videos/test.mp4

# 4. 数据分析
python hardware_test/data_analyzer.py logs/data.csv --plot --hotfix
```

## 实时监控

### 基本使用

```bash
python hardware_test/realtime_monitor.py --port COM3
```

### 带绘图

```bash
python hardware_test/realtime_monitor.py --port COM3 --plot
```

### 记录数据

```bash
python hardware_test/realtime_monitor.py --port COM3 --log logs/exp01.csv
```

### 终端显示

```
╔══════════════════════════════════════════════════════════════╗
║                    实时数据监控 - v1.0                       ║
╠══════════════════════════════════════════════════════════════╣
║ 运行时长:   45.2s  |  字节:  12345  |  包:    678        ║
╠══════════════════════════════════════════════════════════════╣
║ IMU (mg)                                                     ║
║   AX:     123   AY:     456   AZ:    1000                   ║
╠══════════════════════════════════════════════════════════════╣
║ 电机                                                          ║
║   左:    500   右:    500                                    ║
╠══════════════════════════════════════════════════════════════╣
║ 电池: 3.85V  |  RSSI:  -65dBm                        ║
╚══════════════════════════════════════════════════════════════╝
```

## 视频录制

### 基本使用

```bash
python hardware_test/video_capture.py --output videos/test01.mp4
```

### 指定摄像头

```bash
python hardware_test/video_capture.py --device 1 --output cam2.mp4
```

### 功能

- 实时录制 (MP4)
- 运动检测 (红色圆点)
- 机器人检测 (绿色圆点)
- ROI框选
- 时间戳标注

### 控制

- `Q` - 退出
- `空格` - 暂停/继续

## 数据分析

### 基本分析

```bash
python hardware_test/data_analyzer.py logs/data.csv
```

### 带图表

```bash
python hardware_test/data_analyzer.py logs/ --plot
```

### 代码热修复建议

```bash
python hardware_test/data_analyzer.py logs/ --hotfix
```

### 输出示例

```
============================================================
分析报告: data_01.csv
============================================================

📊 基本信息:
   时长: 45.2s
   样本数: 1234

📐 IMU统计:
   AX: mean=123.4, std=45.6

⚙️ 电机统计:
   左: mean=500.0, std=10.5
   右: mean=500.0, std=10.2

🔋 电池统计:
   平均: 3.85V
   范围: 3.82V ~ 3.91V
   下降: 0.05V

⚠️ 异常 (2个):
   [medium] imu_spike @ 样本456
   [low] motor_stall @ 样本789

💡 建议:
   • 电池下降较快，考虑降低功耗
```

### 热修复建议输出

```
============================================================
🔧 代码修改建议
============================================================

1. 📁 stm32_motor_control.c (行123)
   问题: 电机输出不平衡
   当前: left=520, right=480
   建议: 添加电机校准系数
   代码:
      // 添加校准系数
      #define MOTOR_LEFT_CALIB  1.05f
      #define MOTOR_RIGHT_CALIB 0.95f
```

## 目录结构

```
hardware_test/
├── hardware_auto_test.py   # 自动化测试
├── realtime_monitor.py     # 实时监控
├── video_capture.py       # 视频录制
├── data_analyzer.py       # 数据分析
├── run_full_dev_workflow.bat  # 完整工作流
│
├── openocd_stm32f4.cfg   # OpenOCD配置
├── stm32_self_test.c      # STM32自检固件
├── SERIAL_PROTOCOL.md     # 通信协议
│
├── logs/                  # 数据日志
├── videos/                # 视频录制
└── plots/                 # 分析图表
```

## 依赖安装

```bash
pip install pyserial pandas matplotlib opencv-python numpy
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    硬件开发工作流                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 编写代码                                                │
│       ↓                                                     │
│  2. 编译固件  (build.bat / make)                           │
│       ↓                                                     │
│  3. 烧录测试  (hardware_auto_test.py)                       │
│       ↓                                                     │
│  4. 实时监控  (realtime_monitor.py)                        │
│       ↓                                                     │
│  5. 视频录制  (video_capture.py)                           │
│       ↓                                                     │
│  6. 数据分析  (data_analyzer.py)                           │
│       ↓                                                     │
│  7. 热修复  (根据分析结果修改代码)                          │
│       ↓                                                     │
│  8. 重复步骤 1-7                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 常见问题

### Q: 串口无法打开

```bash
# 检查端口
python -c "import serial; print(serial.tools.list_ports.comports())"
```

### Q: 摄像头无法打开

```bash
# 检查设备号
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Q: 数据分析报错

```bash
# 检查CSV格式
head -3 logs/data.csv
```

## 扩展开发

### 添加新的数据分析

编辑 `data_analyzer.py`:

```python
@SerialParser.register("NEW[")
def parse_new_data(line: str) -> Dict:
    """解析新数据类型"""
    # 你的解析代码
    return {'type': 'new', 'data': {...}}
```

### 添加新的视频分析

继承 `RobotTracker` 类添加自定义追踪逻辑。

---

最后更新: 2026-02-18
