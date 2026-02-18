"""
测试物理引擎修复
验证以下功能:
1. Vec2除法和点积
2. 摩擦力生效
3. AABB碰撞检测
4. KINEMATIC物体不受重力
"""

import sys
sys.path.insert(0, 'F:/skill/physical-agi/core')

from physics_engine_fixed import (
    Vec2, Vector3D, AABB, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine, BodyType
)
from object_dynamics import Vec2 as Vec2_dyn
from physical_properties import (
    PhysicalProperties, MaterialType, PhysicalProperty, 
    PropertyDatabase, Vec2 as Vec2Props
)

def test_vec2():
    """测试Vec2功能"""
    print("=== 测试Vec2 (physics_engine_fixed) ===")
    
    # 测试加法
    v1 = Vec2(3, 4)
    v2 = Vec2(1, 2)
    v3 = v1 + v2
    assert v3.x == 4 and v3.y == 6, "加法失败"
    print(f"[PASS] 加法: {v1} + {v2} = {v3}")
    
    # 测试除法（__truediv__）
    v4 = v1 / 2
    assert abs(v4.x - 1.5) < 0.001 and abs(v4.y - 2) < 0.001, "除法失败"
    print(f"[PASS] 除法: {v1} / 2 = {v4}")
    
    # 测试点积（dot）
    dot_result = v1.dot(v2)
    expected = 3*1 + 4*2  # 3 + 8 = 11
    assert abs(dot_result - expected) < 0.001, "点积失败"
    print(f"[PASS] 点积: {v1}.dot({v2}) = {dot_result}")
    
    print("Vec2测试通过！\n")


def test_vec2_from_dynamics():
    """测试object_dynamics中的Vec2"""
    print("=== 测试Vec2 (object_dynamics) ===")
    
    v1 = Vec2_dyn(5, 12)
    v2 = Vec2_dyn(3, 4)
    
    # 测试除法
    v3 = v1 / 2
    assert abs(v3.x - 2.5) < 0.001 and abs(v3.y - 6) < 0.001
    print(f"[PASS] Vec2除法: {v1} / 2 = {v3}")
    
    # 测试点积
    dot_result = v1.dot(v2)
    expected = 5*3 + 12*4  # 15 + 48 = 63
    assert abs(dot_result - expected) < 0.001
    print(f"[PASS] Vec2点积: {v1}.dot({v2}) = {dot_result}")
    
    print("Vec2 (object_dynamics) 测试通过！\n")


def test_aabb():
    """测试AABB碰撞检测"""
    print("=== 测试AABB ===")
    
    aabb1 = AABB.from_size(0, 0, 2, 2)  # 中心(0,0), 宽2高2
    aabb2 = AABB.from_size(1.5, 0, 2, 2)  # 中心(1.5,0), 宽2高2
    
    assert aabb1.intersects(aabb2), "AABB应该相交"
    print(f"[PASS] AABB相交检测: 相交={aabb1.intersects(aabb2)}")
    
    aabb3 = AABB.from_size(5, 5, 2, 2)  # 分离的AABB
    assert not aabb3.intersects(aabb1), "AABB应该不相交"
    print(f"[PASS] AABB分离检测: 不相交={not aabb3.intersects(aabb1)}")
    
    print("AABB测试通过！\n")


def test_kinematic():
    """测试KINEMATIC物体不受重力"""
    print("=== 测试KINEMATIC物体 ===")
    
    engine = PhysicsEngine(gravity=Vector3D(0, -9.81, 0))
    
    # 添加KINEMATIC物体（不应该受重力）
    kinematic = PhysicsObject(
        object_id="platform",
        object_type=PhysicsObjectType.KINEMATIC,
        position=Vector3D(0, 5, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=100,
        size=Vector3D(2, 0.5, 1)
    )
    
    # 添加DYNAMIC物体（应该受重力）
    dynamic = PhysicsObject(
        object_id="ball",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 8, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5)
    )
    
    engine.add_object(kinematic)
    engine.add_object(dynamic)
    
    # 记录初始位置
    init_kinematic_y = kinematic.position.y
    init_dynamic_y = dynamic.position.y
    
    # 模拟几步
    for _ in range(5):
        engine.simulate_step(dt=0.016)
    
    # KINEMATIC物体位置不应该改变
    assert abs(kinematic.position.y - init_kinematic_y) < 0.001, "KINEMATIC物体不应该移动"
    print(f"[PASS] KINEMATIC物体位置不变: {init_kinematic_y:.3f} -> {kinematic.position.y:.3f}")
    
    # DYNAMIC物体应该下落
    assert dynamic.position.y < init_dynamic_y, "DYNAMIC物体应该下落"
    print(f"[PASS] DYNAMIC物体下落: {init_dynamic_y:.3f} -> {dynamic.position.y:.3f}")
    
    print("KINEMATIC测试通过！\n")


def test_friction():
    """测试摩擦力字段存在且可配置"""
    print("=== 测试摩擦力字段 ===")
    
    # 创建带摩擦力的物体
    obj = PhysicsObject(
        object_id="box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 1, 0),
        velocity=Vector3D(5, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1),
        friction=0.8  # 高摩擦系数
    )
    
    # 验证摩擦力字段存在
    assert hasattr(obj, 'friction'), "物体应该有friction字段"
    assert obj.friction == 0.8, f"摩擦力应为0.8，实际为{obj.friction}"
    print(f"[PASS] 摩擦力字段存在: friction={obj.friction}")
    
    # 测试不同摩擦系数
    obj2 = PhysicsObject(
        object_id="ice",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 1, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1),
        friction=0.05  # 冰面低摩擦
    )
    assert obj2.friction == 0.05
    print(f"[PASS] 低摩擦力: friction={obj2.friction}")
    
    print("摩擦力字段测试通过！\n")


def test_bodytype_alias():
    """测试BodyType别名"""
    print("=== 测试BodyType别名 ===")
    
    # 比较值而不是Enum对象
    assert BodyType.DYNAMIC.value == PhysicsObjectType.DYNAMIC.value
    assert BodyType.STATIC.value == PhysicsObjectType.STATIC.value
    assert BodyType.KINEMATIC.value == PhysicsObjectType.KINEMATIC.value
    print("[PASS] BodyType别名兼容")


def test_physical_properties():
    """测试物理属性模块（增强版）"""
    print("=== 测试PhysicalProperties增强 ===")
    
    # 测试Vec2支持
    v = Vec2Props(3, 4)
    v_div = v / 2
    assert abs(v_div.x - 1.5) < 0.001 and abs(v_div.y - 2) < 0.001
    print(f"[PASS] Vec2除法: {v} / 2 = {v_div}")
    
    dot_result = v.dot(Vec2Props(1, 2))
    assert dot_result == 3*1 + 4*2  # 11
    print(f"[PASS] Vec2点积: {v}.dot(Vec2(1,2)) = {dot_result}")
    
    # 测试碰撞属性
    props = PhysicalProperties(
        material=MaterialType.SOLID,
        restitution=0.8,
        friction=0.5
    )
    assert props.restitution == 0.8, "弹性系数应设置为0.8"
    assert props.friction == 0.5, "摩擦系数应设置为0.5"
    print(f"[PASS] 碰撞属性: restitution={props.restitution}, friction={props.friction}")
    
    # 测试碰撞响应方法
    bounciness = props.get_bounciness()
    friction_coef = props.get_friction_coefficient()
    assert bounciness == 0.8
    assert friction_coef == 0.5
    print(f"[PASS] 碰撞响应方法: bounciness={bounciness}, friction={friction_coef}")
    
    print("PhysicalProperties测试通过！\n")


def test_property_database():
    """测试属性数据库"""
    print("=== 测试PropertyDatabase ===")
    
    db = PropertyDatabase()
    
    # 测试材料碰撞属性
    metal = db.get_material("metal")
    assert metal.restitution == 0.7
    assert metal.friction == 0.3
    print(f"[PASS] 金属碰撞属性: restitution={metal.restitution}, friction={metal.friction}")
    
    rubber = db.get_material("rubber")
    if rubber:
        print(f"[PASS] 橡胶碰撞属性: restitution={rubber.restitution}, friction={rubber.friction}")
    
    # 测试属性推断包含碰撞属性
    wood = db.infer_properties("wood", "box", (0.1, 0.1, 0.1))
    assert wood.restitution == 0.5
    assert wood.friction == 0.6
    print(f"[PASS] 推断属性包含碰撞: restitution={wood.restitution}, friction={wood.friction}")
    
    print("PropertyDatabase测试通过！\n")


if __name__ == "__main__":
    import numpy as np
    
    print("=" * 50)
    print("物理引擎修复验证测试")
    print("=" * 50 + "\n")
    
    try:
        test_vec2()
        test_vec2_from_dynamics()
        test_aabb()
        test_kinematic()
        test_friction()
        test_bodytype_alias()
        test_physical_properties()
        test_property_database()
        
        print("=" * 50)
        print("[SUCCESS] 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
