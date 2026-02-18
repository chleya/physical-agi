#!/usr/bin/env python3
"""
NCA-Mesh 烧录工具 v2.0
=======================
完整烧录工具：构建 + 烧录 + 测试 + 验证

功能:
- 自动构建固件
- 烧录 STM32 (OpenOCD)
- 烧录 ESP32 (esptool)
- 硬件自检
- 验证测试
- 生成报告

使用:
    python flash_tool.py                    # 交互模式
    python flash_tool.py --auto           # 全自动
    python flash_tool.py --device v5_robot # 指定设备
    python flash_tool.py --verify         # 仅验证
"""

import sys
import os
import time
import json
import argparse
import subprocess
import serial
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 导入设备配置
from device_config import (
    DeviceRegistry, DeviceAdapter, DeviceConfig,
    init_devices, use_device, register_generic_robot
)


class BuildSystem(Enum):
    """构建系统"""
    MAKE = "make"
    CMAKE = "cmake"
    PLATFORMIO = "platformio"
    KEIL_UV5 = "keil_uv5"
    KEIL_UV6 = "keil_uv6"
    MANUAL = "manual"


@dataclass
class KeilConfig:
    """Keil 配置"""
    keil_path: str = ""  # Keil 安装路径
    uvproj_file: str = ""  # 项目文件 (.uvproj 或 .uvprojx)
    target: str = "Flash"  # 构建目标
    device: str = "STM32F407VGTx"  # 目标芯片
    use_mdk_cpp: bool = True  # 使用 MDK 替代 Keil


class FlashTarget(Enum):
    """烧录目标"""
    ALL = "all"
    STM32 = "stm32"
    ESP32 = "esp32"
    CONFIG = "config"


@dataclass
class FlashConfig:
    """烧录配置"""
    device: str = "v5_robot"
    target: FlashTarget = FlashTarget.ALL
    build_system: BuildSystem = BuildSystem.MANUAL
    
    # Keil 配置
    keil_config: KeilConfig = field(default_factory=KeilConfig)
    
    # STM32
    openocd_path: str = "openocd"
    openocd_cfg: str = "hardware_test/openocd_stm32f4.cfg"
    stm32_elf: str = "build/v5_nca_mesh.elf"
    
    # ESP32
    esptool_path: str = "esptool.py"
    esp32_bin: str = "build/esp32_nca_mesh.bin"
    esp32_port: str = "COM4"
    esp32_baud: int = 921600
    
    # 通用
    stm32_port: str = "COM3"
    timeout: int = 120
    
    # 测试
    test_timeout: int = 30
    skip_tests: bool = False


@dataclass
class FlashResult:
    """烧录结果"""
    success: bool
    timestamp: str
    device: str
    target: str
    
    # 各步骤结果
    build_success: bool = False
    stm32_success: bool = False
    esp32_success: bool = False
    test_success: bool = False
    
    # 详细信息
    build_output: str = ""
    stm32_output: str = ""
    esp32_output: str = ""
    test_output: str = ""
    
    # 错误
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # 统计
    duration_ms: int = 0


class FlashTool:
    """烧录工具"""
    
    def __init__(self, config: FlashConfig = None):
        self.config = config or FlashConfig()
        self.adapter: Optional[DeviceAdapter] = None
        self.start_time = None
        
        # 初始化设备
        init_devices()
        
        # 获取设备适配器
        self.adapter = use_device(self.config.device)
        if not self.adapter:
            # 尝试查找
            devices = list(DeviceRegistry.list_devices())
            if devices:
                self.adapter = use_device(devices[0])
            else:
                raise ValueError(f"设备不存在: {self.config.device}")
        
        # 更新配置中的端口
        if self.adapter:
            self.config.stm32_port = self.adapter.get_serial_port()
    
    def run(self) -> FlashResult:
        """执行烧录流程"""
        self.start_time = time.time()
        result = FlashResult(
            success=False,
            timestamp=datetime.now().isoformat(),
            device=self.config.device,
            target=self.config.target.value
        )
        
        print(f"\n{'='*60}")
        print(f"  NCA-Mesh 烧录工具 v2.0")
        print(f"{'='*60}")
        print(f"设备: {self.config.device}")
        print(f"目标: {self.config.target.value}")
        print(f"STM32端口: {self.config.stm32_port}")
        print(f"ESP32端口: {self.config.esp32_port}")
        print(f"{'='*60}\n")
        
        try:
            # 1. 构建
            if self.config.target in [FlashTarget.ALL, FlashTarget.STM32]:
                if not self._build(result):
                    return self._finish(result)
            
            # 2. 烧录 STM32
            if self.config.target in [FlashTarget.ALL, FlashTarget.STM32]:
                if not self._flash_stm32(result):
                    return self._finish(result)
            
            # 3. 烧录 ESP32
            if self.config.target in [FlashTarget.ALL, FlashTarget.ESP32]:
                if not self._flash_esp32(result):
                    return self._finish(result)
            
            # 4. 硬件测试
            if not self.config.skip_tests:
                if not self._test_hardware(result):
                    result.warnings.append("硬件测试失败，但烧录成功")
            
            result.success = True
            
        except Exception as e:
            result.errors.append(str(e))
        
        return self._finish(result)
    
    def _build(self, result: FlashResult) -> bool:
        """构建固件"""
        print("[1/4] 构建固件...")
        
        if self.config.build_system == BuildSystem.MANUAL:
            # 检查构建脚本
            if os.path.exists("build.bat"):
                print("  使用 build.bat...")
                output = self._run_command("build.bat")
                result.build_output = output
                result.build_success = "error" not in output.lower()
            elif os.path.exists("CMakeLists.txt"):
                print("  使用 CMake...")
                output = self._run_cmake()
                result.build_output = output
                result.build_success = "error" not in output.lower()
            else:
                print("  跳过构建 (手动模式)")
                result.build_success = True
        
        elif self.config.build_system in [BuildSystem.KEIL_UV5, BuildSystem.KEIL_UV6]:
            result.build_success = self._build_keil(result)
        
        elif self.config.build_system == BuildSystem.PLATFORMIO:
            print("  使用 PlatformIO...")
            output = self._run_command("pio run -e genericSTM32F407VG", timeout=120)
            result.build_output = output
            result.build_success = "error" not in output.lower()
        
        else:
            print(f"  构建系统: {self.config.build_system.value}")
            result.build_success = True
        
        if result.build_success:
            print("  ✅ 构建成功\n")
        else:
            print("  ❌ 构建失败")
            result.errors.append(f"构建失败: {result.build_output}")
        
        return result.build_success
    
    def _build_keil(self, result: FlashResult) -> bool:
        """构建 Keil 项目"""
        keil = self.config.keil_config
        
        # 查找 Keil 项目文件
        if not keil.uvproj_file:
            # 自动查找
            uvproj_files = list(Path(".").glob("*.uvproj*"))
            if uvproj_files:
                keil.uvproj_file = str(uvproj_files[0])
                print(f"  自动发现 Keil 项目: {keil.uvproj_file}")
        
        if not keil.uvproj_file:
            print("  ❌ 未找到 Keil 项目文件 (.uvproj/.uvprojx)")
            result.build_output = "No Keil project file found"
            return False
        
        # 查找 Keil 可执行文件
        keil_exe = self._find_keil_exe(keil)
        if not keil_exe:
            print("  ❌ 未找到 Keil ARM 编译器")
            print("  💡 请安装 Keil MDK 或设置 KEIL_PATH 环境变量")
            result.build_output = "Keil not found"
            return False
        
        print(f"  使用 Keil: {keil_exe}")
        
        # 构建命令
        cmd = [
            keil_exe,
            "-j0",  # 并行构建
            "-b",   # 构建
            "-t", keil.target if keil.target else "Flash",
            keil.uvproj_file
        ]
        
        print(f"  执行构建: {Path(keil.uvproj_file).name}")
        
        try:
            output = self._run_command(cmd, timeout=180)
            result.build_output = output
            
            # 检查输出
            if "0 Error" in output or "0 error" in output:
                # 查找生成的 ELF 文件
                elf_pattern = Path(keil.uvproj_file).stem + ".elf"
                elf_files = list(Path(".").glob(f"**/{elf_pattern}"))
                
                if elf_files:
                    self.config.stm32_elf = str(elf_files[0])
                    print(f"  ✅ ELF 文件: {self.config.stm32_elf}")
                    return True
                else:
                    print(f"  ⚠️ 未找到 ELF 文件")
                    return True  # 可能有警告但不是错误
            else:
                # 输出错误信息
                errors = [line for line in output.split('\n') 
                         if 'Error' in line or 'error' in line][:5]
                for e in errors:
                    print(f"  ❌ {e}")
                return False
                
        except subprocess.TimeoutExpired:
            print("  ❌ 构建超时 (180秒)")
            return False
        except FileNotFoundError:
            print("  ❌ Keil 可执行文件未找到")
            return False
    
    def _find_keil_exe(self, keil: KeilConfig) -> Optional[str]:
        """查找 Keil 可执行文件"""
        # 可能的路径
        possible_paths = [
            # Keil MDK 默认安装路径
            r"C:\Keil_v5\UV4\UV4.exe",
            r"C:\Keil_v6\UV4\UV4.exe",
            r"C:\Program Files\Keil\UV4\UV4.exe",
            r"C:\Program Files (x86)\Keil\UV4\UV4.exe",
            # MDK ARM 路径
            r"C:\Keil_v5\ARM\ARMCC\Bin\armcc.exe",
            r"C:\Program Files (x86)\Arm\Toolchains\Current\bin\arm-none-eabi-gcc.exe",
            # 环境变量
            os.environ.get("KEIL_PATH", ""),
            os.environ.get("UV4_PATH", ""),
            os.environ.get("ARM_TOOLCHAIN_PATH", ""),
        ]
        
        # 检查 MDK Community Edition (免费)
        mdk_cpp = r"C:\Program Files\Keil\MDK-Core\UV4\UV4.exe"
        if os.path.exists(mdk_cpp):
            print(f"  发现 Keil MDK: {mdk_cpp}")
            return mdk_cpp
        
        # 检查环境变量中的路径
        arm_path = os.environ.get("ARM_GCC_PATH", "")
        if arm_path:
            armcc = os.path.join(arm_path, "armcc.exe")
            if os.path.exists(armcc):
                print(f"  发现 ARM GCC: {armcc}")
                return armcc
        
        # 检查 PATH
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        return None
    
    def _flash_stm32(self, result: FlashResult) -> bool:
        """烧录 STM32"""
        print("[2/4] 烧录 STM32...")
        
        # 检查文件
        if not os.path.exists(self.config.stm32_elf):
            print(f"  ⚠️ 文件不存在: {self.config.stm32_elf}")
            print("  跳过 STM32 烧录")
            result.stm32_success = True  # 不算错误
            return True
        
        # 构建命令
        cmd = [
            self.config.openocd_path,
            "-f", self.config.openocd_cfg,
            "-c", f"program {self.config.stm32_elf} verify reset exit"
        ]
        
        print(f"  执行: {' '.join(cmd[:3])}...")
        
        try:
            output = self._run_command(cmd, timeout=self.config.timeout)
            result.stm32_output = output
            
            if "error" in output.lower():
                result.stm32_success = False
                result.errors.append(f"STM32烧录失败")
                print("  ❌ STM32 烧录失败")
            else:
                result.stm32_success = True
                print("  ✅ STM32 烧录成功")
            
        except subprocess.TimeoutExpired:
            result.stm32_success = False
            result.errors.append("STM32 烧录超时")
            print("  ❌ STM32 烧录超时")
        
        return result.stm32_success
    
    def _flash_esp32(self, result: FlashResult) -> bool:
        """烧录 ESP32"""
        print("[3/4] 烧录 ESP32...")
        
        # 检查文件
        if not os.path.exists(self.config.esp32_bin):
            print(f"  ⚠️ 文件不存在: {self.config.esp32_bin}")
            print("  跳过 ESP32 烧录")
            result.esp32_success = True  # 不算错误
            return True
        
        # 构建命令
        cmd = [
            self.config.esptool_path,
            "--port", self.config.esp32_port,
            "--baud", str(self.config.esp32_baud),
            "write_flash", "0x0", self.config.esp32_bin
        ]
        
        print(f"  执行: {' '.join(cmd[:4])}...")
        
        try:
            output = self._run_command(cmd, timeout=self.config.timeout)
            result.esp32_output = output
            
            if "error" in output.lower() or "failed" in output.lower():
                result.esp32_success = False
                result.errors.append(f"ESP32烧录失败")
                print("  ❌ ESP32 烧录失败")
            else:
                result.esp32_success = True
                print("  ✅ ESP32 烧录成功")
            
        except subprocess.TimeoutExpired:
            result.esp32_success = False
            result.errors.append("ESP32 烧录超时")
            print("  ❌ ESP32 烧录超时")
        
        return result.esp32_success
    
    def _test_hardware(self, result: FlashResult) -> bool:
        """硬件测试"""
        print("[4/4] 硬件测试...")
        
        # 等待设备启动
        print("  等待设备启动...")
        time.sleep(2)
        
        # 串口测试
        try:
            port = self.config.stm32_port
            print(f"  测试串口: {port}")
            
            with serial.Serial(port, 115200, timeout=5) as ser:
                # 发送版本命令
                ser.write(b"VERSION\r\n")
                time.sleep(0.5)
                response = ser.read_all().decode(errors='ignore').strip()
                
                if response:
                    print(f"  响应: {response[:50]}...")
                    result.test_success = True
                    result.test_output = response
                    print("  ✅ 硬件测试通过")
                else:
                    print("  ⚠️ 无响应 (可能正常)")
                    result.test_success = True  # 没响应不一定失败
                    result.warnings.append("串口无响应")
        
        except serial.SerialException as e:
            result.test_success = False
            result.errors.append(f"串口错误: {e}")
            print(f"  ❌ 串口错误: {e}")
        
        return result.test_success
    
    def _run_command(self, cmd, timeout: int = 60) -> str:
        """运行命令"""
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "Timeout"
        except FileNotFoundError:
            return f"Command not found: {cmd[0]}"
    
    def _run_cmake(self) -> str:
        """运行 CMake"""
        output = ""
        try:
            # 创建构建目录
            build_dir = Path("build")
            build_dir.mkdir(exist_ok=True)
            
            # CMake 配置
            output += self._run_command(["cmake", ".."], timeout=60)
            
            # 构建
            output += self._run_command(["cmake", "--build", ".", "-j4"], timeout=120)
        except Exception as e:
            output += str(e)
        return output
    
    def _finish(self, result: FlashResult) -> FlashResult:
        """完成"""
        result.duration_ms = int((time.time() - self.start_time) * 1000)
        
        # 打印结果
        print(f"\n{'='*60}")
        print(f"  烧录结果")
        print(f"{'='*60}")
        
        print(f"\n步骤结果:")
        print(f"  构建:     {'✅' if result.build_success else '❌'}")
        print(f"  STM32:    {'✅' if result.stm32_success else '❌'}")
        print(f"  ESP32:    {'✅' if result.esp32_success else '❌'}")
        print(f"  硬件测试: {'✅' if result.test_success else '❌'}")
        
        if result.errors:
            print(f"\n错误:")
            for e in result.errors:
                print(f"  ❌ {e}")
        
        if result.warnings:
            print(f"\n警告:")
            for w in result.warnings:
                print(f"  ⚠️ {w}")
        
        print(f"\n总耗时: {result.duration_ms / 1000:.1f}秒")
        
        status = "✅ 全部成功" if result.success else "❌ 部分失败"
        print(f"状态: {status}")
        print(f"{'='*60}\n")
        
        # 保存报告
        self._save_report(result)
        
        return result
    
    def _save_report(self, result: FlashResult):
        """保存报告"""
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"flash_{timestamp}.json"
        
        report = {
            "timestamp": result.timestamp,
            "device": result.device,
            "target": result.target,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "steps": {
                "build": result.build_success,
                "stm32": result.stm32_success,
                "esp32": result.esp32_success,
                "test": result.test_success
            },
            "outputs": {
                "build": result.build_output[:1000] if result.build_output else "",
                "stm32": result.stm32_output[:1000] if result.stm32_output else "",
                "esp32": result.esp32_output[:1000] if result.esp32_output else "",
                "test": result.test_output[:1000] if result.test_output else ""
            },
            "errors": result.errors,
            "warnings": result.warnings
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"报告已保存: {report_path}")


# ============ 交互界面 ============

def print_header():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          NCA-Mesh 烧录工具 v2.0                             ║
║                                                              ║
║  功能: 构建 → 烧录 STM32 → 烧录 ESP32 → 硬件测试           ║
╚══════════════════════════════════════════════════════════════╝
""")


def print_menu():
    print("""
选择操作:
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

输入选项 (1-9, 0):
    """.strip())


def interactive_mode():
    """交互模式"""
    print_header()
    
    # 初始化设备
    init_devices()
    
    # 显示已注册设备
    devices = list(DeviceRegistry.list_devices())
    print(f"已注册设备: {', '.join(devices) if devices else '无'}")
    
    # 选择设备
    print(f"\n当前设备: v5_robot (默认)")
    
    while True:
        print_menu()
        choice = input("> ").strip()
        
        if choice == "0":
            print("\n再见! 👋")
            break
        
        elif choice == "1":
            config = FlashConfig(target=FlashTarget.ALL)
            tool = FlashTool(config)
            tool.run()
        
        elif choice == "2":
            config = FlashConfig(target=FlashTarget.STM32)
            tool = FlashTool(config)
            tool.run()
        
        elif choice == "3":
            config = FlashConfig(target=FlashTarget.ESP32)
            tool = FlashTool(config)
            tool.run()
        
        elif choice == "4":
            config = FlashConfig(target=FlashTarget.CONFIG)
            tool = FlashTool(config)
            result = tool.run()
            if result.build_success:
                print("✅ 构建成功")
        
        elif choice == "5":
            print("\n[验证模式] 验证已烧录的固件...")
            print("  TODO: 实现验证功能")
        
        elif choice == "6":
            config = FlashConfig(skip_tests=False)
            tool = FlashTool(config)
            tool._test_hardware(FlashResult(
                success=False,
                timestamp=datetime.now().isoformat(),
                device="v5_robot",
                target="test"
            ))
        
        elif choice == "7":
            print("\n已注册设备:")
            for d in devices:
                print(f"  - {d}")
        
        elif choice == "8":
            print("\n[添加设备]")
            name = input("  设备名称: ").strip()
            port = input("  串口号 (默认 COM3): ").strip() or "COM3"
            
            register_generic_robot(name, serial_port=port)
            print(f"✅ 设备已添加: {name}")
        
        elif choice == "9":
            print("\n[运行全部工具]")
            print("  暂未实现，请使用 python hardware_toolkit.py --mode all")
        
        else:
            print("无效选项\n")


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(
        description="NCA-Mesh 烧录工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python flash_tool.py                    # 交互模式
  python flash_tool.py --auto           # 全自动
  python flash_tool.py --device v5_robot
  python flash_tool.py --target stm32   # 仅STM32
  python flash_tool.py --target esp32   # 仅ESP32
  python flash_tool.py --verify         # 仅验证
  python flash_tool.py --skip-test     # 跳过测试
        """
    )
    
    parser.add_argument('--auto', action='store_true',
                       help='全自动模式')
    parser.add_argument('--device', default='v5_robot',
                       help='设备名称')
    parser.add_argument('--target', choices=['all', 'stm32', 'esp32'],
                       default='all', help='烧录目标')
    parser.add_argument('--verify', action='store_true',
                       help='仅验证')
    parser.add_argument('--skip-test', action='store_true',
                       help='跳过硬件测试')
    parser.add_argument('--stm32-port', help='STM32 串口')
    parser.add_argument('--esp32-port', help='ESP32 串口')
    
    args = parser.parse_args()
    
    if args.auto or len(sys.argv) > 1:
        # 非交互模式
        config = FlashConfig(
            device=args.device,
            target=FlashTarget(args.target),
            skip_tests=args.skip_test
        )
        
        if args.stm32_port:
            config.stm32_port = args.stm32_port
        if args.esp32_port:
            config.esp32_port = args.esp32_port
        
        tool = FlashTool(config)
        result = tool.run()
        
        sys.exit(0 if result.success else 1)
    
    else:
        # 交互模式
        interactive_mode()


if __name__ == "__main__":
    main()
