"""
硬件冒烟测试脚本
用于验证物理引擎在硬件环境下的基本功能

使用方法:
    cd F:\skill\physical-agi
    python tests/hardware_smoke_test.py

或者使用pytest:
    pytest tests/hardware_smoke_test.py -v
"""

import sys
import os
import time
import argparse
from typing import Dict, List, Tuple

# 添加被测模块
core_path = os.path.dirname(os.path.dirname(__file__))
if core_path not in sys.path:
    sys.path.insert(0, core_path)
if '' not in sys.path:
    sys.path.insert(0, '')

from physics_engine_edge import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType,
    PhysicsEngine, PhysicsConfig,
    create_mobile_robot, create_robot_arm_agent
)

# 智能体和NCA在simulator_v2中
import simulator_v2 as sim
NCANetwork = sim.NCANetwork
NCAParams = sim.NCAParams
EmbodiedAgent = sim.EmbodiedAgent
AgentConfig = sim.AgentConfig


# 测试结果收集
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[Tuple[str, str]] = []
        self.start_time = time.time()
    
    def add_pass(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")
    
    def add_fail(self, name: str, error: str):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  [FAIL] {name}: {error}")
    
    def summary(self) -> Dict:
        elapsed = time.time() - self.start_time
        return {
            'passed': self.passed,
            'failed': self.failed,
            'errors': self.errors,
            'elapsed': elapsed,
            'status': 'PASS' if self.failed == 0 else 'FAIL'
        }


def print_header(title: str):
    """打印测试标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def smoke_test_physics_engine() -> TestResult:
    """物理引擎冒烟测试"""
    print_header("物理引擎冒烟测试")
    
    result = TestResult()
    
    # 1. 测试创建
    print("\n[1/8] 测试创建...")
    try:
        config = PhysicsConfig()
        engine = PhysicsEngine(config=config)
        result.add_pass("创建PhysicsEngine")
    except Exception as e:
        result.add_fail("创建PhysicsEngine", str(e))
    
    # 2. 测试添加对象
    print("\n[2/8] 测试添加对象...")
    try:
        obj = create_mobile_robot("smoke_test", (0, 5, 0))
        engine.add_object(obj)
        assert "smoke_test" in engine.objects
        result.add_pass("添加对象")
    except Exception as e:
        result.add_fail("添加对象", str(e))
    
    # 3. 测试施力
    print("\n[3/8] 测试施力...")
    try:
        force = Vector3D(10, 0, 0)
        result_apply = engine.apply_force("smoke_test", force)
        assert result_apply is True
        result.add_pass("施力")
    except Exception as e:
        result.add_fail("施力", str(e))
    
    # 4. 测试单步模拟
    print("\n[4/8] 测试单步模拟...")
    try:
        result_sim = engine.simulate_step(dt=0.016)
        assert result_sim is not None
        assert "skipped" in result_sim
        result.add_pass("单步模拟")
    except Exception as e:
        result.add_fail("单步模拟", str(e))
    
    # 5. 测试多步模拟稳定性
    print("\n[5/8] 测试多步模拟(100步)...")
    try:
        stable = True
        for i in range(100):
            result_sim = engine.simulate_step(dt=0.016)
            if result_sim is None:
                stable = False
                break
            # 检查是否产生NaN
            obj = engine.objects.get("smoke_test")
            if obj:
                if not all(np.isfinite([obj.position.x, obj.position.y, obj.position.z])):
                    stable = False
                    break
        
        if stable:
            result.add_pass("多步模拟")
        else:
            result.add_fail("多步模拟", "不稳定或NaN")
    except Exception as e:
        result.add_fail("多步模拟", str(e))
    
    # 6. 测试碰撞检测
    print("\n[6/8] 测试碰撞检测...")
    try:
        # 添加地面
        ground = create_mobile_robot("ground", (0, 0, 0))
        ground.position = Vector3D(0, -0.5, 0)
        ground.mass = float('inf')
        engine.add_object(ground)
        
        # 模拟直到碰撞
        collided = False
        for i in range(50):
            result_sim = engine.simulate_step()
            obj = engine.objects.get("smoke_test")
            if obj and obj.position.y < 0.6:  # 地面上方
                collided = True
                break
        
        if collided:
            result.add_pass("碰撞检测")
        else:
            result.add_fail("碰撞检测", "未检测到碰撞")
    except Exception as e:
        result.add_fail("碰撞检测", str(e))
    
    # 7. 测试移除对象
    print("\n[7/8] 测试移除对象...")
    try:
        result_remove = engine.remove_object("smoke_test")
        assert result_remove is True
        assert "smoke_test" not in engine.objects
        result.add_pass("移除对象")
    except Exception as e:
        result.add_fail("移除对象", str(e))
    
    # 8. 测试配置
    print("\n[8/8] 测试配置...")
    try:
        config = PhysicsConfig()
        config.LOW_POWER_MODE = True
        engine_lp = PhysicsEngine(config=config)
        assert engine_lp.low_power is True
        result.add_pass("配置")
    except Exception as e:
        result.add_fail("配置", str(e))
    
    return result


def smoke_test_nca_network() -> TestResult:
    """NCA网络冒烟测试"""
    print_header("NCA网络冒烟测试")
    
    result = TestResult()
    
    # 1. 测试创建
    print("\n[1/4] 测试创建...")
    try:
        params = NCAParams()
        net = NCANetwork(params)
        result.add_pass("创建NCANetwork")
    except Exception as e:
        result.add_fail("创建NCANetwork", str(e))
    
    # 2. 测试前向传播
    print("\n[2/4] 测试前向传播...")
    try:
        x = np.random.randn(6)
        y = net.forward(x)
        assert y.shape == (2,)
        assert all(-1 <= v <= 1 for v in y)
        result.add_pass("前向传播")
    except Exception as e:
        result.add_fail("前向传播", str(e))
    
    # 3. 测试变异
    print("\n[3/4] 测试变异...")
    try:
        net2 = net.mutate(rate=0.01)
        assert net2.w1.shape == net.w1.shape
        result.add_pass("变异")
    except Exception as e:
        result.add_fail("变异", str(e))
    
    # 4. 测试输出边界
    print("\n[4/4] 测试输出边界...")
    try:
        # 多次前向传播，检查输出边界
        all_bounded = True
        for _ in range(100):
            x = np.random.randn(6) * 10  # 大输入
            y = net.forward(x)
            if not all(-1 <= v <= 1 for v in y):
                all_bounded = False
                break
        
        if all_bounded:
            result.add_pass("输出边界")
        else:
            result.add_fail("输出边界", "输出超出[-1,1]范围")
    except Exception as e:
        result.add_fail("输出边界", str(e))
    
    return result


def smoke_test_agent() -> TestResult:
    """智能体冒烟测试"""
    print_header("智能体冒烟测试")
    
    result = TestResult()
    
    # 1. 测试创建
    print("\n[1/5] 测试创建...")
    try:
        config = AgentConfig(name="smoke_agent")
        engine = PhysicsEngine()
        agent = EmbodiedAgent("smoke_agent", engine, (0, 5))
        result.add_pass("创建智能体")
    except Exception as e:
        result.add_fail("创建智能体", str(e))
    
    # 2. 测试感知
    print("\n[2/5] 测试感知...")
    try:
        perception = agent.perceive({})
        assert perception.shape == (6,)
        result.add_pass("感知")
    except Exception as e:
        result.add_fail("感知", str(e))
    
    # 3. 测试决策
    print("\n[3/5] 测试决策...")
    try:
        action = agent.decide(np.random.randn(6))
        assert action.shape == (2,)
        result.add_pass("决策")
    except Exception as e:
        result.add_fail("决策", str(e))
    
    # 4. 测试动作
    print("\n[4/5] 测试动作...")
    try:
        action = np.array([1.0, 0.0])
        agent.act(action, {})
        assert agent.age == 1
        assert len(agent.history) == 1
        result.add_pass("动作")
    except Exception as e:
        result.add_fail("动作", str(e))
    
    # 5. 测试适应度计算
    print("\n[5/5] 测试适应度计算...")
    try:
        from physics_engine_edge import TaskType
        fitness = agent.calculate_fitness(TaskType.EXPLORE)
        assert isinstance(fitness, (int, float))
        result.add_pass("适应度")
    except Exception as e:
        result.add_fail("适应度", str(e))
    
    return result


def performance_benchmark() -> Dict:
    """性能基准测试"""
    print_header("性能基准测试")
    
    results = {}
    
    # 创建测试引擎
    config = PhysicsConfig()
    config.LOW_POWER_MODE = False
    engine = PhysicsEngine(config=config)
    
    # 创建多个物体
    num_objects = 20
    for i in range(num_objects):
        obj = create_mobile_robot(f"bench_{i}", 
            (np.random.uniform(-5, 5), np.random.uniform(0, 10), 0))
        engine.add_object(obj)
    
    # 基准测试
    print(f"\n测试 {num_objects} 个物体的模拟性能...")
    
    start = time.time()
    steps = 0
    max_time = 1.0  # 最多1秒
    
    while time.time() - start < max_time:
        engine.simulate_step()
        steps += 1
    
    elapsed = time.time() - start
    fps = steps / elapsed
    
    results['objects'] = num_objects
    results['steps'] = steps
    results['elapsed'] = elapsed
    results['fps'] = fps
    
    print(f"  模拟步数: {steps}")
    print(f"  耗时: {elapsed:.3f}s")
    print(f"  性能: {fps:.1f} FPS")
    
    return results


def run_all_tests(verbose: bool = True) -> Dict:
    """运行所有冒烟测试"""
    print("\n" + "=" * 60)
    print("  边缘演化智能群 - 硬件冒烟测试")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print('=' * 60)
    
    all_results = {}
    
    # 运行测试
    all_results['physics'] = smoke_test_physics_engine()
    all_results['nca'] = smoke_test_nca_network()
    all_results['agent'] = smoke_test_agent()
    
    # 性能基准
    all_results['performance'] = performance_benchmark()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print('=' * 60)
    
    total_passed = 0
    total_failed = 0
    
    for name, result in all_results.items():
        if isinstance(result, TestResult):
            print(f"\n{name.upper()}:")
            print(f"  通过: {result.passed}")
            print(f"  失败: {result.failed}")
            total_passed += result.passed
            total_failed += result.failed
            
            if result.errors:
                print(f"\n  错误详情:")
                for name_err, error in result.errors:
                    print(f"    - {name_err}: {error}")
        else:
            print(f"\n{name.upper()}:")
            for k, v in result.items():
                print(f"  {k}: {v}")
    
    print(f"\n{'=' * 60}")
    print(f"  总计: 通过 {total_passed}, 失败 {total_failed}")
    
    overall = 'PASS' if total_failed == 0 else 'FAIL'
    print(f"  总体状态: {overall}")
    print('=' * 60)
    
    all_results['total'] = {
        'passed': total_passed,
        'failed': total_failed,
        'status': overall
    }
    
    return all_results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="硬件冒烟测试")
    parser.add_argument("--quick", action="store_true",
                       help="快速测试，跳过性能基准")
    parser.add_argument("--verbose", action="store_true",
                       help="详细输出")
    args = parser.parse_args()
    
    if args.quick:
        # 只运行基本测试
        results = {}
        results['physics'] = smoke_test_physics_engine()
        results['nca'] = smoke_test_nca_network()
        results['agent'] = smoke_test_agent()
        
        total_passed = sum(r.passed for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        
        print(f"\n快速测试完成: 通过 {total_passed}, 失败 {total_failed}")
        
        if total_failed > 0:
            sys.exit(1)
    else:
        run_all_tests(verbose=args.verbose)


if __name__ == "__main__":
    main()
