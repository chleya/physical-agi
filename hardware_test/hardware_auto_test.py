#!/usr/bin/env python3
"""
NCA-Mesh 一键硬件测试框架
==============================
硬件一插上电脑，OpenOCD 直接帮我测试完

功能:
- 自动烧录 (OpenOCD + esptool)
- 硬件自检 (STM32 + ESP32)
- 功能测试序列
- 数据采集与报告生成
- 视频录制 (可选)

使用:
    python hardware_auto_test.py --id 01
    python hardware_auto_test.py --mode full
    python hardware_auto_test.py --batch devices.txt
"""

import subprocess
import serial
import time
import argparse
import os
import sys
import json
import csv
import glob
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# ============ 颜色输出 ============
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(level: str, msg: str):
    """带颜色的日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {
        'INFO': Colors.BLUE,
        'OK': Colors.GREEN,
        'WARN': Colors.WARNING,
        'FAIL': Colors.FAIL,
        'STEP': Colors.CYAN,
    }.get(level, Colors.ENDC)
    
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.ENDC}")

# ============ 配置类 ============
@dataclass
class DeviceConfig:
    """设备配置"""
    device_id: str
    stm32_port: str
    esp32_port: str
    location: str = ""
    openocd_cfg: str = "hardware_test/openocd_stm32f4.cfg"
    esp32_baud: int = 921600

@dataclass
class TestConfig:
    """测试配置"""
    stm32_elf: str = "build/v5_nca_mesh.elf"
    esp32_bin: str = "build/esp32_nca_mesh.bin"
    openocd_path: str = "openocd"
    esptool_path: str = "esptool.py"
    timeout_self_test: int = 30
    timeout_serial: int = 5
    report_dir: str = "reports"
    video_dir: str = "videos"
    log_dir: str = "logs"

@dataclass
class TestResult:
    """测试结果"""
    device_id: str = ""
    timestamp: str = ""
    status: str = "PENDING"  # PENDING, PASS, FAIL, PARTIAL
    
    # 各模块测试结果
    stm32_flash: bool = False
    esp32_flash: bool = False
    imu_test: bool = False
    motor_test: bool = False
    esp32_comm_test: bool = False
    battery_test: bool = False
    nca_test: bool = False
    
    # 详细数据
    imu_data: Dict = field(default_factory=dict)
    motor_data: Dict = field(default_factory=dict)
    battery_voltage: float = 0.0
    test_duration_ms: int = 0
    
    # 日志
    log: str = ""
    error: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'device_id': self.device_id,
            'timestamp': self.timestamp,
            'status': self.status,
            'tests': {
                'stm32_flash': self.stm32_flash,
                'esp32_flash': self.esp32_flash,
                'imu': self.imu_test,
                'motor': self.motor_test,
                'esp32_comm': self.esp32_comm_test,
                'battery': self.battery_test,
                'nca': self.nca_test,
            },
            'data': {
                'imu': self.imu_data,
                'motor': self.motor_data,
                'battery_voltage': self.battery_voltage,
                'duration_ms': self.test_duration_ms,
            },
            'error': self.error,
        }

# ============ 核心测试类 ============
class HardwareTestFramework:
    """
    硬件自动化测试框架
    
    使用方法:
        framework = HardwareTestFramework(config)
        result = framework.run_full_test(device_config)
    """
    
    def __init__(self, test_config: TestConfig):
        self.config = test_config
        self.start_time = None
        
    # ============ 烧录相关 ============
    
    def flash_stm32(self, device: DeviceConfig) -> bool:
        """烧录 STM32 (OpenOCD)"""
        log('INFO', f"🔥 烧录 STM32: {device.stm32_port}")
        
        if not os.path.exists(self.config.stm32_elf):
            log('FAIL', f"STM32 ELF 文件不存在: {self.config.stm32_elf}")
            return False
        
        cmd = [
            self.config.openocd_path,
            "-f", device.openocd_cfg,
            "-c", f"program {self.config.stm32_elf} verify reset exit"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                log('OK', "STM32 烧录成功")
                return True
            else:
                log('FAIL', f"STM32 烧录失败:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            log('FAIL', "STM32 烧录超时")
            return False
        except FileNotFoundError:
            log('FAIL', f"OpenOCD 未找到: {self.config.openocd_path}")
            return False
    
    def flash_esp32(self, device: DeviceConfig) -> bool:
        """烧录 ESP32 (esptool)"""
        log('INFO', f"🔥 烧录 ESP32: {device.esp32_port}")
        
        if not os.path.exists(self.config.esp32_bin):
            log('FAIL', f"ESP32 BIN 文件不存在: {self.config.esp32_bin}")
            return False
        
        cmd = [
            self.config.esptool_path,
            "--port", device.esp32_port,
            "--baud", str(device.esp32_baud),
            "write_flash", "0x0", self.config.esp32_bin
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                log('OK', "ESP32 烧录成功")
                return True
            else:
                log('FAIL', f"ESP32 烧录失败:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            log('FAIL', "ESP32 烧录超时")
            return False
        except FileNotFoundError:
            log('FAIL', f"esptool 未找到: {self.config.esptool_path}")
            return False
    
    # ============ 串口通信 ============
    
    def send_command(self, port: str, cmd: str, timeout: int = 5) -> str:
        """发送命令并读取响应"""
        try:
            with serial.Serial(port, 115200, timeout=timeout) as ser:
                ser.write(f"{cmd}\r\n".encode())
                time.sleep(0.5)
                response = ser.read_all().decode(errors='ignore')
                return response.strip()
        except serial.SerialException as e:
            log('FAIL', f"串口错误: {e}")
            return ""
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应"""
        result = {'raw': response, 'status': None, 'data': {}}
        
        # 格式: OK[data] 或 FAIL[data]
        if response.startswith('OK['):
            result['status'] = 'OK'
            data_str = response[3:-1]
            for item in data_str.split(','):
                if '=' in item:
                    key, value = item.split('=', 1)
                    try:
                        result['data'][key] = float(value)
                    except ValueError:
                        result['data'][key] = value
        elif response.startswith('FAIL['):
            result['status'] = 'FAIL'
            result['error'] = response[5:-1]
        
        return result
    
    # ============ 自检测试 ============
    
    def run_self_test(self, device: DeviceConfig) -> Dict[str, Any]:
        """运行硬件自检"""
        log('STEP', "🧪 运行硬件自检...")
        
        # 等待设备启动
        time.sleep(2)
        
        # 发送自检命令
        response = self.send_command(
            device.stm32_port, 
            "SELF_TEST",
            self.config.timeout_self_test
        )
        
        if not response:
            log('FAIL', "自检无响应")
            return {'success': False, 'error': 'no response'}
        
        result = self.parse_response(response)
        log('OK', f"自检结果: {response}")
        
        return result
    
    def test_imu(self, device: DeviceConfig) -> Dict[str, Any]:
        """测试 IMU"""
        log('STEP', "📐 测试 IMU...")
        
        response = self.send_command(device.stm32_port, "GET_IMU")
        
        if 'OK[' in response:
            log('OK', f"IMU 数据: {response}")
            return {'success': True, 'raw': response}
        else:
            log('WARN', f"IMU 测试失败: {response}")
            return {'success': False, 'raw': response}
    
    def test_motor(self, device: DeviceConfig) -> Dict[str, Any]:
        """测试电机"""
        log('STEP', "⚙️ 测试电机...")
        
        # 启动电机
        response = self.send_command(device.stm32_port, "START_MOTOR 500 500")
        
        if 'OK[' in response:
            time.sleep(1)
            # 停止电机
            self.send_command(device.stm32_port, "STOP_MOTOR")
            log('OK', "电机测试通过")
            return {'success': True}
        else:
            log('FAIL', f"电机测试失败: {response}")
            return {'success': False, 'error': response}
    
    def test_esp32_comm(self, device: DeviceConfig) -> Dict[str, Any]:
        """测试 ESP32 通信"""
        log('STEP', "📡 测试 ESP32 通信...")
        
        response = self.send_command(device.stm32_port, "TEST_ESP32")
        
        if 'OK[' in response:
            log('OK', "ESP32 通信测试通过")
            return {'success': True}
        else:
            log('FAIL', f"ESP32 通信失败: {response}")
            return {'success': False, 'error': response}
    
    def test_battery(self, device: DeviceConfig) -> Dict[str, Any]:
        """测试电池"""
        log('STEP', "🔋 测试电池...")
        
        response = self.send_command(device.stm32_port, "GET_BATTERY")
        
        if 'OK[' in response:
            result = self.parse_response(response)
            voltage = result['data'].get('voltage', 0)
            log('OK', f"电池电压: {voltage}V")
            return {'success': True, 'voltage': voltage}
        else:
            log('WARN', f"电池测试失败: {response}")
            return {'success': False, 'voltage': 0}
    
    # ============ NCA 测试 ============
    
    def test_nca_inference(self, device: DeviceConfig) -> Dict[str, Any]:
        """测试 NCA 推理"""
        log('STEP', "🧠 测试 NCA 推理...")
        
        # 这里可以调用自定义的 NCA 测试脚本
        test_script = "tests/test_nca_on_device.py"
        
        if os.path.exists(test_script):
            try:
                result = subprocess.run(
                    [sys.executable, test_script, "--port", device.stm32_port],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    log('OK', "NCA 测试通过")
                    return {'success': True, 'output': result.stdout}
                else:
                    log('FAIL', f"NCA 测试失败: {result.stderr}")
                    return {'success': False, 'error': result.stderr}
            except Exception as e:
                log('WARN', f"NCA 测试跳过: {e}")
                return {'success': None, 'error': str(e)}
        else:
            log('WARN', "NCA 测试脚本不存在，跳过")
            return {'success': None, 'error': 'script not found'}
    
    # ============ 报告生成 ============
    
    def generate_report(self, device: DeviceConfig, result: TestResult) -> str:
        """生成测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path(self.config.report_dir) / f"device_{device.device_id}_{timestamp}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON 报告
        json_path = report_dir / "report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 保存 CSV 摘要
        csv_path = report_dir / "summary.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['项目', '结果'])
            writer.writerow(['设备ID', result.device_id])
            writer.writerow(['时间戳', result.timestamp])
            writer.writerow(['总体状态', result.status])
            writer.writerow(['', ''])
            writer.writerow(['STM32烧录', '✅ 通过' if result.stm32_flash else '❌ 失败'])
            writer.writerow(['ESP32烧录', '✅ 通过' if result.esp32_flash else '❌ 失败'])
            writer.writerow(['IMU测试', '✅ 通过' if result.imu_test else '❌ 失败'])
            writer.writerow(['电机测试', '✅ 通过' if result.motor_test else '❌ 失败'])
            writer.writerow(['ESP32通信', '✅ 通过' if result.esp32_comm_test else '❌ 失败'])
            writer.writerow(['电池测试', '✅ 通过' if result.battery_test else '❌ 失败'])
            writer.writerow(['NCA推理', '✅ 通过' if result.nca_test else '❌ 失败'])
            writer.writerow(['', ''])
            writer.writerow(['电池电压', f"{result.battery_voltage}V"])
            writer.writerow(['测试时长', f"{result.test_duration_ms}ms"])
        
        # 生成 HTML 报告
        html_path = report_dir / "report.html"
        self._generate_html_report(html_path, device, result)
        
        return str(report_dir)
    
    def _generate_html_report(self, path: Path, device: DeviceConfig, result: TestResult):
        """生成 HTML 报告"""
        status_color = {
            'PASS': '#4CAF50',
            'FAIL': '#F44336',
            'PARTIAL': '#FF9800',
            'PENDING': '#9E9E9E',
        }.get(result.status, '#9E9E9E')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>硬件测试报告 - {device.device_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid {status_color}; padding-bottom: 10px; }}
        .status {{ background: {status_color}; color: white; padding: 10px 20px; border-radius: 4px; font-size: 24px; display: inline-block; margin: 10px 0; }}
        .test-item {{ padding: 10px; margin: 5px 0; background: #f9f9f9; border-left: 4px solid #ddd; }}
        .test-pass {{ border-left-color: #4CAF50; }}
        .test-fail {{ border-left-color: #F44336; }}
        .meta {{ color: #666; font-size: 14px; }}
        .error {{ background: #ffebee; padding: 10px; border-radius: 4px; color: #c62828; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 硬件测试报告</h1>
        <div class="status">{result.status}</div>
        
        <div class="meta">
            <p>设备ID: <strong>{device.device_id}</strong></p>
            <p>位置: {device.location}</p>
            <p>时间: {result.timestamp}</p>
            <p>时长: {result.test_duration_ms}ms</p>
        </div>
        
        <h2>测试结果</h2>
        <div class="test-item {'test-pass' if result.stm32_flash else 'test-fail'}">
            STM32 烧录: {'✅ 通过' if result.stm32_flash else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.esp32_flash else 'test-fail'}">
            ESP32 烧录: {'✅ 通过' if result.esp32_flash else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.imu_test else 'test-fail'}">
            IMU 测试: {'✅ 通过' if result.imu_test else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.motor_test else 'test-fail'}">
            电机测试: {'✅ 通过' if result.motor_test else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.esp32_comm_test else 'test-fail'}">
            ESP32 通信: {'✅ 通过' if result.esp32_comm_test else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.battery_test else 'test-fail'}">
            电池测试: {'✅ 通过' if result.battery_test else '❌ 失败'}
        </div>
        <div class="test-item {'test-pass' if result.nca_test else 'test-fail'}">
            NCA 推理: {'✅ 通过' if result.nca_test else '❌ 失败'}
        </div>
        
        <h2>电池电压</h2>
        <p>{result.battery_voltage}V</p>
        
        {'<div class="error"><h3>错误信息</h3><pre>' + result.error + '</pre></div>' if result.error else ''}
    </div>
</body>
</html>
"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    # ============ 主测试流程 ============
    
    def run_full_test(self, device: DeviceConfig, mode: str = 'full') -> TestResult:
        """
        运行完整测试流程
        
        Args:
            device: 设备配置
            mode: 'full' 或 'quick'
        
        Returns:
            TestResult: 测试结果
        """
        self.start_time = time.time()
        result = TestResult(
            device_id=device.device_id,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        log('INFO', f"{'='*50}")
        log('INFO', f"  设备: {device.device_id} ({device.location})")
        log('INFO', f"{'='*50}")
        
        try:
            # 1. 烧录 STM32
            result.stm32_flash = self.flash_stm32(device)
            if not result.stm32_flash and mode == 'full':
                result.status = 'FAIL'
                return self._finalize(device, result)
            
            # 2. 烧录 ESP32
            result.esp32_flash = self.flash_esp32(device)
            if not result.esp32_flash and mode == 'full':
                result.status = 'FAIL'
                return self._finalize(device, result)
            
            # 3. 等待设备启动
            log('INFO', "⏳ 等待设备启动...")
            time.sleep(2)
            
            # 4. 运行自检
            if mode == 'full':
                self_test = self.run_self_test(device)
                result.imu_test = self_test['data'].get('IMU', 0) == 1
                result.motor_test = self_test['data'].get('MOTOR_L', 0) == 1
                result.esp32_comm_test = self_test['data'].get('ESP32', 0) == 1
                result.battery_voltage = self_test['data'].get('BAT', 0)
                
                # 5. 运行功能测试
                self.test_imu(device)
                self.test_motor(device)
                self.test_esp32_comm(device)
                self.test_battery(device)
                self.test_nca_inference(device)
            
            # 计算总体状态
            result.status = self._calculate_status(result)
            
        except Exception as e:
            log('FAIL', f"测试异常: {e}")
            result.status = 'FAIL'
            result.error = str(e)
        
        return self._finalize(device, result)
    
    def _calculate_status(self, result: TestResult) -> str:
        """计算总体状态"""
        if not result.stm32_flash or not result.esp32_flash:
            return 'FAIL'
        
        tests = [
            result.imu_test,
            result.motor_test,
            result.esp32_comm_test,
            result.battery_test,
            result.nca_test
        ]
        
        passed = sum(1 for t in tests if t is True)
        failed = sum(1 for t in tests if t is False)
        
        if failed > passed:
            return 'FAIL'
        elif failed > 0:
            return 'PARTIAL'
        else:
            return 'PASS'
    
    def _finalize(self, device: DeviceConfig, result: TestResult) -> TestResult:
        """完成测试并生成报告"""
        result.test_duration_ms = int((time.time() - self.start_time) * 1000)
        
        # 生成报告
        report_dir = self.generate_report(device, result)
        
        log('INFO', f"{'='*50}")
        log('INFO', f"  测试完成!")
        log('INFO', f"  状态: {result.status}")
        log('INFO', f"  报告: {report_dir}")
        log('INFO', f"{'='*50}")
        
        return result

# ============ 批量测试 ============

def run_batch_test(device_file: str, config: TestConfig) -> List[TestResult]:
    """运行批量测试"""
    devices = []
    
    # 读取设备列表
    with open(device_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) >= 3:
                devices.append(DeviceConfig(
                    device_id=parts[0],
                    stm32_port=parts[1],
                    esp32_port=parts[2],
                    location=parts[3] if len(parts) > 3 else ""
                ))
    
    results = []
    framework = HardwareTestFramework(config)
    
    for device in devices:
        result = framework.run_full_test(device)
        results.append(result)
        
        # 保存批次报告
        csv_path = Path(config.report_dir) / "batch_summary.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['设备ID', '位置', '状态', 'STM32', 'ESP32', 'IMU', '电机', 'ESP32通信', '电池'])
            for r in results:
                writer.writerow([
                    r.device_id, device.location, r.status,
                    '✅' if r.stm32_flash else '❌',
                    '✅' if r.esp32_flash else '❌',
                    '✅' if r.imu_test else '❌',
                    '✅' if r.motor_test else '❌',
                    '✅' if r.esp32_comm_test else '❌',
                    '✅' if r.battery_test else '❌',
                ])
    
    return results

# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(
        description="NCA-Mesh 一键硬件测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单设备完整测试
  python hardware_auto_test.py --id 01
  
  # 单设备快速测试
  python hardware_auto_test.py --id 01 --mode quick
  
  # 批量测试
  python hardware_auto_test.py --batch devices.txt
  
  # 指定端口
  python hardware_auto_test.py --stm32_port COM3 --esp32_port COM4
        """
    )
    
    # 设备参数
    parser.add_argument('--id', default='01', help='设备ID')
    parser.add_argument('--stm32_port', default='COM3', help='STM32 串口')
    parser.add_argument('--esp32_port', default='COM4', help='ESP32 串口')
    parser.add_argument('--location', default='', help='设备位置')
    
    # 模式选择
    parser.add_argument('--mode', choices=['full', 'quick'], default='full',
                       help='测试模式 (默认: full)')
    parser.add_argument('--batch', help='批量测试设备列表文件')
    
    # 路径配置
    parser.add_argument('--stm32_elf', default='build/v5_nca_mesh.elf',
                       help='STM32 ELF 文件路径')
    parser.add_argument('--esp32_bin', default='build/esp32_nca_mesh.bin',
                       help='ESP32 BIN 文件路径')
    parser.add_argument('--report_dir', default='reports',
                       help='报告目录')
    
    args = parser.parse_args()
    
    # 创建配置
    test_config = TestConfig(
        stm32_elf=args.stm32_elf,
        esp32_bin=args.esp32_bin,
        report_dir=args.report_dir
    )
    
    framework = HardwareTestFramework(test_config)
    
    if args.batch:
        # 批量测试
        results = run_batch_test(args.batch, test_config)
        log('INFO', f"批量测试完成: {len(results)} 台设备")
    else:
        # 单设备测试
        device = DeviceConfig(
            device_id=args.id,
            stm32_port=args.stm32_port,
            esp32_port=args.esp32_port,
            location=args.location
        )
        result = framework.run_full_test(device, args.mode)
        
        if result.status == 'PASS':
            log('OK', "🎉 所有测试通过!")
            sys.exit(0)
        elif result.status == 'PARTIAL':
            log('WARN', "⚠️ 部分测试失败，请查看报告")
            sys.exit(1)
        else:
            log('FAIL', "❌ 测试失败")
            sys.exit(1)

if __name__ == "__main__":
    main()
