#!/usr/bin/env python3
"""
环境预测与反应系统
==================
基于当前环境状态预测未来，并做出反应

功能:
1. 环境状态提取 - 从传感器数据提取状态特征
2. 预测模型 - 预测下一时刻状态
3. 反应系统 - 根据预测结果触发反应
4. 行为规划 - 生成应对策略
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class ReactionType(Enum):
    """反应类型"""
    AVOID = "avoid"          # 避障
    APPROACH = "approach"    # 靠近目标
    WAIT = "wait"           # 等待
    ESCAPE = "escape"       # 逃跑
    EXPLORE = "explore"     # 探索
    RETURN = "return"       # 返回
    STOP = "stop"           # 停止


@dataclass
class EnvironmentState:
    """环境状态"""
    timestamp: float
    position: Tuple[float, float] = (0, 0)
    velocity: Tuple[float, float] = (0, 0)
    target: Tuple[float, float] = (0, 0)
    neighbors: List[Tuple[float, float]] = field(default_factory=list)
    rssi_values: List[float] = field(default_factory=list)
    obstacle_distance: float = float('inf')
    obstacle_direction: float = 0.0
    temperature: float = 25.0
    battery_level: float = 100.0
    
    def to_vector(self) -> np.ndarray:
        """转换为特征向量"""
        features = [
            self.position[0], self.position[1],
            self.velocity[0], self.velocity[1],
            self.target[0], self.target[1],
            self.obstacle_distance,
            self.obstacle_direction,
            self.temperature,
            self.battery_level,
            len(self.neighbors),
            np.mean(self.rssi_values) if self.rssi_values else -100
        ]
        return np.array(features, dtype=np.float32)


@dataclass
class Prediction:
    """预测结果"""
    timestamp: float
    horizon: float           # 预测时间范围 (秒)
    predicted_states: List[EnvironmentState] = field(default_factory=list)
    confidence: float = 0.0
    risk_level: float = 0.0  # 风险等级 0-1
    
    @property
    def has_collision_risk(self) -> bool:
        return self.risk_level > 0.7
    
    @property
    def has_goal_reached(self) -> bool:
        if not self.predicted_states:
            return False
        final = self.predicted_states[-1]
        dist = np.sqrt((final.position[0] - final.target[0])**2 + 
                       (final.position[1] - final.target[1])**2)
        return dist < 0.1


@dataclass
class Reaction:
    """反应动作"""
    reaction_type: ReactionType
    confidence: float
    action_vector: Tuple[float, float]  # [dx, dy]
    reason: str
    priority: int = 0  # 优先级


class Predictor:
    """预测器 - 基于历史数据预测未来状态"""
    
    def __init__(self, history_size: int = 50):
        self.history: List[EnvironmentState] = []
        self.history_size = history_size
        
        # 简单线性预测参数
        self.velocity_trend = np.zeros(2)
        self.position_trend = np.zeros(2)
        
    def add_state(self, state: EnvironmentState):
        """添加状态到历史"""
        self.history.append(state)
        if len(self.history) > self.history_size:
            self.history.pop(0)
        self._update_trends()
    
    def _update_trends(self):
        """更新趋势"""
        if len(self.history) < 3:
            return
        
        # 计算速度趋势
        velocities = np.array([(s.velocity[0], s.velocity[1]) for s in self.history[-10:]])
        self.velocity_trend = np.mean(velocities, axis=0)
        
        # 计算位置趋势
        positions = np.array([(s.position[0], s.position[1]) for s in self.history[-10:]])
        self.position_trend = np.mean(positions, axis=0)
    
    def predict(self, current_state: EnvironmentState, horizon: float = 1.0, steps: int = 10) -> Prediction:
        """预测未来状态"""
        if len(self.history) < 3:
            # 历史数据不足，返回默认预测
            return Prediction(
                timestamp=current_state.timestamp,
                horizon=horizon,
                predicted_states=[current_state] * steps,
                confidence=0.0,
                risk_level=0.0
            )
        
        predicted_states = []
        dt = horizon / steps
        
        # 预测位置
        pos = current_state.position
        vel = current_state.velocity
        
        for i in range(steps):
            # 简单预测: 位置 += 速度 * dt
            new_pos = (
                pos[0] + vel[0] * dt * (i + 1),
                pos[1] + vel[1] * dt * (i + 1)
            )
            
            # 预测障碍物
            obs_dist = current_state.obstacle_distance - i * 0.1
            obs_dir = current_state.obstacle_direction
            
            state = EnvironmentState(
                timestamp=current_state.timestamp + dt * (i + 1),
                position=new_pos,
                velocity=vel,
                target=current_state.target,
                obstacle_distance=max(0, obs_dist),
                obstacle_direction=obs_dir,
                battery_level=max(0, current_state.battery_level - i * 0.5)
            )
            predicted_states.append(state)
        
        # 计算置信度 (基于历史一致性)
        confidence = min(1.0, len(self.history) / 20)
        
        # 计算风险等级
        risk = self._calculate_risk(current_state, predicted_states)
        
        return Prediction(
            timestamp=current_state.timestamp,
            horizon=horizon,
            predicted_states=predicted_states,
            confidence=confidence,
            risk_level=risk
        )
    
    def _calculate_risk(self, current: EnvironmentState, predicted: List[EnvironmentState]) -> float:
        """计算风险等级"""
        risk = 0.0
        
        # 障碍物风险
        if current.obstacle_distance < 0.5:
            risk += 0.5
        elif current.obstacle_distance < 1.0:
            risk += 0.3
        
        # 预测碰撞风险
        for state in predicted:
            if state.obstacle_distance < 0.3:
                risk += 0.2
                break
        
        # 电池风险
        if current.battery_level < 20:
            risk += 0.2
        elif current.battery_level < 50:
            risk += 0.1
        
        # 目标距离风险
        dist_to_target = np.sqrt(
            (current.position[0] - current.target[0])**2 +
            (current.position[1] - current.target[1])**2
        )
        if dist_to_target > 10:
            risk += 0.1
        
        return min(1.0, risk)


class ReactionSystem:
    """反应系统 - 根据预测结果生成反应"""
    
    def __init__(self):
        self.reaction_rules = [
            # (条件, 反应类型, 优先级)
            (lambda p: p.has_collision_risk, ReactionType.AVOID, 10),
            (lambda p: p.predicted_states[-1].obstacle_distance < 0.5, ReactionType.AVOID, 9),
            (lambda p: p.risk_level > 0.8, ReactionType.STOP, 8),
            (lambda p: p.risk_level > 0.5 and p.predicted_states[-1].battery_level < 30, ReactionType.RETURN, 7),
            (lambda p: p.has_goal_reached, ReactionType.RETURN, 5),
            (lambda p: p.confidence < 0.3, ReactionType.EXPLORE, 3),
        ]
    
    def react(self, prediction: Prediction, current_state: EnvironmentState) -> Reaction:
        """根据预测结果生成反应"""
        
        # 检查规则
        for condition, reaction_type, priority in self.reaction_rules:
            if condition(prediction):
                return self._create_reaction(reaction_type, prediction, current_state, priority)
        
        # 默认: 靠近目标
        return self._create_reaction(ReactionType.APPROACH, prediction, current_state, 1)
    
    def _create_reaction(self, reaction_type: ReactionType, prediction: Prediction, 
                        state: EnvironmentState, priority: int) -> Reaction:
        """创建反应动作"""
        
        if reaction_type == ReactionType.AVOID:
            # 远离障碍物
            avoid_dir = (state.obstacle_direction + 180) % 360
            rad = np.radians(avoid_dir)
            action = (np.cos(rad), np.sin(rad))
            reason = f"避障: 障碍物距离 {state.obstacle_distance:.2f}m"
            
        elif reaction_type == ReactionType.STOP:
            action = (0, 0)
            reason = "风险过高: 停止移动"
            
        elif reaction_type == ReactionType.APPROACH:
            # 靠近目标
            dx = state.target[0] - state.position[0]
            dy = state.target[1] - state.position[1]
            dist = np.sqrt(dx**2 + dy**2)
            if dist > 0:
                action = (dx/dist, dy/dist)
            else:
                action = (0, 0)
            reason = "靠近目标"
            
        elif reaction_type == ReactionType.EXPLORE:
            # 探索: 随机方向
            angle = np.random.uniform(0, 360)
            rad = np.radians(angle)
            action = (np.cos(rad), np.sin(rad))
            reason = "不确定环境，探索中"
            
        elif reaction_type == ReactionType.RETURN:
            action = (0, 0)
            reason = "已到达目标，返回"
            
        else:
            action = (0, 0)
            reason = "默认停止"
        
        return Reaction(
            reaction_type=reaction_type,
            confidence=prediction.confidence,
            action_vector=action,
            reason=reason,
            priority=priority
        )


class PredictiveController:
    """预测控制器 - 整合预测和反应"""
    
    def __init__(self):
        self.predictor = Predictor()
        self.reaction_system = ReactionSystem()
        self.last_reaction: Optional[Reaction] = None
        
    def update(self, state: EnvironmentState) -> Reaction:
        """更新状态并获取反应"""
        
        # 1. 添加当前状态到历史
        self.predictor.add_state(state)
        
        # 2. 预测未来状态
        prediction = self.predictor.predict(state, horizon=1.0, steps=10)
        
        # 3. 生成反应
        reaction = self.reaction_system.react(prediction, state)
        
        self.last_reaction = reaction
        return reaction
    
    def get_status(self) -> dict:
        """获取状态"""
        return {
            "history_size": len(self.predictor.history),
            "last_reaction": self.last_reaction.reaction_type.value if self.last_reaction else None,
            "confidence": self.last_reaction.confidence if self.last_reaction else 0
        }


# ============ 演示 ============

def demo():
    """演示预测反应系统"""
    print("=" * 50)
    print("环境预测与反应系统演示")
    print("=" * 50)
    
    controller = PredictiveController()
    
    # 模拟一系列环境状态
    scenarios = [
        # 正常接近目标
        EnvironmentState(timestamp=0, position=(0, 0), velocity=(1, 0), 
                       target=(10, 0), obstacle_distance=5.0),
        EnvironmentState(timestamp=0.1, position=(0.1, 0), velocity=(1, 0),
                       target=(10, 0), obstacle_distance=4.9),
        
        # 障碍物接近
        EnvironmentState(timestamp=0.2, position=(0.5, 0), velocity=(1, 0),
                       target=(10, 0), obstacle_distance=1.0),
        EnvironmentState(timestamp=0.3, position=(0.6, 0), velocity=(1, 0),
                       target=(10, 0), obstacle_distance=0.5),
        
        # 低电量
        EnvironmentState(timestamp=0.4, position=(1.0, 0), velocity=(1, 0),
                       target=(10, 0), obstacle_distance=3.0, battery_level=15),
    ]
    
    for i, state in enumerate(scenarios):
        print(f"\n--- 场景 {i+1} ---")
        print(f"位置: {state.position}, 目标: {state.target}")
        print(f"障碍物距离: {state.obstacle_distance}m")
        print(f"电池: {state.battery_level}%")
        
        reaction = controller.update(state)
        
        print(f"\n预测结果:")
        prediction = controller.predictor.predict(state)
        print(f"  风险等级: {prediction.risk_level:.2f}")
        print(f"  置信度: {prediction.confidence:.2f}")
        
        print(f"\n反应:")
        print(f"  类型: {reaction.reaction_type.value}")
        print(f"  动作: {reaction.action_vector}")
        print(f"  原因: {reaction.reason}")
    
    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
