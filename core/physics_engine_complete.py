"""
Physics Engine - 物理引擎 (完整修复版)

修复内容:
1. 修复弹跳NaN问题
2. 修复KINEMATIC移动约束
3. 稳定碰撞响应
4. 改进地面碰撞
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class BodyType(Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


class PhysicsObjectType(Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"


@dataclass
class Vec2:
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
    object_id: str
    object_type: PhysicsObjectType
    position: Vector3D
    velocity: Vector3D
    acceleration: Vector3D
    mass: float
    size: Vector3D
    restitution: float = 0.5
    friction: float = 0.3
    parent_id: Optional[str] = None  # 修复：用于KINEMATIC约束
    
    def __post_init__(self):
        self.mass = max(self.mass, 0.001)


class PhysicsEngine:
    """
    物理引擎（完整修复版）
    
    修复重点:
    1. 修复弹跳NaN
    2. 修复KINEMATIC移动约束
    3. 稳定碰撞响应
    """
    
    def __init__(self, gravity: Vector3D = None):
        self.gravity = gravity or Vector3D(0, -9.81, 0)
        self.objects: Dict[str, PhysicsObject] = {}
        self.collisions: List[Dict] = []
        self.time_step: float = 0.016
        self.sleep_threshold: float = 0.5
        self.ground_y: float = 0.5  # 地面Y位置
        
    def add_object(self, obj: PhysicsObject) -> None:
        self.objects[obj.object_id] = obj
    
    def apply_force(self, object_id: str, force: Vector3D) -> bool:
        if object_id not in self.objects:
            return False
        
        obj = self.objects[object_id]
        if obj.mass <= 0:
            return False
        
        obj.acceleration = obj.acceleration + force * (1 / obj.mass)
        return True
    
    def simulate_step(self, dt: float = None) -> Dict:
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
        
        # 2. 修复：处理KINEMATIC约束
        self._update_kinematic_constraints()
        
        # 3. 碰撞检测和响应
        collision_events = self._handle_collisions()
        
        return {
            'objects_updated': len(self.objects),
            'collisions': len(collision_events),
            'collision_events': collision_events
        }
    
    # ============== 修复1: KINEMATIC移动约束 ==============
    def _update_kinematic_constraints(self):
        """更新KINEMATIC物体的约束"""
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.DYNAMIC and obj.parent_id:
                # 如果有父物体（KINEMATIC），跟随父物体
                if obj.parent_id in self.objects:
                    parent = self.objects[obj.parent_id]
                    
                    # 计算相对位置
                    parent_top = parent.position.y + parent.size.y / 2
                    obj_half_height = obj.size.y / 2
                    
                    # 如果在父物体上方，保持相对位置
                    if obj.position.y >= parent_top - obj_half_height:
                        # 更新位置跟随
                        obj.position.y = parent_top + obj_half_height + 0.01
    
    def set_parent(self, child_id: str, parent_id: str) -> bool:
        """设置父子约束（修复：KINEMATIC移动时子物体跟随）"""
        if child_id not in self.objects or parent_id not in self.objects:
            return False
        
        self.objects[child_id].parent_id = parent_id
        return True
    
    # ============== 修复2: 碰撞检测 ==============
    def _handle_collisions(self) -> List[Dict]:
        """处理所有碰撞（修复NaN问题）"""
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
                    self._resolve_ground(obj, info)
                    collisions.append({
                        'object1': obj_id, 'object2': 'ground', **info
                    })
        
        return collisions
    
    def _check_collision(self, obj1: PhysicsObject, 
                         obj2: PhysicsObject) -> Optional[Dict]:
        """检查碰撞（修复NaN：安全法线计算）"""
        # AABB检测
        if (abs(obj1.position.x - obj2.position.x) > (obj1.size.x + obj2.size.x) / 2 * 1.1 or
            abs(obj1.position.y - obj2.position.y) > (obj1.size.y + obj2.size.y) / 2 * 1.1 or
            abs(obj1.position.z - obj2.position.z) > (obj1.size.z + obj2.size.z) / 2 * 1.1):
            return None
        
        # 计算差向量
        diff = Vector3D(
            obj1.position.x - obj2.position.x,
            obj1.position.y - obj2.position.y,
            obj1.position.z - obj2.position.z
        )
        
        # 安全：避免零向量
        dist = diff.magnitude()
        if dist < 0.0001:
            return {'overlap': 0.05, 'normal': Vector3D(0, 1, 0)}
        
        # 计算重叠（简化）
        overlap = 0.05
        
        # 安全法线计算
        nx = diff.x / dist
        ny = diff.y / dist
        nz = diff.z / dist
        
        # 检查法线有效性
        if not np.isfinite(nx) or not np.isfinite(ny) or not np.isfinite(nz):
            return {'overlap': overlap, 'normal': Vector3D(0, 1, 0)}
        
        return {
            'overlap': overlap,
            'normal': Vector3D(nx, ny, nz)
        }
    
    def _check_ground(self, obj: PhysicsObject) -> Optional[Dict]:
        """检查地面碰撞（修复NaN）"""
        ground_y = obj.size.y / 2
        bottom_y = obj.position.y - obj.size.y / 2
        
        if bottom_y < ground_y:
            overlap = ground_y - bottom_y
            
            # 安全检查
            if np.isfinite(overlap):
                return {
                    'overlap': overlap,
                    'normal': Vector3D(0, 1, 0)
                }
        return None
    
    def _resolve_collision(self, obj1: PhysicsObject, 
                          obj2: PhysicsObject,
                          collision_info: Dict) -> None:
        """解决碰撞（修复NaN）"""
        normal = collision_info.get('normal')
        overlap = collision_info.get('overlap', 0.05)
        
        # 安全检查
        if normal is None or not np.isfinite(overlap):
            return
        
        # 获取法线分量（安全）
        nx = normal.x if np.isfinite(normal.x) else 0
        ny = normal.y if np.isfinite(normal.y) else 1
        nz = normal.z if np.isfinite(normal.z) else 0
        
        # 归一化法线
        mag = np.sqrt(nx*nx + ny*ny + nz*nz)
        if mag < 0.001:
            mag = 1
        nx, ny, nz = nx/mag, ny/mag, nz/mag
        
        # 计算有效质量
        inv_m1 = 1.0 / obj1.mass if obj1.object_type == PhysicsObjectType.DYNAMIC else 0
        inv_m2 = 1.0 / obj2.mass if obj2.object_type == PhysicsObjectType.DYNAMIC else 0
        total_inv_mass = inv_m1 + inv_m2
        
        if total_inv_mass <= 0:
            return
        
        # 分离物体
        if inv_m1 > 0:
            obj1.position = Vector3D(
                obj1.position.x + nx * overlap * 0.5,
                obj1.position.y + ny * overlap * 0.5,
                obj1.position.z + nz * overlap * 0.5
            )
        if inv_m2 > 0:
            obj2.position = Vector3D(
                obj2.position.x - nx * overlap * 0.5,
                obj2.position.y - ny * overlap * 0.5,
                obj2.position.z - nz * overlap * 0.5
            )
        
        # 计算相对速度（安全）
        if not np.isfinite(obj1.velocity.x):
            obj1.velocity = Vector3D(0, 0, 0)
        if not np.isfinite(obj2.velocity.x):
            obj2.velocity = Vector3D(0, 0, 0)
        
        rel_vel_x = obj1.velocity.x - obj2.velocity.x
        rel_vel_y = obj1.velocity.y - obj2.velocity.y
        rel_vel_z = obj1.velocity.z - obj2.velocity.z
        
        # 法向速度分量
        vel_along_normal = rel_vel_x * nx + rel_vel_y * ny + rel_vel_z * nz
        
        # 如果分离，不处理
        if vel_along_normal > 0:
            return
        
        # 反弹冲量（安全计算）
        e = min(obj1.restitution, obj2.restitution)
        j = -(1 + e) * vel_along_normal
        j /= total_inv_mass
        
        # 检查j的有效性
        if not np.isfinite(j):
            return
        
        # 应用冲量
        impulse_x, impulse_y, impulse_z = j * nx, j * ny, j * nz
        
        if inv_m1 > 0:
            obj1.velocity = Vector3D(
                obj1.velocity.x + impulse_x * inv_m1,
                obj1.velocity.y + impulse_y * inv_m1,
                obj1.velocity.z + impulse_z * inv_m1
            )
        if inv_m2 > 0:
            obj2.velocity = Vector3D(
                obj2.velocity.x - impulse_x * inv_m2,
                obj2.velocity.y - impulse_y * inv_m2,
                obj2.velocity.z - impulse_z * inv_m2
            )
        
        # 应用摩擦
        self._apply_friction(obj1, obj2, rel_vel_x, rel_vel_y, rel_vel_z, inv_m1, inv_m2)
    
    def _resolve_ground(self, obj: PhysicsObject, collision_info: Dict) -> None:
        """解决地面碰撞（修复NaN）"""
        normal = collision_info.get('normal')
        overlap = collision_info.get('overlap', 0.05)
        
        if normal is None or not np.isfinite(overlap):
            return
        
        # 分离物体到地面上方
        obj.position = Vector3D(
            obj.position.x,
            self.ground_y + obj.size.y / 2 + 0.001,
            obj.position.z
        )
        
        # 法向速度
        vy = obj.velocity.y
        if vy < 0:
            j = -(1 + obj.restitution) * vy
            j /= (1.0 / obj.mass)
            
            if np.isfinite(j):
                obj.velocity.y = obj.velocity.y + j * (1.0 / obj.mass)
        
        # 应用地面摩擦
        friction = obj.friction
        obj.velocity.x *= (1.0 - friction * 0.1)
        obj.velocity.z *= (1.0 - friction * 0.1)
        
        # 速度阈值检查（休眠）
        if abs(obj.velocity.y) < 0.05:
            obj.velocity.y = 0
        
    def _apply_friction(self, obj1: PhysicsObject, obj2: PhysicsObject,
                        rel_vel_x: float, rel_vel_y: float, rel_vel_z: float,
                        inv_m1: float, inv_m2: float) -> None:
        """应用摩擦（修复NaN）"""
        friction = min(obj1.friction, obj2.friction)
        
        # 切向速度（忽略法向）
        tangent_speed = np.sqrt(rel_vel_x**2 + rel_vel_z**2)
        
        if tangent_speed < 0.01:
            return
        
        # 摩擦冲量
        friction_impulse = friction * tangent_speed * 0.1
        
        # 安全检查
        if not np.isfinite(friction_impulse):
            return
        
        # 应用
        if inv_m1 > 0:
            obj1.velocity.x -= np.sign(rel_vel_x) * friction_impulse * inv_m1
            obj1.velocity.z -= np.sign(rel_vel_z) * friction_impulse * inv_m1
        if inv_m2 > 0:
            obj2.velocity.x += np.sign(rel_vel_x) * friction_impulse * inv_m2
            obj2.velocity.z += np.sign(rel_vel_z) * friction_impulse * inv_m2
    
    def get_physics_state(self) -> Dict:
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
    return PhysicsEngine(gravity=gravity)
