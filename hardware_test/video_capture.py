#!/usr/bin/env python3
"""
视频录制与状态检测
==================
功能:
- 摄像头实时录制
- 动作检测 (OpenCV)
- 状态标注
- 自动保存 (带时间戳)

使用:
    python video_capture.py
    python video_capture.py --device 0
    python video_capture.py --output robot_test_20260218.mp4
"""

import cv2
import time
import argparse
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np


@dataclass
class FrameInfo:
    """帧信息"""
    timestamp: float
    frame_idx: int
    motion_detected: bool
    has_robot: bool
    roi: Tuple[int, int, int, int]  # x, y, w, h


class VideoRecorder:
    """视频录制器"""
    
    def __init__(self, 
                 output_path: str,
                 fps: int = 30,
                 resolution: Tuple[int, int] = (1280, 720)):
        self.output_path = output_path
        self.fps = fps
        self.resolution = resolution
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.writer = None
        self.running = False
        self.frame_idx = 0
        self.start_time = 0
        
        # 运动检测
        self.mog2 = cv2.createBackgroundSubtractorMOG2()
        self.prev_frame = None
        self.motion_threshold = 5000  # 像素变化阈值
        
        # 状态
        self.is_recording = False
        self.roi = (0, 0, 0, 0)
        self.motion_score = 0
    
    def start(self, device: int = 0) -> bool:
        """启动录制"""
        self.cap = cv2.VideoCapture(device)
        
        if not self.cap.isOpened():
            print(f"[ERROR] 无法打开摄像头: {device}")
            return False
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            self.output_path, fourcc, self.fps, self.resolution
        )
        
        if not self.writer.isOpened():
            print(f"[ERROR] 无法创建视频文件: {self.output_path}")
            return False
        
        self.running = True
        self.start_time = time.time()
        
        print(f"[INFO] 开始录制: {self.output_path}")
        print(f"[INFO] 分辨率: {self.resolution}, FPS: {self.fps}")
        
        return True
    
    def stop(self):
        """停止录制"""
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.writer:
            self.writer.release()
        
        duration = time.time() - self.start_time
        print(f"[INFO] 录制完成: {self.output_path}")
        print(f"[INFO] 时长: {duration:.1f}s, 帧数: {self.frame_idx}")
    
    def process_frame(self, frame) -> Tuple[FrameInfo, frame]:
        """处理帧"""
        self.frame_idx += 1
        timestamp = time.time() - self.start_time
        
        # 运动检测
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        motion_detected = False
        if self.prev_frame is not None:
            diff = cv2.absdiff(self.prev_frame, gray)
            self.motion_score = cv2.sumElems(diff)[0]
            motion_detected = self.motion_score > self.motion_threshold
        
        self.prev_frame = gray
        
        # 机器人检测 (简化: 检测绿色区域)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (30, 50, 50), (90, 255, 255))
        
        # 找最大轮廓
        contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        has_robot = len(contours) > 0
        
        if contours:
            # 取最大轮廓作为ROI
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            if cv2.contourArea(largest) > 1000:  # 忽略小区域
                self.roi = (x, y, w, h)
        
        info = FrameInfo(
            timestamp=timestamp,
            frame_idx=self.frame_idx,
            motion_detected=motion_detected,
            has_robot=has_robot,
            roi=self.roi
        )
        
        return info, frame
    
    def record(self, frame):
        """录制帧"""
        if self.writer and self.is_recording:
            self.writer.write(frame)
    
    def annotate(self, frame, info: FrameInfo, overlay_text: str = "") -> frame:
        """标注帧"""
        # 绘制ROI
        x, y, w, h = info.roi
        if w > 0 and h > 0:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # 状态指示
        if info.motion_detected:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)  # 红色: 运动中
        
        if info.has_robot:
            cv2.circle(frame, (60, 30), 10, (0, 255, 0), -1)  # 绿色: 检测到机器人
        
        # 时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cv2.putText(frame, timestamp, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 帧率
        fps = info.frame_idx / info.timestamp if info.timestamp > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 额外文本
        if overlay_text:
            cv2.putText(frame, overlay_text, (10, frame.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return frame
    
    def run_loop(self):
        """主循环"""
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                print("[ERROR] 读取帧失败")
                break
            
            info, processed = self.process_frame(frame)
            annotated = self.annotate(processed, info)
            
            # 显示
            cv2.imshow('Robot Camera', annotated)
            
            # 自动录制
            self.is_recording = True
            self.record(annotated)
            
            # 按键处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):  # 空格暂停
                self.is_recording = not self.is_recording
                print(f"[INFO] 录制: {'ON' if self.is_recording else 'OFF'}")
        
        self.stop()
        cv2.destroyAllWindows()


class RobotTracker:
    """机器人追踪器"""
    
    def __init__(self):
        self.positions: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
        self.velocity_history: List[float] = []
    
    def update(self, roi: Tuple[int, int, int, int], timestamp: float):
        """更新位置"""
        x, y, w, h = roi
        center_x = x + w // 2
        center_y = y + h // 2
        
        self.positions.append((center_x, center_y, timestamp))
        
        # 计算速度
        if len(self.positions) >= 2:
            prev = self.positions[-2]
            dx = center_x - prev[0]
            dy = center_y - prev[1]
            dt = timestamp - prev[2]
            if dt > 0:
                velocity = np.sqrt(dx**2 + dy**2) / dt
                self.velocity_history.append(velocity)
    
    def get_trajectory(self) -> np.ndarray:
        """获取轨迹"""
        if len(self.positions) < 2:
            return np.array([])
        
        points = np.array([p[:2] for p in self.positions])
        return points
    
    def get_stats(self) -> dict:
        """获取统计"""
        if not self.velocity_history:
            return {'avg_velocity': 0, 'max_velocity': 0, 'distance': 0}
        
        return {
            'avg_velocity': np.mean(self.velocity_history),
            'max_velocity': np.max(self.velocity_history),
            'distance': np.sum(self.velocity_history) / len(self.velocity_history),
        }


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(description="视频录制与状态检测")
    parser.add_argument('--device', type=int, default=0, help='摄像头设备号')
    parser.add_argument('--output', help='输出文件名 (默认: auto)')
    parser.add_argument('--fps', type=int, default=30, help='帧率')
    parser.add_argument('--width', type=int, default=1280, help='宽度')
    parser.add_argument('--height', type=int, default=720, help='高度')
    args = parser.parse_args()
    
    # 生成输出文件名
    if args.output:
        output = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"videos/robot_{timestamp}.mp4"
    
    # 确保目录存在
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    
    # 创建录制器
    recorder = VideoRecorder(
        output_path=output,
        fps=args.fps,
        resolution=(args.width, args.height)
    )
    
    # 启动
    if recorder.start(args.device):
        recorder.run_loop()


if __name__ == "__main__":
    main()
