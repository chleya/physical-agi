"""
NCA前向传播模块
完全解耦，可独立使用
"""

import numpy as np
from typing import Optional


class NCAParams:
    """NCA参数"""
    def __init__(self):
        self.input_size = 6
        self.hidden_size = 32
        self.output_size = 2
        self.lr = 0.001
        self.noise_scale = 0.1


class NCANetwork:
    """
    NCA神经网络 (解耦版本)
    
    独立模块，可单独测试和替换
    """
    
    def __init__(self, params: Optional[NCAParams] = None):
        self.params = params or NCAParams()
        
        # 初始化权重
        np.random.seed(42)  # 可配置的随机种子
        self.w1 = np.random.randn(
            self.params.input_size, 
            self.params.hidden_size
        ) * 0.1
        self.b1 = np.zeros(self.params.hidden_size)
        self.w2 = np.random.randn(
            self.params.hidden_size, 
            self.params.output_size
        ) * 0.1
        self.b2 = np.zeros(self.params.output_size)
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        前向传播
        
        Args:
            x: 输入向量 (6,)
            
        Returns:
            输出向量 (2,)
        """
        # Layer 1: tanh激活
        h = np.tanh(np.dot(x, self.w1) + self.b1)
        
        # Layer 2: tanh激活
        y = np.tanh(np.dot(h, self.w2) + self.b2)
        
        return y
    
    def get_action(self, x: np.ndarray, noise: Optional[float] = None) -> np.ndarray:
        """
        获取动作（带噪声探索）
        
        Args:
            x: 输入向量
            noise: 噪声尺度（None=不使用）
            
        Returns:
            动作向量
        """
        action = self.forward(x)
        
        if noise is not None:
            action = action + np.random.randn(2) * noise
        
        return action
    
    def mutate(self, rate: float = 0.1) -> 'NCANetwork':
        """
        变异
        
        Args:
            rate: 变异率
            
        Returns:
            变异后的网络
        """
        child = NCANetwork(self.params)
        child.w1 = self.w1 + np.random.randn(*self.w1.shape) * rate
        child.b1 = self.b1 + np.random.randn(*self.b1.shape) * rate
        child.w2 = self.w2 + np.random.randn(*self.w2.shape) * rate
        child.b2 = self.b2 + np.random.randn(*self.b2.shape) * rate
        return child
    
    def crossover(self, other: 'NCANetwork') -> 'NCANetwork':
        """
        交叉
        
        Args:
            other: 另一个网络
            
        Returns:
            交叉后的网络
        """
        child = NCANetwork(self.params)
        
        # 随机选择父本
        mask1 = np.random.random(self.w1.shape) < 0.5
        mask2 = np.random.random(self.w2.shape) < 0.5
        
        child.w1 = np.where(mask1, self.w1, other.w1)
        child.w2 = np.where(mask2, self.w2, other.w2)
        
        return child
    
    def save(self, path: str):
        """保存权重"""
        np.savez(path, 
            w1=self.w1, b1=self.b1,
            w2=self.w2, b2=self.b2)
    
    @classmethod
    def load(cls, path: str) -> 'NCANetwork':
        """加载权重"""
        data = np.load(path)
        net = cls()
        net.w1 = data['w1']
        net.b1 = data['b1']
        net.w2 = data['w2']
        net.b2 = data['b2']
        return net


# ========== 独立测试 ==========
if __name__ == "__main__":
    # 测试
    net = NCANetwork()
    
    # 前向传播测试
    x = np.random.randn(6)
    y = net.forward(x)
    print(f"Input: {x}")
    print(f"Output: {y}")
    print(f"Output shape: {y.shape}")
    print(f"Output bounds: [{y.min():.3f}, {y.max():.3f}]")
    
    # 变异测试
    child = net.mutate(0.01)
    print(f"\nMutation test: {'PASS' if child.w1.shape == net.w1.shape else 'FAIL'}")
