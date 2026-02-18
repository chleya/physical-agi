# 烧录工具使用说明

## 快速开始

### 交互模式

```bash
python flash_tool.py
```

### 命令行模式

```bash
# 烧录全部
python flash_tool.py --auto

# 仅烧录 STM32
python flash_tool.py --target stm32

# 仅烧录 ESP32
python flash_tool.py --target esp32

# 指定设备
python flash_tool.py --device my_robot --auto
```

## 功能说明

### 交互模式菜单

```
1. 烧录全部 (STM32 + ESP32)
2. 仅烧录 STM32
3. 仅烧录 ESP32
4. 仅构建
5. 仅验证
6. 硬件测试
7. 查看设备
8. 添加设备
9. 运行全部工具
0. 退出
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| --auto | 全自动模式 |
| --device | 设备名称 |
| --target | 烧录目标 (all/stm32/esp32) |
| --verify | 仅验证 |
| --skip-test | 跳过硬件测试 |
| --stm32-port | STM32 串口 |
| --esp32-port | ESP32 串口 |

## 设备配置

### 使用已注册设备

```python
from flash_tool import FlashTool, FlashConfig

config = FlashConfig(device="v5_robot")
tool = FlashTool(config)
result = tool.run()
```

### 添加新设备

```python
from device_config import register_generic_robot

register_generic_robot(
    name="my_robot",
    serial_port="COM10",
    baud_rate=115200
)
```

## 报告输出

烧录完成后会生成报告文件:

```
reports/flash_20260218_153045.json
```

报告内容:

```json
{
  "timestamp": "2026-02-18T15:30:45",
  "device": "v5_robot",
  "target": "all",
  "success": true,
  "duration_ms": 45230,
  "steps": {
    "build": true,
    "stm32": true,
    "esp32": true,
    "test": true
  },
  "errors": [],
  "warnings": []
}
```

## 硬件测试

烧录完成后会自动进行硬件测试:

1. **串口通信测试**
   - 发送 VERSION 命令
   - 验证响应

2. **设备响应测试**
   - 等待设备启动
   - 读取响应数据

## 故障排除

### 烧录失败

```bash
# 检查串口
python -c "import serial; print(serial.tools.list_ports.comports())"

# 检查 OpenOCD
openocd --version

# 检查 esptool
esptool.py version
```

### Keil 支持

工具支持使用 Keil MDK 构建 STM32 项目:

```bash
# 自动检测 Keil 项目 (*.uvproj, *.uvprojx)
# 如果找到会自动使用

# 手动指定
python flash_tool.py --build keil
```

**注意:** 需要安装 Keil MDK Community Edition (免费)

下载: https://www.keil.com/download/

### STM32 烧录失败

1. 检查 BOOT0 跳帽位置
2. 检查 ST-Link 连接
3. 验证 ELF 文件存在

### ESP32 烧录失败

1. 检查串口连接
2. 检查波特率
3. 验证 BIN 文件存在

## 与其他工具集成

```python
# 烧录 + 监控
from flash_tool import FlashTool
from realtime_monitor import RealtimeMonitor

# 烧录
tool = FlashTool()
result = tool.run()

if result.success:
    # 启动监控
    monitor = RealtimeMonitor(port="COM3")
    monitor.start()
```

---

最后更新: 2026-02-18
