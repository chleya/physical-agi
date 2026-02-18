#!/usr/bin/env python3
"""
硬件视觉检测器
==============
功能:
- 摄像头实时检测
- LED 状态识别
- 电机转动检测
- 连线状态检测
- 实时反馈给 OpenClaw

使用:
    python vision_inspector.py --camera 0
    python vision_inspector.py --camera 0 --check-wiring
    python vision_inspector.py --camera 0 --openclaw-mode
"""

import cv2
import numpy as np
import time
import argparse
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
import threading
import queue


class ComponentType(Enum):
    """组件类型"""
    LED = "led"
    MOTOR = "motor"
    BOARD = "board"
    WIRE = "wire"
    DISPLAY = "display"


@dataclass
class DetectedComponent:
    """检测到的组件"""
    type: ComponentType
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    state: str  # "on", "off", "rotating", "static"
    color: Optional[Tuple[int, int, int]] = None
    label: str = ""


@dataclass
class InspectionResult:
    """检测结果"""
    timestamp: str
    components: List[DetectedComponent]
    wiring_ok: bool
    leds_ok: bool
    motors_ok: bool
    overall_status: str  # "OK", "WARNING", "ERROR"
    messages: List[str]


class ColorDetector:
    """颜色检测器"""
    
    # 常见颜色范围 (HSV)
    COLOR_RANGES = {
        'red': ([0, 120, 70], [10, 255, 255]),
        'red2': ([170, 120, 70], [180, 255, 255]),
        'green': ([40, 70, 70], [90, 255, 255]),
        'blue': ([100, 150, 0], [140, 255, 255]),
        'yellow': ([20, 100, 100], [30, 255, 255]),
        'white': ([0, 0, 200], [180, 30, 255]),
        'black': ([0, 0, 0], [180, 255, 30]),
    }
    
    @classmethod
    def detect_color(cls, hsv: np.ndarray, color_name: str) -> List[Tuple[int, int, int]]:
        """检测指定颜色的轮廓"""
        ranges = cls.COLOR_RANGES.get(color_name, [])
        if not ranges:
            return []
        
        lower = np.array(ranges[0], dtype=np.uint8)
        upper = np.array(ranges[1], dtype=np.uint8)
        
        mask = cv2.inRange(hsv, lower, upper)
        
        # 形态学处理
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 忽略太小的区域
                x, y, w, h = cv2.boundingRect(contour)
                center = (int(x + w/2), int(y + h/2))
                results.append((center, area))
        
        return results


class LEDDetector:
    """LED 状态检测器"""
    
    def __init__(self):
        self.led_states = {}  # {led_id: "on"/"off"}
        self.history = []
    
    def detect(self, frame: np.ndarray) -> List[DetectedComponent]:
        """检测 LED 状态"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        detected = []
        
        # 检测红色 LED (亮/灭)
        red_contours = ColorDetector.detect_color(hsv, 'red')
        red_contours2 = ColorDetector.detect_color(hsv, 'red2')
        all_red = red_contours + red_contours2
        
        for center, area in all_red[:5]:  # 最多5个LED
            x = center[0] - 15
            y = center[1] - 15
            w, h = 30, 30
            
            # 检测亮度来判断开关
            roi = frame[max(0,y):y+h, max(0,x):x+w]
            if roi.size > 0:
                brightness = cv2.mean(roi)[0]
                state = "on" if brightness > 100 else "off"
                
                detected.append(DetectedComponent(
                    type=ComponentType.LED,
                    bounding_box=(x, y, w, h),
                    confidence=min(area / 500, 1.0),
                    state=state,
                    color=(0, 0, 255),
                    label=f"LED-{state}"
                ))
        
        return detected


class MotorDetector:
    """电机状态检测器"""
    
    def __init__(self):
        self.prev_frame = None
        self.motion_history = []
    
    def detect(self, frame: np.ndarray) -> List[DetectedComponent]:
        """检测电机转动"""
        detected = []
        
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            return detected
        
        # 计算差异
        gray1 = cv2.cvtColor(self.prev_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
        
        diff = cv2.absdiff(gray1, gray2)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # 忽略太小的运动
                x, y, w, h = cv2.boundingRect(contour)
                
                # 分类运动类型
                if area > 5000:
                    state = "rotating_fast"
                elif area > 2000:
                    state = "rotating"
                else:
                    state = "moving"
                
                detected.append(DetectedComponent(
                    type=ComponentType.MOTOR,
                    bounding_box=(x, y, w, h),
                    confidence=min(area / 10000, 1.0),
                    state=state,
                    color=(0, 255, 0) if "rotating" in state else (255, 0, 0),
                    label=f"Motor-{state}"
                ))
        
        self.prev_frame = frame.copy()
        return detected


class WiringInspector:
    """连线检测器"""
    
    def __init__(self):
        self.wire_segments = []
        self.connected_components = {}
    
    def detect(self, frame: np.ndarray) -> Dict:
        """检测连线状态"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检测不同颜色的线
        colors = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'yellow': (0, 255, 255),
            'black': (0, 0, 0),
            'white': (255, 255, 255),
        }
        
        detected_wires = {}
        
        for color_name, bgr in colors.items():
            contours = ColorDetector.detect_color(hsv, color_name)
            
            for center, area in contours:
                if color_name not in detected_wires:
                    detected_wires[color_name] = []
                
                detected_wires[color_name].append({
                    'center': center,
                    'area': area
                })
        
        # 分析连线完整性
        status = {
            'red_wires': len(detected_wires.get('red', [])),
            'black_wires': len(detected_wires.get('black', [])),
            'other_wires': sum(len(v) for k, v in detected_wires.items() 
                             if k not in ['red', 'black']),
            'details': detected_wires
        }
        
        return status
    
    def check_connections(self, frame: np.ndarray) -> Tuple[bool, List[str]]:
        """检查关键连接"""
        messages = []
        wiring_ok = True
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检查红色 (VCC) 线路
        red_wires = ColorDetector.detect_color(hsv, 'red')
        if len(red_wires) < 2:
            messages.append("⚠️ 检测到较少的红色电源线")
            wiring_ok = False
        
        # 检查黑色 (GND) 线路
        black_wires = ColorDetector.detect_color(hsv, 'black')
        if len(black_wires) < 2:
            messages.append("⚠️ 检测到较少的地线")
            wiring_ok = False
        
        # 检查是否有悬空线
        if abs(len(red_wires) - len(black_wires)) > 3:
            messages.append("⚠️ 红黑线数量不匹配，可能有悬空线")
            wiring_ok = False
        
        return wiring_ok, messages


class VisionInspector:
    """综合视觉检测器"""
    
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.cap = None
        
        self.led_detector = LEDDetector()
        self.motor_detector = MotorDetector()
        self.wiring_inspector = WiringInspector()
        
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=2)
        
        # 检测历史
        self.history: List[InspectionResult] = []
        
        # OpenClaw 反馈
        self.last_status = "UNKNOWN"
        self.last_messages = []
    
    def start(self):
        """启动检测"""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头: {self.camera_id}")
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.running = True
        
        # 启动检测线程
        self.detect_thread = threading.Thread(target=self._detect_loop, daemon=True)
        self.detect_thread.start()
        
        print(f"[INFO] 视觉检测已启动: 摄像头 {self.camera_id}")
    
    def stop(self):
        """停止检测"""
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        print("[INFO] 视觉检测已停止")
    
    def _detect_loop(self):
        """检测循环"""
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                print("[ERROR] 无法读取帧")
                break
            
            # 缩小处理
            small_frame = cv2.resize(frame, (640, 360))
            
            # 并行检测
            leds = self.led_detector.detect(small_frame)
            motors = self.motor_detector.detect(small_frame)
            wiring_status = self.wiring_inspector.detect(small_frame)
            wiring_ok, wiring_msgs = self.wiring_inspector.check_connections(small_frame)
            
            # 综合结果
            components = leds + motors
            
            leds_ok = all(c.state == "on" for c in components if c.type == ComponentType.LED)
            motors_ok = any("rotating" in c.state for c in components if c.type == ComponentType.MOTOR)
            
            if leds_ok and motors_ok:
                status = "OK"
            elif not components:
                status = "NO_COMPONENTS"
            elif not leds_ok:
                status = "WARNING"
            else:
                status = "WARNING"
            
            result = InspectionResult(
                timestamp=datetime.now().isoformat(),
                components=components,
                wiring_ok=wiring_ok,
                leds_ok=leds_ok,
                motors_ok=motors_ok,
                overall_status=status,
                messages=wiring_msgs
            )
            
            self.history.append(result)
            self.last_status = status
            self.last_messages = wiring_msgs
            
            # 放入队列
            if not self.result_queue.full():
                self.result_queue.put((frame, result))
            
            time.sleep(0.03)  # ~30 FPS
    
    def get_result(self, timeout: float = 1.0) -> Tuple[np.ndarray, InspectionResult]:
        """获取检测结果"""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None, None
    
    def get_status_for_openclaw(self) -> Dict:
        """获取适合 OpenClaw 读取的状态"""
        if not self.history:
            return {
                "status": "UNKNOWN",
                "messages": ["等待检测..."],
                "components": 0,
                "wiring_ok": False
            }
        
        latest = self.history[-1]
        
        return {
            "status": latest.overall_status,
            "messages": latest.messages,
            "components_found": len(latest.components),
            "leds_ok": latest.leds_ok,
            "motors_ok": latest.motors_ok,
            "wiring_ok": latest.wiring_ok,
            "timestamp": latest.timestamp
        }
    
    def draw_result(self, frame: np.ndarray, result: InspectionResult) -> np.ndarray:
        """绘制检测结果"""
        # 绘制组件
        for comp in result.components:
            x, y, w, h = comp.bounding_box
            
            # 颜色
            color = comp.color or (0, 255, 0)
            
            # 边框
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # 标签
            label = f"{comp.label} ({comp.confidence:.0%})"
            cv2.putText(frame, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 状态指示
        status_color = {
            "OK": (0, 255, 0),
            "WARNING": (0, 255, 255),
            "ERROR": (0, 0, 255),
            "UNKNOWN": (128, 128, 128),
        }.get(result.overall_status, (128, 128, 128))
        
        cv2.circle(frame, (30, 30), 15, status_color, -1)
        cv2.putText(frame, result.overall_status, (55, 38),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        
        # 消息
        for i, msg in enumerate(result.messages[:3]):
            cv2.putText(frame, msg, (10, frame.shape[0] - 60 + i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cv2.putText(frame, timestamp, (frame.shape[1]-250, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def run_interactive(self):
        """交互式运行"""
        print("\n" + "="*60)
        print("  硬件视觉检测器")
        print("  按 'Q' 退出, 'S' 保存截图")
        print("="*60 + "\n")
        
        while True:
            result = self.get_result(timeout=2.0)
            
            if result[0] is None:
                continue
            
            frame, inspection = result
            
            # 绘制结果
            annotated = self.draw_result(frame, inspection)
            
            # 显示
            cv2.imshow('Hardware Vision Inspector', annotated)
            
            # 获取 OpenClaw 状态
            status = self.get_status_for_openclaw()
            print(f"\r状态: {status['status']} | 组件: {status['components_found']} | 连线: {'✅' if status['wiring_ok'] else '❌'}", end='', flush=True)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, annotated)
                print(f"\n截图已保存: {filename}")
        
        self.stop()
        cv2.destroyAllWindows()
    
    def run_openclaw_mode(self, callback=None):
        """
        OpenClaw 模式 - 无头运行，定期输出状态
        
        Args:
            callback: 状态回调函数
        """
        print("\n" + "="*60)
        print("  OpenClaw 视觉反馈模式")
        print("  每秒输出一次状态给 OpenClaw")
        print("="*60 + "\n")
        
        last_output = time.time()
        
        while self.running:
            status = self.get_status_for_openclaw()
            
            # 每秒输出一次
            if time.time() - last_output > 1.0:
                output = {
                    "vision_status": status,
                    "components": status['components_found'],
                    "all_ok": (status['status'] == "OK" and 
                              status['wiring_ok'] and 
                              status['leds_ok'] and
                              status['motors_ok'])
                }
                
                print(f"[VISION] {json.dumps(output, ensure_ascii=False)}")
                
                if callback:
                    callback(output)
                
                last_output = time.time()
            
            time.sleep(0.1)
    
    def save_report(self, filename: str = None):
        """保存检测报告"""
        if filename is None:
            filename = f"vision_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(self.history),
            "ok_count": sum(1 for r in self.history if r.overall_status == "OK"),
            "warning_count": sum(1 for r in self.history if r.overall_status == "WARNING"),
            "error_count": sum(1 for r in self.history if r.overall_status == "ERROR"),
            "latest_status": self.last_status,
            "messages": self.last_messages
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] 报告已保存: {filename}")
        return filename


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(
        description="硬件视觉检测器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式检测
  python vision_inspector.py --camera 0
  
  # OpenClaw 模式 (无头，定期输出 JSON)
  python vision_inspector.py --camera 0 --openclaw-mode
  
  # 检查连线
  python vision_inspector.py --camera 0 --check-wiring

OpenClaw 集成:
  在 OpenClaw 中调用:
    from vision_inspector import VisionInspector
    inspector = VisionInspector(camera_id=0)
    inspector.start()
    status = inspector.get_status_for_openclaw()
        """
    )
    
    parser.add_argument('--camera', type=int, default=0, help='摄像头ID')
    parser.add_argument('--openclaw-mode', action='store_true', 
                       help='OpenClaw 无头模式')
    parser.add_argument('--check-wiring', action='store_true',
                       help='重点检查连线')
    parser.add_argument('--save-report', action='store_true',
                       help='保存检测报告')
    args = parser.parse_args()
    
    try:
        inspector = VisionInspector(camera_id=args.camera)
        inspector.start()
        
        if args.openclaw_mode:
            def print_callback(status):
                pass  # 已在 run_openclaw_mode 中打印
            inspector.run_openclaw_mode(callback=print_callback)
        else:
            inspector.run_interactive()
        
        if args.save_report:
            inspector.save_report()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
