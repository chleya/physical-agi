"""
信号处理模块
完全解耦，可独立使用
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """信号"""
    sender_id: str
    data: np.ndarray
    timestamp: float
    rssi: float = 0.0  # 信号强度


class SignalProcessor:
    """
    RSSI信号处理器
    
    功能:
    - RSSI计算
    - 信号衰减模拟
    - 邻居发现
    """
    
    def __init__(self, 
                 communication_range: float = 10.0,
                 decay_factor: float = 0.1):
        """
        Args:
            communication_range: 通信范围
            decay_factor: 衰减因子
        """
        self.communication_range = communication_range
        self.decay_factor = decay_factor
        self.signals: Dict[str, Signal] = {}
    
    def calculate_rssi(self, 
                       distance: float, 
                       max_distance: Optional[float] = None) -> float:
        """
        计算RSSI信号强度
        
        Args:
            distance: 距离
            max_distance: 最大距离（默认使用通信范围）
            
        Returns:
            RSSI值 [0, 1]
        """
        if max_distance is None:
            max_distance = self.communication_range
        
        if distance > max_distance:
            return 0.0
        
        return max(0, 1.0 - distance / max_distance)
    
    def calculate_decay(self, 
                       rssi: float, 
                       time_delta: float) -> float:
        """
        计算信号随时间衰减
        
        Args:
            rssi: 原始RSSI
            time_delta: 时间间隔
            
        Returns:
            衰减后的RSSI
        """
        return rssi * np.exp(-self.decay_factor * time_delta)
    
    def receive_signal(self, signal: Signal) -> None:
        """接收信号"""
        self.signals[signal.sender_id] = signal
    
    def get_neighbors(self, 
                     my_position: np.ndarray,
                     all_positions: Dict[str, np.ndarray],
                     threshold: float = 0.1) -> List[str]:
        """
        获取邻居列表
        
        Args:
            my_position: 我的位置
            all_positions: 所有智能体位置 {id: position}
            threshold: RSSI阈值
            
        Returns:
            邻居ID列表
        """
        neighbors = []
        
        for agent_id, position in all_positions.items():
            if agent_id == id(my_position):
                continue
            
            distance = np.linalg.norm(my_position - position)
            rssi = self.calculate_rssi(distance)
            
            if rssi > threshold:
                neighbors.append(agent_id)
        
        return neighbors
    
    def broadcast(self, 
                 sender_id: str,
                 data: np.ndarray,
                 positions: Dict[str, np.ndarray]) -> Dict[str, Signal]:
        """
        广播信号到所有邻居
        
        Args:
            sender_id: 发送者ID
            data: 信号数据
            positions: 位置字典
            
        Returns:
            接收到的信号字典
        """
        signals = {}
        sender_pos = positions.get(sender_id)
        
        if sender_pos is None:
            return signals
        
        for agent_id, position in positions.items():
            if agent_id == sender_id:
                continue
            
            distance = np.linalg.norm(sender_pos - position)
            rssi = self.calculate_rssi(distance)
            
            if rssi > 0:
                signals[agent_id] = Signal(
                    sender_id=sender_id,
                    data=data,
                    timestamp=0,  # 应该使用实际时间
                    rssi=rssi
                )
        
        return signals


class MessageProtocol:
    """
    通信协议
    
    支持:
    - 点对点消息
    - 广播消息
    - 组播消息
    """
    
    def __init__(self):
        self.inbox: Dict[str, List[Signal]] = {}
        self.outbox: List[Signal] = []
    
    def send(self, 
             to_id: str, 
             data: np.ndarray,
             rssi: float = 1.0) -> None:
        """发送消息"""
        self.outbox.append(Signal(
            sender_id="self",
            data=data,
            timestamp=0,
            rssi=rssi
        ))
    
    def receive(self, from_id: str) -> List[Signal]:
        """接收消息"""
        return self.inbox.get(from_id, [])
    
    def broadcast(self, 
                 data: np.ndarray,
                 rssi: float = 1.0) -> None:
        """广播消息"""
        self.outbox.append(Signal(
            sender_id="self",
            data=data,
            timestamp=0,
            rssi=rssi
        ))


# ========== 独立测试 ==========
if __name__ == "__main__":
    # 测试信号处理器
    proc = SignalProcessor(
        communication_range=10.0,
        decay_factor=0.1
    )
    
    # RSSI计算测试
    print("RSSI计算测试:")
    for dist in [0, 5, 10, 15]:
        rssi = proc.calculate_rssi(dist)
        print(f"  距离 {dist}m: RSSI = {rssi:.3f}")
    
    # 邻居发现测试
    print("\n邻居发现测试:")
    positions = {
        'A': np.array([0, 0]),
        'B': np.array([3, 4]),  # 距离5
        'C': np.array([9, 0]),  # 距离9
        'D': np.array([15, 0]), # 距离15
    }
    
    neighbors = proc.get_neighbors(
        np.array([0, 0]),
        positions,
        threshold=0.1
    )
    print(f"  A的邻居: {neighbors}")
    
    # 广播测试
    print("\n广播测试:")
    signals = proc.broadcast(
        sender_id='A',
        data=np.array([1, 2, 3]),
        positions=positions
    )
    print(f"  收到信号的智能体: {list(signals.keys())}")
