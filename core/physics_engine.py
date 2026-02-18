"""
Physics Engine - 物理引擎

功能:
1. 物理仿真
2. 碰撞检测
3. 运动模拟
4. 力的计算
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from dataclasses import dataclass


class PhysicsObjectType(Enum):
    """物理对象类型"""
    DYNAMIC = "dynamic"       # 动态
    STATIC = "static"         # 静态
    KINEMATIC = "kinematic"   # 运动学


@dataclass
class Vector3D:
    """三维向量"""
    x: float
    y: float
    z: float
    
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)


@dataclass
class PhysicsObject:
    """物理对象"""
    object_id: str
    object_type: PhysicsObjectType
    position: Vector3D
    velocity: Vector3D
    acceleration: Vector3D
    mass: float
    size: Vector3D  # 边界框大小
    restitution: float = 0.5  # 弹性系数


class PhysicsEngine:
    """
    物理引擎
    
    模拟物理世界:
    1. 牛顿力学
    2. 碰撞检测
    3. 运动积分
    4. 约束求解
    """
    
    def __init__(self, gravity: Vector3D = None):
        self.gravity = gravity or Vector3D(0, -9.81, 0)
        self.objects: Dict[str, PhysicsObject] = {}
        self.collisions: List[Dict] = []
        self.time_step: float = 0.01
        
    def add_object(self, obj: PhysicsObject) -> None:
        """
        添加物理对象
        
        Args:
            obj: 物理对象
        """
        self.objects[obj.object_id] = obj
    
    def remove_object(self, object_id: str) -> bool:
        """
        移除物理对象
        
        Args:
            object_id: 对象ID
            
        Returns:
            是否成功
        """
        if object_id in self.objects:
            del self.objects[object_id]
            return True
        return False
    
    def apply_force(self, object_id: str, force: Vector3D) -> bool:
        """
        施加力
        
        Args:
            object_id: 对象ID
            force: 力向量
            
        Returns:
            是否成功
        """
        if object_id not in self.objects:
            return False
        
        obj = self.objects[object_id]
        # F = ma -> a = F/m
        obj.acceleration = obj.acceleration + force * (1 / obj.mass)
        return True
    
    def simulate_step(self, dt: float = None) -> Dict:
        """
        模拟一步
        
        Args:
            dt: 时间步长
            
        Returns:
            模拟结果
        """
        dt = dt or self.time_step
        
        collision_events = []
        
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.STATIC:
                continue
            
            # 应用重力
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                gravity_force = self.gravity * obj.mass
                self.apply_force(obj_id, gravity_force)
            
            # 更新速度和位置 (Euler积分)
            obj.velocity = obj.velocity + obj.acceleration * dt
            obj.position = obj.position + obj.velocity * dt
            
            # 重置加速度
            obj.acceleration = Vector3D(0, 0, 0)
        
        # 检测碰撞
        collision_events = self._detect_collisions()
        
        return {
            'objects_updated': len(self.objects),
            'collisions': len(collision_events),
            'collision_events': collision_events
        }
    
    def _detect_collisions(self) -> List[Dict]:
        """检测碰撞"""
        collisions = []
        object_ids = list(self.objects.keys())
        
        for i, id1 in enumerate(object_ids):
            for id2 in object_ids[i+1:]:
                obj1 = self.objects[id1]
                obj2 = self.objects[id2]
                
                if self._check_collision(obj1, obj2):
                    collision = {
                        'object1': id1,
                        'object2': id2,
                        'timestamp': np.datetime64('now').astype('float64') / 1e9
                    }
                    collisions.append(collision)
                    self.collisions.append(collision)
                    
                    # 处理碰撞响应
                    self._resolve_collision(obj1, obj2)
        
        return collisions
    
    def _check_collision(self, obj1: PhysicsObject, 
                        obj2: PhysicsObject) -> bool:
        """
        检查两个对象是否碰撞
        
        使用简化的AABB碰撞检测
        """
        # 中心点距离
        diff = obj1.position - obj2.position
        
        # 边界框半径
        r1 = obj1.size.magnitude() / 2
        r2 = obj2.size.magnitude() / 2
        
        return diff.magnitude() < (r1 + r2)
    
    def _resolve_collision(self, obj1: PhysicsObject, 
                          obj2: PhysicsObject) -> None:
        """解决碰撞"""
        if obj1.object_type == PhysicsObjectType.STATIC and \
           obj2.object_type == PhysicsObjectType.STATIC:
            return
        
        # 计算碰撞法线
        diff = obj2.position - obj1.position
        normal = diff.normalize()
        
        # 分离对象
        overlap = 0.1  # 简化
        if obj1.object_type != PhysicsObjectType.STATIC:
            obj1.position = obj1.position - normal * overlap * 0.5
        if obj2.object_type != PhysicsObjectType.STATIC:
            obj2.position = obj2.position + normal * overlap * 0.5
        
        # 反弹
        relative_velocity = obj1.velocity - obj2.velocity
        velocity_along_normal = np.dot(
            [relative_velocity.x, relative_velocity.y, relative_velocity.z],
            [normal.x, normal.y, normal.z]
        )
        
        if velocity_along_normal > 0:
            return  # 已经在分离
        
        e = min(obj1.restitution, obj2.restitution)
        
        j = -(1 + e) * velocity_along_normal
        j /= (1 / obj1.mass + 1 / obj2.mass)
        
        impulse = normal * j
        
        if obj1.object_type != PhysicsObjectType.STATIC:
            obj1.velocity = obj1.velocity + impulse * (1 / obj1.mass)
        if obj2.object_type != PhysicsObjectType.STATIC:
            obj2.velocity = obj2.velocity - impulse * (1 / obj2.mass)
    
    def get_physics_state(self) -> Dict:
        """获取物理状态"""
        return {
            'object_count': len(self.objects),
            'gravity': {'x': self.gravity.x, 'y': self.gravity.y, 'z': self.gravity.z},
            'collision_count': len(self.collisions),
            'objects': {
                oid: {
                    'position': (obj.position.x, obj.position.y, obj.position.z),
                    'velocity': (obj.velocity.x, obj.velocity.y, obj.velocity.z),
                    'type': obj.object_type.value
                }
                for oid, obj in self.objects.items()
            }
        }


# 便利函数
def create_physics_engine(gravity: Vector3D = None) -> PhysicsEngine:
    """创建物理引擎"""
    return PhysicsEngine(gravity=gravity)
