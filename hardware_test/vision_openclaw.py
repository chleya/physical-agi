#!/usr/bin/env python3
"""
OpenClaw 视觉集成模块
====================
让 OpenClaw 能够通过摄像头监控硬件状态

使用方法:
    from vision_openclaw import OpenClawVision
    vision = OpenClawVision()
    vision.start()
    
    # 在 OpenClaw 循环中检查
    if vision.is_all_ok():
        print("硬件状态正常")
    else:
        print(vision.get_status_message())
"""

import sys
import time
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class HardwareStatus:
    """硬件状态"""
    vision_ok: bool
    wiring_ok: bool
    leds_ok: bool
    motors_ok: bool
    serial_ok: bool
    overall_ok: bool
    messages: List[str]
    timestamp: str


class OpenClawVision:
    """OpenClaw 视觉集成"""
    
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.inspector = None
        self.running = False
        
        # 状态
        self.last_status = None
        self.status_history = []
        
        # 阈值
        self.motor_threshold = 0.5  # 电机检测阈值
        self.wiring_threshold = 0.8  # 连线检测阈值
    
    def start(self, blocking: bool = False):
        """启动视觉检测"""
        try:
            from vision_inspector import VisionInspector
            
            self.inspector = VisionInspector(camera_id=self.camera_id)
            self.inspector.start()
            self.running = True
            
            print(f"[OpenClaw-Vision] 已启动: 摄像头 {self.camera_id}")
            
            if blocking:
                try:
                    self.inspector.run_openclaw_mode()
                except KeyboardInterrupt:
                    self.stop()
            
        except ImportError as e:
            print(f"[OpenClaw-Vision] 错误: {e}")
            print("[OpenClaw-Vision] 请确保 vision_inspector.py 在同一目录")
    
    def stop(self):
        """停止检测"""
        if self.inspector:
            self.inspector.stop()
        self.running = False
        print("[OpenClaw-Vision] 已停止")
    
    def check(self) -> HardwareStatus:
        """检查硬件状态"""
        if not self.inspector or not self.running:
            return HardwareStatus(
                vision_ok=False,
                wiring_ok=False,
                leds_ok=False,
                motors_ok=False,
                serial_ok=False,
                overall_ok=False,
                messages=["视觉检测未启动"],
                timestamp="N/A"
            )
        
        status = self.inspector.get_status_for_openclaw()
        
        # 综合判断
        all_ok = (
            status['wiring_ok'] and
            status['leds_ok'] and
            status['motors_ok']
        )
        
        result = HardwareStatus(
            vision_ok=True,
            wiring_ok=status['wiring_ok'],
            leds_ok=status['leds_ok'],
            motors_ok=status['motors_ok'],
            serial_ok=True,  # 假设
            overall_ok=all_ok,
            messages=status.get('messages', []),
            timestamp=status.get('timestamp', 'N/A')
        )
        
        self.last_status = result
        self.status_history.append(result)
        
        return result
    
    def is_all_ok(self) -> bool:
        """所有检查是否通过"""
        status = self.check()
        return status.overall_ok
    
    def is_wiring_ok(self) -> bool:
        """连线是否正常"""
        return self.check().wiring_ok
    
    def is_motors_ok(self) -> bool:
        """电机是否正常"""
        return self.check().motors_ok
    
    def is_leds_ok(self) -> bool:
        """LED 是否正常"""
        return self.check().leds_ok
    
    def get_status_message(self) -> str:
        """获取状态消息"""
        status = self.check()
        
        if status.overall_ok:
            return "✅ 硬件状态正常"
        
        msgs = []
        if not status.wiring_ok:
            msgs.append("❌ 连线问题")
        if not status.leds_ok:
            msgs.append("❌ LED 异常")
        if not status.motors_ok:
            msgs.append("⚠️ 电机未转动")
        
        return " | ".join(msgs) if msgs else "⚠️ 状态未知"
    
    def wait_for_ok(self, timeout: float = 30.0, interval: float = 0.5) -> bool:
        """
        等待硬件状态正常
        
        Args:
            timeout: 超时时间 (秒)
            interval: 检查间隔
            
        Returns:
            是否在超时前恢复正常
        """
        start = time.time()
        
        while time.time() - start < timeout:
            if self.is_all_ok():
                return True
            time.sleep(interval)
        
        return False
    
    def get_report(self) -> Dict:
        """获取检测报告"""
        if self.last_status:
            return {
                'status': self.last_status,
                'check_count': len(self.status_history),
                'ok_rate': sum(1 for s in self.status_history if s.overall_ok) / len(self.status_history) if self.status_history else 0
            }
        return {'error': '无检测数据'}
    
    def save_screenshot(self) -> Optional[str]:
        """保存截图"""
        if self.inspector:
            frame, _ = self.inspector.get_result(timeout=1.0)
            if frame is not None:
                import cv2
                from datetime import datetime
                filename = f"openclaw_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, frame)
                return filename
        return None


# ============ OpenClaw 集成示例 ============

def openclaw_hardware_check(vision: OpenClawVision) -> Dict:
    """
    OpenClaw 硬件检查回调
    
    返回给 OpenClaw 的消息格式
    """
    status = vision.check()
    
    result = {
        'type': 'hardware_check',
        'timestamp': status.timestamp,
        'overall': 'OK' if status.overall_ok else 'ISSUES',
        'checks': {
            'vision': 'OK' if status.vision_ok else 'ERROR',
            'wiring': 'OK' if status.wiring_ok else 'ISSUES',
            'leds': 'OK' if status.leds_ok else 'ISSUES',
            'motors': 'OK' if status.motors_ok else 'WAITING',
        },
        'messages': status.messages
    }
    
    return result


def openclaw_action_handler(vision: OpenClawVision, action: str) -> str:
    """
    OpenClaw 动作处理
    
    支持的动作:
    - check: 检查硬件
    - wait_ok: 等待正常
    - screenshot: 截图
    - status: 获取状态
    """
    
    if action == 'check':
        result = openclaw_hardware_check(vision)
        return json.dumps(result, ensure_ascii=False)
    
    elif action == 'wait_ok':
        ok = vision.wait_for_ok(timeout=30)
        return json.dumps({'action': 'wait_ok', 'result': ok}, ensure_ascii=False)
    
    elif action == 'screenshot':
        filename = vision.save_screenshot()
        return json.dumps({'action': 'screenshot', 'result': filename}, ensure_ascii=False)
    
    elif action == 'status':
        return json.dumps({'action': 'status', 'message': vision.get_status_message()}, ensure_ascii=False)
    
    else:
        return json.dumps({'action': 'unknown', 'action': action}, ensure_ascii=False)


# ============ 主测试 ============

if __name__ == "__main__":
    print("="*60)
    print("  OpenClaw 视觉集成测试")
    print("="*60)
    
    vision = OpenClawVision(camera_id=0)
    
    try:
        vision.start(blocking=False)
        
        # 测试检查
        print("\n检查硬件状态...")
        time.sleep(2)
        
        status = vision.check()
        print(f"\n状态: {vision.get_status_message()}")
        print(f"  视觉: {'✅' if status.vision_ok else '❌'}")
        print(f"  连线: {'✅' if status.wiring_ok else '❌'}")
        print(f"  LED: {'✅' if status.leds_ok else '❌'}")
        print(f"  电机: {'✅' if status.motors_ok else '❌'}")
        
        # 测试 OpenClaw 消息
        print("\n生成 OpenClaw 消息...")
        msg = openclaw_action_handler(vision, 'check')
        print(msg)
        
        vision.stop()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
        vision.stop()
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n提示: 请确保摄像头已连接")
