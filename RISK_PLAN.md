# 风险清单与备用方案

## 概述

本文档记录项目已知风险、备用方案（fallback）和应急计划。

---

## 硬件风险

### 1. ESP-NOW通信失效

| 项目 | 内容 |
|------|------|
| **风险等级** | 🔴 高 |
| **发生概率** | 中（30%） |
| **影响** | 无法实现多机协作 |

**征兆**:
- 设备配对失败
- 数据包丢失率 > 50%
- 通信延迟 > 100ms

**备用方案**: UART链式通信

```c
// UART通信协议 (fallback)
#define UART_BAUD_RATE 115200
#define UART_TX_PIN 17
#define UART_RX_PIN 16

// 数据包格式
typedef struct {
    uint8_t header;      // 0xAA
    uint8_t id;         // 设备ID
    int16_t position[2]; // 位置
    uint8_t checksum;    // 校验和
} uart_packet_t;

// 主循环
void uart_loop() {
    if (uart_available()) {
        uart_packet_t pkt = uart_read();
        if (checksum_valid(pkt)) {
            handle_message(pkt);
        }
    }
}
```

**恢复步骤**:
1. 检查GPIO配置
2. 验证UART引脚
3. 测试点对点通信
4. 逐步扩展到多机

---

### 2. 电机驱动失效

| 项目 | 内容 |
|------|------|
| **风险等级** | 🔴 高 |
| **发生概率** | 低（10%） |
| **影响** | 机器人无法移动 |

**征兆**:
- 电机不转
- 电机抖动
- 发热异常

**备用方案**: PWM直驱

```c
// PWM直驱 (fallback)
#define PWM_FREQ 20000
#define PWM_RESOLUTION 8

void pwm_drive(float left_speed, float right_speed) {
    // 左电机
    ledcWrite(LEFT_PWM_CHANNEL, (int)(abs(left_speed) * 255));
    digitalWrite(LEFT_IN1, left_speed > 0);
    digitalWrite(LEFT_IN2, left_speed < 0);
    
    // 右电机
    ledcWrite(RIGHT_PWM_CHANNEL, (int)(abs(right_speed) * 255));
    digitalWrite(RIGHT_IN1, right_speed > 0);
    digitalWrite(RIGHT_IN2, right_speed < 0);
}
```

**恢复步骤**:
1. 检查电源电压
2. 检查DRV8833过热保护
3. 验证PWM信号
4. 检查电机线圈

---

### 3. IMU数据异常

| 项目 | 内容 |
|------|------|
| **风险等级** | 🟡 中 |
| **发生概率** | 中（20%） |
| **影响** | 姿态估计错误 |

**征兆**:
- 角度跳变
- 静止时加速度非零
- 航向角漂移

**备用方案**: 简单卡尔曼滤波

```c
// 简单卡尔曼滤波 (fallback)
typedef struct {
    float x;      // 状态
    float p;      // 误差协方差
    float q;       // 过程噪声
    float r;       // 测量噪声
} kalman_t;

float kalman_update(kalman_t *k, float z) {
    // 预测
    k->p = k->p + k->q;
    
    // 更新
    float k_gain = k->p / (k->p + k->r);
    k->x = k->x + k_gain * (z - k->x);
    k->p = (1 - k_gain) * k->p;
    
    return k->x;
}
```

**恢复步骤**:
1. 检查I2C地址冲突
2. 校准IMU
3. 检查电源噪声
4. 降低采样率

---

### 4. 电池供电不足

| 项目 | 内容 |
|------|------|
| **风险等级** | 🟡 中 |
| **发生概率** | 中（30%） |
| **影响** | 系统重启/行为异常 |

**征兆**:
- ESP32频繁重启
- 电机无力
- LED闪烁

**备用方案**: 降级运行

```c
// 降级运行模式
typedef enum {
    MODE_FULL,      // 完整模式: NCA推理 + IMU + 通信
    MODE_SIMPLE,   // 简单模式: 随机行走
    MODE_SAFE      // 安全模式: 停止
} run_mode_t;

run_mode_t current_mode = MODE_FULL;

void check_battery() {
    float voltage = read_battery();
    if (voltage < 3.3) {
        current_mode = MODE_SAFE;
    } else if (voltage < 3.6) {
        current_mode = MODE_SIMPLE;
    } else {
        current_mode = MODE_FULL;
    }
}
```

---

## 软件风险

### 5. NCA推理溢出

| 项目 | 内容 |
|------|------|
| **风险等级** | 🟡 中 |
| **发生概率** | 低（5%） |
| **影响** | 行为异常/崩溃 |

**征兆**:
- 输出NaN
- 输出超出[-1, 1]
- 机器人行为异常

**备用方案**: 输出裁剪

```c
// 安全输出裁剪 (fallback)
float clip_output(float x, float min_val, float max_val) {
    if (isnan(x)) return 0.0f;
    if (x < min_val) return min_val;
    if (x > max_val) return max_val;
    return x;
}

// 使用
float output[2] = nca_forward(input);
output[0] = clip_output(output[0], -1.0f, 1.0f);
output[1] = clip_output(output[1], -1.0f, 1.0f);
```

---

### 6. 内存不足

| 项目 | 内容 |
|------|------|
| **风险等级** | 🟡 低 |
| **发生概率** | 低（10%） |
| **影响** | 系统崩溃 |

**征兆**:
- malloc返回NULL
- 程序崩溃

**备用方案**: 内存池

```c
// 固定内存池 (fallback)
#define POOL_SIZE 10
#define MSG_SIZE 64

typedef struct {
    uint8_t data[MSG_SIZE];
    uint8_t length;
} msg_t;

msg_t msg_pool[POOL_SIZE];
uint8_t msg_pool_used[POOL_SIZE] = {0};

msg_t* pool_alloc() {
    for (int i = 0; i < POOL_SIZE; i++) {
        if (!msg_pool_used[i]) {
            msg_pool_used[i] = 1;
            return &msg_pool[i];
        }
    }
    return NULL;  // 池已满
}

void pool_free(msg_t *msg) {
    for (int i = 0; i < POOL_SIZE; i++) {
        if (&msg_pool[i] == msg) {
            msg_pool_used[i] = 0;
            return;
        }
    }
}
```

---

## 项目风险

### 7. 仿真→硬件迁移失败

| 项目 | 内容 |
|------|------|
| **风险等级** | 🔴 高 |
| **发生概率** | 高（50%） |
| **影响** | 无法部署到硬件 |

**征兆**:
- 仿真适应度 > 100，实际 < 10
- 行为完全不一致

**备用方案**: 硬件在环训练

```python
# 硬件在环训练 (fallback)
def hardware_in_loop_training():
    """
    直接在硬件上训练
    """
    for generation in range(100):
        # 评估当前策略
        fitness = evaluate_on_robot()
        
        # 如果 fitness 低于阈值，变异
        if fitness < threshold:
            policy = policy.mutate(rate=0.2)
        
        # 保存最佳
        if fitness > best_fitness:
            save_checkpoint(policy)
```

---

## 应急联系

| 情况 | 联系人 | 备用 |
|------|--------|------|
| 硬件问题 | 硬件供应商 | DIY社区 |
| ESP32问题 | Espressif支持 | GitHub Issues |
| 算法问题 | 学术论文 | GitHub Discussions |

---

## 检查清单

### 部署前检查

- [ ] 电池电压 > 3.7V
- [ ] 电机连接正确
- [ ] IMU校准完成
- [ ] ESP-NOW配对成功
- [ ] 测试脚本通过
- [ ] 备份当前代码

### 运行时监控

- [ ] 电池电压
- [ ] 电机温度
- [ ] 通信延迟
- [ ] 帧率
- [ ] 错误计数

### 异常处理

- [ ] 电机停转 → 切换到安全模式
- [ ] 通信丢失 → 降级到UART
- [ ] 姿态异常 → 使用备份滤波
- [ ] 内存不足 → 清理缓存

---

## 恢复流程

### 完全崩溃恢复

1. **保存现场**
   ```
   git stash
   保存检查点
   ```

2. **诊断问题**
   ```
   运行冒烟测试
   检查日志
   ```

3. **恢复到已知状态**
   ```
   git checkout last_working
   ```

4. **逐步恢复**
   ```
   运行单元测试
   运行集成测试
   部署到硬件
   ```

---

最后更新: 2026-02-18
