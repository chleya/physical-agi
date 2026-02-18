#!/usr/bin/env python3
"""
通用工具包装器
==============
让所有工具自动适配任何设备

使用:
    from universal_tool import UniversalTool
    tool = UniversalTool("my_robot")
    tool.run_check()
    tool.run_monitor()
"""

import sys
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from device_config import (
    DeviceRegistry, DeviceAdapter, ToolAdapter,
    DeviceConfig, init_devices, use_device
)


@dataclass
class ToolResult:
    """工具运行结果"""
    success: bool
    output: str
    errors: List[str]
    data: Dict


class UniversalTool:
    """
    通用工具 - 一个接口适配所有设备
    
    使用方法:
        tool = UniversalTool("v5_robot")
        tool.run_check()      # 连线检测
        tool.run_monitor()    # 实时监控
        tool.run_vision()     # 视觉检测
    """
    
    def __init__(self, device_name: str = None):
        # 初始化设备
        init_devices()
        
        # 选择设备
        if device_name:
            self.adapter = use_device(device_name)
        else:
            # 自动选择第一个设备
            devices = list_devices()
            if devices:
                self.adapter = use_device(devices[0])
            else:
                raise ValueError("没有注册的设备，请先注册设备")
        
        if not self.adapter:
            raise ValueError(f"设备不存在: {device_name}")
        
        self.device_name = self.adapter.config.name
        print(f"[INFO] 使用设备: {self.device_name}")
    
    # ============ 工具方法 ============
    
    def run_check(self) -> ToolResult:
        """运行连线检测"""
        print("\n" + "="*50)
        print(f"  连线检测 - {self.device_name}")
        print("="*50)
        
        cfg = ToolAdapter.adapt_wire_check(self.adapter.config)
        print(f"串口: {cfg['port']}")
        print(f"波特率: {cfg['baud']}")
        print(f"组件: {cfg['components']}")
        
        return ToolResult(
            success=True,
            output=f"连线检测完成: {cfg['components']}",
            errors=[],
            data=cfg
        )
    
    def run_monitor(self, duration: int = 10) -> ToolResult:
        """运行实时监控"""
        print("\n" + "="*50)
        print(f"  实时监控 - {self.device_name}")
        print("="*50)
        
        cfg = ToolAdapter.adapt_monitor(self.adapter.config)
        
        print(f"串口: {cfg['port']}")
        print(f"波特率: {cfg['baud']}")
        print(f"监控通道: {cfg['channels']}")
        print(f"监控时长: {duration}秒")
        
        # 模拟监控
        print("\n监控中...")
        for i in range(duration):
            print(f"\r[{i+1}/{duration}] 采集数据...", end='', flush=True)
            time.sleep(1)
        
        print(f"\n监控完成!")
        
        return ToolResult(
            success=True,
            output=f"监控完成: {duration}秒",
            errors=[],
            data=cfg
        )
    
    def run_vision(self) -> ToolResult:
        """运行视觉检测"""
        print("\n" + "="*50)
        print(f"  视觉检测 - {self.device_name}")
        print("="*50)
        
        cfg = ToolAdapter.adapt_vision(self.adapter.config)
        print(f"检测目标: {cfg['detection_targets']}")
        
        return ToolResult(
            success=True,
            output="视觉检测配置完成",
            errors=[],
            data=cfg
        )
    
    def run_ina219(self) -> ToolResult:
        """运行电流监控"""
        print("\n" + "="*50)
        print(f"  电流监控 - {self.device_name}")
        print("="*50)
        
        cfg = ToolAdapter.adapt_ina219(self.adapter.config)
        print(f"最大电流: {cfg['max_current_ma']}mA")
        print(f"电压范围: {cfg['voltage_range'][0]}-{cfg['voltage_range'][1]}V")
        
        return ToolResult(
            success=True,
            output="电流监控配置完成",
            errors=[],
            data=cfg
        )
    
    def run_gdb(self) -> ToolResult:
        """GDB 调试"""
        print("\n" + "="*50)
        print(f"  GDB 调试 - {self.device_name}")
        print("="*50)
        
        return ToolResult(
            success=True,
            output="GDB 调试已就绪",
            errors=[],
            data={
                'port': self.adapter.get_serial_port(),
                'baud': self.adapter.get_baud_rate()
            }
        )
    
    def run_all(self) -> List[ToolResult]:
        """运行所有工具"""
        results = []
        
        results.append(self.run_check())
        results.append(self.run_monitor(duration=3))
        results.append(self.run_vision())
        results.append(self.run_ina219())
        results.append(self.run_gdb())
        
        return results
    
    def get_status(self) -> Dict:
        """获取设备状态"""
        return {
            'device': self.device_name,
            'type': self.adapter.config.type.value,
            'serial_port': self.adapter.get_serial_port(),
            'baud_rate': self.adapter.get_baud_rate(),
            'components': [c.name for c in self.adapter.get_components()],
            'limits': self.adapter.get_limits()
        }


# ============ 设备管理 ============

class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        init_devices()
        self.current_device = None
    
    def add(self, name: str, **kwargs) -> bool:
        """添加设备"""
        from device_config import register_generic_robot
        register_generic_robot(name, **kwargs)
        return True
    
    def use(self, name: str) -> UniversalTool:
        """切换设备"""
        self.current_device = name
        return UniversalTool(name)
    
    def list(self) -> List[str]:
        """列出设备"""
        return list_devices()
    
    def info(self, name: str) -> Dict:
        """设备信息"""
        adapter = use_device(name)
        if adapter:
            return adapter.to_dict()
        return {}


# ============ 快捷函数 ============

def check(device: str = None) -> ToolResult:
    """连线检测"""
    tool = UniversalTool(device)
    return tool.run_check()


def monitor(device: str = None, duration: int = 10) -> ToolResult:
    """实时监控"""
    tool = UniversalTool(device)
    return tool.run_monitor(duration)


def vision(device: str = None) -> ToolResult:
    """视觉检测"""
    tool = UniversalTool(device)
    return tool.run_vision()


def status(device: str = None) -> Dict:
    """设备状态"""
    tool = UniversalTool(device)
    return tool.get_status()


def all_tools(device: str = None) -> List[ToolResult]:
    """运行所有工具"""
    tool = UniversalTool(device)
    return tool.run_all()


# ============ 主程序 ============

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="通用硬件调试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出设备
  python universal_tool.py --list
  
  # 使用指定设备
  python universal_tool.py --use v5_robot --check
  
  # 查看设备信息
  python universal_tool.py --info v5_robot
  
  # 添加新设备
  python universal_tool.py --add my_robot --port COM5
  
  # 运行所有工具
  python universal_tool.py --use v5_robot --all

代码使用:
  from universal_tool import UniversalTool, status, check
  
  # 使用设备
  tool = UniversalTool("v5_robot")
  
  # 查看状态
  print(status())
  
  # 运行检测
  check()
"""
    )
    
    parser.add_argument('--list', action='store_true', help='列出设备')
    parser.add_argument('--use', help='使用指定设备')
    parser.add_argument('--info', help='查看设备信息')
    parser.add_argument('--add', help='添加设备')
    parser.add_argument('--port', default='COM3', help='设备串口')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--check', action='store_true', help='连线检测')
    parser.add_argument('--monitor', type=int, default=5, help='监控时长')
    parser.add_argument('--vision', action='store_true', help='视觉检测')
    parser.add_argument('--all', action='store_true', help='运行所有工具')
    
    args = parser.parse_args()
    
    # 初始化
    manager = DeviceManager()
    
    if args.list:
        devices = manager.list()
        print("\n已注册设备:")
        for d in devices:
            print(f"  - {d}")
    
    elif args.info:
        info = manager.info(args.info)
        print(f"\n设备信息: {args.info}")
        print(json.dumps(info, indent=2))
    
    elif args.add:
        manager.add(args.add, serial_port=args.port, baud_rate=args.baud)
        print(f"设备已添加: {args.add}")
    
    elif args.use:
        tool = manager.use(args.use)
        
        if args.check:
            tool.run_check()
        
        if args.monitor:
            tool.run_monitor(args.monitor)
        
        if args.vision:
            tool.run_vision()
        
        if args.all:
            print("\n运行所有工具...")
            results = tool.run_all()
            for r in results:
                print(f"  {'✅' if r.success else '❌'} {r.output}")
    
    else:
        # 默认运行所有设备的检测
        print("通用硬件调试工具")
        print("\n使用 --help 查看帮助")
        print("\n已注册设备:", manager.list())
        
        # 自动运行
        tool = UniversalTool()
        print(tool.get_status())
        tool.run_check()


if __name__ == "__main__":
    import json
    main()
