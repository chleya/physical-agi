#!/usr/bin/env python3
"""
AI 故障预测器
=============
功能:
- 时序数据分析
- 异常检测
- 故障预测
- 根因分析

使用:
    python ai_predictor.py --train data.csv
    python ai_predictor.py --predict realtime
"""

import numpy as np
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import pickle


@dataclass
class PredictionResult:
    """预测结果"""
    timestamp: str
    prediction: str  # 'normal', 'warning', 'critical'
    confidence: float
    probability: Dict[str, float]  # 各故障概率
    recommendation: str
    affected_systems: List[str]


class SimpleLSTM:
    """简化 LSTM 预测模型"""
    
    def __init__(self, input_size: int, hidden_size: int = 32):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.weights = np.random.randn(input_size, hidden_size) * 0.1
        self.hidden = np.zeros(hidden_size)
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """前向传播"""
        self.hidden = np.tanh(np.dot(x, self.weights))
        return self.hidden
    
    def predict(self, x: np.ndarray) -> np.ndarray:
        """预测"""
        return self.forward(x)


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, threshold: float = 2.5):
        self.threshold = threshold
        self.mean = 0
        self.std = 1
        self.samples = deque(maxlen=1000)
    
    def fit(self, data: np.ndarray):
        """拟合数据分布"""
        self.mean = np.mean(data)
        self.std = np.std(data)
        if self.std < 0.01:
            self.std = 0.01
    
    def is_anomaly(self, value: float) -> bool:
        """检测异常"""
        z_score = abs((value - self.mean) / self.std)
        return z_score > self.threshold
    
    def get_anomaly_score(self, value: float) -> float:
        """获取异常分数"""
        return abs((value - self.mean) / self.std)


class FaultPredictor:
    """故障预测器"""
    
    def __init__(self):
        self.models = {}
        self.detectors = {}
        self.history = deque(maxlen=10000)
        self.thresholds = {
            'motor_current': {'warning': 300, 'critical': 500},
            'battery_voltage': {'warning': 3.5, 'critical': 3.2},
            'motor_temp': {'warning': 50, 'critical': 70},
            'imu_noise': {'warning': 500, 'critical': 1000},
        }
    
    def add_model(self, name: str, model, detector: AnomalyDetector):
        """添加模型"""
        self.models[name] = model
        self.detectors[name] = detector
    
    def train(self, name: str, data: np.ndarray):
        """训练模型"""
        if name not in self.detectors:
            self.detectors[name] = AnomalyDetector()
        self.detectors[name].fit(data)
    
    def predict(self, data: Dict[str, float]) -> PredictionResult:
        """
        综合预测
        
        Args:
            data: 当前传感器数据
            
        Returns:
            预测结果
        """
        timestamp = datetime.now().isoformat()
        probabilities = {}
        affected = []
        max_prob = 0
        prediction = 'normal'
        
        # 分析各项指标
        for key, value in data.items():
            prob = self._analyze_metric(key, value)
            probabilities[key] = prob
            
            if prob > 0.3:
                affected.append(key)
            
            max_prob = max(max_prob, prob)
        
        # 综合判断
        if max_prob > 0.8:
            prediction = 'critical'
            recommendation = "立即停止运行，检查故障原因"
        elif max_prob > 0.5:
            prediction = 'warning'
            recommendation = "建议降低负载或更换电池"
        elif max_prob > 0.2:
            prediction = 'normal'
            recommendation = "继续观察，注意异常"
        else:
            prediction = 'normal'
            recommendation = "状态良好，无需干预"
        
        # 保存历史
        self.history.append({
            'timestamp': timestamp,
            'data': data,
            'prediction': prediction,
            'probabilities': probabilities
        })
        
        return PredictionResult(
            timestamp=timestamp,
            prediction=prediction,
            confidence=max_prob,
            probability=probabilities,
            recommendation=recommendation,
            affected_systems=affected
        )
    
    def _analyze_metric(self, key: str, value: float) -> float:
        """分析单个指标"""
        if key not in self.thresholds:
            return 0.0
        
        thresholds = self.thresholds[key]
        
        if 'current' in key.lower():
            # 电流分析
            if value > thresholds['critical']:
                return 0.9
            elif value > thresholds['warning']:
                return 0.6
            else:
                return 0.1
        
        elif 'voltage' in key.lower():
            # 电压分析
            if value < thresholds['critical']:
                return 0.9
            elif value < thresholds['warning']:
                return 0.6
            else:
                return 0.1
        
        elif 'temp' in key.lower():
            # 温度分析
            if value > thresholds['critical']:
                return 0.95
            elif value > thresholds['warning']:
                return 0.7
            else:
                return 0.05
        
        elif 'noise' in key.lower() or 'std' in key.lower():
            # 噪声分析
            if value > thresholds['critical']:
                return 0.85
            elif value > thresholds['warning']:
                return 0.5
            else:
                return 0.1
        
        return 0.0
    
    def analyze_root_cause(self, prediction: PredictionResult, 
                          historical_data: List[Dict]) -> Dict:
        """根因分析"""
        if prediction.prediction == 'normal':
            return {'result': 'no_issue', 'cause': None}
        
        # 分析历史数据找规律
        causes = []
        
        for item in historical_data[-100:]:  # 最近100条
            if item['prediction'] == prediction.prediction:
                # 检查共同特征
                for key, value in item['data'].items():
                    if key in prediction.affected_systems:
                        causes.append(key)
        
        # 统计最常见原因
        from collections import Counter
        cause_counts = Counter(causes)
        
        if cause_counts:
            most_common = cause_counts.most_common(3)
            return {
                'result': 'issue_detected',
                'primary_cause': most_common[0][0] if most_common else None,
                'contributing_factors': [c[0] for c in most_common],
                'confidence': prediction.confidence
            }
        
        return {
            'result': 'issue_detected',
            'primary_cause': prediction.affected_systems[0] if prediction.affected_systems else None,
            'contributing_factors': prediction.affected_systems,
            'confidence': prediction.confidence
        }
    
    def get_trend(self, metric: str, window: int = 100) -> Dict:
        """获取趋势"""
        values = []
        for item in self.history[-window:]:
            if metric in item['data']:
                values.append(item['data'][metric])
        
        if len(values) < 10:
            return {'trend': 'unknown', 'slope': 0, 'prediction': 'insufficient_data'}
        
        # 线性回归
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        # 趋势判断
        if slope > 0.1:
            trend = 'increasing'
            prediction = '可能会超过阈值'
        elif slope < -0.1:
            trend = 'decreasing'
            prediction = '在改善'
        else:
            trend = 'stable'
            prediction = '保持当前状态'
        
        return {
            'trend': trend,
            'slope': slope,
            'current': values[-1] if values else 0,
            'mean': np.mean(values) if values else 0,
            'std': np.std(values) if values else 0,
            'prediction': prediction
        }
    
    def save_model(self, path: str):
        """保存模型"""
        data = {
            'thresholds': self.thresholds,
            'detectors': {
                k: {'mean': v.mean, 'std': v.std, 'threshold': v.threshold}
                for k, v in self.detectors.items()
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[INFO] 模型已保存: {path}")
    
    def load_model(self, path: str):
        """加载模型"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.thresholds = data.get('thresholds', self.thresholds)
        for k, v in data.get('detectors', {}).items():
            detector = AnomalyDetector(threshold=v.get('threshold', 2.5))
            detector.mean = v.get('mean', 0)
            detector.std = v.get('std', 1)
            self.detectors[k] = detector
        
        print(f"[INFO] 模型已加载: {path}")


class RealtimePredictor:
    """实时预测器"""
    
    def __init__(self, predictor: FaultPredictor = None):
        self.predictor = predictor or FaultPredictor()
        self.data_buffer = deque(maxlen=100)
        self.running = False
    
    def feed(self, data: Dict[str, float]):
        """输入数据"""
        self.data_buffer.append(data)
    
    def predict_once(self) -> PredictionResult:
        """单次预测"""
        if not self.data_buffer:
            return None
        
        # 使用最近的数据
        data = self.data_buffer[-1]
        return self.predictor.predict(data)
    
    def start(self, interval: float = 1.0):
        """开始实时预测"""
        self.running = True
        # 这里可以连接串口或 MQTT 进行实时预测
    
    def stop(self):
        """停止"""
        self.running = False


def print_prediction(result: PredictionResult):
    """打印预测结果"""
    icons = {
        'normal': '✅',
        'warning': '⚠️',
        'critical': '🚨'
    }
    
    print(f"\n{icons.get(result.prediction, '❓')} 预测结果")
    print("="*40)
    print(f"时间: {result.timestamp}")
    print(f"状态: {result.prediction.upper()}")
    print(f"置信度: {result.confidence:.1%}")
    print(f"\n各指标概率:")
    for key, prob in result.probability.items():
        bar = '█' * int(prob * 10)
        print(f"  {key:15s}: {bar:10s} {prob:.1%}")
    
    if result.affected_systems:
        print(f"\n受影响系统: {', '.join(result.affected_systems)}")
    
    print(f"\n💡 建议: {result.recommendation}")


# ============ 主程序 ============

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI 故障预测器")
    parser.add_argument('--train', help='训练数据文件 (CSV)')
    parser.add_argument('--predict', choices=['realtime', 'once'], 
                       default='once', help='预测模式')
    parser.add_argument('--model', help='模型文件路径')
    parser.add_argument('--port', default='COM3', help='串口')
    args = parser.parse_args()
    
    print("="*50)
    print("  AI 故障预测器")
    print("="*50)
    
    # 创建预测器
    predictor = FaultPredictor()
    
    # 加载模型
    if args.model:
        predictor.load_model(args.model)
    
    # 训练
    if args.train:
        print(f"[INFO] 加载训练数据: {args.train}")
        # 模拟数据加载
        data = np.random.randn(1000) * 100 + 500
        predictor.train('motor_current', data)
        predictor.save_model('fault_predictor.json')
    
    # 预测模式
    if args.predict == 'once':
        # 模拟数据
        test_data = {
            'motor_current': np.random.uniform(200, 400),
            'battery_voltage': 3.7,
            'motor_temp': 45,
            'imu_noise': 300
        }
        print(f"\n测试数据: {test_data}")
        result = predictor.predict(test_data)
        print_prediction(result)
    
    elif args.predict == 'realtime':
        # 实时预测
        import serial
        print(f"\n[INFO] 连接串口: {args.port}")
        
        realtime = RealtimePredictor(predictor)
        realtime.start()
        
        try:
            with serial.Serial(args.port, 115200, timeout=1) as ser:
                print("[INFO] 开始实时预测... 按 Ctrl+C 停止")
                while True:
                    line = ser.readline().decode(errors='ignore').strip()
                    if line:
                        data = parse_adc_data(line)
                        if data:
                            realtime.feed(data)
                            result = realtime.predict_once()
                            if result and result.prediction != 'normal':
                                print_prediction(result)
        except KeyboardInterrupt:
            realtime.stop()
            print("\n已停止")


def parse_adc_data(data: str) -> dict:
    """解析ADC数据"""
    result = {}
    for part in data.split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            try:
                result[k.strip()] = float(v)
            except:
                pass
    return result


if __name__ == "__main__":
    main()
