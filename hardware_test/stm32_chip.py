#!/usr/bin/env python3
"""
STM32 芯片配置库
================
支持多种 STM32 芯片的自动适配

支持的芯片:
- STM32F1xx (Cortex-M3)
- STM32F4xx (Cortex-M4)
- STM32F7xx (Cortex-M7)
- STM32H7xx (Cortex-M7)
- STM32L4xx (Cortex-M4)
- STM32G4xx (Cortex-M4)
- STM32WBxx (Cortex-M4)
- STM32G0xx (Cortex-M0+)
- STM32C0xx (Cortex-M0+)

使用:
    from stm32_chip import ChipConfig, get_chip_config
    config = get_chip_config("STM32F407VG")
"""

import json
import os
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class ChipFamily(Enum):
    """芯片系列"""
    STM32F0 = "STM32F0"
    STM32F1 = "STM32F1"
    STM32F2 = "STM32F2"
    STM32F3 = "STM32F3"
    STM32F4 = "STM32F4"
    STM32F7 = "STM32F7"
    STM32H7 = "STM32H7"
    STM32L0 = "STM32L0"
    STM32L1 = "STM32L1"
    STM32L4 = "STM32L4"
    STM32L5 = "STM32L5"
    STM32G0 = "STM32G0"
    STM32G4 = "STM32G4"
    STM32WB = "STM32WB"
    STM32C0 = "STM32C0"


class Cortex(Enum):
    """内核类型"""
    M0 = "Cortex-M0"
    M0P = "Cortex-M0+"
    M3 = "Cortex-M3"
    M4 = "Cortex-M4"
    M7 = "Cortex-M7"


@dataclass
class FlashConfig:
    """Flash 配置"""
    start: int = 0x08000000
    size: int = 0  # KB
    sector_size: int = 0
    sector_count: int = 0
    page_size: int = 0
    base_address: int = 0x08000000


@dataclass
class RamConfig:
    """RAM 配置"""
    size: int = 0  # KB
    start: int = 0x20000000
    sections: Dict[str, tuple] = field(default_factory=dict)


@dataclass
class ClockConfig:
    """时钟配置"""
    hse: int = 8000000  # Hz
    sysclk: int = 168000000  # Hz
    ahb: int = 168000000
    apb1: int = 42000000
    apb2: int = 84000000


@dataclass
class Peripherals:
    """外设"""
    has_i2c: bool = True
    has_spi: bool = True
    has_uart: bool = True
    has_can: bool = False
    has_usb: bool = False
    has_eth: bool = False
    has_dac: bool = False
    has_adc: int = 0  # 通道数
    has_pwm: int = 0   # 定时器数
    has_gpio: int = 0   # GPIO 数量


@dataclass
class ChipConfig:
    """芯片配置"""
    name: str
    part_number: str  # 如 STM32F407VGT6
    family: ChipFamily
    cortex: Cortex
    
    # 内存
    flash: FlashConfig
    ram: RamConfig
    
    # 时钟
    clock: ClockConfig
    
    # 外设
    peripherals: Peripherals
    
    # 包类型
    package: str = ""  # LQFP100, WLCSP81, etc.
    voltage: tuple = (2.0, 3.6)  # V
    
    # 功耗
    temp_range: tuple = (-40, 85)  # Celsius
    
    # OpenOCD 配置
    openocd_target: str = "stm32f4x"
    openocd_flash_driver: str = "stm32f2x"


# 芯片数据库
CHIP_DATABASE: Dict[str, ChipConfig] = {}


def _init_chip_database():
    """初始化芯片数据库"""
    global CHIP_DATABASE
    
    # ============ STM32F4xx 系列 ============
    
    # STM32F405/407
    CHIP_DATABASE["STM32F405RG"] = ChipConfig(
        name="STM32F405RG",
        part_number="STM32F405RGT6",
        family=ChipFamily.STM32F4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=1024,  # 1MB
            sector_size=16*1024,  # 16KB
            sector_count=64,
            page_size=256*1024  # 256KB 整个扇区
        ),
        ram=RamConfig(
            size=192,  # 192KB SRAM
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 112*1024),
                "SRAM2": (0x2001C000, 16*1024),
                "CCM": (0x10000000, 64*1024)  # Core Coupled Memory
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=168000000,
            ahb=168000000,
            apb1=42000000,
            apb2=84000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=2, has_usb=True, has_eth=True,
            has_adc=16, has_pwm=14, has_gpio=82
        ),
        package="LQFP64",
        voltage=(1.8, 3.6),
        temp_range=(-40, 105)
    )
    
    # STM32F407VG (常用)
    CHIP_DATABASE["STM32F407VG"] = ChipConfig(
        name="STM32F407VG",
        part_number="STM32F407VGT6",
        family=ChipFamily.STM32F4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=1024,  # 1MB
            sector_size=16*1024,
            sector_count=64,
            page_size=256*1024
        ),
        ram=RamConfig(
            size=192,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 112*1024),
                "SRAM2": (0x2001C000, 16*1024),
                "CCM": (0x10000000, 64*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=168000000,
            ahb=168000000,
            apb1=42000000,
            apb2=84000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=2, has_usb=True, has_eth=True,
            has_adc=16, has_pwm=14, has_gpio=82
        ),
        package="LQFP100",
        openocd_target="stm32f4x",
        openocd_flash_driver="stm32f4x"
    )
    
    # STM32F401
    CHIP_DATABASE["STM32F401CC"] = ChipConfig(
        name="STM32F401CC",
        part_number="STM32F401CCU6",
        family=ChipFamily.STM32F4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=256,  # 256KB
            sector_size=16*1024,
            sector_count=16
        ),
        ram=RamConfig(
            size=96,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 64*1024),
                "SRAM2": (0x20010000, 32*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=84000000,
            ahb=84000000,
            apb1=42000000,
            apb2=84000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=0, has_usb=True, has_eth=False,
            has_adc=10, has_pwm=10, has_gpio=50
        ),
        package="UFQFPN48",
        openocd_target="stm32f4x"
    )
    
    # STM32F411
    CHIP_DATABASE["STM32F411CC"] = ChipConfig(
        name="STM32F411CC",
        part_number="STM32F411CCU6",
        family=ChipFamily.STM32F4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=256,
            sector_size=16*1024,
            sector_count=16
        ),
        ram=RamConfig(
            size=128,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 64*1024),
                "SRAM2": (0x20010000, 64*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=100000000,
            ahb=100000000,
            apb1=50000000,
            apb2=100000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=0, has_usb=True, has_eth=False,
            has_adc=10, has_pwm=10, has_gpio=50
        ),
        package="UFQFPN48",
        openocd_target="stm32f4x"
    )
    
    # ============ STM32F1xx 系列 ============
    
    # STM32F103
    CHIP_DATABASE["STM32F103RB"] = ChipConfig(
        name="STM32F103RB",
        part_number="STM32F103RBT6",
        family=ChipFamily.STM32F1,
        cortex=Cortex.M3,
        flash=FlashConfig(
            start=0x08000000,
            size=128,
            sector_size=2*1024,
            sector_count=64,
            page_size=2*1024
        ),
        ram=RamConfig(
            size=20,
            start=0x20000000,
            sections={
                "SRAM": (0x20000000, 20*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=72000000,
            ahb=72000000,
            apb1=36000000,
            apb2=72000000
        ),
        peripherals=Peripherals(
            has_i2c=2, has_spi=2, has_uart=3,
            has_can=1, has_usb=True, has_eth=False,
            has_adc=16, has_pwm=4, has_gpio=51
        ),
        package="LQFP64",
        voltage=(2.0, 3.6),
        openocd_target="stm32f1x",
        openocd_flash_driver="stm32f2x"
    )
    
    # ============ STM32F7xx 系列 ============
    
    # STM32F767
    CHIP_DATABASE["STM32F767ZI"] = ChipConfig(
        name="STM32F767ZI",
        part_number="STM32F767ZIT6",
        family=ChipFamily.STM32F7,
        cortex=Cortex.M7,
        flash=FlashConfig(
            start=0x08000000,
            size=2048,  # 2MB
            sector_size=32*1024,
            sector_count=64
        ),
        ram=RamConfig(
            size=512,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 240*1024),
                "SRAM2": (0x20040000, 16*1024),
                "SRAM3": (0x2007C000, 64*1024),
                "DTCM": (0x20000000, 128*1024),
                "ITCM": (0x00000000, 64*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=216000000,
            ahb=216000000,
            apb1=54000000,
            apb2=108000000
        ),
        peripherals=Peripherals(
            has_i2c=4, has_spi=6, has_uart=8,
            has_can=2, has_usb=True, has_eth=True,
            has_adc=24, has_pwm=26, has_gpio=140
        ),
        package="LQFP144",
        voltage=(1.7, 3.6),
        openocd_target="stm32f7x",
        openocd_flash_driver="stm32f7x"
    )
    
    # ============ STM32H7xx 系列 ============
    
    # STM32H743
    CHIP_DATABASE["STM32H743ZI"] = ChipConfig(
        name="STM32H743ZI",
        part_number="STM32H743ZIT6U",
        family=ChipFamily.STM32H7,
        cortex=Cortex.M7,
        flash=FlashConfig(
            start=0x08000000,
            size=2048,
            sector_size=128*1024,
            sector_count=16
        ),
        ram=RamConfig(
            size=1024,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 128*1024),
                "SRAM2": (0x20020000, 128*1024),
                "SRAM3": (0x20040000, 32*1024),
                "SRAM4": (0x2007C000, 64*1024),
                "DTCM1": (0x20000000, 128*1024),
                "ITCM": (0x00000000, 64*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=400000000,
            ahb=200000000,
            apb1=100000000,
            apb2=100000000
        ),
        peripherals=Peripherals(
            has_i2c=4, has_spi=6, has_uart=8,
            has_can=2, has_usb=True, has_eth=True,
            has_adc=20, has_pwm=34, has_gpio=140
        ),
        package="LQFP144",
        voltage=(1.62, 3.6),
        openocd_target="stm32h7x",
        openocd_flash_driver="stm32h7x"
    )
    
    # ============ STM32L4xx 系列 ============
    
    # STM32L475
    CHIP_DATABASE["STM32L475RG"] = ChipConfig(
        name="STM32L475RG",
        part_number="STM32L475RGT6",
        family=ChipFamily.STM32L4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=1024,
            sector_size=2*1024,
            sector_count=512,
            page_size=2*1024
        ),
        ram=RamConfig(
            size=96,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 64*1024),
                "SRAM2": (0x20010000, 32*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=80000000,
            ahb=80000000,
            apb1=40000000,
            apb2=80000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=2, has_usb=True, has_eth=False,
            has_adc=16, has_pwm=16, has_gpio=52
        ),
        package="LQFP64",
        voltage=(1.71, 3.6),
        openocd_target="stm32l4x"
    )
    
    # ============ STM32G4xx 系列 ============
    
    # STM32G431
    CHIP_DATABASE["STM32G431CB"] = ChipConfig(
        name="STM32G431CB",
        part_number="STM32G431CBU6",
        family=ChipFamily.STM32G4,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=128,
            sector_size=2*1024,
            sector_count=64
        ),
        ram=RamConfig(
            size=32,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 32*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=170000000,
            ahb=170000000,
            apb1=85000000,
            apb2=170000000
        ),
        peripherals=Peripherals(
            has_i2c=3, has_spi=3, has_uart=6,
            has_can=2, has_usb=True, has_eth=False,
            has_adc=12, has_pwm=14, has_gpio=52
        ),
        package="UFQFPN48",
        voltage=(1.71, 3.6),
        temp_range=(-40, 125),
        openocd_target="stm32g4x"
    )
    
    # ============ STM32WBxx 系列 ============
    
    # STM32WB55
    CHIP_DATABASE["STM32WB55RG"] = ChipConfig(
        name="STM32WB55RG",
        part_number="STM55RGGU6",
        family=ChipFamily.STM32WB,
        cortex=Cortex.M4,
        flash=FlashConfig(
            start=0x08000000,
            size=512,
            sector_size=4*1024,
            sector_count=128
        ),
        ram=RamConfig(
            size=192,
            start=0x20000000,
            sections={
                "SRAM1": (0x20000000, 128*1024),
                "SRAM2": (0x20020000, 64*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=64000000,
            ahb=64000000,
            apb1=32000000,
            apb2=64000000
        ),
        peripherals=Peripherals(
            has_i2c=2, has_spi=3, has_uart=6,
            has_can=2, has_usb=True, has_eth=False,
            has_adc=16, has_pwm=14, has_gpio=82
        ),
        package="UFQFPN68",
        voltage=(1.65, 3.6),
        openocd_target="stm32wbx"
    )
    
    # ============ STM32G0xx 系列 ============
    
    # STM32G071
    CHIP_DATABASE["STM32G071KB"] = ChipConfig(
        name="STM32G071KB",
        part_number="STM32G071KBT6",
        family=ChipFamily.STM32G0,
        cortex=Cortex.M0P,
        flash=FlashConfig(
            start=0x08000000,
            size=128,
            sector_size=2*1024,
            sector_count=64
        ),
        ram=RamConfig(
            size=36,
            start=0x20000000,
            sections={
                "SRAM": (0x20000000, 36*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=64000000,
            ahb=64000000,
            apb1=32000000,
            apb2=32000000
        ),
        peripherals=Peripherals(
            has_i2c=2, has_spi=2, has_uart=8,
            has_can=0, has_usb=True, has_eth=False,
            has_adc=12, has_pwm=10, has_gpio=57
        ),
        package="LQFP32",
        voltage=(1.65, 3.6),
        temp_range=(-40, 85),
        openocd_target="stm32g0x",
        openocd_flash_driver="stm32g0x"
    )
    
    # ============ STM32C0xx 系列 ============
    
    # STM32C031
    CHIP_DATABASE["STM32C031C6"] = ChipConfig(
        name="STM32C031C6",
        part_number="STM32C031C6U6",
        family=ChipFamily.STM32C0,
        cortex=Cortex.M0P,
        flash=FlashConfig(
            start=0x08000000,
            size=32,
            sector_size=2*1024,
            sector_count=16
        ),
        ram=RamConfig(
            size=12,
            start=0x20000000,
            sections={
                "SRAM": (0x20000000, 12*1024)
            }
        ),
        clock=ClockConfig(
            hse=8000000,
            sysclk=48000000,
            ahb=48000000,
            apb1=48000000,
            apb2=48000000
        ),
        peripherals=Peripherals(
            has_i2c=2, has_spi=2, has_uart=8,
            has_can=0, has_usb=False, has_eth=False,
            has_adc=12, has_pwm=5, has_gpio=30
        ),
        package="UFQFPN28",
        voltage=(1.65, 3.6),
        temp_range=(-40, 85),
        openocd_target="stm32c0x"
    )


# 初始化
_init_chip_database()


# ============ API 函数 ============

def get_chip_config(chip_name: str) -> Optional[ChipConfig]:
    """
    获取芯片配置
    
    Args:
        chip_name: 芯片名称 (如 "STM32F407VG", "STM32F103RB", "STM32H743")
        
    Returns:
        ChipConfig 或 None
    """
    # 直接匹配
    if chip_name in CHIP_DATABASE:
        return CHIP_DATABASE[chip_name]
    
    # 模糊匹配 (部分名称)
    chip_upper = chip_name.upper()
    for name, config in CHIP_DATABASE.items():
        if chip_upper in name.upper() or name.upper() in chip_upper:
            return config
    
    # 尝试匹配系列
    family_match = {
        "F405": "STM32F405RG",
        "F407": "STM32F407VG",
        "F103": "STM32F103RB",
        "F401": "STM32F401CC",
        "F411": "STM32F411CC",
        "F767": "STM32F767ZI",
        "H743": "STM32H743ZI",
        "L475": "STM32L475RG",
        "G431": "STM32G431CB",
        "G071": "STM32G071KB",
        "WB55": "STM32WB55RG",
        "C031": "STM32C031C6"
    }
    
    for key, full_name in family_match.items():
        if key in chip_upper:
            return CHIP_DATABASE.get(full_name)
    
    return None


def list_supported_chips() -> list:
    """列出所有支持的芯片"""
    return list(CHIP_DATABASE.keys())


def detect_chip_from_elf(elf_path: str) -> Optional[ChipConfig]:
    """
    从 ELF 文件检测芯片型号
    
    Args:
        elf_path: ELF 文件路径
        
    Returns:
        ChipConfig 或 None
    """
    try:
        import subprocess
        result = subprocess.run(
            ["arm-none-eabi-readelf", "-p", ".rodata", elf_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return None
        
        # 查找芯片标识
        for line in result.stdout.split('\n'):
            if "STM32" in line:
                for chip_name in CHIP_DATABASE.keys():
                    if chip_name in line:
                        return CHIP_DATABASE[chip_name]
    except:
        pass
    
    return None


def get_openocd_config(chip_config: ChipConfig) -> dict:
    """
    生成 OpenOCD 配置文件
    
    Args:
        chip_config: 芯片配置
        
    Returns:
        OpenOCD 配置字典
    """
    return {
        "source": f"target/{chip_config.openocd_target}.cfg",
        "flash": {
            "driver": chip_config.openocd_flash_driver,
            "start": hex(chip_config.flash.start),
            "size_kb": chip_config.flash.size,
            "chip_name": chip_config.name
        },
        "ram": {
            "start": hex(chip_config.ram.start),
            "size_kb": chip_config.ram.size
        },
        "clock": {
            "hse": chip_config.clock.hse,
            "sysclk": chip_config.clock.sysclk
        }
    }


def print_chip_info(chip_name: str):
    """打印芯片信息"""
    config = get_chip_config(chip_name)
    
    if not config:
        print(f"未知芯片: {chip_name}")
        print(f"\n支持的芯片:")
        for name in sorted(CHIP_DATABASE.keys()):
            print(f"  - {name}")
        return
    
    print(f"\n{'='*60}")
    print(f"  {config.name}")
    print(f"{'='*60}")
    print(f"系列: {config.family.value}")
    print(f"内核: {config.cortex.value}")
    print(f"\n内存:")
    print(f"  Flash: {config.flash.size}KB @ {hex(config.flash.start)}")
    print(f"  RAM:   {config.ram.size}KB @ {hex(config.ram.start)}")
    print(f"\n时钟:")
    print(f"  SYSCLK: {config.clock.sysclk/1e6:.0f}MHz")
    print(f"  AHB:    {config.clock.ahb/1e6:.0f}MHz")
    print(f"  APB1:   {config.clock.apb1/1e6:.0f}MHz")
    print(f"  APB2:   {config.clock.apb2/1e6:.0f}MHz")
    print(f"\n外设:")
    print(f"  I2C: {config.peripherals.has_i2c}")
    print(f"  SPI: {config.peripherals.has_spi}")
    print(f"  UART: {config.peripherals.has_uart}")
    print(f"  USB: {'有' if config.peripherals.has_usb else '无'}")
    print(f"  ETH: {'有' if config.peripherals.has_eth else '无'}")
    print(f"\n功耗:")
    print(f"  电压: {config.voltage[0]}-{config.voltage[1]}V")
    print(f"  温度: {config.temp_range[0]}~{config.temp_range[1]}°C")
    print(f"\n封装: {config.package}")
    print(f"\nOpenOCD:")
    print(f"  Target: {config.openocd_target}")
    print(f"{'='*60}\n")


# ============ 主程序 ============

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="STM32 芯片配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看芯片信息
  python stm32_chip.py --chip STM32F407VG
  
  # 列出所有支持芯片
  python stm32_chip.py --list
  
  # 从ELF检测
  python stm32_chip.py --from-elf firmware.elf
        """
    )
    
    parser.add_argument('--chip', '-c', help='芯片名称')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有支持芯片')
    parser.add_argument('--from-elf', '-e', help='从ELF文件检测')
    parser.add_argument('--openocd', '-o', help='生成OpenOCD配置')
    
    args = parser.parse_args()
    
    if args.list:
        print("\n支持的 STM32 芯片:")
        for name in sorted(CHIP_DATABASE.keys()):
            config = CHIP_DATABASE[name]
            print(f"  {name:20s} ({config.family.value}, {config.cortex.value})")
        print()
    
    elif args.from_elf:
        config = detect_chip_from_elf(args.from_elf)
        if config:
            print(f"检测到芯片: {config.name}")
            print_chip_info(config.name)
        else:
            print("无法检测芯片型号")
    
    elif args.openocd:
        config = get_chip_config(args.openocd)
        if config:
            cfg = get_openocd_config(config)
            print(json.dumps(cfg, indent=2))
        else:
            print(f"未知芯片: {args.openocd}")
    
    elif args.chip:
        print_chip_info(args.chip)
    
    else:
        print_chip_info("STM32F407VG")


if __name__ == "__main__":
    main()
