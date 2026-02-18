# 边缘演化智能群 - 完整项目文档

## 目录

1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [模块说明](#模块说明)
4. [使用指南](#使用指南)
5. [API参考](#api参考)
6. [实验记录](#实验记录)
7. [版本历史](#版本历史)
8. [故障排除](#故障排除)

---

## 项目概述

### 目标

v5硬件 + DancingNCA算法 → 边缘演化具身智能群

### 核心理念

> "协作的本质是对不确定性的消除"

### 项目状态

| 阶段 | 状态 |
|------|------|
| Python验证 | ✅ 完成 |
| C代码导出 | ✅ 完成 |
| 物理引擎 | ✅ 完成 |
| 演化模拟器 | ✅ 完成 |
| 硬件参数导出 | ✅ 完成 |
| Evo-Swarm集成 | ✅ 完成 |
| **硬件部署** | ⏳ 待办 |

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    演化层 (Evolution)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ 遗传算法   │→│  精英选择   │→│  参数变异   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                    策略层 (Policy)                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              NCANetwork (6→32→2)                   │  │
│  │  输入: [self_x, self_y, target_x, target_y,        │  │
│  │        neighbor_count, avg_rssi]                   │  │
│  │  输出: [dx, dy] 移动方向                          │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                    物理层 (Physics)                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              PhysicsEngine                         │  │
│  │  - 碰撞检测 (AABB + Circle)                       │  │
│  │  - 摩擦力模拟                                    │  │
│  │  - 关节约束                                      │  │
│  │  - RSSI通信模拟                                  │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                    硬件层 (Hardware)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   ESP32    │  │  电机驱动   │  │  传感器    │    │
│  │  NCA推理   │  │  DRV8833   │  │ MPU6050    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
感知 → NCA前向传播 → 动作输出 → 物理模拟 → 适应度评估 → 演化
   ↓              ↓            ↓           ↓           ↓
  6维输入    2维输出      施加力     碰撞响应     选择+变异
```

---

## 模块说明

### 物理引擎 (core/physics_engine_edge.py)

| 类/函数 | 功能 |
|--------|------|
| `PhysicsEngine` | 物理模拟核心 |
| `PhysicsObject` | 物理对象 |
| `Vec2/Vector3D` | 向量运算 |
| `create_mobile_robot()` | 创建移动机器人 |
| `create_robot_arm_agent()` | 创建机器人臂 |

### 演化模拟器 (simulator_v2.py)

| 类/函数 | 功能 |
|--------|------|
| `Simulation` | 演化模拟器 |
| `NCANetwork` | 神经网络 |
| `EmbodiedAgent` | 具身智能体 |
| `evolve()` | 执行演化 |

### 硬件导出 (hardware_export/)

| 文件 | 功能 |
|------|------|
| `nca_params.h` | 网络参数 |
| `nca_agent.c` | ESP32实现 |
| `robot_sketch.ino` | Arduino草图 |

---

## 使用指南

### 快速开始

```bash
# 运行演化模拟
cd F:\skill\physical-agi
python simulator_v2.py

# 运行冒烟测试
python tests/smoke_test_simple.py

# 导出硬件参数
python hardware_export.py
```

### 创建自定义模拟

```python
from simulator_v2 import Simulation, TaskType
from physics_engine_edge import PhysicsConfig

# 配置
config = {
    'num_agents': 10,
    'num_targets': 3,
    'task': 'push',
    'physics_config': {...}
}

# 创建模拟器
sim = Simulation(config)

# 演化10代
history = sim.evolve(generations=10)

# 保存检查点
sim.save_checkpoint('checkpoint.json')
```

### 部署到ESP32

```bash
# 1. 导出参数
python hardware_export.py

# 2. 复制文件到ESP32项目
cp hardware_export/nca_params.h <esp32_project>/include/
cp hardware_export/nca_agent.c <esp32_project>/src/

# 3. 编译
cd <esp32_project>
pio run -e esp32dev -t upload
```

---

## API参考

### PhysicsEngine

```python
# 创建
engine = PhysicsEngine(gravity=Vector3D(0, -9.81, 0))

# 添加对象
engine.add_object(robot)

# 施加力
engine.apply_force("robot", Vector3D(1, 0, 0))

# 模拟步进
result = engine.simulate_step(dt=0.016)

# 获取适应度
metrics = engine.get_fitness_metrics()
# {
#     'total_kinetic_energy': 123.45,
#     'average_velocity': 5.67,
#     'max_velocity': 12.34
# }
```

### NCANetwork

```python
# 创建
net = NCANetwork(params)

# 前向传播
output = net.forward(input)  # input: np.ndarray(6)

# 变异
child = net.mutate(rate=0.1)
```

### EmbodiedAgent

```python
# 感知
perception = agent.perceive(environment)

# 决策
action = agent.decide(perception)

# 执行
result = agent.act(action, environment)

# 获取适应度
fitness = agent.calculate_fitness(TaskType.PUSH)
```

---

## 实验记录

### 模板

```markdown
## 实验名称
日期: YYYY-MM-DD

### 目标

### 方法

### 结果

| 指标 | 值 |
|------|-----|
| 适应度 | xxx |
| 步数 | xxx |

### 观察

### 结论

### 改进建议
```

### 示例

```
## 演化实验-2026-02-18
日期: 2026-02-18

目标: 验证推箱子任务的演化效果

方法:
- 10个智能体
- 10代演化
- 精英保留率: 50%

结果:
| 代数 | 最佳适应度 | 平均适应度 |
|-----|-----------|-----------|
| 0   | 36.642   | 34.568   |
| 5   | 195.873  | 88.762   |
| 9   | 326.673  | 128.002  |

观察: 适应度持续提升，收敛成功

结论: 算法有效，可进入硬件验证阶段

改进建议: 可尝试增加智能体数量
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-18 | 初始版本 |
| v1.1 | 2026-02-18 | 修复Vec2问题 |
| v1.2 | 2026-02-18 | 修复NaN |
| v1.3 | 2026-02-18 | 边缘优化 |

### 详细变更

#### v1.3 (2026-02-18)
- ✅ 添加定点运算支持
- ✅ 添加计算预算控制
- ✅ 添加低功耗模式
- ✅ 添加内存池
- ✅ 添加机器人专用接口
- ✅ 添加演化支持接口

---

## 故障排除

### 常见问题

#### Q: 仿真崩溃/NaN

**原因**: 物理参数超出范围

**解决**:
```python
# 检查物理参数
assert obj.mass > 0
assert obj.friction >= 0 and obj.friction <= 1
```

#### Q: 演化不收敛

**原因**: 变异率过高/过低

**解决**:
```python
# 调整变异率
params = NCAParams()
params.noise_scale = 0.1  # 尝试0.05-0.2
```

#### Q: 性能差

**原因**: 物体数量过多

**解决**:
```python
# 启用低功耗模式
config = PhysicsConfig()
config.LOW_POWER_MODE = True
```

### 调试技巧

1. **启用详细输出**
   ```python
   engine.debug = True
   ```

2. **保存检查点**
   ```python
   sim.save_checkpoint('debug.json')
   ```

3. **可视化**
   ```python
   from visualization import plot_history
   plot_history(history)
   ```

---

## 贡献指南

1. Fork项目
2. 创建分支 (`git checkout -b feature/xxx`)
3. 提交变更 (`git commit -m "Add xxx"`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建Pull Request

### 代码风格

- Python: PEP 8
- C: GNU C99
- 文档: Markdown

---

## 许可证

MIT License

---

最后更新: 2026-02-18
