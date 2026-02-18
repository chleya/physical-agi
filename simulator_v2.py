"""
边缘演化智能群 - 具身机器人模拟器
集成物理引擎 + NCA-Mesh算法
"""

import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import time
import json

# 添加物理引擎路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'physical-agi', 'core'))
from physics_engine_edge import (
    Vec2, Vector3D, PhysicsObject, PhysicsObjectType, 
    PhysicsEngine, PhysicsConfig,
    create_mobile_robot
)


class TaskType(Enum):
    """任务类型"""
    PUSH = "push"
    EXPLORE = "explore"
    GATHER = "gather"
    FOLLOW = "follow"


@dataclass
class NCAParams:
    """NCA参数"""
    input_size: int = 6      # 感知输入: [self_x, self_y, target_x, target_y, nearby_count, rssi]
    hidden_size: int = 32
    output_size: int = 2      # 输出: [dx, dy] 移动方向
    lr: float = 0.001
    noise_scale: float = 0.1


class NCANetwork:
    """NCA神经网络"""
    
    def __init__(self, params: NCAParams = None):
        self.params = params or NCAParams()
        
        # 简单MLP（可替换为NCA）
        self.w1 = np.random.randn(self.params.input_size, self.params.hidden_size) * 0.1
        self.b1 = np.zeros(self.params.hidden_size)
        self.w2 = np.random.randn(self.params.hidden_size, self.params.output_size) * 0.1
        self.b2 = np.zeros(self.params.output_size)
        
        # 演化参数
        self.fitness = 0.0
        self.age = 0
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """前向传播"""
        x = np.tanh(np.dot(x, self.w1) + self.b1)
        x = np.tanh(np.dot(x, self.w2) + self.b2)
        return x
    
    def get_action(self, perception: np.ndarray) -> np.ndarray:
        """获取动作"""
        action = self.forward(perception)
        # 添加噪声（探索）
        if self.params.noise_scale > 0:
            noise = np.random.randn(2) * self.params.noise_scale
            action = action + noise
        return action
    
    def mutate(self, rate: float = 0.1) -> 'NCANetwork':
        """参数变异"""
        child = NCANetwork(self.params)
        child.w1 = self.w1 + np.random.randn(*self.w1.shape) * rate
        child.b1 = self.b1 + np.random.randn(*self.b1.shape) * rate
        child.w2 = self.w2 + np.random.randn(*self.w2.shape) * rate
        child.b2 = self.b2 + np.random.randn(*self.b2.shape) * rate
        return child
    
    def crossover(self, other: 'NCANetwork') -> 'NCANetwork':
        """交叉"""
        child = NCANetwork(self.params)
        mask1 = np.random.random(self.w1.shape) < 0.5
        mask2 = np.random.random(self.w2.shape) < 0.5
        child.w1 = np.where(mask1, self.w1, other.w1)
        child.w2 = np.where(mask2, self.w2, other.w2)
        return child


class EmbodiedAgent:
    """具身智能体"""
    
    def __init__(self, 
                 agent_id: str,
                 physics: PhysicsEngine,
                 position: Tuple[float, float] = (0, 0),
                 params: NCAParams = None):
        self.id = agent_id
        self.physics = physics
        self.params = params or NCAParams()
        
        # 创建物理身体
        self.body = create_mobile_robot(f"body_{self.id}", (position[0], position[1], 0))
        self.body.mass = 1.0
        self.body.friction = 0.3
        self.body.restitution = 0.3
        physics.add_object(self.body)
        
        # NCA网络
        self.network = NCANetwork(self.params)
        
        # 状态
        self.age = 0
        self.fitness = 0.0
        self.task = TaskType.EXPLORE
        self.target: Optional[PhysicsObject] = None
        self.history: List[Dict] = []
        
        # 邻居（Mesh网络）
        self.neighbors: List[str] = []
        self.rssi: Dict[str, float] = {}  # 信号强度
    
    def perceive(self, environment: Dict) -> np.ndarray:
        """感知环境"""
        # 基础信息
        self_x = self.body.position.x
        self_y = self.body.position.y
        
        # 目标信息
        if self.target:
            target_x = self.target.position.x
            target_y = self.target.position.y
        else:
            target_x, target_y = 0, 0
        
        # 邻居数量
        nearby_count = len(self.neighbors)
        
        # RSSI强度（基于距离）
        avg_rssi = np.mean(list(self.rssi.values())) if self.rssi else 0
        
        # 6维输入
        perception = np.array([
            self_x / 10.0,  # 归一化
            self_y / 10.0,
            target_x / 10.0,
            target_y / 10.0,
            nearby_count / 10.0,
            avg_rssi
        ])
        
        return perception
    
    def decide(self, perception: np.ndarray) -> np.ndarray:
        """决策"""
        return self.network.get_action(perception)
    
    def act(self, action: np.ndarray, environment: Dict):
        """执行动作"""
        # 动作是方向向量
        dx, dy = action[0], action[1]
        
        # 转换为力
        force_magnitude = 5.0
        force = Vector3D(dx * force_magnitude, dy * force_magnitude, 0)
        self.physics.apply_force(self.body.object_id, force)
        
        # 更新邻居RSSI
        self._update_rssi()
        
        # 记录历史
        self.history.append({
            'step': self.age,
            'position': (self.body.position.x, self.body.position.y),
            'action': (dx, dy),
            'fitness': self.fitness
        })
        
        self.age += 1
    
    def _update_rssi(self):
        """更新RSSI信号强度"""
        for neighbor_id in self.neighbors:
            if neighbor_id in self.physics.objects:
                neighbor = self.physics.objects[neighbor_id]
                dist = np.sqrt(
                    (self.body.position.x - neighbor.position.x)**2 +
                    (self.body.position.y - neighbor.position.y)**2
                )
                # RSSI随距离衰减
                self.rssi[neighbor_id] = max(0, 1.0 - dist / 10.0)
    
    def calculate_fitness(self, task: TaskType) -> float:
        """计算适应度"""
        if task == TaskType.PUSH and self.target:
            # 推动任务：靠近目标 + 保持接触
            dist = np.sqrt(
                (self.body.position.x - self.target.position.x)**2 +
                (self.body.position.y - self.target.position.y)**2
            )
            # 基础分数：靠近目标
            base_score = max(0, 5.0 - dist)
            
            # 额外分数：如果目标在移动
            target_speed = np.sqrt(
                self.target.velocity.x**2 + self.target.velocity.y**2
            )
            move_bonus = target_speed * 2.0
            
            self.fitness = base_score + move_bonus
        
        elif task == TaskType.EXPLORE:
            # 探索任务：移动距离
            if len(self.history) > 1:
                start = self.history[0]['position']
                end = self.history[-1]['position']
                dist = np.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
                self.fitness = dist
        
        # 奖励协作
        collaboration_bonus = len(self.neighbors) * 0.5
        self.fitness += collaboration_bonus
        
        return self.fitness


class Simulation:
    """具身机器人模拟器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'num_agents': 10,
            'num_targets': 3,
            'task': 'push',
            'physics_config': {
                'LOW_POWER_MODE': False,
                'MAX_OPS_PER_FRAME': 10000
            }
        }
        
        # 物理引擎
        physics_config = PhysicsConfig()
        physics_config.LOW_POWER_MODE = self.config['physics_config']['LOW_POWER_MODE']
        physics_config.MAX_OPS_PER_FRAME = self.config['physics_config']['MAX_OPS_PER_FRAME']
        
        self.physics = PhysicsEngine(config=physics_config)
        
        # 智能体
        self.agents: Dict[str, EmbodiedAgent] = {}
        self._create_agents()
        
        # 目标
        self.targets: List[PhysicsObject] = []
        self._create_targets()
        
        # 任务
        self.task = TaskType(self.config.get('task', 'push'))
        
        # 统计
        self.step_count = 0
        self.generation = 0
        self.best_fitness = 0
        self.best_agent = None
        
        # 日志
        self.log: List[Dict] = []
    
    def _create_agents(self):
        """创建智能体"""
        num = self.config['num_agents']
        
        for i in range(num):
            angle = 2 * np.pi * i / num
            dist = np.random.uniform(3, 6)
            pos = (np.cos(angle) * dist, np.sin(angle) * dist)
            
            agent = EmbodiedAgent(f"agent_{i}", self.physics, pos)
            self.agents[agent.id] = agent
    
    def _create_targets(self):
        """创建目标"""
        num = self.config['num_targets']
        
        for i in range(num):
            target = PhysicsObject(
                object_id=f"target_{i}",
                object_type=PhysicsObjectType.DYNAMIC,
                position=Vector3D(
                    np.random.uniform(-1, 1),
                    np.random.uniform(-1, 1),
                    0
                ),
                velocity=Vector3D(0, 0, 0),
                acceleration=Vector3D(0, 0, 0),
                mass=1.5,
                size=Vector3D(0.6, 0.6, 0.6),
                friction=0.5,
                restitution=0.1
            )
            self.targets.append(target)
            self.physics.add_object(target)
        
        # 设置智能体的目标（第一个目标）
        primary_target = self.targets[0] if self.targets else None
        for agent in self.agents.values():
            agent.target = primary_target
    
    def _reset_targets(self):
        """重置目标位置"""
        for target in self.targets:
            if target.object_id in self.physics.objects:
                target.position = Vector3D(
                    np.random.uniform(-1, 1),
                    np.random.uniform(-1, 1),
                    0
                )
                target.velocity = Vector3D(0, 0, 0)
    
    def step(self) -> Dict:
        """执行一步"""
        self.step_count += 1
        
        # 1. 更新邻居关系（Mesh网络）
        self._update_neighbors()
        
        # 2. 每个智能体的感知-决策-行动
        for agent in self.agents.values():
            perception = agent.perceive({})
            action = agent.decide(perception)
            agent.act(action, {})
            agent.calculate_fitness(self.task)
        
        # 3. 物理模拟
        physics_result = self.physics.simulate_step()
        
        # 4. 更新统计
        avg_fitness = np.mean([a.fitness for a in self.agents.values()])
        if avg_fitness > self.best_fitness:
            self.best_fitness = avg_fitness
            self.best_agent = max(self.agents.values(), key=lambda a: a.fitness)
        
        return {
            'step': self.step_count,
            'avg_fitness': avg_fitness,
            'best_fitness': self.best_fitness,
            'physics': physics_result
        }
    
    def _update_neighbors(self):
        """更新邻居关系（基于距离）"""
        range_threshold = 5.0  # 通信范围
        
        for agent in self.agents.values():
            agent.neighbors = []
            agent.rssi = {}
            
            for other in self.agents.values():
                if other.id == agent.id:
                    continue
                
                dist = np.sqrt(
                    (agent.body.position.x - other.body.position.x)**2 +
                    (agent.body.position.y - other.body.position.y)**2
                )
                
                if dist < range_threshold:
                    agent.neighbors.append(other.id)
                    agent.rssi[other.id] = max(0, 1.0 - dist / range_threshold)
    
    def evolve(self, generations: int = 10) -> List[Dict]:
        """演化一代"""
        history = []
        
        for gen in range(generations):
            self.generation = gen
            
            # 运行一代
            for _ in range(100):  # 每代100步
                self.step()
            
            # 收集适应度
            fitnesses = [(aid, agent.fitness) for aid, agent in self.agents.items()]
            fitnesses.sort(key=lambda x: x[1], reverse=True)
            
            history.append({
                'generation': gen,
                'best_fitness': fitnesses[0][1],
                'avg_fitness': np.mean([f for _, f in fitnesses]),
                'diversity': np.std([f for _, f in fitnesses])
            })
            
            print(f"Gen {gen}: Best={fitnesses[0][1]:.3f}, "
                  f"Avg={history[-1]['avg_fitness']:.3f}, "
                  f"Div={history[-1]['diversity']:.3f}")
            
            # 演化：选择和变异
            if gen < generations - 1:
                self._evolve_step(fitnesses)
        
        return history
    
    def _evolve_step(self, fitnesses: List[Tuple[str, float]]):
        """演化一步：精英保留 + 变异（修复版）"""
        # 精英保留：保留top 50%
        num_elites = max(1, len(fitnesses) // 2)
        elites = [aid for aid, _ in fitnesses[:num_elites]]
        
        print(f"  Elites: {len(elites)} agents")
        
        # 重建物理身体（重用旧的）
        old_positions = {}
        for aid, agent in self.agents.items():
            old_positions[agent.id] = (
                agent.body.position.x,
                agent.body.position.y,
                agent.body.velocity.x,
                agent.body.velocity.y
            )
        
        # 创建新一代智能体
        new_agents = {}
        
        for i in range(len(self.agents)):
            agent_id = list(self.agents.keys())[i]
            
            if agent_id in elites:
                # 精英保留
                new_agents[agent_id] = self.agents[agent_id]
                new_agents[agent_id].age = 0  # 重置年龄
                new_agents[agent_id].fitness = 0  # 重置适应度
            else:
                # 从精英池变异
                parent_id = np.random.choice(elites)
                parent = self.agents[parent_id]
                
                # 创建子智能体
                child_id = f"gen{self.generation}_{i}"
                
                # 保持位置连续性
                if agent_id in old_positions:
                    px, py, vx, vy = old_positions[agent_id]
                else:
                    angle = np.random.uniform(0, 2 * np.pi)
                    dist = np.random.uniform(3, 6)
                    px, py = np.cos(angle) * dist, np.sin(angle) * dist
                    vx, vy = 0, 0
                
                child = EmbodiedAgent(child_id, self.physics, (px, py))
                child.body.velocity = Vector3D(vx, vy, 0)
                child.network = parent.network.mutate(rate=0.05)  # 降低变异率
                
                new_agents[child.id] = child
        
        # 清理旧物体
        for aid in list(self.physics.objects.keys()):
            if aid.startswith('body_gen'):
                del self.physics.objects[aid]
        
        # 重建目标
        for target in self.targets:
            if target.object_id not in self.physics.objects:
                self.physics.add_object(target)
                for agent in new_agents.values():
                    agent.target = target
        
        self.agents = new_agents
        
        # 重置适应度
        for agent in self.agents.values():
            agent.fitness = 0.0
            agent.age = 0
    
    def get_statistics(self) -> Dict:
        """获取统计"""
        return {
            'step': self.step_count,
            'generation': self.generation,
            'num_agents': len(self.agents),
            'num_targets': len(self.targets),
            'avg_fitness': np.mean([a.fitness for a in self.agents.values()]),
            'best_fitness': self.best_fitness,
            'avg_neighbors': np.mean([
                len(a.neighbors) for a in self.agents.values()
            ]),
            'total_messages': sum([
                len(a.rssi) for a in self.agents.values()
            ])
        }
    
    def save_checkpoint(self, path: str):
        """保存检查点"""
        checkpoint = {
            'config': self.config,
            'step': self.step_count,
            'generation': self.generation,
            'agents': {
                aid: {
                    'network_w1': agent.network.w1.tolist(),
                    'network_w2': agent.network.w2.tolist(),
                    'fitness': agent.fitness,
                    'position': (agent.body.position.x, agent.body.position.y)
                }
                for aid, agent in self.agents.items()
            }
        }
        
        with open(path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        print(f"Checkpoint saved: {path}")
    
    def load_checkpoint(self, path: str):
        """加载检查点"""
        with open(path, 'r') as f:
            checkpoint = json.load(f)
        
        self.step_count = checkpoint['step']
        self.generation = checkpoint['generation']
        
        # 恢复网络权重
        for aid, data in checkpoint['agents'].items():
            if aid in self.agents:
                self.agents[aid].network.w1 = np.array(data['network_w1'])
                self.agents[aid].network.w2 = np.array(data['network_w2'])
                self.agents[aid].fitness = data['fitness']


def run_experiment():
    """运行实验"""
    print("=" * 60)
    print("边缘演化智能群 - 具身机器人模拟器")
    print("=" * 60)
    
    # 配置
    config = {
        'num_agents': 10,
        'num_targets': 3,
        'task': 'push',
        'physics_config': {
            'LOW_POWER_MODE': False,
            'MAX_OPS_PER_FRAME': 10000
        }
    }
    
    # 创建模拟器
    sim = Simulation(config)
    
    print(f"\n初始状态:")
    print(f"  智能体数: {len(sim.agents)}")
    print(f"  目标数: {len(sim.targets)}")
    print(f"  任务: {sim.task.value}")
    
    # 预热：运行几代演化
    print(f"\n演化训练...")
    start_time = time.time()
    
    history = sim.evolve(generations=10)
    
    elapsed = time.time() - start_time
    print(f"\n演化完成: {elapsed:.2f}s")
    
    # 最终测试
    print(f"\n最终测试 (100步)...")
    for _ in range(100):
        sim.step()
    
    stats = sim.get_statistics()
    print(f"\n最终统计:")
    print(f"  步数: {stats['step']}")
    print(f"  平均适应度: {stats['avg_fitness']:.3f}")
    print(f"  最佳适应度: {stats['best_fitness']:.3f}")
    print(f"  平均邻居: {stats['avg_neighbors']:.1f}")
    print(f"  总消息数: {stats['total_messages']}")
    
    # 保存检查点
    sim.save_checkpoint('simulation_checkpoint.json')
    
    # 绘制历史
    print(f"\n适应度历史:")
    for h in history:
        print(f"  Gen {h['generation']}: Best={h['best_fitness']:.3f}, "
              f"Avg={h['avg_fitness']:.3f}")
    
    return sim, history


def benchmark():
    """性能基准测试"""
    print("\n" + "=" * 60)
    print("性能基准测试")
    print("=" * 60)
    
    # 测试不同规模的性能
    scales = [10, 20, 50]
    
    for scale in scales:
        config = {
            'num_agents': scale,
            'num_targets': max(1, scale // 10),
            'task': 'push',
            'physics_config': {
                'LOW_POWER_MODE': False,
                'MAX_OPS_PER_FRAME': 10000
            }
        }
        
        sim = Simulation(config)
        
        start = time.time()
        for _ in range(100):
            sim.step()
        elapsed = time.time() - start
        
        fps = 100 / elapsed
        stats = sim.get_statistics()
        ops = stats.get('total_messages', 0) / 100
        
        print(f"  Agents={scale}: {fps:.1f} FPS, {ops:.1f} msg/step")
    
    return True


if __name__ == "__main__":
    run_experiment()
    benchmark()
