#!/usr/bin/env python3
"""
数据分析器
==========
功能:
- CSV数据导入
- 自动绘图
- 统计摘要
- 对比分析
- 异常检测

使用:
    python data_analyzer.py logs/data.csv
    python data_analyzer.py logs/ --compare
    python data_analyzer.py --auto-plot
"""

import sys
import os
import argparse
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import csv


@dataclass
class AnalysisResult:
    """分析结果"""
    filename: str
    duration_s: float
    samples: int
    
    # IMU统计
    imu_stats: Dict
    
    # 电机统计
    motor_stats: Dict
    
    # 电池统计
    battery_stats: Dict
    
    # 异常
    anomalies: List[Dict]
    
    # 建议
    suggestions: List[str]


class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self, data_dir: str = "logs"):
        self.data_dir = Path(data_dir)
        self.data: Dict[str, List[Dict]] = {}
        self.results: List[AnalysisResult] = []
    
    def load_csv(self, filepath: str) -> List[Dict]:
        """加载CSV数据"""
        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 转换数值类型
                for k, v in row.items():
                    if k == 'timestamp':
                        continue
                    try:
                        row[k] = float(v)
                    except ValueError:
                        pass
                rows.append(row)
        return rows
    
    def load_dir(self, pattern: str = "*.csv") -> Dict[str, List[Dict]]:
        """加载目录内所有CSV"""
        files = list(self.data_dir.glob(pattern))
        self.data = {}
        
        for f in files:
            self.data[f.name] = self.load_csv(str(f))
        
        return self.data
    
    def analyze(self, name: str, rows: List[Dict]) -> AnalysisResult:
        """分析单个数据集"""
        if not rows:
            return None
        
        # 提取数据列
        timestamps = [float(r.get('timestamp', i) or i) for i, r in enumerate(rows)]
        
        imu_ax = [r.get('ax', 0) for r in rows if 'ax' in r]
        imu_ay = [r.get('ay', 0) for r in rows if 'ay' in r]
        imu_az = [r.get('az', 0) for r in rows if 'az' in r]
        
        motor_l = [r.get('motor_l', r.get('L', 0)) for r in rows]
        motor_r = [r.get('motor_r', r.get('R', 0)) for r in rows]
        
        battery = [r.get('battery_v', 0) for r in rows if 'battery_v' in r]
        rssi = [r.get('rssi', 0) for r in rows if 'rssi' in r]
        
        # 计算统计
        result = AnalysisResult(
            filename=name,
            duration_s=timestamps[-1] - timestamps[0] if timestamps else 0,
            samples=len(rows),
            
            imu_stats={
                'ax_mean': np.mean(imu_ax) if imu_ax else 0,
                'ax_std': np.std(imu_ax) if imu_ax else 0,
                'ax_min': np.min(imu_ax) if imu_ax else 0,
                'ax_max': np.max(imu_ax) if imu_ax else 0,
                'ay_mean': np.mean(imu_ay) if imu_ay else 0,
                'ay_std': np.std(imu_ay) if imu_ay else 0,
            },
            
            motor_stats={
                'left_mean': np.mean(motor_l) if motor_l else 0,
                'left_std': np.std(motor_l) if motor_l else 0,
                'left_min': np.min(motor_l) if motor_l else 0,
                'left_max': np.max(motor_l) if motor_l else 0,
                'right_mean': np.mean(motor_r) if motor_r else 0,
                'right_std': np.std(motor_r) if motor_r else 0,
            },
            
            battery_stats={
                'mean': np.mean(battery) if battery else 0,
                'min': np.min(battery) if battery else 0,
                'max': np.max(battery) if battery else 0,
                'drop': (np.max(battery) - np.min(battery)) if len(battery) > 1 else 0,
            },
            
            anomalies=[],
            suggestions=[]
        )
        
        # 异常检测
        result.anomalies = self._detect_anomalies(rows)
        
        # 生成建议
        result.suggestions = self._generate_suggestions(result)
        
        return result
    
    def _detect_anomalies(self, rows: List[Dict]) -> List[Dict]:
        """检测异常"""
        anomalies = []
        
        for i, row in enumerate(rows):
            # IMU异常
            ax = row.get('ax', 0)
            if abs(ax) > 20000:  # 加速度过大
                anomalies.append({
                    'type': 'imu_spike',
                    'timestamp': i,
                    'value': ax,
                    'severity': 'high' if abs(ax) > 30000 else 'medium'
                })
            
            # 电机卡死
            motor_l = row.get('motor_l', 0)
            if motor_l > 500 and abs(row.get('motor_r', 0)) < 10:
                anomalies.append({
                    'type': 'motor_stall',
                    'timestamp': i,
                    'value': motor_l,
                    'severity': 'high'
                })
            
            # 电池低压
            battery = row.get('battery_v', 0)
            if battery > 0 and battery < 3.3:
                anomalies.append({
                    'type': 'low_battery',
                    'timestamp': i,
                    'value': battery,
                    'severity': 'critical'
                })
        
        return anomalies
    
    def _generate_suggestions(self, result: AnalysisResult) -> List[str]:
        """生成建议"""
        suggestions = []
        
        # 电池建议
        if result.battery_stats['drop'] > 0.5:
            suggestions.append("电池下降较快，考虑降低功耗")
        
        # 电机建议
        if result.motor_stats['left_std'] > result.motor_stats['left_mean']:
            suggestions.append("左电机输出不稳定，检查机械结构")
        
        # RSSI建议
        rssi = [r for r in self.data.get(result.filename, []) if 'rssi' in r]
        if rssi:
            rssi_vals = [r['rssi'] for r in rssi]
            if np.mean(rssi_vals) < -70:
                suggestions.append("RSSI信号较弱，考虑调整天线或通信参数")
        
        return suggestions
    
    def print_report(self, result: AnalysisResult):
        """打印报告"""
        print(f"\n{'='*60}")
        print(f"分析报告: {result.filename}")
        print(f"{'='*60}")
        
        print(f"\n📊 基本信息:")
        print(f"   时长: {result.duration_s:.1f}s")
        print(f"   样本数: {result.samples}")
        
        print(f"\n📐 IMU统计:")
        print(f"   AX: mean={result.imu_stats['ax_mean']:.1f}, std={result.imu_stats['ax_std']:.1f}")
        print(f"   AY: mean={result.imu_stats['ay_mean']:.1f}, std={result.imu_stats['ay_std']:.1f}")
        
        print(f"\n⚙️ 电机统计:")
        print(f"   左: mean={result.motor_stats['left_mean']:.1f}, std={result.motor_stats['left_std']:.1f}")
        print(f"   右: mean={result.motor_stats['right_mean']:.1f}, std={result.motor_stats['right_std']:.1f}")
        
        print(f"\n🔋 电池统计:")
        print(f"   平均: {result.battery_stats['mean']:.2f}V")
        print(f"   范围: {result.battery_stats['min']:.2f}V ~ {result.battery_stats['max']:.2f}V")
        print(f"   下降: {result.battery_stats['drop']:.2f}V")
        
        if result.anomalies:
            print(f"\n⚠️ 异常 ({len(result.anomalies)}个):")
            for a in result.anomalies[:5]:  # 只显示前5个
                print(f"   [{a['severity']}] {a['type']} @ 样本{a['timestamp']}")
        
        if result.suggestions:
            print(f"\n💡 建议:")
            for s in result.suggestions:
                print(f"   • {s}")
        
        print()
    
    def compare(self, name1: str, name2: str) -> Dict:
        """对比两个数据集"""
        if name1 not in self.data or name2 not in self.data:
            return None
        
        r1 = self.analyze(name1, self.data[name1])
        r2 = self.analyze(name2, self.data[name2])
        
        comparison = {
            'duration_diff': r2.duration_s - r1.duration_s,
            'samples_diff': r2.samples - r1.samples,
            'motor_left_mean_diff': r2.motor_stats['left_mean'] - r1.motor_stats['left_mean'],
            'battery_drop_diff': r2.battery_stats['drop'] - r1.battery_stats['drop'],
            'anomalies_diff': len(r2.anomalies) - len(r1.anomalies),
        }
        
        return comparison
    
    def auto_plot(self, output_dir: str = "plots"):
        """自动生成图表"""
        try:
            import matplotlib.pyplot as plt
            
            Path(output_dir).mkdir(exist_ok=True)
            
            for name, rows in self.data.items():
                if len(rows) < 10:
                    continue
                
                # 提取数据
                timestamps = list(range(len(rows)))
                ax = [r.get('ax', 0) for r in rows]
                ay = [r.get('ay', 0) for r in rows]
                motor_l = [r.get('motor_l', r.get('L', 0)) for r in rows]
                battery = [r.get('battery_v', 0) for r in rows]
                
                # 创建图表
                fig, axes = plt.subplots(2, 2, figsize=(12, 8))
                fig.suptitle(f'数据分析: {name}')
                
                axes[0,0].plot(timestamps, ax, 'r-', label='AX')
                axes[0,0].plot(timestamps, ay, 'g-', label='AY')
                axes[0,0].set_title('IMU 加速度')
                axes[0,0].legend()
                axes[0,0].grid(True)
                
                axes[0,1].plot(timestamps, motor_l, 'b-', label='左电机')
                axes[0,1].set_title('电机速度')
                axes[0,1].legend()
                axes[0,1].grid(True)
                
                axes[1,0].plot(timestamps, battery, 'g-')
                axes[1,0].set_title('电池电压')
                axes[1,0].grid(True)
                
                # 统计摘要
                axes[1,1].axis('off')
                summary = f"""
基本统计
--------
样本数: {len(rows)}
时长: {timestamps[-1]}s

IMU AX
------
均值: {np.mean(ax):.2f}
标准差: {np.std(ax):.2f}

电机左
------
均值: {np.mean(motor_l):.2f}
标准差: {np.std(motor_l):.2f}
"""
                axes[1,1].text(0.1, 0.9, summary, transform=axes[1,1].transAxes,
                              fontsize=10, verticalalignment='top',
                              fontfamily='monospace')
                
                plt.tight_layout()
                
                # 保存
                output_path = Path(output_dir) / f"{name.replace('.csv', '')}.png"
                plt.savefig(output_path, dpi=100)
                plt.close()
                
                print(f"[INFO] 保存图表: {output_path}")
            
            print(f"[INFO] 所有图表已保存到: {output_dir}")
            
        except ImportError:
            print("[WARN] 请安装 matplotlib: pip install matplotlib")


# ============ 自动修正建议 ============
class CodeHotfixer:
    """代码热修复建议器"""
    
    @staticmethod
    def analyze_and_suggest(data_analyzer: DataAnalyzer) -> List[Dict]:
        """分析数据并给出代码修改建议"""
        suggestions = []
        
        for name, rows in data_analyzer.data.items():
            # 分析电机数据
            motor_l = [r.get('motor_l', 0) for r in rows]
            motor_r = [r.get('motor_r', 0) for r in rows]
            
            # 检测电机不平衡
            l_mean = np.mean(motor_l)
            r_mean = np.mean(motor_r)
            if abs(l_mean - r_mean) > 100:
                suggestions.append({
                    'file': 'stm32_motor_control.c',
                    'line': 123,
                    'issue': '电机输出不平衡',
                    'current': f'left={l_mean:.0f}, right={r_mean:.0f}',
                    'fix': '添加电机校准系数',
                    'code': '''
// 添加校准系数
#define MOTOR_LEFT_CALIB  1.05f
#define MOTOR_RIGHT_CALIB 0.95f

void set_motor_speed(int16_t left, int16_t right) {
    left_pwm = (int)(left * MOTOR_LEFT_CALIB);
    right_pwm = (int)(right * MOTOR_RIGHT_CALIB);
}
'''
                })
            
            # 检测IMU噪声
            ax = [r.get('ax', 0) for r in rows]
            if np.std(ax) > 5000:
                suggestions.append({
                    'file': 'imu_filter.c',
                    'line': 45,
                    'issue': 'IMU噪声过大',
                    'current': f'std={np.std(ax):.0f}',
                    'fix': '增加卡尔曼滤波',
                    'code': '''
// 添加卡尔曼滤波
kalman_t kalman_ax = {0, 1, 0.1, 0.1};

float filter_imu(float raw) {
    return kalman_update(&kalman_ax, raw);
}
'''
                })
            
            # 检测电池消耗
            battery = [r.get('battery_v', 0) for r in rows]
            if battery and battery[-1] < battery[0] - 0.3:
                suggestions.append({
                    'file': 'power_manager.c',
                    'line': 67,
                    'issue': '电池消耗过快',
                    'current': f'drop={battery[0]-battery[-1]:.2f}V',
                    'fix': '启用低功耗模式',
                    'code': '''
// 低功耗模式
#define LOW_POWER_THRESHOLD 3.6f

void check_battery() {
    if (voltage < LOW_POWER_THRESHOLD) {
        enter_low_power_mode();
    }
}
'''
                })
        
        return suggestions
    
    @staticmethod
    def print_suggestions(suggestions: List[Dict]):
        """打印修改建议"""
        if not suggestions:
            print("\n✅ 未发现问题，无需修改")
            return
        
        print(f"\n{'='*60}")
        print("🔧 代码修改建议")
        print(f"{'='*60}\n")
        
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. 📁 {s['file']} (行{s['line']})")
            print(f"   问题: {s['issue']}")
            print(f"   当前: {s['current']}")
            print(f"   建议: {s['fix']}")
            print(f"   代码:")
            for line in s['code'].strip().split('\n'):
                print(f"      {line}")
            print()


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(description="数据分析器")
    parser.add_argument('path', nargs='?', default='logs', help='CSV文件或目录')
    parser.add_argument('--compare', action='store_true', help='对比模式')
    parser.add_argument('--plot', action='store_true', help='生成图表')
    parser.add_argument('--hotfix', action='store_true', help='代码热修复建议')
    args = parser.parse_args()
    
    analyzer = DataAnalyzer()
    
    # 加载数据
    path = Path(args.path)
    if path.is_file() and path.suffix == '.csv':
        analyzer.data = {path.name: analyzer.load_csv(str(path))}
    elif path.is_dir():
        analyzer.load_dir()
    elif path.exists():
        analyzer.load_csv(str(path))
    else:
        print(f"[ERROR] 路径不存在: {path}")
        sys.exit(1)
    
    if not analyzer.data:
        print("[ERROR] 无有效数据")
        sys.exit(1)
    
    # 分析并报告
    for name, rows in analyzer.data.items():
        result = analyzer.analyze(name, rows)
        analyzer.print_report(result)
    
    # 对比
    if args.compare and len(analyzer.data) >= 2:
        names = list(analyzer.data.keys())
        comp = analyzer.compare(names[0], names[1])
        if comp:
            print(f"\n{'='*60}")
            print("对比分析")
            print(f"{'='*60}")
            for k, v in comp.items():
                print(f"   {k}: {v:+.2f}")
    
    # 绘图
    if args.plot:
        analyzer.auto_plot()
    
    # 热修复建议
    if args.hotfix:
        hotfixer = CodeHotfixer()
        suggestions = hotfixer.analyze_and_suggest(analyzer)
        hotfixer.print_suggestions(suggestions)


if __name__ == "__main__":
    main()
