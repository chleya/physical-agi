"""
物体动力学模块（修复版）
提供物体运动和相互作用建模的基础能力

修复内容:
1. 添加Vec2类
2. 修复接触力计算
3. 添加摩擦力实现
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class DynamicsType(Enum):
    """动力学类型"""
    LINEAR = "linear"
    ROTATIONAL = "rotational"
    COUPLED = "coupled"


# ============== 修复1: 添加Vec2类 ==============
@dataclass
class Vec2:
    """二维向量"""
    x: float
    y: float
    
    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float):
        return Vec2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float):
        if scalar == 0:
            raise ValueError("Division by zero")
        return Vec2(self.x / scalar, self.y / scalar)
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2)
    
    def normalize(self) -> 'Vec2':
        mag = self.magnitude()
        if mag == 0:
            return Vec2(0, 0)
        return self / mag


@dataclass
class StateVector:
    """状态向量"""
    position: np.ndarray  # 位置 [x, y, z]
    velocity: np.ndarray  # 速度 [vx, vy, vz]
    acceleration: np.ndarray  # 加速度 [ax, ay, az]
    
    def to_array(self) -> np.ndarray:
        return np.concatenate([self.position, self.velocity, self.acceleration])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'StateVector':
        n = len(arr) // 3
        return cls(
            position=arr[:n],
            velocity=arr[n:2*n],
            acceleration=arr[2*n:3*n]
        )


@dataclass
class ObjectDynamics:
    """物体动力学模型"""
    object_id: str
    mass: float
    inertia: np.ndarray  # 转动惯量矩阵
    
    # 动力学类型
    dynamics_type: DynamicsType = DynamicsType.COUPLED
    
    # 状态
    state: StateVector = None
    
    # 外力
    external_forces: np.ndarray = field(default_factory=lambda: np.zeros(3))
    external_torques: np.ndarray = field(default_factory=lambda: np.zeros(3))
    
    def __post_init__(self):
        if self.state is None:
            self.state = StateVector(
                position=np.zeros(3),
                velocity=np.zeros(3),
                acceleration=np.zeros(3)
            )
        if isinstance(self.inertia, list):
            self.inertia = np.array(self.inertia)
    
    def compute_acceleration(self) -> np.ndarray:
        """计算加速度"""
        if self.dynamics_type == DynamicsType.LINEAR:
            return self.external_forces / self.mass
        elif self.dynamics_type == DynamicsType.ROTATIONAL:
            return np.linalg.solve(self.inertia, self.external_torques)
        else:  # COUPLED
            linear_acc = self.external_forces / self.mass
            angular_acc = np.linalg.solve(self.inertia, self.external_torques)
            return np.concatenate([linear_acc, angular_acc])
    
    def update(self, dt: float):
        """更新状态"""
        self.acceleration = self.compute_acceleration()
        self.state.velocity = self.state.velocity + self.acceleration * dt
        self.state.position = self.state.position + self.state.velocity * dt


@dataclass
class Interaction:
    """相互作用"""
    type: str  # contact, gravity, friction, etc.
    objects: Tuple[str, str]
    
    # 相互作用参数
    stiffness: float = 1e6
    damping: float = 100.0
    friction_coefficient: float = 0.5
    
    # 计算的力
    force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    torque: np.ndarray = field(default_factory=lambda: np.zeros(3))


class DynamicsEngine:
    """动力学引擎"""
    
    def __init__(self, gravity: Tuple[float, float, float] = (0, -9.8, 0)):
        self.objects: Dict[str, ObjectDynamics] = {}
        self.interactions: List[Interaction] = []
        self.gravity = np.array(gravity)
        self.time: float = 0.0
        self.solver_type: str = "euler"  # euler, runge_kutta
    
    def add_object(self, obj: ObjectDynamics):
        """添加物体"""
        self.objects[obj.object_id] = obj
    
    def remove_object(self, obj_id: str):
        """移除物体"""
        if obj_id in self.objects:
            del self.objects[obj_id]
    
    def add_interaction(self, interaction: Interaction):
        """添加相互作用"""
        self.interactions.append(interaction)
    
    def compute_forces(self):
        """计算所有力"""
        # 重置外力
        for obj in self.objects.values():
            obj.external_forces = np.zeros(3)
            obj.external_torques = np.zeros(3)
        
        # 重力
        for obj in self.objects.values():
            obj.external_forces = obj.external_forces + obj.mass * self.gravity
        
        # 接触力
        self._compute_contact_forces()
        
        # 摩擦力
        self._compute_friction_forces()
    
    def _compute_contact_forces(self):
        """计算接触力"""
        for interaction in self.interactions:
            if interaction.type == "contact":
                obj1_id, obj2_id = interaction.objects
                if obj1_id in self.objects and obj2_id in self.objects:
                    obj1 = self.objects[obj1_id]
                    obj2 = self.objects[obj2_id]
                    
                    # 简化：计算穿透深度和法线
                    penetration = self._calculate_penetration(obj1, obj2)
                    normal = self._calculate_normal(obj1, obj2)
                    
                    if penetration > 0:
                        # 弹性力
                        force_magnitude = interaction.stiffness * penetration
                        # 阻尼力
                        rel_velocity = obj1.state.velocity - obj2.state.velocity
                        damping_force = interaction.damping * np.dot(rel_velocity, normal)
                        
                        total_force = (force_magnitude - damping_force) * normal
                        
                        interaction.force = total_force
                        obj1.external_forces = obj1.external_forces - total_force
                        obj2.external_forces = obj2.external_forces + total_force
    
    def _compute_friction_forces(self):
        """计算摩擦力（修复版：实际应用摩擦力）"""
        for interaction in self.interactions:
            if interaction.type == "friction":
                obj1_id, obj2_id = interaction.objects
                if obj1_id in self.objects and obj2_id in self.objects:
                    obj1 = self.objects[obj1_id]
                    obj2 = self.objects[obj2_id]
                    
                    # 相对速度
                    rel_velocity = obj1.state.velocity - obj2.state.velocity
                    rel_speed = np.linalg.norm(rel_velocity)
                    
                    if rel_speed < 0.001:
                        continue  # 速度太小，跳过
                    
                    # 法向力大小
                    normal_force = np.linalg.norm(interaction.force)
                    
                    # 最大静摩擦力
                    max_friction = interaction.friction_coefficient * normal_force
                    
                    # 简化摩擦力：反向于相对速度
                    friction_direction = -rel_velocity / rel_speed
                    friction_force = interaction.damping * rel_speed * friction_direction
                    
                    # 限制摩擦力大小
                    friction_magnitude = np.linalg.norm(friction_force)
                    if friction_magnitude > max_friction:
                        friction_force = friction_force / friction_magnitude * max_friction
                    
                    interaction.force = friction_force
                    obj1.external_forces = obj1.external_forces + friction_force
                    obj2.external_forces = obj2.external_forces - friction_force
    
    def _calculate_penetration(self, obj1: ObjectDynamics, obj2: ObjectDynamics) -> float:
        """计算穿透深度"""
        dist = np.linalg.norm(obj1.state.position - obj2.state.position)
        # 简化：假设两个物体是球形
        radius1 = 0.1  # 简化：假设半径为0.1
        radius2 = 0.1
        return max(0, radius1 + radius2 - dist)
    
    def _calculate_normal(self, obj1: ObjectDynamics, obj2: ObjectDynamics) -> np.ndarray:
        """计算接触法线"""
        direction = obj2.state.position - obj1.state.position
        dist = np.linalg.norm(direction)
        if dist > 0:
            return direction / dist
        return np.array([0, 0, 1])
    
    def simulate(self, dt: float, steps: int = 1):
        """模拟动力学"""
        for _ in range(steps):
            self.time += dt
            
            # 计算力
            self.compute_forces()
            
            # 更新状态
            for obj in self.objects.values():
                obj.update(dt)
    
    def get_state(self) -> Dict:
        """获取当前状态"""
        return {
            'time': self.time,
            'objects': {
                id_: {
                    'position': obj.state.position.tolist(),
                    'velocity': obj.state.velocity.tolist(),
                    'acceleration': obj.state.acceleration.tolist(),
                    'mass': obj.mass
                }
                for id_, obj in self.objects.items()
            }
        }


class TrajectoryPredictor:
    """轨迹预测器"""
    
    def __init__(self):
        self.dynamics_engine = DynamicsEngine()
    
    def predict(self, object_id: str, initial_state: Dict, 
               forces: List[Dict], duration: float, dt: float = 0.01) -> List[Dict]:
        """预测轨迹"""
        # 创建临时动力学引擎
        engine = DynamicsEngine()
        
        # 添加物体
        obj = ObjectDynamics(
            object_id=object_id,
            mass=initial_state.get("mass", 1.0),
            inertia=np.eye(3) * 0.1,
            state=StateVector(
                position=np.array(initial_state.get("position", [0, 0, 0])),
                velocity=np.array(initial_state.get("velocity", [0, 0, 0])),
                acceleration=np.zeros(3)
            )
        )
        engine.add_object(obj)
        
        # 模拟
        trajectory = []
        steps = int(duration / dt)
        for _ in range(steps):
            state = engine.get_state()
            trajectory.append(state)
            engine.simulate(dt)
        
        return trajectory
    
    def predict_collision(self, obj1_state: Dict, obj2_state: Dict,
                          obj1_velocity: Tuple, obj2_velocity: Tuple,
                          max_time: float = 10.0) -> Optional[float]:
        """预测碰撞时间"""
        # 简化：线性外推
        p1 = np.array(obj1_state)
        p2 = np.array(obj2_state)
        v1 = np.array(obj1_velocity)
        v2 = np.array(obj2_velocity)
        
        rel_p = p1 - p2
        rel_v = v1 - v2
        
        # 相对距离
        dist = np.linalg.norm(rel_p)
        
        # 相对速度（接近速度）
        approach_speed = -np.dot(rel_v, rel_p / dist) if dist > 0 else 0
        
        if approach_speed <= 0:
            return None  # 没有接近
        
        # 假设物体是球形
        radius1 = 0.1
        radius2 = 0.1
        min_dist = radius1 + radius2
        
        if dist < min_dist:
            return 0.0  # 已经碰撞
        
        time_to_collision = (dist - min_dist) / approach_speed
        
        if time_to_collision < max_time:
            return time_to_collision
        
        return None


if __name__ == "__main__":
    # 简单测试
    engine = DynamicsEngine()
    
    # 创建物体
    obj1 = ObjectDynamics(
        object_id="ball",
        mass=1.0,
        inertia=np.eye(3) * 0.1,
        state=StateVector(
            position=np.array([0, 5, 0]),
            velocity=np.zeros(3),
            acceleration=np.zeros(3)
        )
    )
    
    obj2 = ObjectDynamics(
        object_id="ground",
        mass=float('inf'),
        inertia=np.eye(3) * float('inf'),
        state=StateVector(
            position=np.array([0, 0, 0]),
            velocity=np.zeros(3),
            acceleration=np.zeros(3)
        )
    )
    
    engine.add_object(obj1)
    engine.add_object(obj2)
    
    # 添加接触相互作用
    contact = Interaction(
        type="contact",
        objects=("ball", "ground"),
        stiffness=1e6,
        damping=100
    )
    engine.add_interaction(contact)
    
    # 模拟
    print("Simulating ball drop...")
    for i in range(100):
        engine.simulate(dt=0.016, steps=10)
        state = engine.get_state()
        ball = state['objects']['ball']
        print(f"Time {state['time']:.2f}: position = {ball['position']}")
        
        if ball['position'][1] < 0.5:
            print("Ball reached ground!")
            break
    
    # 轨迹预测
    predictor = TrajectoryPredictor()
    trajectory = predictor.predict(
        "test",
        initial_state={"position": [0, 5, 0], "mass": 1.0},
        forces=[],
        duration=2.0
    )
    print(f"\nPredicted {len(trajectory)} trajectory points")
