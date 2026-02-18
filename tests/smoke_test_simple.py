"""
硬件冒烟测试脚本 - 简化版
"""

import sys
import numpy as np
sys.path.insert(0, 'core')
sys.path.insert(0, '')

from physics_engine_edge import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType,
    PhysicsEngine, PhysicsConfig,
    create_mobile_robot, create_robot_arm_agent
)

# 导入simulator_v2中的类
from simulator_v2 import NCANetwork, NCAParams, EmbodiedAgent

print("=" * 60)
print("物理引擎冒烟测试")
print("=" * 60)

# 1. 测试创建
print("\n[1/5] 测试创建...")
try:
    config = PhysicsConfig()
    engine = PhysicsEngine(config=config)
    print("  [PASS] 创建PhysicsEngine")
except Exception as e:
    print(f"  [FAIL] 创建PhysicsEngine: {e}")

# 2. 测试添加对象
print("\n[2/5] 测试添加对象...")
try:
    obj = create_mobile_robot("test", (0, 5, 0))
    engine.add_object(obj)
    assert "test" in engine.objects
    print("  [PASS] 添加对象")
except Exception as e:
    print(f"  [FAIL] 添加对象: {e}")

# 3. 测试施力
print("\n[3/5] 测试施力...")
try:
    force = Vector3D(10, 0, 0)
    result = engine.apply_force("test", force)
    assert result is True
    print("  [PASS] 施力")
except Exception as e:
    print(f"  [FAIL] 施力: {e}")

# 4. 测试模拟
print("\n[4/5] 测试模拟...")
try:
    for i in range(50):
        engine.simulate_step()
    print("  [PASS] 50步模拟成功")
except Exception as e:
    print(f"  [FAIL] 模拟: {e}")

# 5. 测试NCA
print("\n[5/5] 测试NCA...")
try:
    net = NCANetwork()
    x = net.forward(np.random.randn(6))
    assert x.shape == (2,)
    print("  [PASS] NCA前向传播")
except Exception as e:
    print(f"  [FAIL] NCA: {e}")

print("\n" + "=" * 60)
print("冒烟测试完成")
print("=" * 60)
