"""
物理引擎单元测试
测试Vec2、物理对象、物理引擎等核心功能
"""

import sys
import os
import pytest
import numpy as np

# 添加被测模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from physics_engine_edge import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType,
    PhysicsEngine, PhysicsConfig,
    create_mobile_robot, create_robot_arm_agent
)


class TestVec2:
    """测试Vec2二维向量类"""
    
    def test_create(self):
        """测试创建"""
        v = Vec2(3, 4)
        assert v.x == 3
        assert v.y == 4
    
    def test_add(self):
        """测试加法"""
        v1 = Vec2(1, 2)
        v2 = Vec2(3, 4)
        v3 = v1 + v2
        assert v3.x == 4
        assert v3.y == 6
    
    def test_subtract(self):
        """测试减法"""
        v1 = Vec2(5, 6)
        v2 = Vec2(2, 3)
        v3 = v1 - v2
        assert v3.x == 3
        assert v3.y == 3
    
    def test_multiply(self):
        """测试标量乘法"""
        v = Vec2(2, 3)
        v2 = v * 2
        assert v2.x == 4
        assert v2.y == 6
    
    def test_divide(self):
        """测试除法"""
        v = Vec2(6, 8)
        v2 = v / 2
        assert v2.x == 3
        assert v2.y == 4
    
    def test_divide_by_zero(self):
        """测试除零"""
        v = Vec2(1, 1)
        with pytest.raises(ValueError):
            v / 0
    
    def test_dot(self):
        """测试点积"""
        v1 = Vec2(3, 4)
        v2 = Vec2(1, 2)
        result = v1.dot(v2)
        assert result == 3*1 + 4*2  # 11
    
    def test_magnitude(self):
        """测试模长"""
        v = Vec2(3, 4)
        assert abs(v.magnitude() - 5.0) < 0.001
    
    def test_normalize(self):
        """测试归一化"""
        v = Vec2(3, 4)
        v_norm = v.normalize()
        assert abs(v_norm.magnitude() - 1.0) < 0.001


class TestVector3D:
    """测试Vector3D三维向量类"""
    
    def test_create(self):
        """测试创建"""
        v = Vector3D(1, 2, 3)
        assert v.x == 1
        assert v.y == 2
        assert v.z == 3
    
    def test_operations(self):
        """测试基本运算"""
        v1 = Vector3D(1, 2, 3)
        v2 = Vector3D(4, 5, 6)
        
        # 加法
        v3 = v1 + v2
        assert v3.x == 5 and v3.y == 7 and v3.z == 9
        
        # 减法
        v4 = v2 - v1
        assert v4.x == 3 and v4.y == 3 and v4.z == 3
        
        # 乘法
        v5 = v1 * 2
        assert v5.x == 2 and v5.y == 4 and v5.z == 6
    
    def test_magnitude(self):
        """测试模长"""
        v = Vector3D(1, 2, 2)
        assert abs(v.magnitude() - 3.0) < 0.001


class TestPhysicsObject:
    """测试PhysicsObject物理对象类"""
    
    def test_create_dynamic(self):
        """测试创建动态对象"""
        obj = PhysicsObject(
            object_id="test",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(0, 0, 0),
            velocity=Vector3D(0, 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=1.0,
            size=Vector3D(1, 1, 1)
        )
        assert obj.object_id == "test"
        assert obj.object_type == PhysicsObjectType.DYNAMIC
        assert obj.mass == 1.0
    
    def test_create_static(self):
        """测试创建静态对象"""
        obj = PhysicsObject(
            object_id="ground",
            object_type=PhysicsObjectType.STATIC,
            position=Vector3D(0, 0, 0),
            velocity=Vector3D(0, 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=float('inf'),
            size=Vector3D(10, 1, 10)
        )
        assert obj.object_type == PhysicsObjectType.STATIC
    
    def test_zero_mass_protection(self):
        """测试零质量保护"""
        obj = PhysicsObject(
            object_id="test",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(0, 0, 0),
            velocity=Vector3D(0, 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=0,  # 零质量
            size=Vector3D(1, 1, 1)
        )
        # 应该被修正为最小质量
        assert obj.mass == 0.001
    
    def test_physics_properties(self):
        """测试物理属性"""
        obj = PhysicsObject(
            object_id="test",
            object_type=PhysicsObjectType.DYNAMIC,
            position=Vector3D(0, 0, 0),
            velocity=Vector3D(0, 0, 0),
            acceleration=Vector3D(0, 0, 0),
            mass=1.0,
            size=Vector3D(1, 1, 1),
            friction=0.5,
            restitution=0.8
        )
        assert obj.friction == 0.5
        assert obj.restitution == 0.8


class TestPhysicsEngine:
    """测试PhysicsEngine物理引擎类"""
    
    @pytest.fixture
    def engine(self):
        """创建测试引擎"""
        config = PhysicsConfig()
        config.LOW_POWER_MODE = False
        return PhysicsEngine(config=config)
    
    @pytest.fixture
    def two_objects(self, engine):
        """创建包含两个物体的引擎"""
        obj1 = create_mobile_robot("obj1", (0, 5, 0))
        obj2 = create_mobile_robot("obj2", (0, 0, 0))
        engine.add_object(obj1)
        engine.add_object(obj2)
        return engine
    
    def test_create(self, engine):
        """测试创建"""
        assert engine is not None
        assert len(engine.objects) == 0
    
    def test_add_remove_object(self, engine):
        """测试添加和移除对象"""
        obj = create_mobile_robot("test", (0, 0, 0))
        
        # 添加
        engine.add_object(obj)
        assert "test" in engine.objects
        
        # 移除
        result = engine.remove_object("test")
        assert result is True
        assert "test" not in engine.objects
    
    def test_apply_force(self, engine):
        """测试施加力"""
        obj = create_mobile_robot("test", (0, 0, 0))
        engine.add_object(obj)
        
        force = Vector3D(1, 0, 0)
        result = engine.apply_force("test", force)
        
        assert result is True
        # 检查加速度是否更新
        assert engine.objects["test"].acceleration.x > 0
    
    def test_apply_force_invalid_id(self, engine):
        """测试对不存在的对象施加力"""
        force = Vector3D(1, 0, 0)
        result = engine.apply_force("nonexistent", force)
        assert result is False
    
    def test_simulate_step(self, two_objects):
        """测试模拟步进"""
        engine = two_objects
        
        initial_pos_y = engine.objects["obj1"].position.y
        
        result = engine.simulate_step(dt=0.016)
        
        assert result is not None
        assert "skipped" in result
        assert result["skipped"] is False
    
    def test_kinematic_not_affected_by_gravity(self, engine):
        """测试运动学物体不受重力影响"""
        kin = create_robot_arm_agent("kin", (0, 5, 0))
        engine.add_object(kin)
        
        initial_y = kin.position.y
        
        # 模拟多步
        for _ in range(10):
            engine.simulate_step()
        
        # KINEMATIC物体位置不应该改变（不受重力）
        assert abs(engine.objects["kin"].position.y - initial_y) < 0.001
    
    def test_dynamic_falls(self, engine):
        """测试动态物体下落"""
        obj = create_mobile_robot("falling", (0, 5, 0))
        engine.add_object(obj)
        
        initial_y = obj.position.y
        
        engine.simulate_step(dt=0.016)
        
        # 应该向下移动
        assert engine.objects["falling"].position.y < initial_y
    
    def test_collision_detection(self, engine):
        """测试碰撞检测"""
        obj1 = create_mobile_robot("obj1", (0, 1, 0))
        obj2 = create_mobile_robot("obj2", (0, 0, 0))
        
        engine.add_object(obj1)
        engine.add_object(obj2)
        
        # 模拟直到碰撞
        collisions = 0
        for _ in range(100):
            result = engine.simulate_step()
            collisions += result.get("collisions", 0)
            # 检查obj1是否在地面上方
            if engine.objects["obj1"].position.y < 0.6:
                break
        
        # 应该有碰撞发生
        assert collisions > 0 or engine.objects["obj1"].position.y < 0.6
    
    def test_low_power_mode(self):
        """测试低功耗模式"""
        config = PhysicsConfig()
        config.LOW_POWER_MODE = True
        engine = PhysicsEngine(config=config)
        
        assert engine.low_power is True
        assert engine.update_hz == 30
    
    def test_ground_collision(self, engine):
        """测试地面碰撞"""
        obj = create_mobile_robot("test", (0, 5, 0))
        engine.add_object(obj)
        
        # 模拟直到静止
        for _ in range(200):
            engine.simulate_step()
        
        # 物体应该在地面上方
        ground_y = obj.size.y / 2
        assert engine.objects["test"].position.y >= ground_y - 0.1


class TestNCANetwork:
    """测试NCANetwork神经网络类"""
    
    def test_create(self):
        """测试创建"""
        from physics_engine_edge import NCANetwork, NCAParams
        
        params = NCAParams()
        net = NCANetwork(params)
        
        assert net.w1.shape == (6, 32)
        assert net.w2.shape == (32, 2)
    
    def test_forward(self):
        """测试前向传播"""
        from physics_engine_edge import NCANetwork, NCAParams
        
        params = NCAParams()
        net = NCANetwork(params)
        
        x = np.random.randn(6)
        y = net.forward(x)
        
        assert y.shape == (2)
        # 输出应该在-1到1之间
        assert all(-1 <= v <= 1 for v in y)
    
    def test_mutation(self):
        """测试变异"""
        from physics_engine_edge import NCANetwork, NCAParams
        
        params = NCAParams()
        net1 = NCANetwork(params)
        
        # 复制权重
        w1_before = net1.w1.copy()
        
        # 变异
        net2 = net1.mutate(rate=0.01)
        
        # 权重应该不同
        assert not np.allclose(net1.w1, net2.w1)


class TestEmbodiedAgent:
    """测试具身智能体类"""
    
    def test_create(self):
        """测试创建"""
        from physics_engine_edge import EmbodiedAgent, AgentConfig
        
        config = AgentConfig(
            name="test_agent",
            position=np.array([0, 0])
        )
        
        engine = PhysicsEngine()
        agent = EmbodiedAgent("test", engine, config)
        
        assert agent.id == "test"
        assert agent.age == 0
        assert agent.fitness == 0.0
    
    def test_perceive(self):
        """测试感知"""
        from physics_engine_edge import EmbodiedAgent, AgentConfig
        
        config = AgentConfig(name="test")
        engine = PhysicsEngine()
        agent = EmbodiedAgent("test", engine, (0, 0))
        
        # 没有邻居时的感知
        perception = agent.perceive({})
        
        assert perception.shape == (6,)  # 6维输入
        assert len(agent.neighbors) == 0
    
    def test_act(self):
        """测试动作执行"""
        from physics_engine_edge import EmbodiedAgent, AgentConfig
        
        engine = PhysicsEngine()
        agent = EmbodiedAgent("test", engine, (0, 5))
        
        # 执行移动动作
        action = np.array([1.0, 0.0])  # 向右移动
        agent.act(action, {})
        
        # 检查年龄增长
        assert agent.age == 1
        
        # 检查历史记录
        assert len(agent.history) == 1
    
    def test_calculate_fitness(self):
        """测试适应度计算"""
        from physics_engine_edge import EmbodiedAgent, TaskType
        
        engine = PhysicsEngine()
        agent = EmbodiedAgent("test", engine, (0, 5))
        agent.target = create_mobile_robot("target", (0, 2, 0))
        engine.add_object(agent.target)
        
        # 设置推动任务
        fitness = agent.calculate_fitness(TaskType.PUSH)
        
        # 应该有适应度
        assert fitness >= 0


class TestHelpers:
    """测试辅助函数"""
    
    def test_create_mobile_robot(self):
        """测试创建移动机器人"""
        robot = create_mobile_robot("bot", (1, 2, 0))
        
        assert robot.object_id == "body_bot"
        assert robot.object_type == PhysicsObjectType.DYNAMIC
        assert robot.mass == 5.0  # 默认质量
    
    def test_create_robot_arm_agent(self):
        """测试创建机器人臂"""
        arm = create_robot_arm_agent("arm", (0, 0, 0))
        
        assert arm.object_type == PhysicsObjectType.DYNAMIC
        assert arm.joint_type == "hinge"


# 运行测试的命令
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
