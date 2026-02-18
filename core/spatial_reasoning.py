"""
空间推理模块
提供空间关系理解和推理的基础能力
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict


class SpatialRelation(Enum):
    """空间关系类型"""
    ABOVE = "above"
    BELOW = "below"
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"
    BEHIND = "behind"
    INSIDE = "inside"
    OUTSIDE = "outside"
    ON = "on"
    NEAR = "near"
    FAR = "far"
    CONNECTED = "connected"
    SEPARATED = "separated"
    OVERLAPPING = "overlapping"
    CONTAINING = "containing"


@dataclass
class BoundingBox:
    """边界框"""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    
    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2
        )
    
    @property
    def size(self) -> Tuple[float, float, float]:
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z
        )
    
    @property
    def volume(self) -> float:
        s = self.size
        return s[0] * s[1] * s[2]
    
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """检查点是否在边界框内"""
        return (self.min_x <= point[0] <= self.max_x and
                self.min_y <= point[1] <= self.max_y and
                self.min_z <= point[2] <= self.max_z)
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """检查两个边界框是否相交"""
        return not (self.max_x < other.min_x or other.max_x < self.min_x or
                   self.max_y < other.min_y or other.max_y < self.min_y or
                   self.max_z < other.min_z or other.max_z < self.min_z)
    
    def contains(self, other: 'BoundingBox') -> bool:
        """检查是否包含另一个边界框"""
        return (self.min_x <= other.min_x and self.max_x >= other.max_x and
                self.min_y <= other.min_y and self.max_y >= other.max_y and
                self.min_z <= other.min_z and self.max_z >= other.max_z)
    
    @classmethod
    def from_position_size(cls, position: Tuple[float, float, float], 
                          size: Tuple[float, float, float]) -> 'BoundingBox':
        """从位置和大小创建边界框"""
        half_size = tuple(s / 2 for s in size)
        return cls(
            min_x=position[0] - half_size[0],
            min_y=position[1] - half_size[1],
            min_z=position[2] - half_size[2],
            max_x=position[0] + half_size[0],
            max_y=position[1] + half_size[1],
            max_z=position[2] + half_size[2]
        )


@dataclass
class SpatialObject:
    """空间对象"""
    id: str
    name: str
    position: Tuple[float, float, float]
    size: Tuple[float, float, float]
    orientation: Tuple[float, float, float] = (0, 0, 0)  # roll, pitch, yaw
    category: str = "unknown"
    
    # 计算属性
    bounding_box: BoundingBox = None
    
    def __post_init__(self):
        self.bounding_box = BoundingBox.from_position_size(self.position, self.size)


class SpatialReasoner:
    """空间推理器"""
    
    def __init__(self):
        self.objects: Dict[str, SpatialObject] = {}
        self.relations: Dict[Tuple[str, str], Set[SpatialRelation]] = defaultdict(set)
    
    def add_object(self, obj: SpatialObject):
        """添加空间对象"""
        self.objects[obj.id] = obj
        self._compute_relations(obj.id)
    
    def remove_object(self, obj_id: str):
        """移除空间对象"""
        if obj_id in self.objects:
            del self.objects[obj_id]
            # 移除相关关系
            keys_to_remove = [k for k in self.relations if obj_id in k]
            for k in keys_to_remove:
                del self.relations[k]
    
    def get_object(self, obj_id: str) -> Optional[SpatialObject]:
        """获取空间对象"""
        return self.objects.get(obj_id)
    
    def _compute_relations(self, obj_id: str):
        """计算对象与所有其他对象的关系"""
        obj = self.objects.get(obj_id)
        if not obj:
            return
        
        for other_id, other in self.objects.items():
            if other_id == obj_id:
                continue
            
            relations = self._determine_relations(obj, other)
            self.relations[(obj_id, other_id)] = relations
    
    def _determine_relations(self, obj1: SpatialObject, 
                            obj2: SpatialObject) -> Set[SpatialRelation]:
        """确定两个对象之间的空间关系"""
        relations = set()
        
        # 获取位置和大小
        p1 = np.array(obj1.position)
        p2 = np.array(obj2.position)
        s1 = np.array(obj1.size)
        s2 = np.array(obj2.size)
        
        # 计算中心距离
        dist = np.linalg.norm(p1 - p2)
        
        # 计算相对位置
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        
        # 垂直关系
        if dy > s1[1]/2 + s2[1]/2:
            relations.add(SpatialRelation.ABOVE)
        elif dy < -(s1[1]/2 + s2[1]/2):
            relations.add(SpatialRelation.BELOW)
        
        # 水平关系
        if abs(dx) < s1[0]/2 + s2[0]/2 and abs(dz) < s1[2]/2 + s2[2]/2:
            if dy > 0:
                relations.add(SpatialRelation.ON)
            else:
                relations.add(SpatialRelation.BELOW)
        else:
            if dx > 0:
                relations.add(SpatialRelation.RIGHT)
            elif dx < 0:
                relations.add(SpatialRelation.LEFT)
            if dz > 0:
                relations.add(SpatialRelation.FRONT)
            elif dz < 0:
                relations.add(SpatialRelation.BEHIND)
        
        # 包含关系
        if obj1.bounding_box.contains(obj2.bounding_box):
            relations.add(SpatialRelation.CONTAINING)
            relations.add(SpatialRelation.OUTSIDE)
        elif obj2.bounding_box.contains(obj1.bounding_box):
            relations.add(SpatialRelation.INSIDE)
        
        # 相交关系
        if obj1.bounding_box.intersects(obj2.bounding_box):
            if not relations & {SpatialRelation.INSIDE, SpatialRelation.CONTAINING}:
                relations.add(SpatialRelation.OVERLAPPING)
        
        # 邻近关系
        threshold = 0.5  # 阈值
        if dist < threshold:
            relations.add(SpatialRelation.NEAR)
        else:
            relations.add(SpatialRelation.FAR)
        
        # 分离关系
        if not obj1.bounding_box.intersects(obj2.bounding_box):
            relations.add(SpatialRelation.SEPARATED)
        
        return relations
    
    def get_relations(self, obj1_id: str, obj2_id: str) -> Set[SpatialRelation]:
        """获取两个对象之间的空间关系"""
        return self.relations.get((obj1_id, obj2_id), set())
    
    def find_objects_with_relation(self, reference_id: str, 
                                   relation: SpatialRelation) -> List[str]:
        """查找与参考对象有特定关系的对象"""
        results = []
        
        for (id1, id2), rels in self.relations.items():
            if id1 == reference_id and relation in rels:
                results.append(id2)
            elif id2 == reference_id and relation in rels:
                results.append(id1)
        
        return results
    
    def find_objects_in_region(self, min_pos: Tuple[float, float, float],
                               max_pos: Tuple[float, float, float]) -> List[str]:
        """查找在指定区域内的对象"""
        results = []
        min_bbox = BoundingBox(min_pos[0], min_pos[1], min_pos[2],
                              max_pos[0], max_pos[1], max_pos[2])
        
        for obj in self.objects.values():
            if min_bbox.intersects(obj.bounding_box):
                results.append(obj.id)
        
        return results
    
    def compute_path(self, start_id: str, end_id: str) -> List[Tuple[float, float, float]]:
        """计算路径"""
        # 简化：A*算法
        start = self.objects.get(start_id)
        end = self.objects.get(end_id)
        
        if not start or not end:
            return []
        
        # 简化：返回直线
        return [start.position, end.position]
    
    def spatial_query(self, query: str) -> List[str]:
        """空间查询"""
        query = query.lower()
        
        if "above" in query or "on top of" in query:
            # 查找"on"关系的对象
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.ON)
        
        elif "below" in query or "under" in query:
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.BELOW)
        
        elif "inside" in query or "in" in query:
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.INSIDE)
        
        elif "near" in query or "close to" in query:
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.NEAR)
        
        elif "left of" in query:
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.LEFT)
        
        elif "right of" in query:
            target = self._extract_target(query)
            if target:
                return self.find_objects_with_relation(target, SpatialRelation.RIGHT)
        
        return []
    
    def _extract_target(self, query: str) -> Optional[str]:
        """从查询中提取目标对象"""
        # 简化：查找最后一个对象名
        words = query.split()
        if len(words) >= 2:
            target_name = words[-1]
            for obj in self.objects.values():
                if obj.name.lower() == target_name.lower():
                    return obj.id
        return None


class SpatialMemory:
    """空间记忆"""
    
    def __init__(self):
        self.scenes: Dict[str, List[SpatialObject]] = {}
        self.current_scene_id: Optional[str] = None
        self.visited_locations: Dict[str, Tuple[float, float, float]] = {}
    
    def add_scene(self, scene_id: str, objects: List[SpatialObject]):
        """添加场景"""
        self.scenes[scene_id] = objects
    
    def switch_scene(self, scene_id: str):
        """切换场景"""
        if scene_id in self.scenes:
            self.current_scene_id = scene_id
    
    def remember_location(self, name: str, position: Tuple[float, float, float]):
        """记住位置"""
        self.visited_locations[name] = position
    
    def get_location(self, name: str) -> Optional[Tuple[float, float, float]]:
        """获取记住的位置"""
        return self.visited_locations.get(name)
    
    def get_current_scene(self) -> List[SpatialObject]:
        """获取当前场景"""
        if self.current_scene_id:
            return self.scenes.get(self.current_scene_id, [])
        return []


if __name__ == "__main__":
    # 简单测试
    reasoner = SpatialReasoner()
    
    # 添加对象
    table = SpatialObject(
        id="table",
        name="Table",
        position=(0, 0.4, 0),
        size=(1.0, 0.4, 0.6),
        category="furniture"
    )
    
    cup = SpatialObject(
        id="cup",
        name="Cup",
        position=(0.1, 0.6, 0.1),
        size=(0.08, 0.12, 0.08),
        category="container"
    )
    
    book = SpatialObject(
        id="book",
        name="Book",
        position=(-0.2, 0.6, -0.1),
        size=(0.2, 0.03, 0.15),
        category="object"
    )
    
    reasoner.add_object(table)
    reasoner.add_object(cup)
    reasoner.add_object(book)
    
    # 查询关系
    relations = reasoner.get_relations("cup", "table")
    print(f"Cup-Table relations: {[r.value for r in relations]}")
    
    relations = reasoner.get_relations("book", "table")
    print(f"Book-Table relations: {[r.value for r in relations]}")
    
    # 空间查询
    above_table = reasoner.find_objects_with_relation("table", SpatialRelation.ON)
    print(f"Objects on table: {above_table}")
    
    # 场景记忆
    memory = SpatialMemory()
    memory.add_scene("room1", [table, cup, book])
    memory.switch_scene("room1")
    
    current_objects = memory.get_current_scene()
    print(f"Current scene objects: {[obj.name for obj in current_objects]}")
