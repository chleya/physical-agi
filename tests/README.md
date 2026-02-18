# 测试框架使用说明

## 概述

本项目包含自动化测试框架，用于验证物理引擎的正确性和稳定性。

## 目录结构

```
tests/
├── __init__.py              # 测试初始化
├── test_physics.py         # 单元测试
├── hardware_smoke_test.py   # 冒烟测试
└── README.md               # 本文档
```

## 快速开始

### 安装依赖

```bash
pip install pytest numpy
```

### 运行所有测试

```bash
# 切换到项目目录
cd F:\skill\physical-agi

# 运行单元测试
pytest tests/test_physics.py -v

# 运行冒烟测试
python tests/hardware_smoke_test.py

# 或使用pytest运行冒烟测试
pytest tests/hardware_smoke_test.py -v
```

### 快速测试（跳过性能基准）

```bash
python tests/hardware_smoke_test.py --quick
```

## 单元测试 (test_physics.py)

### 测试类别

| 类名 | 测试内容 |
|------|---------|
| `TestVec2` | 二维向量运算（加减乘除、点积、归一化） |
| `TestVector3D` | 三维向量运算 |
| `TestPhysicsObject` | 物理对象创建和属性 |
| `TestPhysicsEngine` | 物理引擎核心功能 |
| `TestNCANetwork` | NCA神经网络前向传播、变异 |
| `TestEmbodiedAgent` | 具身智能体感知、决策、动作 |
| `TestHelpers` | 辅助函数 |

### 运行单个测试类

```bash
pytest tests/test_physics.py::TestVec2 -v
```

### 运行单个测试

```bash
pytest tests/test_physics.py::TestVec2::test_add -v
```

### 生成测试覆盖率报告

```bash
pytest tests/test_physics.py --cov=physics_engine_edge --cov-report=html
```

## 冒烟测试 (hardware_smoke_test.py)

### 测试项目

1. **物理引擎冒烟测试**
   - 创建/添加/移除对象
   - 施力模拟
   - 单步/多步模拟
   - 碰撞检测
   - 配置测试

2. **NCA网络冒烟测试**
   - 网络创建
   - 前向传播
   - 参数变异
   - 输出边界验证

3. **智能体冒烟测试**
   - 智能体创建
   - 感知-决策-动作循环
   - 适应度计算

4. **性能基准**
   - 多物体模拟性能
   - FPS测量

### 运行冒烟测试

```bash
# 标准运行
python tests/hardware_smoke_test.py

# 快速模式（无性能基准）
python tests/hardware_smoke_test.py --quick

# 详细输出
python tests/hardware_smoke_test.py --verbose
```

### 冒烟测试预期输出

```
============================================================
  边缘演化智能群 - 硬件冒烟测试
  ============================================================

[物理引擎冒烟测试]

[1/8] 测试创建...
  [PASS] 创建PhysicsEngine

[2/8] 测试添加对象...
  [PASS] 添加对象
  ...

============================================================
  测试结果汇总
  ============================================================

PHYSICS:
  通过: 8
  失败: 0

NCA:
  通过: 4
  失败: 0

AGENT:
  通过: 5
  失败: 0

============================================================
  总计: 通过 17, 失败 0
  总体状态: PASS
  ============================================================
```

## 添加新测试

### 添加单元测试

在 `test_physics.py` 中添加新的测试类：

```python
class TestYourFeature:
    def test_something(self):
        """测试说明"""
        # 测试代码
        assert result == expected
```

### 添加冒烟测试

在 `hardware_smoke_test.py` 中添加：

```python
def smoke_test_your_feature() -> TestResult:
    """功能冒烟测试"""
    print_header("你的功能冒烟测试")
    result = TestResult()
    
    # 测试代码...
    
    return result
```

然后在 `run_all_tests()` 中调用。

## CI/CD集成

### GitHub Actions示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install pytest numpy
    
    - name: Run tests
      run: |
        pytest tests/ -v
    
    - name: Run smoke test
      run: |
        python tests/hardware_smoke_test.py
```

## 常见问题

### Q: 测试失败怎么办？

1. 查看错误信息
2. 检查是否修改了相关代码
3. 运行单个测试获取详细信息：
   ```bash
   pytest tests/test_physics.py::TestPhysicsEngine::test_simulate_step -v -s
   ```

### Q: 如何跳过某些测试？

```bash
# 跳过单个测试
pytest tests/test_physics.py -k "not test_name"

# 跳过整个类
pytest tests/test_physics.py -k "not TestClassName"
```

### Q: 性能测试太慢？

使用快速模式：
```bash
python tests/hardware_smoke_test.py --quick
```

## 测试最佳实践

1. **每个测试独立** - 不依赖其他测试的顺序
2. **测试有文档** - 每个测试有清晰的文档字符串
3. **快速执行** - 单元测试 < 1秒
4. **明确的断言** - 断言有清晰的信息

## 维护指南

### 添加新功能时

1. 先写测试
2. 让测试失败
3. 实现功能
4. 让测试通过

### 修改现有功能时

1. 运行相关测试
2. 确保测试通过
3. 如需修改测试，说明原因

---

最后更新: 2026-02-18
