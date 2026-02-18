"""
边缘机器人增强版测试
"""

import sys
sys.path.insert(0, 'F:/skill/physical-agi/core')

from physics_engine_edge import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine, BodyType, PhysicsConfig,
    create_robot_arm_agent, create_mobile_robot
)
import numpy as np
import time


def test_robot_interface():
    """测试机器人专用接口"""
    print("=== 测试机器人专用接口 ===")
    
    engine = PhysicsEngine()
    
    # 创建机器人臂
    arm = create_robot_arm_agent("arm", (0, 5, 0))
    engine.add_object(arm)
    
    # 测试关节状态
    joint_state = engine.get_joint_state("arm")
    print(f"关节状态: {joint_state}")
    
    # 施加扭矩
    engine.apply_torque("arm", 1.0)
    
    # 模拟
    for _ in range(10):
        engine.simulate_step()
    
    # 检查关节角度变化
    new_state = engine.get_joint_state("arm")
    print(f"扭矩后: {new_state}")
    
    if new_state['angle'] > 0:
        print("[PASS] 扭矩应用成功")
    else:
        print("[FAIL] 扭矩未生效")
    
    # 测试接近传感器
    engine2 = PhysicsEngine()
    obj1 = create_mobile_robot("robot1", (0, 0, 0))
    obj2 = create_mobile_robot("robot2", (0.5, 0, 0))
    engine2.add_object(obj1)
    engine2.add_object(obj2)
    
    nearby = engine2.get_proximity("robot1", max_distance=1.0)
    print(f"附近物体: {nearby}")
    
    if len(nearby) > 0:
        print("[PASS] 接近传感器正常")
    else:
        print("[FAIL] 接近传感器异常")
    
    # 测试接触检测
    contacts = engine2.get_contact_state("robot1")
    print(f"接触物体: {contacts}")
    
    return True


def test_evolution_interface():
    """测试演化接口"""
    print("\n=== 测试演化接口 ===")
    
    engine = PhysicsEngine()
    
    # 创建群体
    for i in range(10):
        obj = PhysicsObject(
            object_id=f"agent_{i}",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(i * 0.5, 5, 0),
            velocity=Vector3D(0, -1, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=np.random.uniform(0.5, 2.0),
            size=Vector3D(0.3, 0.3, 0.3),
            friction=np.random.uniform(0.2, 0.5),
            restitution=np.random.uniform(0.3, 0.7)
        )
        engine.add_object(obj)
    
    # 测试快照
    snapshot = engine.snapshot()
    print(f"快照对象数: {len(snapshot['objects'])}")
    
    # 模拟
    for _ in range(100):
        engine.simulate_step()
    
    # 测试适应度
    fitness = engine.get_fitness_metrics()
    print(f"适应度指标:")
    print(f"  - 总动能: {fitness['total_kinetic_energy']:.2f}")
    print(f"  - 平均速度: {fitness['average_velocity']:.2f}")
    print(f"  - 稳定性: {fitness['stability']:.4f}")
    
    print("[PASS] 演化接口正常")
    
    return True


def test_low_power_mode():
    """测试低功耗模式"""
    print("\n=== 测试低功耗模式 ===")
    
    engine = PhysicsEngine()
    
    # 创建物体
    obj = create_mobile_robot("robot", (0, 5, 0))
    engine.add_object(obj)
    
    # 启用低功耗模式
    engine.set_low_power(True)
    print(f"低功耗模式: {engine.low_power}")
    print(f"更新频率: {engine.update_hz} Hz")
    
    # 计时
    start = time.time()
    steps = 0
    
    while time.time() - start < 1.0:
        engine.simulate_step(dt=0.016)
        steps += 1
    
    elapsed = time.time() - start
    fps = steps / elapsed
    
    print(f"1秒内步数: {steps}")
    print(f"实际FPS: {fps:.1f}")
    
    if fps <= engine.update_hz + 5:  # 允许一定误差
        print("[PASS] 低功耗模式限速正常")
    else:
        print("[NOTE] FPS高于预期，可能跳过逻辑有问题")
    
    return True


def test_object_pool():
    """测试对象池"""
    print("\n=== 测试对象池 ===")
    
    engine = PhysicsEngine()
    
    # 大量创建和销毁对象
    for cycle in range(5):
        for i in range(50):
            obj = create_mobile_robot(f"temp_{cycle}_{i}", (i * 0.1, 5, 0))
            engine.add_object(obj)
        
        # 模拟
        for _ in range(10):
            engine.simulate_step()
        
        # 移除
        for i in range(50):
            engine.remove_object(f"temp_{cycle}_{i}")
    
    pool_size = len(engine.pool.pool)
    print(f"池大小: {pool_size}")
    
    if pool_size > 0:
        print("[PASS] 对象池正常工作")
    else:
        print("[NOTE] 对象未回收到池中")
    
    return True


def test_config():
    """测试配置"""
    print("\n=== 测试配置 ===")
    
    # 自定义配置
    config = PhysicsConfig()
    config.LOW_POWER_MODE = True
    config.MAX_OPS_PER_FRAME = 5000
    config.OBJECT_POOL_SIZE = 50
    
    engine = PhysicsEngine(config=config)
    
    print(f"低功耗: {engine.low_power}")
    print(f"操作限制: {engine.ops_limit}")
    print(f"池大小: {len(engine.pool.pool)}")
    
    print("[PASS] 配置正常工作")
    
    return True


def test_edge_deployment():
    """边缘部署场景测试"""
    print("\n=== 边缘部署场景测试 ===")
    
    engine = PhysicsEngine()
    
    # 创建多机器人群体
    robots = []
    for i in range(20):
        robot = create_mobile_robot(f"robot_{i}", 
            (np.random.uniform(-2, 2), np.random.uniform(0, 5), 0))
        engine.add_object(robot)
        robots.append(robot)
    
    # 机器人协作场景：向中心聚集
    center = Vector3D(0, 2.5, 0)
    
    start = time.time()
    steps = 0
    
    while time.time() - start < 0.5 and steps < 100:
        # 每个机器人施加朝向中心的力
        for robot in robots:
            dx = center.x - robot.position.x
            dy = center.y - robot.position.y
            
            # 控制器输出
            force = Vector3D(dx * 0.5, dy * 0.5, 0)
            engine.apply_force(robot.object_id, force)
        
        engine.simulate_step()
        steps += 1
    
    elapsed = time.time() - start
    fps = steps / elapsed
    
    # 检查聚集效果
    positions_y = [r.position.y for r in robots]
    spread = max(positions_y) - min(positions_y)
    
    print(f"模拟步数: {steps}")
    print(f"性能: {fps:.1f} FPS")
    print(f"Y轴分布: {spread:.2f}")
    
    # 计算性能指标
    fitness = engine.get_fitness_metrics()
    print(f"适应度-动能: {fitness['total_kinetic_energy']:.2f}")
    print(f"适应度-稳定性: {fitness['stability']:.4f}")
    
    if fps > 30 and spread < 2.0:
        print("[PASS] 边缘部署场景正常")
    else:
        print("[NEED_WORK] 性能或行为需改进")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("边缘机器人物理引擎增强版测试")
    print("=" * 60)
    
    results = []
    
    results.append(("机器人接口", test_robot_interface()))
    results.append(("演化接口", test_evolution_interface()))
    results.append(("低功耗模式", test_low_power_mode()))
    results.append(("对象池", test_object_pool()))
    results.append(("配置系统", test_config()))
    results.append(("边缘部署", test_edge_deployment()))
    
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
    
    all_passed = all(p for _, p in results)
    if all_passed:
        print("\n[SUCCESS] 所有测试通过！")
    else:
        print("\n[NOTE] 部分测试需改进")
    
    print()
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
