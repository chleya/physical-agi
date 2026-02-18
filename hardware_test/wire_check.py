#!/usr/bin/env python3
"""
硬件连线检测器
==============
功能:
- 检测STM32与ESP32连接
- 检测电机驱动连接
- 检测IMU连接
- 检测电源电压
- 生成连线报告

使用:
    python wire_check.py --port COM3
    python wire_check.py --port COM3 --verbose
"""

import serial
import time
import argparse
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class CheckResult(Enum):
    """检测结果"""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARNING = "⚠️ WARN"
    SKIP = "⏭️ SKIP"
    UNKNOWN = "❓ UNKNOWN"


@dataclass
class WireCheck:
    """连线检测项"""
    name: str
    description: str
    check_func: str
    expected: str
    result: CheckResult = CheckResult.UNKNOWN
    message: str = ""


@dataclass
class PinDefinition:
    """引脚定义"""
    name: str
    stm32_pin: str
    esp32_pin: str
    function: str
    voltage: float  # 逻辑电平


# ============ 引脚定义 ============
PIN_DEFINITIONS = {
    # UART 连接 (STM32 ↔ ESP32)
    'uart_stm32_tx': PinDefinition(
        name="STM32 TX → ESP32 RX",
        stm32_pin="PA2 (UART3_TX)",
        esp32_pin="GPIO 16",
        function="UART TX",
        voltage=3.3
    ),
    'uart_stm32_rx': PinDefinition(
        name="STM32 RX ← ESP32 TX",
        stm32_pin="PA3 (UART3_RX)",
        esp32_pin="GPIO 17",
        function="UART RX",
        voltage=3.3
    ),
    
    # ESP32 BOOT模式
    'esp32_boot': PinDefinition(
        name="ESP32 BOOT",
        stm32_pin="PD4",
        esp32_pin="GPIO 0",
        function="Boot Mode",
        voltage=3.3
    ),
    'esp32_reset': PinDefinition(
        name="ESP32 RESET",
        stm32_pin="PD5",
        esp32_pin="EN",
        function="Reset",
        voltage=3.3
    ),
    
    # I2C (IMU)
    'i2c_scl': PinDefinition(
        name="I2C SCL → IMU",
        stm32_pin="PB6 (I2C1_SCL)",
        esp32_pin="N/A",
        function="I2C Clock",
        voltage=3.3
    ),
    'i2c_sda': PinDefinition(
        name="I2C SDA ↔ IMU",
        stm32_pin="PB7 (I2C1_SDA)",
        esp32_pin="N/A",
        function="I2C Data",
        voltage=3.3
    ),
    
    # 电机驱动 (DRV8833)
    'motor_l_in1': PinDefinition(
        name="左电机 IN1",
        stm32_pin="PE0",
        esp32_pin="N/A",
        function="Motor PWM",
        voltage=3.3
    ),
    'motor_l_in2': PinDefinition(
        name="左电机 IN2",
        stm32_pin="PE1",
        esp32_pin="N/A",
        function="Motor PWM",
        voltage=3.3
    ),
    'motor_r_in1': PinDefinition(
        name="右电机 IN1",
        stm32_pin="PE2",
        esp32_pin="N/A",
        function="Motor PWM",
        voltage=3.3
    ),
    'motor_r_in2': PinDefinition(
        name="右电机 IN2",
        stm32_pin="PE3",
        esp32_pin="N/A",
        function="Motor PWM",
        voltage=3.3
    ),
    
    # 电源
    'vcc_3v3': PinDefinition(
        name="3.3V 电源",
        stm32_pin="3.3V",
        esp32_pin="3.3V",
        function="主电源",
        voltage=3.3
    ),
    'gnd': PinDefinition(
        name="GND 地线",
        stm32_pin="GND",
        esp32_pin="GND",
        function="公共地",
        voltage=0
    ),
    'battery': PinDefinition(
        name="电池输入",
        stm32_pin="VBAT",
        esp32_pin="VBAT",
        function="电池供电",
        voltage=3.7  # 3.7V LiPo
    ),
}


# ============ 连线图 ============
WIRING_DIAGRAM = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          硬件连线图 (俯视图)                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║    ┌─────────────────┐          ┌─────────────────┐                          ║
║    │    STM32F4      │          │     ESP32       │                          ║
║    │                 │          │                 │                          ║
║    │  PA2 ──────────┼──────────┤ GPIO 17 (RX)   │                          ║
║    │  PA3 ──────────┼──────────┤ GPIO 16 (TX)   │                          ║
║    │                 │          │                 │                          ║
║    │  PD4 ──────────┼──────────┤ GPIO 0 (BOOT)  │                          ║
║    │  PD5 ──────────┼──────────┤ EN   (RST)     │                          ║
║    │                 │          │                 │                          ║
║    │  PB6 ──────────┼──────────┤ (空)            │                          ║
║    │  PB7 ──────────┼──────────┤ (空)            │                          ║
║    │                 │          │                 │                          ║
║    │  PE0 ─────┐    │          │                 │                          ║
║    │  PE1 ─────┼────┼──────────┤                 │                          ║
║    │  PE2 ─────┼────┤          │                 │                          ║
║    │  PE3 ─────┘    │          │                 │                          ║
║    │                 │          │                 │                          ║
║    │  3.3V ─────────┼──────────┤ 3.3V           │                          ║
║    │  GND  ─────────┼──────────┤ GND            │                          ║
║    │                 │          │                 │                          ║
║    └────────┬────────┘          └────────┬────────┘                          ║
║             │                            │                                   ║
║    ┌────────┴────────┐          ┌────────┴────────┐                          ║
║    │   DRV8833      │          │    MPU6050      │                          ║
║    │                 │          │                 │                          ║
║    │  VMOT ─────────┴── BATTERY                 │                          ║
║    │  GND  ─────────┴── GND                    │                          ║
║    │                 │          │                 │                          ║
║    │  AIN1 ← PE0    │          │  VCC ── 3.3V   │                          ║
║    │  AIN2 ← PE1    │          │  GND ── GND    │                          ║
║    │  BIN1 ← PE2    │          │  SCL ← PB6     │                          ║
║    │  BIN2 ← PE3    │          │  SDA ← PB7     │                          ║
║    │                 │          │                 │                          ║
║    │  AOUT1 → 左电机│          │  AD0 ── GND     │                          ║
║    │  AOUT2 → 左电机│          │                 │                          ║
║    │  BOUT1 → 右电机│          │                 │                          ║
║    │  BOUT2 → 右电机│          │                 │                          ║
║    └─────────────────┘          └─────────────────┘                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

颜色约定:
  红色   = VCC (3.3V / VBAT)
  黑色   = GND
  白色/黄色 = TX/RX (UART)
  蓝色   = I2C (SCL/SDA)
  绿色/橙色 = PWM (电机)
"""


# ============ 连线检测器 ============
class WireChecker:
    """硬件连线检测器"""
    
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.checks: List[WireCheck] = []
        self.stm32_connected = False
        self.esp32_connected = False
    
    def run_all_checks(self, verbose: bool = False) -> Dict:
        """运行所有检测"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'port': self.port,
            'checks': [],
            'summary': {'pass': 0, 'fail': 0, 'warning': 0, 'skip': 0}
        }
        
        print(f"\n{'='*60}")
        print("  🔌 硬件连线检测器 v1.0")
        print(f"{'='*60}\n")
        
        # 1. 检测串口连接
        self._check_serial_connection(verbose)
        
        # 2. 检测STM32通信
        self._check_stm32_connection(verbose)
        
        # 3. 检测ESP32通信
        self._check_esp32_connection(verbose)
        
        # 4. 检测IMU
        self._check_imu(verbose)
        
        # 5. 检测电机驱动
        self._check_motor_driver(verbose)
        
        # 6. 检测电源
        self._check_power(verbose)
        
        # 7. 检测UART连接
        self._check_uart_loopback(verbose)
        
        # 打印结果
        print(f"\n{'='*60}")
        print("  检测结果")
        print(f"{'='*60}\n")
        
        for check in self.checks:
            icon = check.result.value
            print(f"{icon} {check.name}: {check.message}")
            results['checks'].append({
                'name': check.name,
                'result': check.result.value,
                'message': check.message
            })
            results['summary'][self._get_result_type(check.result)] += 1
        
        # 打印总结
        print(f"\n{'='*60}")
        print(f"  总结: {results['summary']['pass']} 通过, "
              f"{results['summary']['fail']} 失败, "
              f"{results['summary']['warning']} 警告")
        print(f"{'='*60}")
        
        return results
    
    def _get_result_type(self, result: CheckResult) -> str:
        """获取结果类型"""
        if result == CheckResult.PASS:
            return 'pass'
        elif result == CheckResult.FAIL:
            return 'fail'
        elif result == CheckResult.WARNING:
            return 'warning'
        else:
            return 'skip'
    
    def _add_check(self, name: str, desc: str, func: str, 
                   expected: str, result: CheckResult, msg: str):
        """添加检测项"""
        self.checks.append(WireCheck(
            name=name, description=desc,
            check_func=func, expected=expected,
            result=result, message=msg
        ))
    
    def _check_serial_connection(self, verbose: bool):
        """检测串口连接"""
        try:
            with serial.Serial(self.port, self.baud, timeout=2) as ser:
                # 尝试读取数据
                time.sleep(0.5)
                if ser.in_waiting > 0:
                    self._add_check(
                        name="串口连接",
                        desc="检测STM32串口是否可访问",
                        func="serial.open()",
                        expected="可读数据",
                        result=CheckResult.PASS,
                        msg=f"串口 {self.port} 可正常访问"
                    )
                else:
                    self._add_check(
                        name="串口连接",
                        desc="检测STM32串口是否可访问",
                        func="serial.open()",
                        expected="可读数据",
                        result=CheckResult.WARNING,
                        msg=f"串口 {self.port} 打开成功，但无数据"
                    )
        except serial.SerialException as e:
            self._add_check(
                name="串口连接",
                desc="检测STM32串口是否可访问",
                func="serial.open()",
                expected="可读数据",
                result=CheckResult.FAIL,
                msg=f"无法打开串口: {e}"
            )
    
    def _check_stm32_connection(self, verbose: bool):
        """检测STM32通信"""
        # 发送版本请求
        response = self._send_command("VERSION")
        
        if "v" in response or "STM32" in response:
            self.stm32_connected = True
            self._add_check(
                name="STM32 通信",
                desc="检测STM32是否响应",
                func="VERSION",
                expected="版本号",
                result=CheckResult.PASS,
                msg=f"STM32 响应: {response[:30]}"
            )
        else:
            self._add_check(
                name="STM32 通信",
                desc="检测STM32是否响应",
                func="VERSION",
                expected="版本号",
                result=CheckResult.FAIL,
                msg="STM32 无响应，请检查:"
                    "\n   - BOOT0 跳帽是否在正确位置"
                    "\n - ST-Link 是否连接"
                    "\n - 串口是否正确"
            )
    
    def _check_esp32_connection(self, verbose: bool):
        """检测ESP32通信"""
        # 通过STM32查询ESP32状态
        response = self._send_command("GET_ESP32_STATUS")
        
        if "ESP32" in response or "OK" in response:
            self.esp32_connected = True
            self._add_check(
                name="ESP32 通信",
                desc="检测ESP32是否正常通信",
                func="GET_ESP32_STATUS",
                expected="ESP32 OK",
                result=CheckResult.PASS,
                msg="ESP32 通信正常"
            )
        else:
            self._add_check(
                name="ESP32 通信",
                desc="检测ESP32是否正常通信",
                func="GET_ESP32_STATUS",
                expected="ESP32 OK",
                result=CheckResult.FAIL,
                msg="ESP32 无响应，请检查:"
                    "\n   - ESP32 是否已烧录固件"
                    "\n - UART 连线是否正确 (TX/RX 交叉)"
                    "\n - GPIO 0 是否拉高"
            )
    
    def _check_imu(self, verbose: bool):
        """检测IMU (MPU6050)"""
        response = self._send_command("GET_IMU_ID")
        
        if "0x68" in response or "104" in response:
            self._add_check(
                name="IMU (MPU6050)",
                desc="检测IMU芯片",
                func="WHO_AM_I",
                expected="0x68 (104)",
                result=CheckResult.PASS,
                msg="MPU6050 检测成功，地址: 0x68"
            )
        elif "FAIL" in response or "0" in response:
            self._add_check(
                name="IMU (MPU6050)",
                desc="检测IMU芯片",
                func="WHO_AM_I",
                expected="0x68 (104)",
                result=CheckResult.FAIL,
                msg="IMU 无响应，请检查:"
                    "\n   - VCC 是否 3.3V"
                    "\n - GND 是否连接"
                    "\n - SCL (PB6) 和 SDA (PB7) 连线"
                    "\n - AD0 是否接地"
            )
        else:
            self._add_check(
                name="IMU (MPU6050)",
                desc="检测IMU芯片",
                func="WHO_AM_I",
                expected="0x68 (104)",
                result=CheckResult.WARNING,
                msg="IMU 响应异常"
            )
    
    def _check_motor_driver(self, verbose: bool):
        """检测电机驱动"""
        # 测试电机
        response = self._send_command("TEST_MOTOR 100 100")
        
        if "OK" in response:
            self._add_check(
                name="电机驱动 (DRV8833)",
                desc="检测电机驱动",
                func="TEST_MOTOR",
                expected="OK",
                result=CheckResult.PASS,
                msg="电机驱动正常"
            )
        else:
            self._add_check(
                name="电机驱动 (DRV8833)",
                desc="检测电机驱动",
                func="TEST_MOTOR",
                expected="OK",
                result=CheckResult.FAIL,
                msg="电机测试失败，请检查:"
                    "\n   - VMOT 是否接电池 (7-12V)"
                    "\n - GND 是否公共地"
                    "\n - IN1/IN2 (PE0/PE1) 和 IN3/IN4 (PE2/PE3)"
                    "\n - 电机是否连接 OUT1-OUT4"
            )
    
    def _check_power(self, verbose: bool):
        """检测电源"""
        response = self._send_command("GET_BATTERY")
        
        if "OK[" in response:
            try:
                # 解析电压
                voltage = float(response.split('=')[1].split(']')[0])
                
                if 3.0 <= voltage <= 4.3:
                    self._add_check(
                        name="电池电压",
                        desc="检测电池电压",
                        func="GET_BATTERY",
                        expected="3.0V - 4.3V",
                        result=CheckResult.PASS,
                        msg=f"电压正常: {voltage:.2f}V"
                    )
                elif voltage < 3.0:
                    self._add_check(
                        name="电池电压",
                        desc="检测电池电压",
                        func="GET_BATTERY",
                        expected="3.0V - 4.3V",
                        result=CheckResult.FAIL,
                        msg=f"电压过低: {voltage:.2f}V，请充电"
                    )
                else:
                    self._add_check(
                        name="电池电压",
                        desc="检测电池电压",
                        func="GET_BATTERY",
                        expected="3.0V - 4.3V",
                        result=CheckResult.WARNING,
                        msg=f"电压异常: {voltage:.2f}V"
                    )
            except:
                self._add_check(
                    name="电池电压",
                    desc="检测电池电压",
                    func="GET_BATTERY",
                    expected="电压值",
                    result=CheckResult.WARNING,
                    msg=f"电压读取失败: {response}"
                )
        else:
            self._add_check(
                name="电池电压",
                desc="检测电池电压",
                func="GET_BATTERY",
                expected="电压值",
                result=CheckResult.FAIL,
                msg="无法读取电压，请检查ADC连接"
            )
    
    def _check_uart_loopback(self, verbose: bool):
        """检测UART回环"""
        # 发送测试数据并检查是否返回
        test_data = "LOOPBACK_TEST"
        response = self._send_command(f"ECHO {test_data}")
        
        if test_data in response:
            self._add_check(
                name="UART 回环测试",
                desc="检测STM32 ↔ ESP32 UART连接",
                func="ECHO",
                expected="回显数据",
                result=CheckResult.PASS,
                msg="UART 通信正常"
            )
        elif self.esp32_connected:
            self._add_check(
                name="UART 回环测试",
                desc="检测STM32 ↔ ESP32 UART连接",
                func="ECHO",
                expected="回显数据",
                result=CheckResult.WARNING,
                msg="回环测试无响应（ESP32可能未实现）"
            )
        else:
            self._add_check(
                name="UART 回环测试",
                desc="检测STM32 ↔ ESP32 UART连接",
                func="ECHO",
                expected="回显数据",
                result=CheckResult.FAIL,
                msg="UART 通信失败，请检查:"
                    "\n   - PA2 ↔ GPIO 17 (TX-RX)"
                    "\n - PA3 ↔ GPIO 16 (RX-TX)"
                    "\n - 注意: UART 是交叉连接的!"
            )
    
    def _send_command(self, cmd: str, timeout: int = 2) -> str:
        """发送命令并获取响应"""
        try:
            with serial.Serial(self.port, self.baud, timeout=timeout) as ser:
                ser.write(f"{cmd}\r\n".encode())
                time.sleep(0.2)
                response = ser.read_all().decode(errors='ignore').strip()
                return response
        except:
            return ""
    
    def print_wiring_diagram(self):
        """打印连线图"""
        print(WIRING_DIAGRAM)
    
    def show_auto_fixes(self):
        """显示自动修复建议"""
        failures = [c for c in self.checks if c.result == CheckResult.FAIL]
        
        if not failures:
            print("\n✅ 没有发现连线错误！")
            return
        
        print(f"\n{'='*60}")
        print("  🔧 自动修复建议")
        print(f"{'='*60}\n")
        
        fix_map = {
            '串口连接': """
╔═══════════════════════════════════════════════════════════════╗
║  串口问题                                                      ║
╠═══════════════════════════════════════════════════════════════╣
║ 1. 检查设备管理器，确认 COM 端口号                            ║
║ 2. 确认 USB 线是数据线，不是充电线                           ║
║ 3. 检查 BOOT0 跳帽位置                                       ║
║ 4. 尝试不同的波特率 (115200, 9600)                          ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            'STM32 通信': """
╔═══════════════════════════════════════════════════════════════╗
║  STM32 无响应                                                  ║
╠═══════════════════════════════════════════════════════════════╣
║ 检查清单:                                                      ║
║ □ BOOT0 跳帽是否在 "Bootloader" 位置                          ║
║ □ ST-Link 或 USB 转串口是否连接                                ║
║ □ 串口 TX/RX 是否接对 (交叉)                                   ║
║ □ 波特率是否正确 (115200)                                     ║
║                                                                ║
║ 解决方法:                                                      ║
║ 1. 重新插拔 USB                                               ║
║ 2. 按复位键                                                   ║
║ 3. 检查固件是否已烧录                                         ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            'ESP32': """
╔═══════════════════════════════════════════════════════════════╗
║  ESP32 无响应                                                  ║
╠═══════════════════════════════════════════════════════════════╣
║ 连线检查:                                                      ║
║ □ PA2 (STM32 TX) → GPIO17 (ESP32 RX) ← 白色线                 ║
║ □ PA3 (STM32 RX) ← GPIO16 (ESP32 TX) ← 黄色线                 ║
║ □ GND 互联                                                    ║
║ □ GPIO0 拉高 (BOOT 模式)                                      ║
║ □ EN (RST) 拉高                                              ║
║                                                                ║
║ 解决方法:                                                      ║
║ 1. 检查 UART 交叉连线                                         ║
║ 2. 确认 ESP32 已烧录固件                                      ║
║ 3. 检查 GPIO0 电平 (上拉 = 3.3V)                             ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            'IMU': """
╔═══════════════════════════════════════════════════════════════╗
║  MPU6050 无响应                                                ║
╠═══════════════════════════════════════════════════════════════╣
║ 连线检查 (I2C):                                                ║
║ □ VCC → 3.3V (红色)                                          ║
║ □ GND → GND (黑色)                                           ║
║ □ SCL → PB6 (蓝色)                                           ║
║ □ SDA → PB7 (绿色)                                           ║
║ □ AD0 → GND (地址 0x68)                                      ║
║                                                                ║
║ 检测方法:                                                      ║
║ 1. 用万用表检查 3.3V 电压                                      ║
║ 2. 确认 I2C 地址正确 (0x68)                                   ║
║ 3. 检查是否有虚焊                                             ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            '电机': """
╔═══════════════════════════════════════════════════════════════╗
║  电机驱动问题                                                   ║
╠═══════════════════════════════════════════════════════════════╣
║ 连线检查 (DRV8833):                                            ║
║ □ VMOT → 电池 7.4V (红+黑)                                    ║
║ □ GND → 公共地 (黑色)                                         ║
║ □ AIN1 → PE0 (绿色)                                           ║
║ □ AIN2 → PE1 (橙色)                                           ║
║ □ BIN1 → PE2 (黄色)                                           ║
║ □ BIN2 → PE3 (棕色)                                           ║
║                                                                ║
║ 安全检查:                                                      ║
║ □ 电机线是否牢固                                               ║
║ □ 电池是否已充电                                               ║
║ □ 不要短路电机输出                                             ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            '电池': """
╔═══════════════════════════════════════════════════════════════╗
║  电池问题                                                      ║
╠═══════════════════════════════════════════════════════════════╣
║ 可能原因:                                                      ║
║ □ 电池未连接                                                   ║
║ □ 电池电压过低 (< 3.0V)                                       ║
║ □ 分压电阻损坏                                                ║
║ □ ADC 引脚错误                                                ║
║                                                                ║
║ 解决方法:                                                      ║
║ 1. 用万用表测量电池电压                                        ║
║ 2. 充满电后重试                                               ║
║ 3. 检查分压电阻 (100K+100K)                                   ║
║ 4. 确认 VBAT 连接正确                                         ║
╚═══════════════════════════════════════════════════════════════╝
            """,
            'UART': """
╔═══════════════════════════════════════════════════════════════╗
║  UART 通信问题                                                 ║
╠═══════════════════════════════════════════════════════════════╣
║ ⚠️  关键: UART 必须交叉连接!                                   ║
║                                                                ║
║    错误 ❌:           正确 ✅:                                ║
║    TX ─── TX           TX ─── RX                             ║
║    RX ─── RX           RX ─── TX                             ║
║                                                                ║
║ 检查:                                                          ║
║ □ STM32 PA2 (TX) → ESP32 GPIO17 (RX) 白色线                   ║
║ □ STM32 PA3 (RX) ← ESP32 GPIO16 (TX) 黄色线                   ║
║ □ GND 共连                                                     ║
╚═══════════════════════════════════════════════════════════════╝
            """,
        }
        
        for check in failures:
            print(f"\n--- {check.name} ---\n")
            
            # 查找匹配的建议
            suggestion = None
            for key, value in fix_map.items():
                if key in check.name:
                    suggestion = value
                    break
            
            if suggestion:
                print(suggestion)
            else:
                print(check.message)


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(
        description="硬件连线检测器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本检测
  python wire_check.py --port COM3
  
  # 详细模式
  python wire_check.py --port COM3 --verbose
  
  # 显示连线图
  python wire_check.py --diagram

注意事项:
  ⚠️ 请在通电前运行此检测工具!
  ⚠️ 确保所有连线正确后再上电!
        """
    )
    
    parser.add_argument('--port', default='COM3', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--diagram', '-d', action='store_true', help='显示连线图')
    parser.add_argument('--auto-fix', '-f', action='store_true', help='显示修复建议')
    args = parser.parse_args()
    
    # 显示连线图
    if args.diagram:
        print(WIRING_DIAGRAM)
        return
    
    # 运行检测
    checker = WireChecker(args.port, args.baud)
    checker.print_wiring_diagram()
    results = checker.run_all_checks(args.verbose)
    
    # 自动修复建议
    if args.auto_fix:
        checker.show_auto_fixes()
    
    # 保存结果
    report_path = f"reports/wire_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("reports").mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
