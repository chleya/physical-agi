#!/usr/bin/env python3
"""
实时示波器
==========
功能:
- ADC 波形实时显示
- PWM 信号捕获
- 多通道对比
- 触发功能
- 数据导出

使用:
    python realtime_oscope.py
    python realtime_oscope.py --channel ADC1 --port COM3
"""

import serial
import time
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
from dataclasses import dataclass
from typing import List, Optional, Callable
from collections import deque
import threading


@dataclass
class ChannelConfig:
    """通道配置"""
    name: str
    color: str
    scale: float = 1.0
    offset: float = 0.0
    enabled: bool = True


class OScopeChannel:
    """示波器通道"""
    
    def __init__(self, config: ChannelConfig, buffer_size: int = 1000):
        self.config = config
        self.buffer = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)
        self.trigger_level = None
        self.triggered = False
        self.trigger_count = 0
    
    def add_data(self, value: float, timestamp: float):
        """添加数据点"""
        self.buffer.append(value * self.config.scale + self.config.offset)
        self.timestamps.append(timestamp)
    
    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()
        self.timestamps.clear()
        self.triggered = False
        self.trigger_count = 0


class RealtimeOscope:
    """实时示波器"""
    
    def __init__(self, port: str = 'COM3', baud: int = 115200):
        self.port = port
        self.baud = baud
        self.channels: List[OScopeChannel] = []
        self.running = False
        self.serial_thread = None
        self.start_time = 0
        
        # 触发设置
        self.trigger_channel = None
        self.trigger_edge = 'rising'  # rising, falling, both
        self.trigger_level = 0.0
        self.triggered = False
        self.auto_trigger_ms = 100  # 自动触发间隔
        
        # 统计
        self.sample_count = 0
        self.sample_rate = 0.0
        self.last_rate_check = 0
        
        # 回调
        self.on_data_callbacks: List[Callable] = []
    
    def add_channel(self, name: str, color: str, scale: float = 1.0) -> OScopeChannel:
        """添加通道"""
        config = ChannelConfig(name=name, color=color, scale=scale)
        channel = OScopeChannel(config)
        self.channels.append(channel)
        return channel
    
    def set_trigger(self, channel_name: str, level: float, edge: str = 'rising'):
        """设置触发"""
        for ch in self.channels:
            if ch.config.name == channel_name:
                self.trigger_channel = ch
                self.trigger_level = level
                self.trigger_edge = edge
                return True
        return False
    
    def start(self):
        """启动采集"""
        self.running = True
        self.start_time = time.time()
        self.serial_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.serial_thread.start()
    
    def stop(self):
        """停止采集"""
        self.running = False
        if self.serial_thread:
            self.serial_thread.join(timeout=1)
    
    def _read_loop(self):
        """读取循环"""
        try:
            with serial.Serial(self.port, self.baud, timeout=1) as ser:
                while self.running:
                    if ser.in_waiting:
                        line = ser.readline().decode(errors='ignore').strip()
                        self._parse_data(line)
                    else:
                        time.sleep(0.001)
        except serial.SerialException as e:
            print(f"[ERROR] 串口错误: {e}")
    
    def _parse_data(self, line: str):
        """解析数据"""
        # 格式: CH1=123,CH2=456,TIME=789
        if '=' not in line:
            return
        
        timestamp = time.time() - self.start_time
        
        try:
            for part in line.split(','):
                if '=' in part:
                    name, value = part.split('=', 1)
                    value = float(value)
                    
                    for ch in self.channels:
                        if ch.config.name == name and ch.config.enabled:
                            ch.add_data(value, timestamp)
                            
                            # 触发检测
                            if self.trigger_channel and ch == self.trigger_channel:
                                self._check_trigger(value)
                            
                            break
            
            self.sample_count += 1
            self._update_rate()
            
        except ValueError:
            pass
    
    def _check_trigger(self, value: float):
        """触发检测"""
        if not self.trigger_channel:
            return
        
        if self.trigger_edge == 'rising' and value >= self.trigger_level:
            if not self.trigger_channel.triggered:
                self.trigger_channel.triggered = True
                self.trigger_channel.trigger_count += 1
        elif self.trigger_edge == 'falling' and value <= self.trigger_level:
            if not self.trigger_channel.triggered:
                self.trigger_channel.triggered = True
                self.trigger_channel.trigger_count += 1
        elif self.trigger_edge == 'both':
            if not self.trigger_channel.triggered:
                self.trigger_channel.triggered = True
                self.trigger_channel.trigger_count += 1
    
    def _update_rate(self):
        """更新采样率"""
        now = time.time()
        if now - self.last_rate_check > 1.0:
            self.sample_rate = self.sample_count / (now - self.last_rate_check)
            self.sample_count = 0
            self.last_rate_check = now
    
    def get_data(self, channel_name: str) -> tuple:
        """获取通道数据"""
        for ch in self.channels:
            if ch.config.name == channel_name:
                return list(ch.timestamps), list(ch.buffer)
        return [], []
    
    def get_stats(self) -> dict:
        """获取统计"""
        return {
            'sample_rate': self.sample_rate,
            'samples_total': sum(len(ch.buffer) for ch in self.channels),
            'trigger_count': sum(ch.trigger_count for ch in self.channels),
            'running': self.running
        }


class OscopeVisualizer:
    """示波器可视化"""
    
    def __init__(self, scope: RealtimeOscope):
        self.scope = scope
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.canvas.manager.set_window_title('实时示波器')
        
        # 设置样式
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('gray')
        
        self.lines = []
        self.setup_plot()
        
        # 按钮
        self.ax_pause = plt.axes([0.45, 0.02, 0.1, 0.05])
        self.btn_pause = Button(self.ax_pause, '暂停', color='gray', hovercolor='0.8')
        self.btn_pause.on_clicked(self.toggle_pause)
        
        self.paused = False
        
        # 动画
        self.ani = animation.FuncAnimation(
            self.fig, self.update, interval=50, blit=True
        )
    
    def setup_plot(self):
        """设置图表"""
        self.ax.set_title('实时示波器', color='white', fontsize=14)
        self.ax.set_xlabel('时间 (s)', color='white')
        self.ax.set_ylabel('电压 (V)', color='white')
        self.ax.grid(True, alpha=0.3, color='gray')
        
        # 创建线
        for ch in self.scope.channels:
            line, = self.ax.plot([], [], 
                                 color=ch.config.color, 
                                 linewidth=1.5,
                                 label=ch.config.name)
            self.lines.append(line)
        
        self.ax.legend(loc='upper right', facecolor='#2e2e2e', 
                      labelcolor='white')
    
    def toggle_pause(self, event):
        """暂停/继续"""
        self.paused = not self.paused
        self.btn_pause.label.set_text('继续' if self.paused else '暂停')
    
    def update(self, frame):
        """更新图表"""
        if self.paused:
            return self.lines
        
        for i, ch in enumerate(self.scope.channels):
            if ch.config.enabled and len(ch.buffer) > 1:
                self.lines[i].set_data(list(ch.timestamps), list(ch.buffer))
                
                # 自动缩放
                y_data = list(ch.buffer)
                if y_data:
                    y_min = min(y_data)
                    y_max = max(y_data)
                    y_range = max(y_max - y_min, 0.1)
                    self.ax.set_ylim(y_min - y_range*0.1, y_max + y_range*0.1)
        
        # 自动滚动 x 轴
        for line in self.lines:
            x_data = line.get_xdata()
            if len(x_data) > 1:
                self.ax.set_xlim(x_data[0], x_data[-1])
        
        # 更新标题
        stats = self.scope.get_stats()
        self.ax.set_title(f'实时示波器 - 采样率: {stats["sample_rate"]:.1f} Hz', 
                         color='white')
        
        return self.lines
    
    def show(self):
        """显示"""
        plt.tight_layout()
        plt.show()
    
    def save(self, filename: str, duration: float = 5.0):
        """保存波形"""
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        
        canvas = FigureCanvas(self.fig)
        canvas.draw()
        
        # 截取最近的数据
        data = {}
        for i, ch in enumerate(self.scope.channels):
            if len(ch.buffer) > 0:
                data[ch.config.name] = {
                    'timestamps': list(ch.timestamps),
                    'values': list(ch.buffer)
                }
        
        # 保存为 PNG
        self.fig.savefig(filename, dpi=100, facecolor='#1e1e1e')
        print(f"[INFO] 波形已保存: {filename}")
        
        # 保存数据
        import json
        json_path = filename.replace('.png', '.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[INFO] 数据已保存: {json_path}")


def parse_adc_data(data: str) -> dict:
    """解析ADC数据"""
    result = {}
    for part in data.split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            try:
                result[k.strip()] = float(v)
            except:
                pass
    return result


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(description="实时示波器")
    parser.add_argument('--port', default='COM3', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--save', help='保存文件名')
    parser.add_argument('--duration', type=float, default=5.0, help='保存时长')
    args = parser.parse_args()
    
    # 创建示波器
    scope = RealtimeOscope(port=args.port, baud=args.baud)
    
    # 添加通道
    scope.add_channel('ADC1', 'red', scale=0.001)  # mV -> V
    scope.add_channel('ADC2', 'blue', scale=0.001)
    scope.add_channel('ADC3', 'green', scale=0.001)
    
    print("="*50)
    print("  实时示波器")
    print("="*50)
    print("通道: ADC1 (红), ADC2 (蓝), ADC3 (绿)")
    print("控制: 空格暂停, S 保存, Q 退出")
    print("="*50)
    
    # 启动
    scope.start()
    
    # 可视化
    viz = OscopeVisualizer(scope)
    
    # 键盘控制
    def on_key(event):
        if event.key == ' ':
            viz.toggle_pause(None)
        elif event.key == 's' or event.key == 'S':
            viz.save(f'waveform_{int(time.time())}.png')
        elif event.key == 'q' or event.key == 'Q':
            scope.stop()
            plt.close()
    
    viz.fig.canvas.mpl_connect('key_press_event', on_key)
    
    try:
        viz.show()
    except KeyboardInterrupt:
        scope.stop()
        print("\n已停止")


if __name__ == "__main__":
    main()
