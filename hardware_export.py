"""
硬件参数导出模块
将演化训练的NCA参数导出为ESP32可用的C代码
"""

import sys
import os
import json
import numpy as np
from typing import Dict, List, Tuple, Any


class HardwareExporter:
    """
    硬件参数导出器
    
    将模拟器中的演化结果转换为ESP32固件可用的格式
    """
    
    def __init__(self):
        self.params = {}
        self.network_weights = {}
        self.config = {}
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict:
        """
        加载检查点
        """
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
        
        self.config = checkpoint.get('config', {})
        
        # 提取最佳智能体的网络参数
        agents = checkpoint.get('agents', {})
        best_agent = None
        best_fitness = -float('inf')
        
        for aid, data in agents.items():
            if data.get('fitness', 0) > best_fitness:
                best_fitness = data.get('fitness', 0)
                best_agent = aid
        
        if best_agent:
            self.network_weights = {
                'w1': np.array(agents[best_agent]['network_w1']),
                'w2': np.array(agents[best_agent]['network_w2']),
                'fitness': best_fitness
            }
            print(f"Best agent: {best_agent}, Fitness: {best_fitness:.3f}")
        
        return checkpoint
    
    def export_esp32_header(self, output_path: str, agent_name: str = "evo_agent"):
        """
        导出ESP32头文件
        """
        if not self.network_weights:
            print("No weights to export!")
            return
        
        w1 = self.network_weights['w1']
        w2 = self.network_weights['w2']
        
        # 生成C头文件内容
        content = f'''/**
 * NCA Agent Parameters
 * Auto-generated from evolution simulator
 * 
 * Agent: {agent_name}
 * Fitness: {self.network_weights.get('fitness', 0):.3f}
 * Architecture: {w1.shape[0]} -> {w1.shape[1]} -> {w2.shape[1]}
 */

#ifndef NCA_PARAMS_{agent_name.upper()}_H
#define NCA_PARAMS_{agent_name.upper()}_H

#include <stdint.h>

// Network Architecture
#define NCA_INPUT_SIZE     {w1.shape[0]}
#define NCA_HIDDEN_SIZE    {w1.shape[1]}
#define NCA_OUTPUT_SIZE    {w2.shape[1]}

// Network Parameters - Layer 1: {w1.shape[0]} x {w1.shape[1]}
static const float w1[NCA_INPUT_SIZE][NCA_HIDDEN_SIZE] = {{
'''
        
        # 添加w1参数
        for i in range(w1.shape[0]):
            row = ", ".join([f"{val:+.6f}" for val in w1[i]])
            content += f"    {{{row}}}"
            if i < w1.shape[0] - 1:
                content += ","
            content += "\n"
        
        content += f'''}};

// Layer 1 Bias
static const float b1[NCA_HIDDEN_SIZE] = {{
    {", ".join([f"{val:+.6f}" for val in self.network_weights.get('b1', np.zeros(w1.shape[1]))])}
}};

// Network Parameters - Layer 2: {w2.shape[0]} x {w2.shape[1]}
static const float w2[NCA_HIDDEN_SIZE][NCA_OUTPUT_SIZE] = {{
'''
        
        # 添加w2参数
        for i in range(w2.shape[0]):
            row = ", ".join([f"{val:+.6f}" for val in w2[i]])
            content += f"    {{{row}}}"
            if i < w2.shape[0] - 1:
                content += ","
            content += "\n"
        
        content += f'''}};

// Layer 2 Bias
static const float b2[NCA_OUTPUT_SIZE] = {{
    {", ".join([f"{val:+.6f}" for val in self.network_weights.get('b2', np.zeros(w2.shape[1]))])}
}};

// Agent Configuration
typedef struct {{
    float lr;           // Learning rate: 0.001
    float noise;        // Noise scale: 0.1
    float friction;     // Motor friction: 0.3
    float speed;        // Max speed: 5.0
}} nca_config_t;

static const nca_config_t default_config = {{
    .lr = 0.001f,
    .noise = 0.1f,
    .friction = 0.3f,
    .speed = 5.0f
}};

#endif // NCA_PARAMS_{agent_name.upper()}_H
'''
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"ESP32 header exported: {output_path}")
    
    def export_esp32_c_code(self, output_path: str, agent_name: str = "evo_agent"):
        """
        导出ESP32 C实现代码
        """
        content = f'''/**
 * NCA Agent Implementation for ESP32
 * Auto-generated from evolution simulator
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "nca_params_{agent_name}.h"

// Forward declaration
void nca_forward(float input[NCA_INPUT_SIZE], float output[NCA_OUTPUT_SIZE]);
void nca_act(float input[NCA_INPUT_SIZE], float *dx, float *dy);

// Memory buffer for operations
static float hidden[NCA_HIDDEN_SIZE];
static float output_buf[NCA_OUTPUT_SIZE];

/**
 * Forward pass through the network
 */
void nca_forward(float input[NCA_INPUT_SIZE], float output[NCA_OUTPUT_SIZE]) {{
    // Layer 1: input -> hidden with tanh activation
    for (int j = 0; j < NCA_HIDDEN_SIZE; j++) {{
        float sum = b1[j];
        for (int i = 0; i < NCA_INPUT_SIZE; i++) {{
            sum += input[i] * w1[i][j];
        }}
        hidden[j] = tanhf(sum);  // tanh activation
    }}
    
    // Layer 2: hidden -> output with tanh activation
    for (int j = 0; j < NCA_OUTPUT_SIZE; j++) {{
        float sum = b2[j];
        for (int i = 0; i < NCA_HIDDEN_SIZE; i++) {{
            sum += hidden[i] * w2[i][j];
        }}
        output_buf[j] = tanhf(sum);
    }}
    
    // Copy to output
    for (int i = 0; i < NCA_OUTPUT_SIZE; i++) {{
        output[i] = output_buf[i];
    }}
}}

/**
 * Get action from perception
 * Maps network output to motor commands
 */
void nca_act(float input[NCA_INPUT_SIZE], float *dx, float *float) {{
    float output[NCA_OUTPUT_SIZE];
    nca_forward(input, output);
    
    // Add noise for exploration (decays over time)
    float noise_scale = default_config.noise * expf(-default_config.noise * 0.01f);
    
    *dx = output[0] * default_config.speed + ((float)rand() / RAND_MAX - 0.5f) * noise_scale;
    *dy = output[1] * default_config.speed + ((float)rand() / RAND_MAX - 0.5f) * noise_scale;
    
    // Clamp to max speed
    float max_speed = default_config.speed;
    float magnitude = sqrtf(*dx * *dx + *dy * *dy);
    if (magnitude > max_speed) {{
        *dx = *dx / magnitude * max_speed;
        *dy = *dy / magnitude * max_speed;
    }}
}}

/**
 * RSSI-based communication
 * Returns signal strength based on distance
 */
float nca_rssi(float distance, float max_distance) {{
    if (distance > max_distance) return 0.0f;
    return 1.0f - (distance / max_distance);
}}

/**
 * Get neighbor count within range
 */
int nca_get_neighbor_count(float distances[], int max_neighbors, float range_threshold) {{
    int count = 0;
    for (int i = 0; i < max_neighbors; i++) {{
        if (distances[i] < range_threshold) {{
            count++;
        }}
    }}
    return count;
}}

/**
 * Initialize agent
 */
void nca_init() {{
    srand(esp_random());
}}

#ifndef NCA_IMPLEMENTATION

// Include implementation when requested
#define NCA_IMPLEMENTATION
#include "nca_agent.c"

#endif

#endif // NCA_AGENT_{agent_name.upper()}_C
'''
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"ESP32 C code exported: {output_path}")
    
    def export_platformio_config(self, output_path: str):
        """
        导出PlatformIO配置文件
        """
        content = '''; PlatformIO Configuration File
; Auto-generated for ESP32 evolution deployment

[env:esp32dev]
platform = espressif32
board = esp32dev
framework = espidf
monitor_speed = 115200
build_flags = 
    -DNCA_INPUT_SIZE=6
    -DNCA_HIDDEN_SIZE=32
    -DNCA_OUTPUT_SIZE=2
    -DUSE_HARDWARE_FPU

[env:nodemcu-32s]
platform = espressif32
board = nodemcu-32s
framework = espidf
monitor_speed = 115200

[platformio]
src_dir = .
include_dir = include
lib_dir = lib
'''
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"PlatformIO config exported: {output_path}")
    
    def export_arduino_sketch(self, output_path: str, agent_name: str = "evo_agent"):
        """
        导出Arduino草图（更简单的ESP32代码）
        """
        content = f'''/**
 * Edge Evolution Robot - ESP32 Sketch
 * Auto-generated from evolution simulator
 * 
 * Connects physical sensors to NCA network
 * Controls motors based on network output
 */

#include <Arduino.h>
#include <math.h>

// Network Parameters
#define INPUT_SIZE 6
#define HIDDEN_SIZE 32
#define OUTPUT_SIZE 2

// Motor Pins
#define LEFT_MOTOR_A 12
#define LEFT_MOTOR_B 13
#define RIGHT_MOTOR_A 14
#define RIGHT_MOTOR_B 15
#define LEFT_PWM 2
#define RIGHT_PWM 4

// Sensor Pins
#define TRIG_PIN 5
#define ECHO_PIN 18
#define LEFT_IR 35
#define RIGHT_IR 34

// WiFi / ESP-NOW
#include <WiFi.h>
#include <esp_now.h>

// Network weights (imported from params)
extern const float w1[INPUT_SIZE][HIDDEN_SIZE];
extern const float b1[HIDDEN_SIZE];
extern const float w2[HIDDEN_SIZE][OUTPUT_SIZE];
extern const float b2[OUTPUT_SIZE];

// Neural network state
float hidden[HIDDEN_SIZE];
float output[OUTPUT_SIZE];

// Agent state
float position_x = 0, position_y = 0;
float target_x = 0, target_y = 0;
int neighbor_count = 0;
float avg_rssi = 0;

// Configuration
const float MAX_SPEED = 5.0f;
const float NOISE_SCALE = 0.1f;
const float COMMUNICATION_RANGE = 10.0f;

/**
 * Initialize ESP-NOW for mesh communication
 */
void init_mesh() {{
    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) {{
        Serial.println("ESP-NOW init failed");
        return;
    }}
    Serial.println("ESP-NOW initialized");
}}

/**
 * Forward pass through NCA network
 */
void nca_forward(float input[INPUT_SIZE]) {{
    // Layer 1
    for (int j = 0; j < HIDDEN_SIZE; j++) {{
        float sum = b1[j];
        for (int i = 0; i < INPUT_SIZE; i++) {{
            sum += input[i] * w1[i][j];
        }}
        hidden[j] = tanhf(sum);
    }}
    
    // Layer 2
    for (int j = 0; j < OUTPUT_SIZE; j++) {{
        float sum = b2[j];
        for (int i = 0; i < HIDDEN_SIZE; i++) {{
            sum += hidden[i] * w2[i][j];
        }}
        output[j] = tanhf(sum);
    }}
}}

/**
 * Read ultrasonic distance sensor
 */
float read_distance() {{
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    
    long duration = pulseIn(ECHO_PIN, HIGH);
    return duration * 0.034 / 2;  // cm
}}

/**
 * Control motor speed
 */
void set_motor_speed(float left_speed, float right_speed) {{
    // Clamp to max
    left_speed = constrain(left_speed, -MAX_SPEED, MAX_SPEED);
    right_speed = constrain(right_speed, -MAX_SPEED, MAX_SPEED);
    
    // Set direction
    digitalWrite(LEFT_MOTOR_A, left_speed > 0);
    digitalWrite(LEFT_MOTOR_B, left_speed < 0);
    digitalWrite(RIGHT_MOTOR_A, right_speed > 0);
    digitalWrite(RIGHT_MOTOR_B, right_speed < 0);
    
    // Set PWM
    analogWrite(LEFT_PWM, abs(left_speed) * 51);  // 0-255 -> 0-5
    analogWrite(RIGHT_PWM, abs(right_speed) * 51);
}}

/**
 * Main control loop
 */
void control_loop() {{
    // Build perception input
    float perception[INPUT_SIZE] = {{
        position_x / 10.0f,    // Normalized position
        position_y / 10.0f,
        target_x / 10.0f,      // Normalized target
        target_y / 10.0f,
        neighbor_count / 10.0f,
        avg_rssi
    }};
    
    // Forward pass
    nca_forward(perception);
    
    // Add noise (for continued exploration)
    float dx = output[0] * MAX_SPEED + (random(100) / 100.0 - 0.5) * NOISE_SCALE;
    float dy = output[1] * MAX_SPEED + (random(100) / 100.0 - 0.5) * NOISE_SCALE;
    
    // Differential drive control
    float left_speed = dx - dy;
    float right_speed = dx + dy;
    
    set_motor_speed(left_speed, right_speed);
}}

/**
 * ESP-NOW receive callback
 */
void on_receive(const uint8_t *mac_addr, const uint8_t *data, int len) {{
    // Extract neighbor info
    // Format: [neighbor_id, rssi, position_x, position_y]
    if (len >= 4) {{
        neighbor_count = data[0];
        avg_rssi = data[1] / 255.0f;
    }}
}}

/**
 * Setup
 */
void setup() {{
    Serial.begin(115200);
    
    // Initialize pins
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    pinMode(LEFT_MOTOR_A, OUTPUT);
    pinMode(LEFT_MOTOR_B, OUTPUT);
    pinMode(RIGHT_MOTOR_A, OUTPUT);
    pinMode(RIGHT_MOTOR_B, OUTPUT);
    
    // Initialize mesh
    init_mesh();
    esp_now_register_recv_cb(on_receive);
    
    Serial.println("Robot initialized");
}}

/**
 * Main loop - runs at ~60Hz
 */
void loop() {{
    // Read sensors
    float distance = read_distance();
    
    // Update position (simplified)
    position_x += output[0] * 0.016 * MAX_SPEED;
    position_y += output[1] * 0.016 * MAX_SPEED;
    
    // Control
    control_loop();
    
    // Send status to neighbors
    // esp_now_send(...)
    
    delay(16);  // ~60Hz
}}
'''
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"Arduino sketch exported: {output_path}")
    
    def export_test_suite(self, output_path: str):
        """
        导出测试套件
        """
        content = '''/**
 * Hardware-in-the-Loop Test Suite
 * Tests NCA network on ESP32
 */

#include <stdio.h>
#include <assert.h>
#include <math.h>
#include "nca_params.h"

// Test helper
#define EPSILON 0.001

void test_forward() {
    float input[INPUT_SIZE] = {0};
    float output[OUTPUT_SIZE] = {0};
    
    // Zero input should produce bounded output
    nca_forward(input, output);
    
    for (int i = 0; i < OUTPUT_SIZE; i++) {
        assert(output[i] >= -1.0 && output[i] <= 1.0);
    }
    
    printf("Forward pass test: PASSED\\n");
}

void test_activation() {
    // tanh should output in [-1, 1]
    float test_values[] = {-10, -1, 0, 1, 10};
    
    for (int i = 0; i < 5; i++) {
        float result = tanhf(test_values[i]);
        assert(result >= -1.0 && result <= 1.0);
    }
    
    printf("Activation test: PASSED\\n");
}

void test_rssi() {
    // RSSI should be in [0, 1]
    assert(nca_rssi(0, 10) == 1.0);
    assert(nca_rssi(5, 10) == 0.5);
    assert(nca_rssi(10, 10) == 0.0);
    assert(nca_rssi(15, 10) == 0.0);
    
    printf("RSSI test: PASSED\\n");
}

void test_motor_output() {
    float dx, dy;
    
    // Test bounds
    float input[INPUT_SIZE] = {0};
    nca_forward(input, output);
    nca_act(input, &dx, &dy);
    
    assert(dx >= -MAX_SPEED - 1 && dx <= MAX_SPEED + 1);
    assert(dy >= -MAX_SPEED - 1 && dy <= MAX_SPEED + 1);
    
    printf("Motor output test: PASSED\\n");
}

void run_tests() {
    printf("Running hardware tests...\\n");
    
    test_activation();
    test_forward();
    test_rssi();
    test_motor_output();
    
    printf("All tests PASSED!\\n");
}

void main() {
    nca_init();
    run_tests();
}
'''
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"Test suite exported: {output_path}")


def export_all(checkpoint_path: str, output_dir: str):
    """
    导出所有硬件文件
    """
    exporter = HardwareExporter()
    
    # 加载检查点
    exporter.load_checkpoint(checkpoint_path)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 导出所有文件
    exporter.export_esp32_header(f"{output_dir}/nca_params.h", "evo_agent")
    exporter.export_esp32_c_code(f"{output_dir}/nca_agent.c", "evo_agent")
    exporter.export_platformio_config(f"{output_dir}/platformio.ini")
    exporter.export_arduino_sketch(f"{output_dir}/robot_sketch.ino")
    exporter.export_test_suite(f"{output_dir}/test_hardware.c")
    
    print(f"\nAll files exported to: {output_dir}")
    
    return exporter


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        checkpoint = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "./hardware_export"
    else:
        checkpoint = "simulation_checkpoint.json"
        output = "./hardware_export"
    
    export_all(checkpoint, output)
