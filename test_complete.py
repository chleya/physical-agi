"""
完整修复验证测试
"""

import sys
sys.path.insert(0, 'F:/skill/physical-agi/core')

from physics_engine_complete import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine, BodyType
)
import numpy as np


def test_nan_safety():
    """测试NaN安全"""
    print("=== 测试NaN安全 ===")
    
    engine = PhysicsEngine()
    
    # 测试正常碰撞
    obj1 = PhysicsObject(
        object_id="ball",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 2, 0),
        velocity=Vector3D(1, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5),
        restitution=0.8,
        friction=0.1
    )
    
    obj2 = PhysicsObject(
        object_id="ground",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=float('inf'),
        size=Vector3D(10, 1, 10),
        restitution=0.8
    )
    
    engine.add_object(obj1)
    engine.add_object(obj2)
    
    init_energy = 0.5 * (1**2 + 0**2) + 1 * 9.81 * (2 - 0.5)
    print(f"初始能量: {init_energy:.4f}")
    
    nan_detected = False
    for i in range(10):
        engine.simulate_step(dt=0.016)
        
        # 检查NaN
        for attr in ['x', 'y', 'z']:
            if not np.isfinite(getattr(obj1.position, attr)):
                nan_detected = True
                break
            if not np.isfinite(getattr(obj1.velocity, attr)):
                nan_detected = True
                break
        
        if nan_detected:
            print(f"[FAIL] 弹跳{i+1}出现NaN")
            break
        
        ke = 0.5 * (obj1.velocity.x**2 + obj1.velocity.y**2 + obj1.velocity.z**2)
        pe = 1 * 9.81 * max(obj1.position.y - 0.5, 0)
        total = ke + pe
        print(f"  弹跳{i+1}: KE={ke:.4f}, PE={pe:.4f}, 总={total:.4f}")
    
    if not nan_detected:
        print("[PASS] 无NaN问题")
    else:
        print("[FAIL] 检测到NaN")
    
    print()
    return not nan_detected


def test_kinematic_constraint():
    """测试KINEMATIC约束"""
    print("=== 测试KINEMATIC移动约束 ===")
    
    engine = PhysicsEngine()
    
    # 创建平台（KINEMATIC）
    platform = PhysicsObject(
        object_id="platform",
        object_type=PhysicsObjectType.KINEMATIC,
        position=Vector3D(0, 5, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=100,
        size=Vector3D(2, 0.5, 1)
    )
    
    # 创建箱子（放在平台上）
    box = PhysicsObject(
        object_id="box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 5.75, 0),  # 在平台上
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5)
    )
    
    engine.add_object(platform)
    engine.add_object(box)
    
    # 设置父子约束
    engine.set_parent("box", "platform")
    
    print(f"初始: 平台Y={platform.position.y:.2f}, 箱子Y={box.position.y:.2f}")
    
    # 移动平台
    platform.position = Vector3D(2, 5, 0)
    engine.simulate_step(dt=0.016)
    
    print(f"移动后: 平台X={platform.position.x:.2f}, 箱子Y={box.position.y:.2f}")
    
    # 箱子应该还在平台上
    box_on_platform = box.position.y >= platform.position.y + platform.size.y/2 - box.size.y/2
    if box_on_platform:
        print("[PASS] 箱子跟随平台")
    else:
        print("[NEED_WORK] 箱子未跟随")
    
    print()
    return box_on_platform


def test_zero_mass():
    """测试零质量（预期行为：自动修正为最小质量）"""
    print("=== 测试零质量处理 ===")
    
    engine = PhysicsEngine()
    
    obj = PhysicsObject(
        object_id="zero_mass",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 0, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=0,  # 初始零质量
        size=Vector3D(1, 1, 1)
    )
    engine.add_object(obj)
    
    # 检查质量是否被自动修正
    actual_mass = obj.mass
    print(f"初始质量: 0, 实际质量: {actual_mass}")
    
    if actual_mass > 0:
        print("[PASS] 零质量自动修正为最小质量")
    else:
        print("[FAIL] 质量未修正")
    
    # 测试apply_force（现在应该成功，因为质量已修正）
    result = engine.apply_force("zero_mass", Vector3D(1, 0, 0))
    if result:
        print("[PASS] 修正后apply_force成功")
    else:
        print("[FAIL] 修正后apply_force应成功")
    
    # 模拟不应崩溃
    try:
        obj2 = PhysicsObject(
            object_id="ground",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(0, 0, 0),
            velocity=Vector3D(0, 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=float('inf'),
            size=Vector3D(10, 1, 10)
        )
        engine.add_object(obj2)
        engine.simulate_step(dt=0.016)
        print("[PASS] 零质量碰撞安全处理")
        return True
    except Exception as e:
        print(f"[FAIL] 零质量碰撞错误: {e}")
        return False


def test_ground_friction():
    """测试地面摩擦"""
    print("=== 测试地面摩擦 ===")
    
    engine = PhysicsEngine(gravity=Vector3D(0, -9.81, 0))
    
    obj = PhysicsObject(
        object_id="box",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 1, 0),
        velocity=Vector3D(5, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(1, 1, 1),
        friction=0.5,
        restitution=0.1
    )
    
    engine.add_object(obj)
    
    init_speed = np.sqrt(obj.velocity.x**2)
    print(f"初始速度: {init_speed:.4f}")
    
    for step in range(100):
        engine.simulate_step(dt=0.016)
        if step % 25 == 0:
            speed = np.sqrt(obj.velocity.x**2)
            print(f"  Step {step}: 速度={speed:.4f}, Y={obj.position.y:.4f}")
    
    final_speed = np.sqrt(obj.velocity.x**2)
    print(f"最终速度: {final_speed:.4f}")
    
    if final_speed < init_speed * 0.1:
        print("[PASS] 摩擦有效减速")
        return True
    else:
        print("[NEED_WORK] 摩擦减速不足")
        return False


def test_all():
    """所有测试"""
    print("=" * 50)
    print("物理引擎完整修复验证")
    print("=" * 50 + "\n")
    
    results = []
    
    results.append(("NaN安全", test_nan_safety()))
    results.append(("KINEMATIC约束", test_kinematic_constraint()))
    results.append(("零质量处理", test_zero_mass()))
    results.append(("地面摩擦", test_ground_friction()))
    
    print("=" * 50)
    print("测试结果汇总:")
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
    
    all_passed = all(p for _, p in results)
    if all_passed:
        print("\n[SUCCESS] 所有测试通过！")
    else:
        print("\n[NEED_WORK] 部分测试需要改进")
    
    print("=" * 50)
    return all_passed


if __name__ == "__main__":
    test_all()
