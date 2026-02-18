#!/usr/bin/env python3
"""
硬件调试终极工具箱
==================
集成所有硬件调试模块

功能:
- 连线检测
- 视觉检测
- 电流监控
- GDB 调试
- 无线 OTA
- 自动回归测试
- 多机调试
- 实时示波器
- AI 故障预测

使用:
    python hardware_toolkit.py --mode all
    python hardware_toolkit.py --mode monitor
    python hardware_toolkit.py --mode debug
"""

import sys
import time
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Mode(Enum):
    """运行模式"""
    ALL = "all"
    CHECK = "check"
    MONITOR = "monitor"
    DEBUG = "debug"
    TEST = "test"
    ANALYZE = "analyze"
    PREDICT = "predict"


@dataclass
class HardwareConfig:
    """硬件配置"""
    stm32_port: str = "COM3"
    esp32_port: str = "COM4"
    camera_id: int = 0
    mqtt_broker: str = "localhost"
    wifi_ssid: str = ""
    wifi_password: str = ""


class HardwareToolkit:
    """硬件调试终极工具箱"""
    
    def __init__(self, config: HardwareConfig = None):
        self.config = config or HardwareConfig()
        self.modules = {}
        self.running = False
    
    def init_all(self) -> Dict[str, bool]:
        """初始化所有模块"""
        results = {}
        
        # 1. 连线检测
        try:
            from wire_check import WireChecker
            self.modules['wire_check'] = WireChecker(self.config.stm32_port)
            results['wire_check'] = True
            print("[✅] 连线检测模块已加载")
        except Exception as e:
            results['wire_check'] = False
            print(f"[❌] 连线检测模块加载失败: {e}")
        
        # 2. 视觉检测
        try:
            from vision_inspector import VisionInspector
            self.modules['vision'] = VisionInspector(self.config.camera_id)
            results['vision'] = True
            print("[✅] 视觉检测模块已加载")
        except Exception as e:
            results['vision'] = False
            print(f"[❌] 视觉检测模块加载失败: {e}")
        
        # 3. 电流监控
        try:
            from ina219_monitor import INA219Monitor
            self.modules['ina219'] = INA219Monitor()
            results['ina219'] = True
            print("[✅] 电流监控模块已加载")
        except Exception as e:
            results['ina219'] = False
            print(f"[❌] 电流监控模块加载失败: {e}")
        
        # 4. GDB 调试
        try:
            from gdb_controller import GDBController
            self.modules['gdb'] = GDBController()
            results['gdb'] = True
            print("[✅] GDB 调试模块已加载")
        except Exception as e:
            results['gdb'] = False
            print(f"[❌] GDB 调试模块加载失败: {e}")
        
        # 5. 无线 OTA
        try:
            from ota_updater import OTAUpdater
            self.modules['ota'] = OTAUpdater(self.config.mqtt_broker)
            results['ota'] = True
            print("[✅] 无线 OTA 模块已加载")
        except Exception as e:
            results['ota'] = False
            print(f"[❌] 无线 OTA 模块加载失败: {e}")
        
        # 6. 自动回归测试
        try:
            from regression_test import RegressionTester
            self.modules['regression'] = RegressionTester()
            results['regression'] = True
            print("[✅] 自动回归测试模块已加载")
        except Exception as e:
            results['regression'] = False
            print(f"[❌] 自动回归测试模块加载失败: {e}")
        
        # 7. 多机调试
        try:
            from multi_robot_debug import MultiRobotDebugger
            self.modules['multi_robot'] = MultiRobotDebugger(self.config.mqtt_broker)
            results['multi_robot'] = True
            print("[✅] 多机调试模块已加载")
        except Exception as e:
            results['multi_robot'] = False
            print(f"[❌] 多机调试模块加载失败: {e}")
        
        # 8. 实时示波器
        try:
            from realtime_oscope import RealtimeOscope
            self.modules['oscope'] = RealtimeOscope(self.config.stm32_port)
            results['oscope'] = True
            print("[✅] 实时示波器模块已加载")
        except Exception as e:
            results['oscope'] = False
            print(f"[❌] 实时示波器模块加载失败: {e}")
        
        # 9. AI 故障预测
        try:
            from ai_predictor import FaultPredictor
            self.modules['ai_predictor'] = FaultPredictor()
            results['ai_predictor'] = True
            print("[✅] AI 故障预测模块已加载")
        except Exception as e:
            results['ai_predictor'] = False
            print(f"[❌] AI 故障预测模块加载失败: {e}")
        
        return results
    
    def run_check(self) -> Dict:
        """运行连线检测"""
        print("\n" + "="*50)
        print("  连线检测模式")
        print("="*50)
        
        results = {}
        
        if 'wire_check' in self.modules:
            checker = self.modules['wire_check']
            results = checker.run_all_checks()
        
        return results
    
    def run_monitor(self) -> Dict:
        """运行监控模式"""
        print("\n" + "="*50)
        print("  监控模式")
        print("="*50)
        
        status = {}
        
        # 监控各模块
        for name, module in self.modules.items():
            try:
                if hasattr(module, 'get_stats'):
                    status[name] = module.get_stats()
                elif hasattr(module, 'get_status'):
                    status[name] = module.get_status()
                else:
                    status[name] = {'status': 'unknown'}
            except Exception as e:
                status[name] = {'error': str(e)}
        
        return status
    
    def run_debug(self) -> Dict:
        """运行调试模式"""
        print("\n" + "="*50)
        print("  调试模式")
        print("="*50)
        
        results = {}
        
        if 'gdb' in self.modules:
            print("[INFO] GDB 调试已就绪")
            print("可用命令: breakpoint, step, continue, halt, variable, memory")
        
        if 'ina219' in self.modules:
            ina219 = self.modules['ina219']
            power = ina219.read_power()
            current = ina219.read_current()
            voltage = ina219.read_voltage()
            
            results['power'] = {
                'voltage_v': voltage,
                'current_ma': current,
                'power_mw': power,
                'overcurrent': ina219.is_overcurrent()
            }
            
            print(f"\n电源状态:")
            print(f"  电压: {voltage:.2f}V")
            print(f"  电流: {current:.1f}mA")
            print(f"  功率: {power:.1f}mW")
            print(f"  过流: {'⚠️ 是' if ina219.is_overcurrent() else '✅ 否'}")
        
        return results
    
    def run_test(self) -> Dict:
        """运行测试模式"""
        print("\n" + "="*50)
        print("  测试模式")
        print("="*50)
        
        results = {}
        
        if 'regression' in self.modules:
            tester = self.modules['regression']
            results = tester.run_full_pipeline()
            print(f"测试结果: {results.get('status', 'unknown')}")
        
        return results
    
    def run_analyze(self) -> Dict:
        """运行分析模式"""
        print("\n" + "="*50)
        print("  分析模式")
        print("="*50)
        
        results = {}
        
        if 'ai_predictor' in self.modules:
            predictor = self.modules['ai_predictor']
            
            # 模拟数据
            test_data = {
                'motor_current': 350,
                'battery_voltage': 3.7,
                'motor_temp': 45,
                'imu_noise': 300
            }
            
            result = predictor.predict(test_data)
            
            results['prediction'] = {
                'status': result.prediction,
                'confidence': result.confidence,
                'recommendation': result.recommendation
            }
            
            print(f"\nAI 预测结果:")
            print(f"  状态: {result.prediction}")
            print(f"  置信度: {result.confidence:.1%}")
            print(f"  建议: {result.recommendation}")
        
        return results
    
    def run_all(self) -> Dict:
        """运行所有功能"""
        print("\n" + "="*60)
        print("  🚀 硬件调试终极工具箱 - 全功能模式")
        print("="*60)
        
        all_results = {}
        
        # 1. 连线检测
        print("\n[1/5] 连线检测...")
        all_results['check'] = self.run_check()
        
        # 2. 启动监控
        print("\n[2/5] 启动监控...")
        all_results['monitor'] = self.run_monitor()
        
        # 3. 调试信息
        print("\n[3/5] 调试信息...")
        all_results['debug'] = self.run_debug()
        
        # 4. AI 预测
        print("\n[4/5] AI 预测...")
        all_results['analyze'] = self.run_analyze()
        
        # 5. 测试
        print("\n[5/5] 快速测试...")
        all_results['test'] = self.run_test()
        
        print("\n" + "="*60)
        print("  全功能测试完成")
        print("="*60)
        
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """生成报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/toolkit_report_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return report_path


def print_summary():
    """打印工具箱总结"""
    summary = """
╔══════════════════════════════════════════════════════════════════════╗
║                 硬件调试终极工具箱 - 功能总结                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                               ║
║  模块列表:                                                     ║
║                                                               ║
║  🔌 wire_check.py      - 连线检测                               ║
║  📷 vision_inspector.py - 视觉检测                              ║
║  ⚡ ina219_monitor.py  - 电流监控                              ║
║  🐛 gdb_controller.py  - GDB 调试                             ║
║  📡 ota_updater.py     - 无线 OTA                             ║
║  ✅ regression_test.py - 自动回归测试                          ║
║  🤖 multi_robot_debug.py - 多机调试                            ║
║  📊 realtime_oscope.py - 实时示波器                            ║
║  🤖 ai_predictor.py   - AI 故障预测                           ║
║                                                               ║
║  使用方法:                                                     ║
║                                                               ║
║  python hardware_toolkit.py --mode all      # 全功能           ║
║  python hardware_toolkit.py --mode check    # 连线检测         ║
║  python hardware_toolkit.py --mode monitor  # 实时监控         ║
║  python hardware_toolkit.py --mode debug    # 调试信息         ║
║  python hardware_toolkit.py --mode test     # 回归测试         ║
║  python hardware_toolkit.py --mode analyze  # AI 分析           ║
║                                                               ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(summary)


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(
        description="硬件调试终极工具箱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python hardware_toolkit.py --mode all      # 全功能测试
  python hardware_toolkit.py --mode check   # 连线检测
  python hardware_toolkit.py --mode monitor  # 实时监控
  python hardware_toolkit.py --mode debug   # 调试信息
  python hardware_toolkit.py --mode test    # 回归测试
  python hardware_toolkit.py --mode analyze # AI 分析

快捷命令:
  python wire_check.py --port COM3
  python vision_inspector.py --camera 0
  python ina_monitor.py
  python gdb_controller.py
  python ota_updater.py
  python regression_test.py
  python multi_robot_debug.py
  python realtime_oscope.py --port COM3
  python ai_predictor.py --predict once
        """
    )
    
    parser.add_argument('--mode', choices=['all', 'check', 'monitor', 'debug', 'test', 'analyze'],
                       default='all', help='运行模式')
    parser.add_argument('--stm32_port', default='COM3', help='STM32 串口')
    parser.add_argument('--esp32_port', default='COM4', help='ESP32 串口')
    parser.add_argument('--camera', type=int, default=0, help='摄像头ID')
    parser.add_argument('--mqtt', default='localhost', help='MQTT 服务器')
    parser.add_argument('--ssid', default='', help='WiFi SSID')
    parser.add_argument('--password', default='', help='WiFi 密码')
    parser.add_argument('--report', action='store_true', help='生成报告')
    
    args = parser.parse_args()
    
    # 打印总结
    print_summary()
    
    # 创建配置
    config = HardwareConfig(
        stm32_port=args.stm32_port,
        esp32_port=args.esp32_port,
        camera_id=args.camera,
        mqtt_broker=args.mqtt,
        wifi_ssid=args.ssid,
        wifi_password=args.password
    )
    
    # 创建工具箱
    toolkit = HardwareToolkit(config)
    
    # 初始化所有模块
    print("\n初始化模块...")
    init_results = toolkit.init_all()
    
    # 统计
    loaded = sum(1 for v in init_results.values() if v)
    total = len(init_results)
    print(f"\n已加载 {loaded}/{total} 个模块")
    
    # 运行指定模式
    if args.mode == 'all':
        results = toolkit.run_all()
    elif args.mode == 'check':
        results = toolkit.run_check()
    elif args.mode == 'monitor':
        results = toolkit.run_monitor()
    elif args.mode == 'debug':
        results = toolkit.run_debug()
    elif args.mode == 'test':
        results = toolkit.run_test()
    elif args.mode == 'analyze':
        results = toolkit.run_analyze()
    else:
        results = {}
    
    # 生成报告
    if args.report:
        report_path = toolkit.generate_report(results)
        print(f"\n报告已保存: {report_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
