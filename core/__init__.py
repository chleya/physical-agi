# Physical AGI Core Module

## 概述
物理AGI核心模块，提供物理世界理解和推理的基础能力。

## 模块结构

```
core/
├── __init__.py              # 模块初始化
├── physics_engine.py        # 物理引擎
├── causality.py             # 因果推理
├── intuitive_physics.py     # 直观物理
├── embodied_cognition.py    # 具身认知
├── object_dynamics.py       # 物体动力学
├── spatial_reasoning.py     # 空间推理
└── physical_properties.py   # 物理属性
```

## 核心功能

### 1. 物理引擎 (Physics Engine)
- 物理规则建模
- 运动模拟
- 力与相互作用
- 碰撞检测

### 2. 因果推理 (Causal Reasoning)
- 因果关系发现
- 因果链推理
- 反事实推理
- 因果归因

### 3. 直观物理 (Intuitive Physics)
- 物理直觉模拟
- 物体行为预测
- 物理常识推理
- 违反检测

### 4. 具身认知 (Embodied Cognition)
- 身体表征
- 运动控制
- 感知-动作循环
- 环境交互

## 与其他模块的集成

- **evo-meta/** - 元认知监控
- **evo-memory/** - 物理经验记忆
- **evo-loop/** - 物理任务执行

## 依赖
- numpy
- scipy
- torch

## 版本
- 1.0.0 - 初始版本
