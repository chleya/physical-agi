"""
Physics Engine - 物理引擎 (重写版)

修复内容:
1. 修复零质量ZeroDivisionError
2. 修复地面碰撞穿模问题
3. 修复摩擦力应用
4. 改进碰撞检测稳定性
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class BodyType(Enum):
    """物体类型别名"""
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


class PhysicsObjectType(Enum):
    """物理对象类型"""
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


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
    size: Vector3D
    restitution: float = 0.5
    friction: float = 0.3
    
    def __post_init__(self):
        # 确保质量有效
        self.mass = max(self.mass, 0.001)


class PhysicsEngine:
    """
    物理引擎（稳定版）
    
    修复重点:
    1. 零质量安全处理
    2. 稳定碰撞响应
    3. 正确摩擦应用
    """
    
    def __init__(self, gravity: Vector3D = None):
        self.gravity = gravity or Vector3D(0, -9.81, 0)
        self.objects: Dict[str, PhysicsObject] = {}
        self.collisions: List[Dict] = []
        self.time_step: float = 0.016  # 60fps
        self.sleep_threshold: float = 0.5
        
    def add_object(self, obj: PhysicsObject) -> None:
        self.objects[obj.object_id] = obj
    
    def apply_force(self, object_id: str, force: Vector3D) -> bool:
        """施加力（安全版本）"""
        if object_id not in self.objects:
            return False
        
        obj = self.objects[object_id]
        if obj.mass <= 0:
            return False
        
        obj.acceleration = obj.acceleration + force * (1 / obj.mass)
        return True
    
    def simulate_step(self, dt: float = None) -> Dict:
        """模拟一步"""
        dt = dt or self.time_step
        
        # 1. 应用力和更新运动
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.STATIC:
                continue
            
            # 只有DYNAMIC受重力影响
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                gravity_force = self.gravity * obj.mass
                self.apply_force(obj_id, gravity_force)
            
            # 更新速度和位置
            obj.velocity = obj.velocity + obj.acceleration * dt
            obj.position = obj.position + obj.velocity * dt
            
            # 重置加速度
            obj.acceleration = Vector3D(0, 0, 0)
        
        # 2. 碰撞检测和响应
        collision_events = self._handle_collisions()
        
        return {
            'objects_updated': len(self.objects),
            'collisions': len(collision_events),
            'collision_events': collision_events
        }
    
    def _handle_collisions(self) -> List[Dict]:
        """处理所有碰撞"""
        collisions = []
        
        # 物体间碰撞
        object_ids = list(self.objects.keys())
        for i, id1 in enumerate(object_ids):
            for id2 in object_ids[i+1:]:
                obj1 = self.objects[id1]
                obj2 = self.objects[id2]
                
                info = self._check_collision(obj1, obj2)
                if info:
                    self._resolve_collision(obj1, obj2, info)
                    collisions.append({
                        'object1': id1, 'object2': id2, **info
                    })
        
        # 地面碰撞
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                info = self._check_ground(obj)
                if info:
                    self._resolve_ground_collision(obj, info)
                    collisions.append({
                        'object1': obj_id, 'object2': 'ground', **info
                    })
        
        return collisions
    
    def _check_collision(self, obj1: PhysicsObject, 
                         obj2: PhysicsObject) -> Optional[Dict]:
        """检查两个物体间的碰撞"""
        # 简化的AABB碰撞检测
        if (abs(obj1.position.x - obj2.position.x) > (obj1.size.x + obj2.size.x) / 2 or
            abs(obj1.position.y - obj2.position.y) > (obj1.size.y + obj2.size.y) / 2 or
            abs(obj1.position.z - obj2.position.z) > (obj1.size.z + obj2.size.z) / 2):
            return None
        
        # 计算碰撞法线和重叠
        diff = obj1.position - obj2.position
        dist = max(abs(diff.x), abs(diff.y), abs(diff.z))
        
        if dist < 0.001:
            return None
        
        # 简化：使用位置差作为法线
        normal = Vector3D(
            diff.x / dist if abs(diff.x) == dist else 0,
            diff.y / dist if abs(diff.y) == dist else 0,
            diff.z / dist if abs(diff.z) == dist else 0
        )
        
        # 如果无法确定法线，使用向上
        if normal.x == 0 and normal.y == 0 and normal.z == 0:
            normal = Vector3D(0, 1, 0)
        
        return {'overlap': 0.05, 'normal': normal}
    
    def _check_ground(self, obj: PhysicsObject) -> Optional[Dict]:
        """检查地面碰撞"""
        ground_y = obj.size.y / 2  # 地面在物体下方size/2处
        bottom_y = obj.position.y - obj.size.y / 2
        
        if bottom_y < ground_y:
            overlap = ground_y - bottom_y
            return {
                'overlap': overlap,
                'normal': Vector3D(0, 1, 0)
            }
        return None
    
    def _resolve_collision(self, obj1: PhysicsObject, 
                          obj2: PhysicsObject,
                          collision_info: Dict) -> None:
        """解决碰撞（稳定版本）"""
        normal = collision_info['normal']
        overlap = collision_info['overlap']
        
        # 只有DYNAMIC物体参与碰撞响应
        inv_m1 = 1.0 / obj1.mass if obj1.object_type == PhysicsObjectType.DYNAMIC else 0
        inv_m2 = 1.0 / obj2.mass if obj2.object_type == PhysicsObjectType.DYNAMIC else 0
        total_inv_mass = inv_m1 + inv_m2
        
        if total_inv_mass <= 0:
            return
        
        # 分离物体
        separation = overlap + 0.001
        if inv_m1 > 0:
            obj1.position = obj1.position + normal * separation * (inv_m1 / total_inv_mass)
        if inv_m2 > 0:
            obj2.position = obj2.position - normal * separation * (inv_m2 / total_inv_mass)
        
        # 计算相对速度
        rel_vel = obj1.velocity - obj2.velocity
        vel_along_normal = (rel_vel.x * normal.x + 
                          rel_vel.y * normal.y + 
                          rel_vel.z * normal.z)
        
        # 如果正在分离，不处理
        if vel_along_normal > 0:
            return
        
        # 计算冲量
        e = min(obj1.restitution, obj2.restitution)
        j = -(1 + e) * vel_along_normal
        j /= total_inv_mass
        
        # 应用冲量
        impulse = Vector3D(j * normal.x, j * normal.y, j * normal.z)
        if inv_m1 > 0:
            obj1.velocity = obj1.velocity + impulse * inv_m1
        if inv_m2 > 0:
            obj2.velocity = obj2.velocity - impulse * inv_m2
        
        # 应用摩擦
        self._apply_friction(obj1, obj2, rel_vel, inv_m1, inv_m2)
    
    def _resolve_ground_collision(self, obj: PhysicsObject, 
                                  collision_info: Dict) -> None:
        """解决地面碰撞"""
        normal = collision_info['normal']  # 应该向上(0,1,0)
        overlap = collision_info['overlap']
        
        # 分离物体
        obj.position = obj.position + normal * (overlap + 0.001)
        
        # 获取法向速度
        normal_vel = (obj.velocity.x * normal.x + 
                     obj.velocity.y * normal.y + 
                     obj.velocity.z * normal.z)
        
        # 如果向上运动，不处理
        if normal_vel > 0:
            return
        
        # 反弹
        j = -(1 + obj.restitution) * normal_vel
        j /= (1.0 / obj.mass)
        
        impulse = Vector3D(j * normal.x, j * normal.y, j * normal.z)
        obj.velocity = obj.velocity + impulse * (1.0 / obj.mass)
        
        # 应用地面摩擦（简化：直接减速水平速度）
        friction = obj.friction
        obj.velocity.x *= (1.0 - friction * 0.1)
        obj.velocity.z *= (1.0 - friction * 0.1)
    
    def _apply_friction(self, obj1: PhysicsObject, obj2: PhysicsObject,
                       rel_vel: Vector3D, inv_m1: float, inv_m2: float) -> None:
        """应用摩擦"""
        # 简化的摩擦应用
        friction = min(obj1.friction, obj2.friction)
        
        # 切向速度
        tangent_speed = np.sqrt(rel_vel.x**2 + rel_vel.z**2)
        
        if tangent_speed < 0.01:
            return
        
        # 摩擦冲量
        friction_impulse = friction * tangent_speed * 0.1
        
        # 应用到水平速度
        if inv_m1 > 0:
            obj1.velocity.x -= np.sign(rel_vel.x) * friction_impulse * inv_m1
            obj1.velocity.z -= np.sign(rel_vel.z) * friction_impulse * inv_m1
        if inv_m2 > 0:
            obj2.velocity.x += np.sign(rel_vel.x) * friction_impulse * inv_m2
            obj2.velocity.z += np.sign(rel_vel.z) * friction_impulse * inv_m2
    
    def get_physics_state(self) -> Dict:
        """获取物理状态"""
        return {
            'object_count': len(self.objects),
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


def create_physics_engine(gravity: Vector3D = None) -> PhysicsEngine:
    """创建物理引擎"""
    return PhysicsEngine(gravity=gravity)
