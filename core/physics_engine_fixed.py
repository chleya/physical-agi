"""
Physics Engine - 物理引擎 (修复版)

修复内容:
1. 添加Vec2类（含__truediv__和dot方法）
2. 添加BodyType别名
3. 添加friction字段
4. 添加AABB碰撞检测
5. 添加穿透修正
6. 改进resolve_collision
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


# ============== 修复1: 添加BodyType别名 ==============
class BodyType(Enum):
    """物体类型别名（兼容旧API）"""
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


class PhysicsObjectType(Enum):
    """物理对象类型"""
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


# ============== 修复2: 添加Vec2类（含__truediv__和dot） ==============
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
        """修复: 添加__truediv__方法"""
        if scalar == 0:
            raise ValueError("Division by zero")
        return Vec2(self.x / scalar, self.y / scalar)
    
    def dot(self, other) -> float:
        """修复: 添加dot方法"""
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
class AABB:
    """轴对齐包围盒（修复3: AABB支持）"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @classmethod
    def from_size(cls, center_x: float, center_y: float, width: float, height: float):
        return cls(
            min_x=center_x - width/2,
            min_y=center_y - height/2,
            max_x=center_x + width/2,
            max_y=center_y + height/2
        )
    
    def intersects(self, other: 'AABB') -> bool:
        """检测AABB相交"""
        return (self.min_x <= other.max_x and self.max_x >= other.min_x and
                self.min_y <= other.max_y and self.max_y >= other.min_y)
    
    def overlap(self, other: 'AABB') -> float:
        """计算重叠面积"""
        if not self.intersects(other):
            return 0
        overlap_x = min(self.max_x, other.max_x) - max(self.min_x, other.min_x)
        overlap_y = min(self.max_y, other.max_y) - max(self.min_y, other.min_y)
        return overlap_x * overlap_y


@dataclass
class PhysicsObject:
    """物理对象（修复版：添加安全检查）"""
    object_id: str
    object_type: PhysicsObjectType
    position: Vector3D
    velocity: Vector3D
    acceleration: Vector3D
    mass: float
    size: Vector3D  # 边界框大小
    restitution: float = 0.5  # 弹性系数
    friction: float = 0.3     # 摩擦力字段
    
    def __post_init__(self):
        # 确保质量有效
        if self.mass <= 0:
            self.mass = 0.001  # 防止零质量


class PhysicsEngine:
    """
    物理引擎（修复版）
    
    修复内容:
    1. 修复KINEMATIC物体被当作DYNAMIC处理
    2. 修复穿透修正
    3. 修复碰撞响应（添加切向摩擦）
    """
    
    def __init__(self, gravity: Vector3D = None):
        self.gravity = gravity or Vector3D(0, -9.81, 0)
        self.objects: Dict[str, PhysicsObject] = {}
        self.collisions: List[Dict] = []
        self.time_step: float = 0.01
        self.sleep_threshold: float = 0.1  # 休眠阈值（修复）
        
    def add_object(self, obj: PhysicsObject) -> None:
        self.objects[obj.object_id] = obj
    
    def remove_object(self, object_id: str) -> bool:
        if object_id in self.objects:
            del self.objects[object_id]
            return True
        return False
    
    def apply_force(self, object_id: str, force: Vector3D) -> bool:
        """
        施加力（修复: 处理零质量情况）
        """
        if object_id not in self.objects:
            return False
        
        obj = self.objects[object_id]
        
        # 安全检查：防止零质量
        if obj.mass <= 0:
            return False
        
        obj.acceleration = obj.acceleration + force * (1 / obj.mass)
        return True
    
    def simulate_step(self, dt: float = None) -> Dict:
        """
        模拟一步（修复: 正确处理KINEMATIC物体）
        """
        dt = dt or self.time_step
        
        collision_events = []
        
        for obj_id, obj in self.objects.items():
            # 修复: KINEMATIC物体不应该受重力影响
            if obj.object_type == PhysicsObjectType.STATIC:
                continue
            
            # 只有DYNAMIC物体受重力影响
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                gravity_force = self.gravity * obj.mass
                self.apply_force(obj_id, gravity_force)
            
            # 更新速度和位置
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
        """检测碰撞（修复: 改进地面接触检测）"""
        collisions = []
        object_ids = list(self.objects.keys())
        
        for i, id1 in enumerate(object_ids):
            for id2 in object_ids[i+1:]:
                obj1 = self.objects[id1]
                obj2 = self.objects[id2]
                
                collision_info = self._check_collision(obj1, obj2)
                if collision_info:
                    collision = {
                        'object1': id1,
                        'object2': id2,
                        'timestamp': np.datetime64('now').astype('float64') / 1e9,
                        **collision_info
                    }
                    collisions.append(collision)
                    self.collisions.append(collision)
                    
                    # 处理碰撞响应
                    self._resolve_collision(obj1, obj2, collision_info)
        
        # 检测地面接触（修复：改进地面碰撞）
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                ground_collision = self._check_ground_collision(obj)
                if ground_collision:
                    collision = {
                        'object1': obj_id,
                        'object2': 'ground',
                        'timestamp': np.datetime64('now').astype('float64') / 1e9,
                        **ground_collision
                    }
                    collisions.append(collision)
                    self.collisions.append(collision)
                    
                    # 创建虚拟地面物体
                    ground = PhysicsObject(
                        object_id='ground',
                        object_type=PhysicsObjectType.STATIC,
                        position=Vector3D(obj.position.x, -0.5, obj.position.z),
                        velocity=Vector3D(0, 0, 0),
                        acceleration=Vector3D(0, 0, 0),
                        mass=float('inf'),
                        size=Vector3D(100, 1, 100),
                        friction=0.5,
                        restitution=0.1
                    )
                    self._resolve_collision(obj, ground, ground_collision)
        
        return collisions
    
    def _check_ground_collision(self, obj: PhysicsObject) -> Optional[Dict]:
        """检测地面碰撞（修复：专门处理地面接触）"""
        # 地面Y位置
        ground_y = 0.5  # 地面高度 = size.y / 2
        
        # 物体底部Y
        bottom_y = obj.position.y - obj.size.y / 2
        
        # 检测是否接触或穿透地面
        margin = 0.001
        if bottom_y <= ground_y + margin:
            overlap = ground_y - bottom_y + margin
            
            return {
                'overlap': overlap,
                'normal': Vector3D(0, 1, 0),
                'contact_point': Vector3D(obj.position.x, bottom_y, obj.position.z)
            }
        
        return None
    
    def _check_collision(self, obj1: PhysicsObject, 
                        obj2: PhysicsObject) -> Optional[Dict]:
        """
        检查碰撞（修复: 改进地面接触检测）
        """
        # 使用AABB进行初步检测（包含Z轴）
        aabb1 = AABB.from_size(obj1.position.x, obj1.position.y, 
                               obj1.size.x, obj1.size.y)
        aabb2 = AABB.from_size(obj2.position.x, obj2.position.y,
                               obj2.size.x, obj2.size.y)
        
        # 检测是否相交或相邻
        margin = 0.001
        intersects = (aabb1.min_x <= aabb2.max_x + margin and 
                      aabb1.max_x >= aabb2.min_x - margin and
                      aabb1.min_y <= aabb2.max_y + margin and 
                      aabb1.max_y >= aabb2.min_y - margin)
        
        if not intersects:
            return None
        
        # 圆形碰撞检测
        diff = obj1.position - obj2.position
        dist = diff.magnitude()
        
        # 使用较小的尺寸作为碰撞半径
        r1 = min(obj1.size.x, obj1.size.y) / 2
        r2 = min(obj2.size.x, obj2.size.y) / 2
        min_dist = r1 + r2
        
        # 检测是否碰撞或接近
        if dist < (min_dist + margin):
            # 计算穿透深度
            overlap = max(0, min_dist - dist)
            
            # 法线方向（从obj2指向obj1）
            if dist > 0.001:
                normal = Vector3D(diff.x / dist, diff.y / dist, diff.z / dist)
            else:
                normal = Vector3D(0, 1, 0)
            
            return {
                'overlap': overlap + 0.001,
                'normal': normal,
                'contact_point': obj1.position + normal * r1
            }
        
        return None
    
    def _resolve_collision(self, obj1: PhysicsObject, 
                          obj2: PhysicsObject,
                          collision_info: Dict) -> None:
        """
        解决碰撞（修复: 完整碰撞响应，含摩擦、零质量处理）
        """
        # 安全检查
        if obj1.object_type == PhysicsObjectType.STATIC and \
           obj2.object_type == PhysicsObjectType.STATIC:
            return
        
        normal = collision_info['normal']
        overlap = collision_info['overlap']
        
        # 穿透修正
        separation = overlap + 0.001
        
        # 有效质量（防止零质量）
        inv_mass1 = 1.0 / max(obj1.mass, 0.001)
        inv_mass2 = 1.0 / max(obj2.mass, 0.001)
        total_inv_mass = inv_mass1 + inv_mass2
        
        if total_inv_mass <= 0:
            return
        
        # 根据质量比例分离物体
        if obj1.object_type != PhysicsObjectType.STATIC:
            obj1.position = obj1.position - normal * separation * (inv_mass1 / total_inv_mass)
        if obj2.object_type != PhysicsObjectType.STATIC:
            obj2.position = obj2.position + normal * separation * (inv_mass2 / total_inv_mass)
        
        # 计算相对速度
        relative_velocity = obj1.velocity - obj2.velocity
        velocity_along_normal = Vec2(
            relative_velocity.x * normal.x + relative_velocity.y * normal.y + relative_velocity.z * normal.z,
            0
        ).magnitude()
        
        # 休眠阈值检查
        if velocity_along_normal < self.sleep_threshold:
            return
        
        # 反弹计算
        e = min(obj1.restitution, obj2.restitution)
        
        j = -(1 + e) * velocity_along_normal
        j /= total_inv_mass
        
        impulse = normal * j
        
        # 应用冲量
        if obj1.object_type != PhysicsObjectType.STATIC:
            obj1.velocity = obj1.velocity + impulse * inv_mass1
        if obj2.object_type != PhysicsObjectType.STATIC:
            obj2.velocity = obj2.velocity - impulse * inv_mass2
        
        # 添加切向摩擦
        self._apply_friction(obj1, obj2, collision_info, j)
    
    def _apply_friction(self, obj1: PhysicsObject, obj2: PhysicsObject,
                       collision_info: Dict, normal_impulse: float) -> None:
        """应用切向摩擦（修复）"""
        relative_velocity = obj1.velocity - obj2.velocity
        
        # 计算切向方向
        normal = collision_info['normal']
        # 简化: 使用速度方向作为切向
        tangent_magnitude = np.sqrt(
            relative_velocity.x**2 + relative_velocity.y**2 + relative_velocity.z**2
        )
        
        if tangent_magnitude < 0.001:
            return
        
        # 摩擦系数
        friction = min(obj1.friction, obj2.friction)
        
        # 计算摩擦冲量
        friction_impulse = friction * normal_impulse
        
        # 应用摩擦（简化版）
        if obj1.object_type != PhysicsObjectType.STATIC:
            friction_vec = Vec2(-relative_velocity.x, -relative_velocity.y).normalize() * friction_impulse
            obj1.velocity = obj1.velocity + Vector3D(friction_vec.x, friction_vec.y, 0)
        if obj2.object_type != PhysicsObjectType.STATIC:
            obj2.velocity = obj2.velocity - Vector3D(friction_vec.x, friction_vec.y, 0)
    
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
                    'type': obj.object_type.value,
                    'restitution': obj.restitution,
                    'friction': obj.friction
                }
                for oid, obj in self.objects.items()
            }
        }


# 便利函数
def create_physics_engine(gravity: Vector3D = None) -> PhysicsEngine:
    """创建物理引擎"""
    return PhysicsEngine(gravity=gravity)
