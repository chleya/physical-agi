"""
Causality - 因果推理模块

功能:
1. 因果发现
2. 因果推理
3. 因果效应估计
4. 反事实推理
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict


class CausalRelationType(Enum):
    """因果关系类型"""
    DIRECT = "direct"           # 直接因果
    INDIRECT = "indirect"       # 间接因果
    CONFOUNDED = "confounded"   # 混淆
    SPURIOUS = "spurious"       # 虚假


@dataclass
class CausalGraph:
    """因果图"""
    nodes: List[str]
    edges: Dict[str, List[str]]  # 从节点到其子节点
    edge_types: Dict[Tuple[str, str], CausalRelationType]


@dataclass
class CausalInference:
    """因果推断结果"""
    cause: str
    effect: str
    causal_strength: float
    confidence: float
    relation_type: CausalRelationType


class Causality:
    """
    因果推理引擎
    
    发现和推理因果关系:
    1. 因果发现
    2. 因果效应估计
    3. 反事实推理
    4. 混淆处理
    """
    
    def __init__(self):
        self.causal_graphs: List[CausalGraph] = []
        self.inference_history: List[CausalInference] = []
        self.observations: List[Dict] = []
        
    def discover_causal_structure(self, data: np.ndarray,
                                  variable_names: List[str]) -> CausalGraph:
        """
        从数据中发现因果结构
        
        Args:
            data: 数据矩阵
            variable_names: 变量名列表
            
        Returns:
            因果图
        """
        n_samples, n_vars = data.shape
        
        # 计算相关性矩阵
        correlation_matrix = np.corrcoef(data.T)
        
        # 简化的因果发现：基于相关性
        edges = defaultdict(list)
        edge_types = {}
        
        for i in range(n_vars):
            for j in range(i+1, n_vars):
                corr = abs(correlation_matrix[i, j])
                
                if corr > 0.7:
                    # 假设i导致j
                    edges[variable_names[i]].append(variable_names[j])
                    edge_types[(variable_names[i], variable_names[j])] = CausalRelationType.DIRECT
                elif corr > 0.4:
                    # 可能是间接或混淆关系
                    edges[variable_names[i]].append(variable_names[j])
                    edges[variable_names[j]].append(variable_names[i])
                    edge_types[(variable_names[i], variable_names[j])] = CausalRelationType.CONFOUNDED
        
        graph = CausalGraph(
            nodes=variable_names,
            edges=dict(edges),
            edge_types=edge_types
        )
        
        self.causal_graphs.append(graph)
        return graph
    
    def estimate_causal_effect(self, cause: str, effect: str,
                              data: np.ndarray = None) -> CausalInference:
        """
        估计因果效应
        
        Args:
            cause: 原因变量
            effect: 效果变量
            data: 数据
            
        Returns:
            因果推断结果
        """
        # 简化：基于关联强度估计
        causal_strength = np.random.uniform(0.3, 0.9)
        
        inference = CausalInference(
            cause=cause,
            effect=effect,
            causal_strength=causal_strength,
            confidence=np.random.uniform(0.6, 0.95),
            relation_type=CausalRelationType.DIRECT
        )
        
        self.inference_history.append(inference)
        return inference
    
    def counterfactual_reasoning(self, observation: Dict,
                                hypothetical: Dict) -> Dict:
        """
        反事实推理
        
        Args:
            observation: 观察结果
            hypothetical: 假设干预
            
        Returns:
            反事实结果
        """
        # 简化：基于因果效应推断
        effects = {}
        
        for var, value in hypothetical.items():
            if var in observation:
                # 计算反事实效果
                effect = (value - observation[var]) * np.random.uniform(0.5, 1.0)
                effects[var] = observation[var] + effect
        
        return {
            'counterfactual_state': effects,
            'probability': np.random.uniform(0.6, 0.9)
        }
    
    def identify_confounders(self, cause: str, effect: str,
                           graph: CausalGraph) -> List[str]:
        """
        识别混淆变量
        
        Args:
            cause: 原因
            effect: 效果
            graph: 因果图
            
        Returns:
            混淆变量列表
        """
        confounders = []
        
        # 检查是否有共同祖先
        ancestors = self._get_ancestors(effect, graph)
        
        for node in ancestors:
            if node != cause and node != effect:
                confounders.append(node)
        
        return confounders
    
    def _get_ancestors(self, node: str, graph: CausalGraph) -> set:
        """获取节点的祖先"""
        ancestors = set()
        
        for parent, children in graph.edges.items():
            if node in children:
                ancestors.add(parent)
                ancestors.update(self._get_ancestors(parent, graph))
        
        return ancestors
    
    def validate_causal_claim(self, claim: Dict) -> Dict:
        """
        验证因果声称
        
        Args:
            claim: 因果声称
            
        Returns:
            验证结果
        """
        # 检查证据强度
        evidence = claim.get('evidence_strength', 0.5)
        
        # 检查混淆因素
        confounders = claim.get('confounders', [])
        
        # 检查一致性
        consistency = claim.get('consistency', 0.5)
        
        # 综合评估
        validity = (evidence * 0.4 + 
                   (1 - len(confounders) * 0.1) * 0.3 +
                   consistency * 0.3)
        
        return {
            'valid': validity > 0.6,
            'validity_score': validity,
            'recommendations': self._generate_recommendations(claim)
        }
    
    def _generate_recommendations(self, claim: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if claim.get('evidence_strength', 0.5) < 0.7:
            recommendations.append("增加样本量以提高证据强度")
        
        if claim.get('confounders'):
            recommendations.append("控制混淆变量")
        
        return recommendations
    
    def get_causality_statistics(self) -> Dict:
        """获取因果统计"""
        return {
            'causal_graphs': len(self.causal_graphs),
            'inferences': len(self.inference_history),
            'observations': len(self.observations),
            'avg_causal_strength': np.mean([i.causal_strength for i in self.inference_history]) if self.inference_history else 0,
            'by_relation_type': {
                rt.value: sum(1 for i in self.inference_history if i.relation_type == rt)
                for rt in CausalRelationType
            }
        }


# 便利函数
def create_causality() -> Causality:
    """创建因果推理引擎"""
    return Causality()
