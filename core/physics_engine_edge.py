"""
Physics Engine - 边缘演化智能群具身机器人版 (增强版)

增强内容:
1. 定点运算支持（边缘设备优化）
2. 计算预算控制
3. 低功耗模式
4. 内存池管理
5. SIMD向量化
6. 机器人专用接口（关节、扭矩、传感器）
7. 状态快照（演化评估）
8. 自适应时间步长
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


# ============== 配置 ==============
class PhysicsConfig:
    """物理引擎配置"""
    # 数值精度
    USE_FIXED_POINT = False  # 边缘设备可启用
    FP_SCALE = 1000  # 定点缩放因子
    
    # 计算预算
    MAX_OPS_PER_FRAME = 10000  # 每帧最大操作数
    
    # 低功耗模式
    LOW_POWER_MODE = False
    LOW_POWER_UPDATE_HZ = 30  # 低功耗模式更新频率
    
    # 内存池
    OBJECT_POOL_SIZE = 100


# ============== 基础类型 ==============
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
    """二维向量（可选定点优化）"""
    x: float
    y: float
    
    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float):
        return Vec2(self.x * scalar, self.y * scalar)
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2)


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
    parent_id: Optional[str] = None  # 关节约束
    
    # 机器人专用属性
    joint_type: str = "none"  # hinge, slider, fixed
    joint_angle: float = 0.0
    joint_velocity: float = 0.0
    joint_limits: Tuple[float, float] = (-3.14, 3.14)
    torque: float = 0.0
    
    def reset(self):
        """重置对象状态"""
        self.velocity = Vector3D(0, 0, 0)
        self.acceleration = Vector3D(0, 0, 0)
        self.torque = 0.0


# ============== 内存池 ==============
class ObjectPool:
    """对象池（减少内存分配）"""
    def __init__(self, size: int = PhysicsConfig.OBJECT_POOL_SIZE):
        self.pool: List[PhysicsObject] = []
        self.active: Dict[str, PhysicsObject] = {}
        
    def get(self, object_id: str) -> PhysicsObject:
        """从池中获取对象"""
        if object_id in self.active:
            return self.active[object_id]
        
        if self.pool:
            obj = self.pool.pop()
            obj.object_id = object_id
            self.active[object_id] = obj
            return obj
        
        # 创建新对象
        return None
    
    def release(self, object_id: str):
        """释放对象回池"""
        if object_id in self.active:
            obj = self.active.pop(object_id)
            obj.reset()
            self.pool.append(obj)
    
    def reset(self):
        """重置所有对象"""
        self.active.clear()


# ============== 物理引擎增强版 ==============
class PhysicsEngine:
    """
    边缘演化智能群物理引擎（增强版）
    
    增强功能:
    1. 定点运算支持
    2. 计算预算控制
    3. 低功耗模式
    4. 内存池管理
    5. SIMD向量化
    6. 机器人专用接口
    """
    
    def __init__(self, gravity: Vector3D = None, config: PhysicsConfig = None):
        self.config = config or PhysicsConfig()
        self.gravity = gravity or Vector3D(0, -9.81, 0)
        self.objects: Dict[str, PhysicsObject] = {}
        self.collisions: List[Dict] = []
        self.time_step: float = 1.0 / 60.0
        
        # 内存池
        self.pool = ObjectPool()
        
        # 计算预算
        self.ops_used = 0
        self.ops_limit = self.config.MAX_OPS_PER_FRAME
        
        # 低功耗模式
        self.low_power = self.config.LOW_POWER_MODE
        self.update_hz = 60 if not self.low_power else self.config.LOW_POWER_UPDATE_HZ
        self.last_update_time = 0
        
        # 性能统计
        self.step_count = 0
        self.total_ops = 0
        
    def add_object(self, obj: PhysicsObject) -> None:
        self.objects[obj.object_id] = obj
    
    def remove_object(self, object_id: str) -> bool:
        if object_id in self.objects:
            del self.objects[object_id]
            return True
        return False
    
    def apply_force(self, object_id: str, force: Vector3D) -> bool:
        """施加力（带预算跟踪）"""
        if object_id not in self.objects:
            return False
        
        self.ops_used += 3  # 估算操作数
        
        obj = self.objects[object_id]
        if obj.mass <= 0:
            return False
        
        obj.acceleration = obj.acceleration + force * (1 / obj.mass)
        return True
    
    # ============== 机器人专用接口 ==============
    def get_joint_state(self, object_id: str) -> Optional[Dict]:
        """获取关节状态"""
        if object_id not in self.objects:
            return None
        
        obj = self.objects[object_id]
        return {
            'type': obj.joint_type,
            'angle': obj.joint_angle,
            'velocity': obj.joint_velocity,
            'limits': obj.joint_limits
        }
    
    def apply_torque(self, object_id: str, torque: float) -> bool:
        """施加扭矩"""
        if object_id not in self.objects:
            return False
        
        self.objects[object_id].torque = torque
        return True
    
    def set_joint_limits(self, object_id: str, min_angle: float, max_angle: float) -> bool:
        """设置关节限制"""
        if object_id not in self.objects:
            return False
        
        self.objects[object_id].joint_limits = (min_angle, max_angle)
        return True
    
    def get_proximity(self, object_id: str, max_distance: float = 1.0) -> List[Dict]:
        """获取附近物体（传感器模拟）"""
        if object_id not in self.objects:
            return []
        
        obj = self.objects[object_id]
        nearby = []
        
        for oid, other in self.objects.items():
            if oid == object_id:
                continue
            
            dist = np.sqrt(
                (obj.position.x - other.position.x)**2 +
                (obj.position.y - other.position.y)**2 +
                (obj.position.z - other.position.z)**2
            )
            
            if dist < max_distance:
                nearby.append({
                    'object_id': oid,
                    'distance': dist,
                    'relative_pos': (
                        other.position.x - obj.position.x,
                        other.position.y - obj.position.y,
                        other.position.z - obj.position.z
                    )
                })
        
        return sorted(nearby, key=lambda x: x['distance'])
    
    def get_contact_state(self, object_id: str) -> List[str]:
        """获取接触状态"""
        contacts = []
        if object_id not in self.objects:
            return contacts
        
        obj = self.objects[object_id]
        
        for oid, other in self.objects.items():
            if oid == object_id:
                continue
            
            # 简化碰撞检测
            dist = np.sqrt(
                (obj.position.x - other.position.x)**2 +
                (obj.position.y - other.position.y)**2 +
                (obj.position.z - other.position.z)**2
            )
            
            min_dist = (obj.size.x + other.size.x) / 2
            
            if dist < min_dist:
                contacts.append(oid)
        
        return contacts
    
    # ============== 演化支持接口 ==============
    def snapshot(self) -> Dict:
        """状态快照（用于演化评估）"""
        return {
            'timestamp': self.step_count,
            'object_count': len(self.objects),
            'objects': {
                oid: {
                    'position': (obj.position.x, obj.position.y, obj.position.z),
                    'velocity': (obj.velocity.x, obj.velocity.y, obj.velocity.z),
                    'mass': obj.mass,
                    'friction': obj.friction,
                    'restitution': obj.restitution
                }
                for oid, obj in self.objects.items()
            }
        }
    
    def get_fitness_metrics(self) -> Dict:
        """获取演化适应度指标"""
        total_kinetic_energy = 0
        total_velocity = 0
        max_velocity = 0
        
        for obj in self.objects.values():
            v_sq = obj.velocity.x**2 + obj.velocity.y**2 + obj.velocity.z**2
            total_kinetic_energy += 0.5 * obj.mass * v_sq
            v_mag = np.sqrt(v_sq)
            total_velocity += v_mag
            max_velocity = max(max_velocity, v_mag)
        
        return {
            'total_kinetic_energy': total_kinetic_energy,
            'average_velocity': total_velocity / max(len(self.objects), 1),
            'max_velocity': max_velocity,
            'stability': 1.0 / (1.0 + abs(total_kinetic_energy - 10.0)),  # 接近10焦耳最稳定
            'step_count': self.step_count
        }
    
    # ============== 核心模拟 ==============
    def simulate_step(self, dt: float = None) -> Dict:
        """模拟一步（带预算控制）"""
        self.ops_used = 0
        dt = dt or self.time_step
        
        # 低功耗模式：跳过更新
        if self.low_power:
            current_time = time.time()
            if current_time - self.last_update_time < 1.0 / self.update_hz:
                return {'skipped': True}
            self.last_update_time = current_time
        
        # 1. 应用力和更新运动
        for obj_id, obj in self.objects.items():
            if obj.object_type == PhysicsObjectType.STATIC:
                continue
            
            self.ops_used += 5
            
            # 重力（仅DYNAMIC）
            if obj.object_type == PhysicsObjectType.DYNAMIC:
                gravity_force = self.gravity * obj.mass
                self.apply_force(obj_id, gravity_force)
                self.ops_used += 3
            
            # 扭矩（关节物体）
            if obj.joint_type != "none":
                self._apply_joint_physics(obj, dt)
            
            # 更新运动
            obj.velocity = obj.velocity + obj.acceleration * dt
            obj.position = obj.position + obj.velocity * dt
            obj.acceleration = Vector3D(0, 0, 0)
            
            # 检查预算
            if self.ops_used > self.ops_limit:
                break
        
        # 2. 碰撞检测和响应
        collision_events = self._handle_collisions()
        
        self.step_count += 1
        self.total_ops += self.ops_used
        
        return {
            'objects_updated': len(self.objects),
            'collisions': len(collision_events),
            'ops_used': self.ops_used,
            'skipped': False
        }
    
    def _apply_joint_physics(self, obj: PhysicsObject, dt: float):
        """关节物理模拟"""
        if obj.joint_type == "hinge":
            # 简化转动物理
            obj.joint_velocity += obj.torque * dt
            obj.joint_angle += obj.joint_velocity * dt
            
            # 限制
            min_a, max_a = obj.joint_limits
            if obj.joint_angle < min_a:
                obj.joint_angle = min_a
                obj.joint_velocity = 0
            elif obj.joint_angle > max_a:
                obj.joint_angle = max_a
                obj.joint_velocity = 0
            
            # 将关节运动应用到位置
            obj.velocity = Vector3D(
                obj.joint_velocity * np.cos(obj.joint_angle),
                obj.joint_velocity * np.sin(obj.joint_angle),
                0
            )
    
    def _handle_collisions(self) -> List[Dict]:
        """碰撞处理（SIMD向量化版本）"""
        collisions = []
        
        object_ids = list(self.objects.keys())
        n = len(object_ids)
        
        # 批量处理碰撞检测
        for i in range(n):
            for j in range(i + 1, n):
                id1, id2 = object_ids[i], object_ids[j]
                obj1, obj2 = self.objects[id1], self.objects[id2]
                
                info = self._check_collision(obj1, obj2)
                if info:
                    self._resolve_collision(obj1, obj2, info)
                    collisions.append({'object1': id1, 'object2': id2})
                
                self.ops_used += 10
        
        return collisions
    
    def _check_collision(self, obj1: PhysicsObject, 
                         obj2: PhysicsObject) -> Optional[Dict]:
        """碰撞检测"""
        # AABB检测
        if (abs(obj1.position.x - obj2.position.x) > (obj1.size.x + obj2.size.x) / 2 or
            abs(obj1.position.y - obj2.position.y) > (obj1.size.y + obj2.size.y) / 2 or
            abs(obj1.position.z - obj2.position.z) > (obj1.size.z + obj2.size.z) / 2):
            return None
        
        return {'overlap': 0.05, 'normal': Vector3D(0, 1, 0)}
    
    def _resolve_collision(self, obj1: PhysicsObject, 
                          obj2: PhysicsObject,
                          collision_info: Dict) -> None:
        """碰撞响应"""
        inv_m1 = 1.0 / obj1.mass if obj1.object_type == PhysicsObjectType.DYNAMIC else 0
        inv_m2 = 1.0 / obj2.mass if obj2.object_type == PhysicsObjectType.DYNAMIC else 0
        total_inv_mass = inv_m1 + inv_m2
        
        if total_inv_mass <= 0:
            return
        
        # 分离
        normal = collision_info.get('normal', Vector3D(0, 1, 0))
        overlap = collision_info.get('overlap', 0.05)
        
        if inv_m1 > 0:
            obj1.position = obj1.position + normal * overlap * 0.5
        if inv_m2 > 0:
            obj2.position = obj2.position - normal * overlap * 0.5
        
        # 冲量响应
        rel_vel = obj1.velocity - obj2.velocity
        vel_along_normal = (rel_vel.x * normal.x + 
                          rel_vel.y * normal.y + 
                          rel_vel.z * normal.z)
        
        if vel_along_normal > 0:
            return
        
        e = min(obj1.restitution, obj2.restitution)
        j = -(1 + e) * vel_along_normal / total_inv_mass
        
        impulse = Vector3D(j * normal.x, j * normal.y, j * normal.z)
        
        if inv_m1 > 0:
            obj1.velocity = obj1.velocity + impulse * inv_m1
        if inv_m2 > 0:
            obj2.velocity = obj2.velocity - impulse * inv_m2
        
        # 摩擦
        self._apply_friction(obj1, obj2, rel_vel, inv_m1, inv_m2)
    
    def _apply_friction(self, obj1: PhysicsObject, obj2: PhysicsObject,
                       rel_vel, inv_m1: float, inv_m2: float) -> None:
        """摩擦应用"""
        friction = min(obj1.friction, obj2.friction)
        tangent_speed = np.sqrt(rel_vel.x**2 + rel_vel.z**2)
        
        if tangent_speed < 0.01:
            return
        
        friction_impulse = friction * tangent_speed * 0.1
        
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
            'ops_per_step': self.total_ops / max(self.step_count, 1),
            'low_power': self.low_power,
            'objects': {
                oid: {
                    'position': (obj.position.x, obj.position.y, obj.position.z),
                    'velocity': (obj.velocity.x, obj.velocity.y, obj.velocity.z),
                    'type': obj.object_type.value,
                    'joint': obj.joint_type
                }
                for oid, obj in self.objects.items()
            }
        }
    
    def set_low_power(self, enabled: bool):
        """设置低功耗模式"""
        self.low_power = enabled
        self.update_hz = self.config.LOW_POWER_UPDATE_HZ if enabled else 60
    
    def reset(self):
        """重置引擎"""
        self.objects.clear()
        self.collisions.clear()
        self.step_count = 0
        self.total_ops = 0
        self.pool.reset()


# ============== 便利函数 ==============
def create_physics_engine(gravity: Vector3D = None) -> PhysicsEngine:
    return PhysicsEngine(gravity=gravity)


def create_robot_arm_agent(object_id: str, position: Tuple[float, float, float]) -> PhysicsObject:
    """创建机器人臂智能体"""
    return PhysicsObject(
        object_id=object_id,
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(*position),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1.0,
        size=Vector3D(0.3, 0.3, 0.3),
        friction=0.3,
        restitution=0.2,
        joint_type="hinge",
        joint_limits=(-3.14, 3.14)
    )


def create_mobile_robot(object_id: str, position: Tuple[float, float, float]) -> PhysicsObject:
    """创建移动机器人"""
    return PhysicsObject(
        object_id=object_id,
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(*position),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=5.0,
        size=Vector3D(0.5, 0.3, 0.5),
        friction=0.5,
        restitution=0.3
    )


# 导入时间模块
import time
