#!/usr/bin/env python3
"""
实时数据监控器
==============
功能:
- 串口数据实时接收和解析
- 实时曲线显示
- 关键指标监控
- 数据记录 (CSV)
- 异常报警

使用:
    python realtime_monitor.py --port COM3
    python realtime_monitor.py --port COM3 --plot
    python realtime_monitor.py --port COM3 --plot --camera 0
"""

import serial
import time
import argparse
import json
import csv
import threading
import queue
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import numpy as np

# ============ 颜色输出 ============
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def log(msg: str, color=Colors.BLUE):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{color}[{ts}] {msg}{Colors.ENDC}")

# ============ 数据结构 ============
@dataclass
class IMUData:
    """IMU数据"""
    ax: float = 0
    ay: float = 0
    az: float = 0
    gx: float = 0
    gy: float = 0
    gz: float = 0
    timestamp: float = 0

@dataclass
class MotorData:
    """电机数据"""
    left_speed: int = 0
    right_speed: int = 0
    left_current: float = 0
    right_current: float = 0
    timestamp: float = 0

@dataclass
class SystemData:
    """系统数据"""
    battery_voltage: float = 0
    cpu_usage: float = 0
    memory_usage: float = 0
    uptime_ms: int = 0
    timestamp: float = 0

@dataclass
class RobotState:
    """机器人完整状态"""
    imu: IMUData = field(default_factory=IMUData)
    motor: MotorData = field(default_factory=MotorData)
    system: SystemData = field(default_factory=SystemData)
    error_count: int = 0
    rssi: float = 0

# ============ 串口解析器 ============
class SerialParser:
    """串口数据解析器"""
    
    # 解析函数注册表
    parsers: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, prefix: str):
        """装饰器注册解析器"""
        def decorator(func):
            cls.parsers[prefix] = func
            return func
        return decorator
    
    @classmethod
    def parse(cls, line: str) -> Optional[Dict]:
        """解析一行数据"""
        for prefix, parser in cls.parsers.items():
            if line.startswith(prefix):
                try:
                    return parser(line)
                except Exception as e:
                    log(f"解析错误: {e}", Colors.WARNING)
                    return None
        return None


@SerialParser.register("IMU[")
def parse_imu(line: str) -> Dict:
    """解析IMU数据: IMU[AX=-123,AY=45,AZ=1000,GX=0,GY=0,GZ=0]"""
    data = {}
    content = line[4:-1]  # 去掉 "IMU[" 和 "]"
    for item in content.split(','):
        if '=' in item:
            k, v = item.split('=', 1)
            data[k.strip()] = float(v)
    return {'type': 'imu', 'data': data}


@SerialParser.register("MOTOR[")
def parse_motor(line: str) -> Dict:
    """解析电机数据: MOTOR[L=500,R=500]"""
    data = {}
    content = line[6:-1]
    for item in content.split(','):
        if '=' in item:
            k, v = item.split('=', 1)
            data[k.strip()] = float(v)
    return {'type': 'motor', 'data': data}


@SerialParser.register("BAT[")
def parse_battery(line: str) -> Dict:
    """解析电池数据: BAT[3850mV]"""
    data = {}
    content = line[4:-1]
    if 'mV' in content:
        data['voltage_mv'] = float(content.replace('mV', ''))
    elif 'V' in content:
        data['voltage_v'] = float(content.replace('V', ''))
    return {'type': 'battery', 'data': data}


@SerialParser.register("NCA[")
def parse_nca(line: str) -> Dict:
    """解析NCA数据: NCA[input=[0.1,0.2,...],output=[0.5,0.3]]"""
    content = line[4:-1]
    return {'type': 'nca', 'raw': content}


@SerialParser.register("RSSI[")
def parse_rssi(line: str) -> Dict:
    """解析RSSI数据: RSSI[-65dBm]"""
    content = line[5:-1]
    return {'type': 'rssi', 'data': {'dbm': float(content.replace('dBm', ''))}}


@SerialParser.register("ERR[")
def parse_error(line: str) -> Dict:
    """解析错误数据: ERR[TIMEOUT]"""
    content = line[4:-1]
    return {'type': 'error', 'data': {'code': content}}


# ============ 实时监控器 ============
class RealtimeMonitor:
    """实时数据监控器"""
    
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.running = False
        
        # 数据队列
        self.data_queue = queue.Queue()
        
        # 状态历史
        self.history: Dict[str, List] = {
            'imu_ax': [], 'imu_ay': [], 'imu_az': [],
            'motor_l': [], 'motor_r': [],
            'battery': [],
            'rssi': [],
            'timestamps': []
        }
        self.max_history = 1000
        
        # 统计
        self.stats = {
            'bytes_received': 0,
            'packets_received': 0,
            'errors': 0,
            'start_time': None
        }
        
        # 回调函数
        self.on_data_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        
        # CSV记录
        self.csv_writer = None
        self.csv_file = None
    
    def start(self, log_file: Optional[str] = None):
        """启动监控"""
        self.running = True
        self.stats['start_time'] = time.time()
        
        # 打开CSV文件
        if log_file:
            self.csv_file = open(log_file, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                'timestamp', 'type',
                'ax', 'ay', 'az', 'gx', 'gy', 'gz',
                'motor_l', 'motor_r',
                'battery_v', 'rssi'
            ])
        
        # 启动接收线程
        self.rx_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.rx_thread.start()
        
        # 启动处理线程
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        log(f"监控已启动: {self.port} @ {self.baud}bps")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.csv_file:
            self.csv_file.close()
        log("监控已停止")
    
    def _receive_loop(self):
        """接收数据线程"""
        try:
            with serial.Serial(self.port, self.baud, timeout=1) as ser:
                while self.running:
                    if ser.in_waiting:
                        line = ser.readline().decode(errors='ignore').strip()
                        self.stats['bytes_received'] += len(line.encode())
                        self.data_queue.put(line)
                    else:
                        time.sleep(0.01)
        except serial.SerialException as e:
            log(f"串口错误: {e}", Colors.FAIL)
            self.stats['errors'] += 1
    
    def _process_loop(self):
        """处理数据线程"""
        while self.running:
            try:
                line = self.data_queue.get(timeout=1)
                self._parse_and_store(line)
            except queue.Empty:
                continue
    
    def _parse_and_store(self, line: str):
        """解析并存储数据"""
        result = SerialParser.parse(line)
        
        if result:
            self.stats['packets_received'] += 1
            ts = time.time() - self.stats['start_time']
            
            # 更新历史
            if result['type'] == 'imu':
                data = result['data']
                self.history['imu_ax'].append(data.get('AX', 0))
                self.history['imu_ay'].append(data.get('AY', 0))
                self.history['imu_az'].append(data.get('AZ', 0))
                self._trim_history()
            
            elif result['type'] == 'motor':
                data = result['data']
                self.history['motor_l'].append(data.get('L', 0))
                self.history['motor_r'].append(data.get('R', 0))
                self._trim_history()
            
            elif result['type'] == 'battery':
                v = result['data'].get('voltage_mv', 0) / 1000
                self.history['battery'].append(v)
                self._trim_history()
            
            elif result['type'] == 'rssi':
                self.history['rssi'].append(result['data']['dbm'])
                self._trim_history()
            
            self.history['timestamps'].append(ts)
            
            # 写CSV
            if self.csv_writer:
                self.csv_writer.writerow([
                    datetime.now().isoformat(),
                    result['type'],
                    *self.history['imu_ax'][-1:],
                    *self.history['motor_l'][-1:],
                    self.history['battery'][-1] if self.history['battery'] else 0,
                    self.history['rssi'][-1] if self.history['rssi'] else 0
                ])
            
            # 回调
            for cb in self.on_data_callbacks:
                cb(result)
        
        self.stats['bytes_received'] += len(line)
    
    def _trim_history(self):
        """修剪历史数据"""
        for key in self.history:
            if key != 'timestamps' and len(self.history[key]) > self.max_history:
                self.history[key].pop(0)
    
    def get_state(self) -> RobotState:
        """获取当前状态"""
        return RobotState(
            imu=IMUData(
                ax=self.history['imu_ax'][-1] if self.history['imu_ax'] else 0,
                ay=self.history['imu_ay'][-1] if self.history['imu_ay'] else 0,
                az=self.history['imu_az'][-1] if self.history['imu_az'] else 0,
            ),
            motor=MotorData(
                left_speed=int(self.history['motor_l'][-1]) if self.history['motor_l'] else 0,
                right_speed=int(self.history['motor_r'][-1]) if self.history['motor_r'] else 0,
            ),
            system=SystemData(
                battery_voltage=self.history['battery'][-1] if self.history['battery'] else 0,
            ),
            rssi=self.history['rssi'][-1] if self.history['rssi'] else 0,
        )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        elapsed = time.time() - self.stats['start_time']
        return {
            'duration_s': elapsed,
            'bytes': self.stats['bytes_received'],
            'packets': self.stats['packets_received'],
            'bytes_per_sec': self.stats['bytes_received'] / elapsed if elapsed > 0 else 0,
            'errors': self.stats['errors'],
        }
    
    def register_on_data(self, callback: Callable):
        """注册数据回调"""
        self.on_data_callbacks.append(callback)
    
    def register_on_error(self, callback: Callable):
        """注册错误回调"""
        self.on_error_callbacks.append(callback)


# ============ 终端显示 ============
class TerminalDisplay:
    """终端实时显示"""
    
    def __init__(self, monitor: RealtimeMonitor):
        self.monitor = monitor
    
    def run(self):
        """运行显示循环"""
        print("\n" * 50)  # 清屏
        print("\r" * 1000, end='')
        
        while True:
            try:
                state = self.monitor.get_state()
                stats = self.monitor.get_stats()
                
                # 清除旧内容
                print("\r" * 1000, end='')
                
                # 显示状态
                status = f"""
╔══════════════════════════════════════════════════════════════╗
║                    实时数据监控 - v1.0                       ║
╠══════════════════════════════════════════════════════════════╣
║ 运行时长: {stats['duration_s']:>8.1f}s  |  字节: {stats['bytes']:>8}  |  包: {stats['packets']:>6}     ║
╠══════════════════════════════════════════════════════════════╣
║ IMU (mg)                                                     ║
║   AX: {state.imu.ax:>7.0f}   AY: {state.imu.ay:>7.0f}   AZ: {state.imu.az:>7.0f}                ║
╠══════════════════════════════════════════════════════════════╣
║ 电机                                                          ║
║   左: {state.motor.left_speed:>6d}   右: {state.motor.right_speed:>6d}                     ║
╠══════════════════════════════════════════════════════════════╣
║ 电池: {state.system.battery_voltage:>5.2f}V  |  RSSI: {state.rssi:>5.0f}dBm              ║
╚══════════════════════════════════════════════════════════════╝
逐帧数据流: 接收中...
""")
                print(status, end='', flush=True)
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\n\n监控已停止")
                break


# ============ 绘图器 (可选) ============
class LivePlotter:
    """实时绘图器 (需要 matplotlib)"""
    
    def __init__(self, monitor: RealtimeMonitor):
        self.monitor = monitor
        self.fig = None
        self.axes = {}
    
    def start(self):
        """启动绘图"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation
            
            self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
            self.fig.suptitle('实时数据监控')
            
            # IMU图
            self.axes[0,0].set_title('IMU 加速度')
            self.ax_line, = self.axes[0,0].plot([], [], 'r-', label='AX')
            self.ay_line, = self.axes[0,0].plot([], [], 'g-', label='AY')
            self.az_line, = self.axes[0,0].plot([], [], 'b-', label='AZ')
            self.axes[0,0].legend()
            
            # 电机图
            self.axes[0,1].set_title('电机速度')
            self.l_line, = self.axes[0,1].plot([], [], 'r-', label='左')
            self.r_line, = self.axes[0,1].plot([], [], 'b-', label='右')
            self.axes[0,1].legend()
            
            # 电池图
            self.axes[1,0].set_title('电池电压')
            self.bat_line, = self.axes[1,0].plot([], [], 'g-')
            
            # RSSI图
            self.axes[1,1].set_title('RSSI')
            self.rssi_line, = self.axes[1,1].plot([], [], 'm-')
            
            # 动画更新
            ani = animation.FuncAnimation(
                self.fig, self._update, interval=100, blit=True
            )
            
            plt.show()
            
        except ImportError:
            print("请安装 matplotlib: pip install matplotlib")
    
    def _update(self, frame):
        """更新图表"""
        h = self.monitor.history
        
        def update_line(line, data):
            line.set_data(range(len(data)), data)
            line.axes.set_xlim(0, min(len(data), 100))
            line.axes.set_ylim(min(data), max(data) if data else (0, 1))
            return line,
        
        update_line(self.ax_line, h['imu_ax'])
        update_line(self.ay_line, h['imu_ay'])
        update_line(self.az_line, h['imu_az'])
        update_line(self.l_line, h['motor_l'])
        update_line(self.r_line, h['motor_r'])
        update_line(self.bat_line, h['battery'])
        update_line(self.rssi_line, h['rssi'])
        
        return list(self.axes.flat)


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(description="实时数据监控器")
    parser.add_argument('--port', default='COM3', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--log', help='记录到CSV文件')
    parser.add_argument('--plot', action='store_true', help='显示实时曲线')
    args = parser.parse_args()
    
    # 创建监控器
    monitor = RealtimeMonitor(args.port, args.baud)
    
    # 启动
    monitor.start(log_file=args.log)
    
    try:
        if args.plot:
            # 带绘图
            plotter = LivePlotter(monitor)
            plotter.start()
        else:
            # 纯终端显示
            display = TerminalDisplay(monitor)
            display.run()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    main()
