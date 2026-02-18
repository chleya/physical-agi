# 串口通信协议定义
# 文件: SERIAL_PROTOCOL.md
# 版本: v1.0
# 日期: 2026-02-18

---

## 概述

本协议定义 STM32 ↔ ESP32 ↔ PC 之间的串口通信格式。

---

## 硬件连接

```
PC (USB) <---> ESP32 (UART1) <---> STM32 (UART3)
                      |
                 USB转TTL (调试)
```

| 连接 | ESP32 UART1 | STM32 UART3 |
|------|-------------|-------------|
| TX | GPIO 17 | PA3 (UART3_RX) |
| RX | GPIO 16 | PA2 (UART3_TX) |
| GND | GND | GND |

---

## 帧格式

### 基本帧结构

```
+------+------+------+-----------+------+------+
| SOF  | LEN  | CMD  | DATA ...  | CRC  | EOF  |
+------+------+------+-----------+------+------+
| 1B   | 1B   | 1B   | N Bytes   | 1B   | 1B   |
+------+------+------+-----------+------+------+
```

| 字段 | 长度 | 说明 |
|------|------|------|
| SOF | 1 | 帧起始标志: `0xAA` |
| LEN | 1 | DATA 长度 (不包含 SOF, LEN, CMD, CRC, EOF) |
| CMD | 1 | 命令码 (见命令表) |
| DATA | N | 数据负载 |
| CRC | 1 | 8位校验和 (从 CMD 开始计算) |
| EOF | 1 | 帧结束标志: `0x55` |

### 校验和计算

```c
uint8_t calc_crc(uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc >> 1) ^ (0x8C if crc & 0x01 else 0);
        }
    }
    return crc;
}
```

---

## 命令表

### STM32 → ESP32 命令

| CMD | 名称 | 方向 | 数据 | 响应 |
|-----|------|------|------|------|
| 0x01 | SELF_TEST | → | 无 | TEST_RESULT |
| 0x02 | GET_STATUS | → | 无 | STATUS |
| 0x03 | START_MOTOR | → | [speed_L(2), speed_R(2)] | ACK |
| 0x04 | STOP_MOTOR | → | 无 | ACK |
| 0x05 | GET_IMU | → | 无 | IMU_DATA |
| 0x10 | RESET | → | 无 | 无 |

### ESP32 → STM32 命令

| CMD | 名称 | 方向 | 数据 | 响应 |
|-----|------|------|------|------|
| 0x80 | ACK | ← | [status(1)] | 无 |
| 0x81 | NACK | ← | [error_code(1)] | 无 |
| 0x82 | TEST_RESULT | ← | [imu(1), motor_l(1), motor_r(1), esp32(1), bat(2), time(2)] | 无 |
| 0x83 | STATUS | ← | [state(1), error(1), uptime(4)] | 无 |
| 0x84 | IMU_DATA | ← | [ax(2), ay(2), az(2), gx(2), gy(2), gz(2)] | 无 |
| 0x90 | CONFIG_WIFI | ← | [ssid_len(1), ssid(N), password_len(1), password(M)] | ACK |
| 0x91 | CONFIG_NCA | ← | [param_id(1), value(4)] | ACK |

### ESP32 ↔ PC 命令

| CMD | 名称 | 方向 | 数据 | 说明 |
|-----|------|------|------|------|
| 0xA0 | VERSION | ↔ | 无 | 获取版本 |
| 0xA1 | PING | ↔ | [timestamp(4)] | 心跳测试 |
| 0xA2 | START_LOG | ↔ | 无 | 开始日志记录 |
| 0xA3 | STOP_LOG | ↔ | 无 | 停止日志记录 |
| 0xA4 | GET_LOG | ↔ | 无 | 获取日志文件 |
| 0xB0 | TEST_RAW | → | [data(N)] | 原始数据测试 |

---

## 数据类型定义

### 基本类型

| 类型 | 大小 | 范围 | 说明 |
|------|------|------|------|
| uint8_t | 1 | 0~255 | 无符号字节 |
| int8_t | 1 | -128~127 | 有符号字节 |
| uint16_t | 2 | 0~65535 | 无符号16位 |
| int16_t | 2 | -32768~32767 | 有符号16位 |
| uint32_t | 4 | 0~4294967295 | 无符号32位 |
| float | 4 | IEEE 754 | 单精度浮点 |

### 复合数据结构

```c
// IMU 数据 (14 bytes)
typedef struct {
    int16_t ax, ay, az;      // 加速度 (mg)
    int16_t gx, gy, gz;      // 陀螺仪 (deg/s)
    int16_t temp;            // 温度 (0.1°C)
} imu_data_t;

// 测试结果 (8 bytes)
typedef struct {
    uint8_t imu:1;           // IMU 状态
    uint8_t motor_l:1;       // 左电机状态
    uint8_t motor_r:1;       // 右电机状态
    uint8_t esp32:1;         // ESP32通信状态
    uint8_t battery:2;       // 电池等级 (0-3)
    uint8_t reserved:2;      // 保留
    uint16_t voltage;        // 电池电压 (mV)
    uint16_t test_time;      // 测试时间 (ms)
} test_result_t;

// 电机速度 (4 bytes)
typedef struct {
    int16_t left;            // 左电机速度 (-1000~1000)
    int16_t right;           // 右电机速度 (-1000~1000)
} motor_speed_t;
```

---

## 通信流程

### 1. 上电自检流程

```
PC              ESP32            STM32
 |                |                |
 |---- PING ----->|                |
 |<--- ACK -------|                |
 |                |                |
 |---- SELF_TEST -------------------->|
 |                |                |
 |                |      <-- TEST_RESULT --+
 |                |                |    |
 |<-------- TEST_RESULT -------------+    |
 |                |                |
```

### 2. 实时数据流

```
PC              ESP32            STM32
 |                |                |
 |---- START_LOG -------------------->|
 |<---- IMU_DATA --------------------|
 |<---- IMU_DATA --------------------|
 |<---- IMU_DATA --------------------|
 |                |                |
 |---- STOP_LOG -------------------->|
```

### 3. 错误响应

```
PC              ESP32            STM32
 |                |                |
 |---- CMD ------>|                |
 |                |---- CMD ------>|
 |                |       <-- NACK --+
 |<---- NACK -----+                |
 |                |                |
```

---

## 错误码定义

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 0x00 | OK | 成功 |
| 0x01 | INVALID_CMD | 无效命令 |
| 0x02 | INVALID_CRC | 校验错误 |
| 0x03 | TIMEOUT | 超时 |
| 0x04 | BUSY | 设备忙 |
| 0x10 | IMU_INIT | IMU初始化失败 |
| 0x11 | IMU_READ | IMU读取失败 |
| 0x20 | MOTOR_STALL | 电机堵转 |
| 0x21 | MOTOR_OVERCURRENT | 电机过流 |
| 0x30 | BAT_LOW | 电池低压 |
| 0x31 | BAT_CRITICAL | 电池严重低压 |
| 0x40 | ESP32_TIMEOUT | ESP32通信超时 |
| 0x41 | ESP32_NOACK | ESP32无响应 |

---

## 示例

### 示例 1: 获取版本

请求: `AA 00 A0 CRC 55`

响应: `AA 08 A0 76 31 2E 30 2E 30 CRC 55`
(版本: "v1.0.0")

### 示例 2: 自检

请求: `AA 00 01 CRC 55`

响应: `AA 08 82 11 01 01 01 01 0D 04 0032 55`
- imu=1, motor_l=1, motor_r=1, esp32=1, battery=1 (正常)
- voltage=3324mV (3.3V)
- test_time=50ms

---

## 实现参考

### Python 实现

```python
import struct
from enum import IntEnum

class SOF(IntEnum):
    START = 0xAA
    END = 0x55

class CMD(IntEnum):
    SELF_TEST = 0x01
    GET_STATUS = 0x02
    START_MOTOR = 0x03
    STOP_MOTOR = 0x04
    GET_IMU = 0x05
    ACK = 0x80
    NACK = 0x81
    TEST_RESULT = 0x82

def make_frame(cmd, data=b''):
    """制作帧"""
    sof = SOF.START
    length = len(data)
    crc = (cmd + sum(data)) & 0xFF  # 简化CRC
    eof = SOF.END
    
    frame = struct.pack('BBB', sof, length, cmd) + data
    frame += struct.pack('BB', crc, eof)
    return frame

def parse_frame(data):
    """解析帧"""
    if len(data) < 4:
        return None
    if data[0] != SOF.START or data[-1] != SOF.END:
        return None
    
    length = data[1]
    cmd = data[2]
    payload = data[3:-2]
    crc = data[-2]
    
    return {'cmd': cmd, 'data': payload, 'crc': crc}
```

### Arduino/ESP32 实现

```cpp
// 发送帧
void sendFrame(uint8_t cmd, uint8_t *data, uint8_t len) {
    uint8_t crc = cmd;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
    }
    
    Serial.write(0xAA);
    Serial.write(len);
    Serial.write(cmd);
    Serial.write(data, len);
    Serial.write(crc);
    Serial.write(0x55);
}

// 接收帧
bool recvFrame(uint8_t *cmd, uint8_t *data, uint8_t *len, int timeout) {
    if (Serial.read() != 0xAA) return false;
    
    *len = Serial.read();
    *cmd = Serial.read();
    
    for (int i = 0; i < *len; i++) {
        data[i] = Serial.read();
    }
    
    uint8_t crc = Serial.read();
    if (Serial.read() != 0x55) return false;
    
    // 验证CRC
    uint8_t calc_crc = *cmd;
    for (int i = 0; i < *len; i++) {
        calc_crc ^= data[i];
    }
    
    return crc == calc_crc;
}
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-18 | 初始版本 |

---

最后更新: 2026-02-18
