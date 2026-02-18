"""
缺陷检测测试（稳定版）
"""

import sys
sys.path.insert(0, 'F:/skill/physical-agi/core')

from physics_engine_stable import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine
)
import numpy as np


def test_zero_division():
    """测试零质量处理"""
    print("=== 测试零质量处理 ===")
    
    engine = PhysicsEngine()
    
    obj_zero_mass = PhysicsObject(
        object_id="zero_mass",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=0,
        size=Vector3D(1, 1, 1)
    )
    engine.add_object(obj_zero_mass)
    
    # 测试apply_force
    result = engine.apply_force("zero_mass", Vector3D(1, 0, 0))
    print(f"零质量apply_force: {'安全处理' if result == False else '未处理'}")
    
    # 测试碰撞
    obj1 = PhysicsObject(
        object_id="obj1",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 2, 0),
        velocity=Vector3D(0, -5, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1)
    )
    obj2 = PhysicsObject(
        object_id="obj2",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=0,  # 零质量
        size=Vector3D(1, 1, 1)
    )
    
    engine2 = PhysicsEngine()
    engine2.add_object(obj1)
    engine2.add_object(obj2)
    
    try:
        engine2.simulate_step(dt=0.016)
        print("零质量碰撞: 安全处理")
    except Exception as e:
        print(f"零质量碰撞错误: {e}")
    
    print()


def test_ground_collision():
    """测试地面碰撞和摩擦"""
    print("=== 测试地面碰撞和摩擦 ===")
    
    engine = PhysicsEngine(gravity=Vector3D(0, -9.81, 0))
    
    obj = PhysicsObject(
        object_id="box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 5, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1),
        friction=0.5,
        restitution=0.1
    )
    
    engine.add_object(obj)
    
    print(f"初始Y: {obj.position.y:.4f}")
    
    # 模拟直到静止
    for step in range(100):
        engine.simulate_step(dt=0.016)
        if step % 20 == 0:
            print(f"  Step {step}: Y={obj.position.y:.4f}, VY={obj.velocity.y:.4f}, VX={obj.velocity.x:.4f}")
        
        # 检查是否在地面
        if obj.position.y < 0.55 and abs(obj.velocity.y) < 0.1:
            print(f"物体在地面静止，Step={step}")
            break
    
    print(f"最终Y: {obj.position.y:.4f}")
    print(f"最终速度: ({obj.velocity.x:.4f}, {obj.velocity.y:.4f})")
    
    # 验证
    if obj.position.y > 0.4:
        print("[PASS] 物体在地面上方")
    else:
        print("[FAIL] 物体穿模")
    
    print()


def test_sliding():
    """测试水平滑动"""
    print("=== 测试水平滑动 ===")
    
    engine = PhysicsEngine(gravity=Vector3D(0, -9.81, 0))
    
    obj = PhysicsObject(
        object_id="sliding_box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0.55, 0),
        velocity=Vector3D(5, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1),
        friction=0.5,
        restitution=0.0
    )
    
    engine.add_object(obj)
    
    init_speed = np.sqrt(obj.velocity.x**2)
    print(f"初始水平速度: {init_speed:.4f}")
    
    # 模拟
    for step in range(100):
        engine.simulate_step(dt=0.016)
        if step % 25 == 0:
            speed = np.sqrt(obj.velocity.x**2 + obj.velocity.z**2)
            print(f"  Step {step}: 速度={speed:.4f}, Y={obj.position.y:.4f}")
    
    final_speed = np.sqrt(obj.velocity.x**2 + obj.velocity.z**2)
    print(f"最终速度: {final_speed:.4f}")
    
    if final_speed < init_speed * 0.5:
        print("[PASS] 摩擦减速有效")
    else:
        print("[NEED_WORK] 摩擦可能不足")
    
    print()


def test_kinematic():
    """测试运动学物体"""
    print("=== 测试运动学物体 ===")
    
    engine = PhysicsEngine()
    
    platform = PhysicsObject(
        object_id="platform",
        object_type=PhysicsObjectType.KINEMATIC,
        position=Vector3D(0, 5, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=100,
        size=Vector3D(2, 0.5, 1)
    )
    
    box = PhysicsObject(
        object_id="box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 6, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5)
    )
    
    engine.add_object(platform)
    engine.add_object(box)
    
    # 手动移动平台
    platform.position = Vector3D(2, 5, 0)
    
    print(f"平台移动后X: {platform.position.x}")
    print(f"箱子位置: ({box.position.x}, {box.position.y})")
    print("[NOTE] 箱子未跟随平台移动 - 需要额外实现")
    
    print()


def test_bounce():
    """测试弹跳"""
    print("=== 测试弹跳 ===")
    
    engine = PhysicsEngine(gravity=Vector3D(0, 0, 0))  # 无重力
    
    obj = PhysicsObject(
        object_id="ball",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 2, 0),
        velocity=Vector3D(1, 0, 0),  # 水平运动
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5),
        restitution=0.8,
        friction=0.1
    )
    
    engine.add_object(obj)
    
    # 添加地面
    ground = PhysicsObject(
        object_id="ground",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=float('inf'),
        size=Vector3D(10, 1, 10),
        restitution=0.8
    )
    engine.add_object(ground)
    
    init_energy = 0.5 * 1 * (1**2 + 0**2) + 1 * 9.81 * 2
    print(f"初始能量: {init_energy:.4f}")
    
    for i in range(5):
        engine.simulate_step(dt=0.016)
        ke = 0.5 * (obj.velocity.x**2 + obj.velocity.y**2)
        pe = 1 * 9.81 * max(obj.position.y - 0.5, 0)
        print(f"  弹跳{i+1}: KE={ke:.4f}, PE={pe:.4f}")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("物理引擎缺陷检测（稳定版）")
    print("=" * 50 + "\n")
    
    test_zero_division()
    test_ground_collision()
    test_sliding()
    test_kinematic()
    test_bounce()
    
    print("=" * 50)
    print("检测完成")
    print("=" * 50)
