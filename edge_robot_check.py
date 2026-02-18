"""
边缘演化智能群 - 具身机器人物理引擎缺陷检测

检查维度:
1. 实时性能（计算延迟）
2. 多智能体碰撞（群体行为）
3. 演化算法集成（遗传、变异）
4. 硬件约束（内存、计算）
5. 长时间运行稳定性
6. 传感器/执行器接口
"""

import sys
sys.path.insert(0, 'F:/skill/physical-agi/core')

from physics_engine_complete import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine, BodyType
)
import numpy as np
import time


def test_realtime_performance():
    """测试实时性能"""
    print("=== 测试实时性能 ===")
    
    engine = PhysicsEngine()
    
    # 创建多个物体
    for i in range(50):
        obj = PhysicsObject(
            object_id=f"agent_{i}",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(np.random.uniform(-5, 5), np.random.uniform(0, 10), 0),
            velocity=Vector3D(np.random.uniform(-1, 1), np.random.uniform(-1, 1), 0),
            acceleration=Vector3D(0, 0, 0),
            mass=1,
            size=Vector3D(0.5, 0.5, 0.5),
            friction=0.3,
            restitution=0.5
        )
        engine.add_object(obj)
    
    # 计时模拟
    start = time.time()
    steps = 0
    max_time = 1.0  # 1秒内尽可能多步
    
    while time.time() - start < max_time:
        engine.simulate_step(dt=0.016)
        steps += 1
    
    elapsed = time.time() - start
    fps = steps / elapsed
    
    print(f"模拟步数: {steps}")
    print(f"耗时: {elapsed:.4f}s")
    print(f"性能: {fps:.1f} FPS (目标: 60+)")
    
    if fps < 30:
        print("[NEED_WORK] 性能不足，边缘设备可能无法实时运行")
    else:
        print("[PASS] 性能可接受")
    
    return fps


def test_multi_agent_collision():
    """测试多智能体碰撞"""
    print("\n=== 测试多智能体碰撞 ===")
    
    engine = PhysicsEngine()
    agents = []
    
    # 创建多个智能体
    for i in range(10):
        agent = PhysicsObject(
            object_id=f"agent_{i}",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(i * 0.6, 5 + i * 0.1, 0),
            velocity=Vector3D(0, -2, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=1,
            size=Vector3D(0.5, 0.5, 0.5),
            friction=0.3,
            restitution=0.5
        )
        agents.append(agent)
        engine.add_object(agent)
    
    # 模拟碰撞
    collision_counts = []
    for step in range(50):
        engine.simulate_step(dt=0.016)
        collision_counts.append(engine.get_physics_state()['collision_count'])
    
    avg_collisions = np.mean(collision_counts)
    print(f"平均碰撞次数/帧: {avg_collisions:.1f}")
    print(f"最大碰撞次数/帧: {max(collision_counts)}")
    
    # 检查是否有穿模
    for agent in agents:
        if agent.position.y < 0:
            print(f"[DETECTED] 智能体穿模: {agent.object_id}")
    
    if max(collision_counts) > 20:
        print("[NOTE] 高碰撞场景，需优化碰撞检测算法")
    else:
        print("[PASS] 碰撞处理正常")
    
    return collision_counts


def test_evolution_compatibility():
    """测试演化算法兼容性"""
    print("\n=== 测试演化算法兼容性 ===")
    
    # 检查是否可以序列化/反序列化
    engine = PhysicsEngine()
    
    # 创建智能体
    for i in range(5):
        obj = PhysicsObject(
            object_id=f"evo_agent_{i}",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(i, 5, 0),
            velocity=Vector3D(np.random.uniform(-1, 1), 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=np.random.uniform(0.5, 2.0),  # 可演化参数
            size=Vector3D(0.5, 0.5, 0.5),
            friction=np.random.uniform(0.1, 0.5),  # 可演化参数
            restitution=np.random.uniform(0.3, 0.8)  # 可演化参数
        )
        engine.add_object(obj)
    
    # 测试参数变异
    def mutate_physics_params(params: dict, mutation_rate: float = 0.1) -> dict:
        """物理参数变异"""
        mutated = params.copy()
        for key in ['mass', 'friction', 'restitution']:
            if np.random.random() < mutation_rate:
                mutated[key] *= np.random.uniform(0.8, 1.2)
        return mutated
    
    # 验证变异
    original = {'mass': 1.0, 'friction': 0.3, 'restitution': 0.5}
    mutated = mutate_physics_params(original, 1.0)
    
    print(f"原始参数: {original}")
    print(f"变异参数: {mutated}")
    
    # 检查是否所有参数都在有效范围
    valid = all(0 < mutated[k] < 3 for k in ['mass', 'friction', 'restitution'])
    if valid:
        print("[PASS] 演化参数在有效范围")
    else:
        print("[NEED_WORK] 需添加参数约束")
    
    # 测试状态导出（用于演化评估）
    def export_agent_state(obj: PhysicsObject) -> dict:
        return {
            'position': (obj.position.x, obj.position.y, obj.position.z),
            'velocity': (obj.velocity.x, obj.velocity.y, obj.velocity.z),
            'mass': obj.mass,
            'friction': obj.friction,
            'restitution': obj.restitution
        }
    
    states = [export_agent_state(obj) for obj in engine.objects.values()]
    print(f"导出{len(states)}个智能体状态")
    
    return True


def test_memory_usage():
    """测试内存使用"""
    print("\n=== 测试内存使用 ===")
    
    engines = []
    
    # 创建多个物理引擎实例
    for i in range(10):
        engine = PhysicsEngine()
        # 添加物体
        for j in range(20):
            obj = PhysicsObject(
                object_id=f"obj_{j}",
                object_type=PhysicsObjectType.DYNAMIC,
                position=Vector3D(j, j, 0),
                velocity=Vector3D(0, 0, 0),
                acceleration=Vector3D(0, 0, 0),
                mass=1,
                size=Vector3D(0.5, 0.5, 0.5)
            )
            engine.add_object(obj)
        engines.append(engine)
    
    print(f"创建{len(engines)}个物理引擎")
    print(f"每个引擎包含20个物体")
    
    # 检查对象数量
    total_objects = sum(len(e.objects) for e in engines)
    print(f"总对象数: {total_objects}")
    
    if total_objects > 1000:
        print("[NEED_WORK] 大规模场景可能内存不足")
    else:
        print("[PASS] 内存使用正常")
    
    return total_objects


def test_sensor_actuator_interface():
    """测试传感器/执行器接口"""
    print("\n=== 测试传感器/执行器接口 ===")
    
    engine = PhysicsEngine()
    
    # 创建智能体
    agent = PhysicsObject(
        object_id="robot",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 5, 0),
        velocity=Vector3D(0, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5)
    )
    engine.add_object(agent)
    
    # 传感器接口：读取状态
    def read_sensor(object_id: str) -> dict:
        """模拟传感器读取"""
        if object_id not in engine.objects:
            return None
        obj = engine.objects[object_id]
        return {
            'position': (obj.position.x, obj.position.y, obj.position.z),
            'velocity': (obj.velocity.x, obj.velocity.y, obj.velocity.z),
            'acceleration': (obj.acceleration.x, obj.acceleration.y, obj.acceleration.z),
            'contact': False  # 需要扩展碰撞检测
        }
    
    # 执行器接口：施加力
    def apply_actuator_force(object_id: str, force: tuple, duration: float):
        """模拟执行器施加力"""
        vec_force = Vector3D(force[0], force[1], force[2])
        engine.apply_force(object_id, vec_force)
    
    # 测试接口
    sensor_data = read_sensor("robot")
    print(f"传感器数据: {sensor_data}")
    
    # 施加控制力
    apply_actuator_force("robot", (1, 0, 0), 0.1)
    engine.simulate_step()
    
    new_sensor = read_sensor("robot")
    print(f"控制后: 速度={new_sensor['velocity']}")
    
    if new_sensor['velocity'][0] > 0:
        print("[PASS] 执行器接口正常")
    else:
        print("[NEED_WORK] 执行器可能需要改进")
    
    # 检查缺少的接口
    missing = []
    if not hasattr(engine, 'get_joint_state'):
        missing.append('get_joint_state')
    if not hasattr(engine, 'apply_torque'):
        missing.append('apply_torque')
    if not hasattr(engine, 'get_proximity'):
        missing.append('get_proximity')
    if not hasattr(engine, 'set_joint_limit'):
        missing.append('set_joint_limit')
    
    if missing:
        print(f"[NOTE] 缺少机器人专用接口: {missing}")
    
    return True


def test_long_term_stability():
    """测试长时间运行稳定性"""
    print("\n=== 测试长时间运行稳定性 ===")
    
    engine = PhysicsEngine()
    
    # 创建不稳定场景
    obj = PhysicsObject(
        object_id="unstable",
        object_type=PhysicsObjectType.DYNAMIC,
        position=Vector3D(0, 10, 0),
        velocity=Vector3D(100, -100, 0),  # 极端速度
        acceleration=Vector3D(0, 0, 0),
        mass=1,
        size=Vector3D(0.5, 0.5, 0.5),
        friction=0.3,
        restitution=0.99  # 高弹性
    )
    engine.add_object(obj)
    
    # 长时间模拟
    errors = 0
    nan_count = 0
    
    for step in range(1000):
        try:
            engine.simulate_step(dt=0.016)
            
            # 检查状态
            if not np.isfinite(obj.position.x):
                nan_count += 1
        except Exception as e:
            errors += 1
    
    print(f"模拟1000步")
    print(f"错误次数: {errors}")
    print(f"NaN次数: {nan_count}")
    print(f"最终位置: ({obj.position.x:.2f}, {obj.position.y:.2f})")
    print(f"最终速度: ({obj.velocity.x:.2f}, {obj.velocity.y:.2f})")
    
    if errors > 0 or nan_count > 0:
        print("[NEED_WORK] 长时间运行不稳定")
    else:
        print("[PASS] 稳定性可接受")
    
    return errors == 0 and nan_count == 0


def test_edge_constraints():
    """测试边缘计算约束"""
    print("\n=== 测试边缘计算约束 ===")
    
    constraints = []
    
    # 1. 检查是否支持定点运算
    # 当前使用numpy浮点，边缘设备可能需要定点
    constraints.append(("定点运算支持", False))
    
    # 2. 检查是否有计算预算控制
    # 当前无限步模拟
    constraints.append(("计算预算控制", False))
    
    # 3. 检查是否有低功耗模式
    # 当前无此功能
    constraints.append(("低功耗模式", False))
    
    # 4. 检查内存池
    # 当前动态分配
    constraints.append(("内存池管理", False))
    
    # 5. 检查并行化
    # 当前单线程
    constraints.append(("SIMD/SIMT并行", False))
    
    print("边缘约束支持检查:")
    for name, supported in constraints:
        status = "[SUPPORTED]" if supported else "[NOT_SUPPORTED]"
        print(f"  {status} {name}")
    
    unsupported = [name for name, sup in constraints if not sup]
    if unsupported:
        print(f"\n[NOTE] 边缘部署需改进: {unsupported}")
    
    return constraints


def test_emergent_behavior():
    """测试涌现行为"""
    print("\n=== 测试涌现行为 ===")
    
    engine = PhysicsEngine()
    agents = []
    
    # 创建群体
    for i in range(20):
        # 随机初始化
        agent = PhysicsObject(
            object_id=f"agent_{i}",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(
                np.random.uniform(-2, 2),
                np.random.uniform(5, 8),
                0
            ),
            velocity=Vector3D(
                np.random.uniform(-0.5, 0.5),
                np.random.uniform(-0.5, 0.5),
                0
            ),
            acceleration=Vector3D(0, 0, 0),
            mass=1,
            size=Vector3D(0.3, 0.3, 0.3),
            friction=0.2,
            restitution=0.3  # 低弹性，减少聚集
        )
        agents.append(agent)
        engine.add_object(agent)
    
    # 模拟群体行为
    positions_x = []
    
    for step in range(100):
        engine.simulate_step(dt=0.016)
        
        if step % 20 == 0:
            xs = [obj.position.x for obj in agents]
            positions_x.append(xs)
            spread = max(xs) - min(xs)
            print(f"  Step {step}: 分布范围={spread:.2f}")
    
    # 分析涌现行为
    final_x = positions_x[-1] if positions_x else []
    if final_x:
        spread = max(final_x) - min(final_x)
        
        if spread < 1.0:
            print("[NOTE] 群体可能形成紧密聚集")
        elif spread > 5.0:
            print("[NOTE] 群体趋于分散")
        else:
            print("[PASS] 群体行为正常")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("边缘演化智能群 - 具身机器人物理引擎缺陷检测")
    print("=" * 60)
    
    results = []
    
    results.append(("实时性能", test_realtime_performance()))
    results.append(("多智能体碰撞", test_multi_agent_collision()))
    results.append(("演化兼容性", test_evolution_compatibility()))
    results.append(("内存使用", test_memory_usage()))
    results.append(("传感器接口", test_sensor_actuator_interface()))
    results.append(("长时间稳定", test_long_term_stability()))
    results.append(("边缘约束", test_edge_constraints()))
    results.append(("涌现行为", test_emergent_behavior()))
    
    print("\n" + "=" * 60)
    print("缺陷检测汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[NEED_WORK]"
        print(f"  {status} {name}")
    
    # 关键改进建议
    print("\n" + "=" * 60)
    print("边缘部署关键改进建议")
    print("=" * 60)
    
    suggestions = [
        "1. 添加定点运算支持（替代float64）",
        "2. 实现计算预算控制（每帧最大操作数）",
        "3. 添加低功耗模式（降低更新频率）",
        "4. 实现对象池（减少内存分配）",
        "5. 添加SIMD并行支持（批量物体更新）",
        "6. 完善机器人专用接口（关节、扭矩、传感器）",
        "7. 添加状态快照（用于演化评估）",
        "8. 实现自适应时间步长（负载均衡）"
    ]
    
    for s in suggestions:
        print(s)
    
    print()


if __name__ == "__main__":
    run_all_tests()
