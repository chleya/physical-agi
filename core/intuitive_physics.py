"""
Intuitive Physics - 直觉物理模块

功能:
1. 物理直觉预测
2. 稳态判断
3. 可能性评估
4. 物理规则学习
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class PhysicsIntuitionType(Enum):
    """物理直觉类型"""
    TRAJECTORY = "trajectory"         # 轨迹预测
    STABILITY = "stability"           # 稳定性判断
    COLLISION = "collision"           # 碰撞预测
    SUPPORT = "support"               # 支撑判断
    BALANCE = "balance"               # 平衡判断


@dataclass
class PhysicsPrediction:
    """物理预测"""
    prediction_type: PhysicsIntuitionType
    predicted_outcome: str
    confidence: float
    reasoning: str
    timestamp: float


class IntuitivePhysics:
    """
    直觉物理引擎
    
    模拟人类对物理世界的直觉理解:
    1. 轨迹预测
    2. 稳定性判断
    3. 碰撞预测
    4. 支撑/平衡判断
    """
    
    def __init__(self):
        self.predictions: List[PhysicsPrediction] = []
        self.physical_knowledge: Dict[str, Dict] = {}
        
    def predict_trajectory(self, initial_velocity: Tuple[float, float, float],
                          position: Tuple[float, float, float],
                          gravity: float = 9.81,
                          time_horizon: float = 2.0) -> PhysicsPrediction:
        """
        预测物体运动轨迹
        
        Args:
            initial_velocity: 初始速度
            position: 初始位置
            gravity: 重力加速度
            time_horizon: 预测时间范围
            
        Returns:
            轨迹预测
        """
        vx, vy, vz = initial_velocity
        
        # 计算落地时间（假设y=0为地面）
        if vy > 0:
            flight_time = (vy + np.sqrt(vy**2 + 2 * gravity * position[1])) / gravity
        else:
            flight_time = 0
        
        flight_time = min(flight_time, time_horizon)
        
        # 最终位置
        final_x = position[0] + vx * flight_time
        final_y = max(0, position[1] + vy * flight_time - 0.5 * gravity * flight_time**2)
        final_z = position[2] + vz * flight_time
        
        predicted_outcome = f"物体将在{flight_time:.2f}秒后落在({final_x:.1f}, {final_y:.1f}, {final_z:.1f})"
        
        prediction = PhysicsPrediction(
            prediction_type=PhysicsIntuitionType.TRAJECTORY,
            predicted_outcome=predicted_outcome,
            confidence=0.85,
            reasoning="基于经典力学公式计算",
            timestamp=np.datetime64('now').astype('float64') / 1e9
        )
        
        self.predictions.append(prediction)
        return prediction
    
    def assess_stability(self, object_center: Tuple[float, float],
                        support_polygon: List[Tuple[float, float]]) -> PhysicsPrediction:
        """
        评估物体稳定性
        
        Args:
            object_center: 物体中心
            support_polygon: 支撑多边形顶点
            
        Returns:
            稳定性预测
        """
        cx, cy = object_center
        
        # 计算支撑多边形的中心
        poly_center = (
            np.mean([p[0] for p in support_polygon]),
            np.mean([p[1] for p in support_polygon])
        )
        
        # 计算中心到支撑多边形边缘的距离
        min_distance = float('inf')
        for i in range(len(support_polygon)):
            p1 = support_polygon[i]
            p2 = support_polygon[(i+1) % len(support_polygon)]
            
            # 点到线段距离
            dist = self._point_to_segment_distance(cx, cy, p1[0], p1[1], p2[0], p2[1])
            min_distance = min(min_distance, dist)
        
        # 稳定性判断
        if min_distance > 0.1:
            outcome = "稳定"
            confidence = 0.9
            reasoning = "物体中心在支撑多边形内部，远离边缘"
        elif min_distance > 0:
            outcome = "临界稳定"
            confidence = 0.6
            reasoning = "物体中心接近支撑多边形边缘"
        else:
            outcome = "不稳定"
            confidence = 0.85
            reasoning = "物体中心在支撑多边形外部"
        
        prediction = PhysicsPrediction(
            prediction_type=PhysicsIntuitionType.STABILITY,
            predicted_outcome=outcome,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=np.datetime64('now').astype('float64') / 1e9
        )
        
        self.predictions.append(prediction)
        return prediction
    
    def _point_to_segment_distance(self, px: float, py: float,
                                   x1: float, y1: float,
                                   x2: float, y2: float) -> float:
        """计算点到线段的距离"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return np.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))
        
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        
        return np.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)
    
    def predict_collision(self, obj1_pos: Tuple[float, float, float],
                         obj1_vel: Tuple[float, float, float],
                         obj2_pos: Tuple[float, float, float],
                         obj2_vel: Tuple[float, float, float]) -> PhysicsPrediction:
        """
        预测碰撞
        
        Args:
            obj1_pos: 对象1位置
            obj1_vel: 对象1速度
            obj2_pos: 对象2位置
            obj2_vel: 对象2速度
            
        Returns:
            碰撞预测
        """
        # 相对位置和速度
        rel_pos = np.array(obj2_pos) - np.array(obj1_pos)
        rel_vel = np.array(obj2_vel) - np.array(obj1_vel)
        
        # 相对距离
        distance = np.linalg.norm(rel_pos)
        
        # 相对速度
        rel_speed = np.linalg.norm(rel_vel)
        
        # 碰撞时间估计
        if rel_speed == 0:
            time_to_collision = float('inf')
        else:
            time_to_collision = distance / rel_speed
        
        if time_to_collision < 1.0:
            outcome = f"将在{time_to_collision:.2f}秒后碰撞"
            confidence = 0.8
        elif time_to_collision < 5.0:
            outcome = f"可能在{time_to_collision:.2f}秒后碰撞"
            confidence = 0.5
        else:
            outcome = "短期内不会碰撞"
            confidence = 0.85
        
        prediction = PhysicsPrediction(
            prediction_type=PhysicsIntuitionType.COLLISION,
            predicted_outcome=outcome,
            confidence=confidence,
            reasoning=f"相对距离: {distance:.2f}, 相对速度: {rel_speed:.2f}",
            timestamp=np.datetime64('now').astype('float64') / 1e9
        )
        
        self.predictions.append(prediction)
        return prediction
    
    def assess_support(self, supporter_size: Tuple[float, float],
                      supported_size: Tuple[float, float],
                      placement_offset: Tuple[float, float]) -> PhysicsPrediction:
        """
        评估支撑关系
        
        Args:
            supporter_size: 支撑物大小
            supported_size: 被支撑物大小
            placement_offset: 放置偏移
            
        Returns:
            支撑判断
        """
        sup_w, sup_h = supporter_size
        obj_w, obj_h = supported_size
        off_x, off_y = placement_offset
        
        # 检查是否在支撑范围内
        in_range_x = abs(off_x) < sup_w / 2
        in_range_y = abs(off_y) < sup_h / 2
        
        # 检查大小关系
        fits = obj_w < sup_w and obj_h < sup_h
        
        if in_range_x and in_range_y and fits:
            outcome = "可以稳定支撑"
            confidence = 0.9
            reasoning = "被支撑物完全在支撑范围内"
        elif in_range_x and in_range_y:
            outcome = "可能滑动"
            confidence = 0.6
            reasoning = "被支撑物大小接近支撑物，可能滑动"
        elif fits:
            outcome = "边缘支撑"
            confidence = 0.5
            reasoning = "被支撑物在支撑物边缘"
        else:
            outcome = "无法支撑"
            confidence = 0.85
            reasoning = "被支撑物超出支撑范围"
        
        prediction = PhysicsPrediction(
            prediction_type=PhysicsIntuitionType.SUPPORT,
            predicted_outcome=outcome,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=np.datetime64('now').astype('float64') / 1e9
        )
        
        self.predictions.append(prediction)
        return prediction
    
    def learn_physical_rule(self, observation: Dict) -> None:
        """
        学习物理规则
        
        Args:
            observation: 观察结果
        """
        rule_type = observation.get('rule_type')
        
        if rule_type not in self.physical_knowledge:
            self.physical_knowledge[rule_type] = {
                'observations': [],
                'confidence': 0.0
            }
        
        self.physical_knowledge[rule_type]['observations'].append(observation)
        
        # 更新置信度
        obs_count = len(self.physical_knowledge[rule_type]['observations'])
        self.physical_knowledge[rule_type]['confidence'] = min(1.0, obs_count * 0.1)
    
    def get_physics_intuition_statistics(self) -> Dict:
        """获取物理直觉统计"""
        return {
            'total_predictions': len(self.predictions),
            'by_type': {
                pt.value: sum(1 for p in self.predictions if p.prediction_type == pt)
                for pt in PhysicsIntuitionType
            },
            'avg_confidence': np.mean([p.confidence for p in self.predictions]) if self.predictions else 0,
            'learned_rules': len(self.physical_knowledge)
        }


# 便利函数
def create_intuitive_physics() -> IntuitivePhysics:
    """创建直觉物理引擎"""
    return IntuitivePhysics()
