"""
物理属性模块（增强版）
提供物理属性建模和推理的基础能力

增强内容:
1. 添加Vec2类支持
2. 增强摩擦力相关属性
3. 添加物理碰撞属性
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class MaterialType(Enum):
    """材料类型"""
    SOLID = "solid"
    LIQUID = "liquid"
    GAS = "gas"
    PLASMA = "plasma"


class PhysicalProperty(Enum):
    """物理属性"""
    MASS = "mass"
    VOLUME = "volume"
    DENSITY = "density"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"
    FORCE = "force"
    ENERGY = "energy"
    POWER = "power"
    CHARGE = "charge"
    MAGNETIC = "magnetic"
    ELASTICITY = "elasticity"
    FRICTION = "friction"
    TRANSPARENCY = "transparency"
    CONDUCTIVITY = "conductivity"
    # 增强：添加碰撞相关属性
    RESTITUTION = "restitution"
    PENETRATION = "penetration"


# ============== 增强1: 添加Vec2类 ==============
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
class PhysicalProperties:
    """物理属性集合（增强版）"""
    properties: Dict[PhysicalProperty, float] = field(default_factory=dict)
    material: MaterialType = MaterialType.SOLID
    
    # 额外属性
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)  # RGB
    texture: str = "smooth"
    hardness: float = 0.5  # 0-1
    porosity: float = 0.0  # 0-1
    conductivity: float = 0.5  # 导热系数
    transparency: float = 0.0  # 透明度 0-1
    
    # 增强：碰撞相关属性
    restitution: float = 0.5  # 弹性系数
    friction: float = 0.3     # 摩擦系数
    
    def get(self, prop: PhysicalProperty) -> Optional[float]:
        """获取属性值"""
        return self.properties.get(prop)
    
    def set(self, prop: PhysicalProperty, value: float):
        """设置属性值"""
        self.properties[prop] = value
    
    def compute_density(self, mass: float, volume: float):
        """计算密度"""
        if volume > 0:
            self.properties[PhysicalProperty.DENSITY] = mass / volume
    
    def get_derived_properties(self) -> Dict[str, float]:
        """获取导出属性"""
        derived = {}
        
        # 密度
        if PhysicalProperty.MASS in self.properties and PhysicalProperty.VOLUME in self.properties:
            mass = self.properties[PhysicalProperty.MASS]
            volume = self.properties[PhysicalProperty.VOLUME]
            if volume > 0:
                derived['density'] = mass / volume
        
        # 动能 (使用速度向量的模)
        if PhysicalProperty.MASS in self.properties and PhysicalProperty.VELOCITY in self.properties:
            mass = self.properties[PhysicalProperty.MASS]
            vel = self.properties[PhysicalProperty.VELOCITY]
            # 支持Vec2或标量
            if isinstance(vel, Vec2):
                vel_mag = vel.magnitude()
            else:
                vel_mag = abs(vel)
            derived['kinetic_energy'] = 0.5 * mass * vel_mag**2
        
        # 势能
        if PhysicalProperty.MASS in self.properties:
            mass = self.properties[PhysicalProperty.MASS]
            gravity = 9.8
            height = self.properties.get(PhysicalProperty.POSITION, {}).get('y', 0)
            derived['potential_energy'] = mass * gravity * height
        
        return derived
    
    # 增强：碰撞响应方法
    def get_bounciness(self) -> float:
        """获取弹性系数（用于碰撞响应）"""
        return self.properties.get(PhysicalProperty.ELASTICITY, self.restitution)
    
    def get_friction_coefficient(self) -> float:
        """获取摩擦系数"""
        return self.properties.get(PhysicalProperty.FRICTION, self.friction)


class PropertyDatabase:
    """属性数据库"""
    
    def __init__(self):
        self.materials: Dict[str, PhysicalProperties] = {}
        self.objects: Dict[str, PhysicalProperties] = {}
        self._initialize_common_materials()
    
    def _initialize_common_materials(self):
        """初始化常见材料属性（增强版：包含碰撞属性）"""
        # 金属
        metal = PhysicalProperties(
            material=MaterialType.SOLID,
            color=(0.7, 0.7, 0.7),
            hardness=0.8,
            conductivity=0.9,
            restitution=0.7,  # 弹性
            friction=0.3     # 摩擦
        )
        metal.properties[PhysicalProperty.DENSITY] = 7800  # kg/m³
        metal.properties[PhysicalProperty.ELASTICITY] = 0.7
        metal.properties[PhysicalProperty.FRICTION] = 0.3
        self.materials['metal'] = metal
        
        # 木头
        wood = PhysicalProperties(
            material=MaterialType.SOLID,
            color=(0.6, 0.4, 0.2),
            hardness=0.4,
            porosity=0.3,
            conductivity=0.2,
            restitution=0.5,
            friction=0.6
        )
        wood.properties[PhysicalProperty.DENSITY] = 600  # kg/m³
        wood.properties[PhysicalProperty.ELASTICITY] = 0.5
        wood.properties[PhysicalProperty.FRICTION] = 0.6
        self.materials['wood'] = wood
        
        # 水
        water = PhysicalProperties(
            material=MaterialType.LIQUID,
            color=(0.2, 0.4, 0.8),
            conductivity=0.1,
            restitution=0.1,  # 水几乎无弹性
            friction=0.01     # 低摩擦
        )
        water.properties[PhysicalProperty.DENSITY] = 1000  # kg/m³
        water.properties[PhysicalProperty.FRICTION] = 0.01
        self.materials['water'] = water
        
        # 空气
        air = PhysicalProperties(
            material=MaterialType.GAS,
            color=(0.9, 0.9, 0.9),
            transparency=0.95,
            restitution=0.0,   # 气体无弹性
            friction=0.001     # 极低摩擦
        )
        air.properties[PhysicalProperty.DENSITY] = 1.2  # kg/m³
        air.properties[PhysicalProperty.FRICTION] = 0.001
        self.materials['air'] = air
        
        # 塑料
        plastic = PhysicalProperties(
            material=MaterialType.SOLID,
            color=(0.9, 0.9, 0.9),
            hardness=0.3,
            conductivity=0.05,
            restitution=0.6,
            friction=0.4
        )
        plastic.properties[PhysicalProperty.DENSITY] = 1200  # kg/m³
        plastic.properties[PhysicalProperty.ELASTICITY] = 0.6
        plastic.properties[PhysicalProperty.FRICTION] = 0.4
        self.materials['plastic'] = plastic
    
    def get_material(self, name: str) -> Optional[PhysicalProperties]:
        """获取材料属性"""
        return self.materials.get(name.lower())
    
    def register_object(self, obj_id: str, properties: PhysicalProperties):
        """注册对象"""
        self.objects[obj_id] = properties
    
    def get_object(self, obj_id: str) -> Optional[PhysicalProperties]:
        """获取对象属性"""
        return self.objects.get(obj_id)
    
    def infer_properties(self, material: str, shape: str = "generic",
                         size: Tuple[float, float, float] = (0.1, 0.1, 0.1)) -> PhysicalProperties:
        """推断物体属性（增强版：包含碰撞属性）"""
        base_props = self.get_material(material)
        if not base_props:
            return PhysicalProperties()
        
        # 复制基本属性
        props = PhysicalProperties(
            material=base_props.material,
            color=base_props.color,
            texture=base_props.texture,
            hardness=base_props.hardness,
            porosity=base_props.porosity,
            conductivity=base_props.conductivity,
            restitution=base_props.restitution,  # 增强：继承弹性系数
            friction=base_props.friction         # 增强：继承摩擦系数
        )
        
        # 根据形状调整
        volume = size[0] * size[1] * size[2]
        props.properties[PhysicalProperty.VOLUME] = volume
        
        if PhysicalProperty.DENSITY in base_props.properties:
            props.properties[PhysicalProperty.MASS] = (
                base_props.properties[PhysicalProperty.DENSITY] * volume
            )
        
        return props


class PropertyInference:
    """属性推断引擎"""
    
    def __init__(self):
        self.property_db = PropertyDatabase()
        self.inference_rules: List[Dict] = []
        self._initialize_rules()
    
    def _initialize_rules(self):
        """初始化推断规则"""
        self.inference_rules = [
            {
                "if": {"material": "metal"},
                "then": {"conductivity": 0.9, "hardness": 0.8}
            },
            {
                "if": {"material": "wood"},
                "then": {"conductivity": 0.2, "hardness": 0.4}
            },
            {
                "if": {"material": "water", "temperature": lambda t: t < 0},
                "then": {"material": "ice"}
            },
            {
                "if": {"material": "water", "temperature": lambda t: t > 100},
                "then": {"material": "steam"}
            }
        ]
    
    def infer_from_observation(self, observations: Dict) -> PhysicalProperties:
        """从观察推断属性"""
        props = PhysicalProperties()
        
        # 从颜色推断材料
        if "color" in observations:
            color = observations["color"]
            if color[0] > 0.8 and color[1] > 0.8 and color[2] > 0.8:
                props.color = color
                if "transparency" not in observations:
                    props.properties[PhysicalProperty.TRANSPARENCY] = 0.5
        
        # 从名称推断材料
        if "name" in observations:
            name = observations["name"].lower()
            if "cup" in name or "bottle" in name:
                material_props = self.property_db.get_material("plastic")
                if material_props:
                    props = material_props
            elif "table" in name or "chair" in name:
                material_props = self.property_db.get_material("wood")
                if material_props:
                    props = material_props
        
        # 从形状推断
        if "shape" in observations:
            shape = observations["shape"]
            if shape == "sphere":
                props.properties[PhysicalProperty.ELASTICITY] = 0.8
            elif shape == "box":
                props.properties[PhysicalProperty.ELASTICITY] = 0.3
        
        return props
    
    def predict_interaction_properties(self, obj1_props: PhysicalProperties,
                                       obj2_props: PhysicalProperties) -> Dict:
        """预测相互作用属性"""
        predictions = {}
        
        # 摩擦系数
        if PhysicalProperty.FRICTION in obj1_props.properties and \
           PhysicalProperty.FRICTION in obj2_props.properties:
            friction1 = obj1_props.properties[PhysicalProperty.FRICTION]
            friction2 = obj2_props.properties[PhysicalProperty.FRICTION]
            predictions['combined_friction'] = (friction1 + friction2) / 2
        
        # 弹性碰撞
        if PhysicalProperty.ELASTICITY in obj1_props.properties and \
           PhysicalProperty.ELASTICITY in obj2_props.properties:
            elasticity1 = obj1_props.properties[PhysicalProperty.ELASTICITY]
            elasticity2 = obj2_props.properties[PhysicalProperty.ELASTICITY]
            predictions['bounciness'] = (elasticity1 + elasticity2) / 2
        
        # 导热性
        if PhysicalProperty.CONDUCTIVITY in obj1_props.properties and \
           PhysicalProperty.CONDUCTIVITY in obj2_props.properties:
            cond1 = obj1_props.properties[PhysicalProperty.CONDUCTIVITY]
            cond2 = obj2_props.properties[PhysicalProperty.CONDUCTIVITY]
            predictions['heat_transfer'] = (cond1 + cond2) / 2
        
        return predictions


class MaterialSimulation:
    """材料模拟"""
    
    def __init__(self):
        self.state_changes: Dict[str, List[Dict]] = {}
        self.transition_rules: List[Dict] = []
        self._initialize_transitions()
    
    def _initialize_transitions(self):
        """初始化相变规则"""
        self.transition_rules = [
            {
                "from": "water",
                "to": "ice",
                "condition": lambda t: t < 0,
                "property_change": {"hardness": 0.9, "transparency": 0.3}
            },
            {
                "from": "water",
                "to": "steam",
                "condition": lambda t: t > 100,
                "property_change": {"density": 0.6, "transparency": 0.95}
            },
            {
                "from": "ice",
                "to": "water",
                "condition": lambda t: t > 0,
                "property_change": {"hardness": 0.1, "transparency": 0.8}
            }
        ]
    
    def simulate_state_change(self, material: str, temperature: float,
                             duration: float) -> Dict:
        """模拟状态变化"""
        current_material = material
        current_temp = temperature
        changes = []
        
        for rule in self.transition_rules:
            if rule["from"] == current_material:
                if rule["condition"](current_temp):
                    new_material = rule["to"]
                    changes.append({
                        "from": current_material,
                        "to": new_material,
                        "temperature": current_temp,
                        "duration": duration,
                        "changes": rule["property_change"]
                    })
                    current_material = new_material
        
        return {
            "initial_material": material,
            "final_material": current_material,
            "changes": changes
        }
    
    def get_material_behavior(self, material: str, interaction_type: str) -> Dict:
        """获取材料行为"""
        behaviors = {
            "solid": {
                "falling": "maintains shape",
                "pushing": "resists",
                "holding": "contains",
                "heating": "expands slowly"
            },
            "liquid": {
                "falling": "flows",
                "pushing": "flows around",
                "holding": "fills container",
                "heating": "evaporates"
            },
            "gas": {
                "falling": "rises",
                "pushing": "compresses",
                "holding": "escapes",
                "heating": "expands"
            }
        }
        
        material_type = self._get_material_type(material)
        return behaviors.get(material_type, {})
    
    def _get_material_type(self, material: str) -> str:
        """获取材料类型"""
        materials = {
            "metal": "solid",
            "wood": "solid",
            "plastic": "solid",
            "ice": "solid",
            "water": "liquid",
            "oil": "liquid",
            "air": "gas",
            "steam": "gas"
        }
        return materials.get(material.lower(), "solid")


if __name__ == "__main__":
    # 简单测试
    db = PropertyDatabase()
    
    # 获取材料
    water = db.get_material("water")
    print(f"Water density: {water.properties.get('density', 'N/A')}")
    
    # 推断物体属性
    cup_props = db.infer_properties("plastic", "cylinder", (0.08, 0.12, 0.08))
    print(f"Cup mass: {cup_props.properties.get('mass', 'N/A')}")
    
    # 属性推断
    inference = PropertyInference()
    obs_props = inference.infer_from_observation({"name": "Metal pan"})
    print(f"Inferred conductivity: {obs_props.properties.get('conductivity', 'N/A')}")
    
    # 相互作用预测
    predictions = inference.predict_interaction_properties(
        db.infer_properties("rubber"),
        db.infer_properties("wood")
    )
    print(f"Predicted bounciness: {predictions.get('bounciness', 'N/A')}")
    
    # 状态模拟
    sim = MaterialSimulation()
    result = sim.simulate_state_change("water", -5.0, 10.0)
    print(f"State change result: {result}")
