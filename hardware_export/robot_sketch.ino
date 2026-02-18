/**
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
void init_mesh() {
    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) {
        Serial.println("ESP-NOW init failed");
        return;
    }
    Serial.println("ESP-NOW initialized");
}

/**
 * Forward pass through NCA network
 */
void nca_forward(float input[INPUT_SIZE]) {
    // Layer 1
    for (int j = 0; j < HIDDEN_SIZE; j++) {
        float sum = b1[j];
        for (int i = 0; i < INPUT_SIZE; i++) {
            sum += input[i] * w1[i][j];
        }
        hidden[j] = tanhf(sum);
    }
    
    // Layer 2
    for (int j = 0; j < OUTPUT_SIZE; j++) {
        float sum = b2[j];
        for (int i = 0; i < HIDDEN_SIZE; i++) {
            sum += hidden[i] * w2[i][j];
        }
        output[j] = tanhf(sum);
    }
}

/**
 * Read ultrasonic distance sensor
 */
float read_distance() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    
    long duration = pulseIn(ECHO_PIN, HIGH);
    return duration * 0.034 / 2;  // cm
}

/**
 * Control motor speed
 */
void set_motor_speed(float left_speed, float right_speed) {
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
}

/**
 * Main control loop
 */
void control_loop() {
    // Build perception input
    float perception[INPUT_SIZE] = {
        position_x / 10.0f,    // Normalized position
        position_y / 10.0f,
        target_x / 10.0f,      // Normalized target
        target_y / 10.0f,
        neighbor_count / 10.0f,
        avg_rssi
    };
    
    // Forward pass
    nca_forward(perception);
    
    // Add noise (for continued exploration)
    float dx = output[0] * MAX_SPEED + (random(100) / 100.0 - 0.5) * NOISE_SCALE;
    float dy = output[1] * MAX_SPEED + (random(100) / 100.0 - 0.5) * NOISE_SCALE;
    
    // Differential drive control
    float left_speed = dx - dy;
    float right_speed = dx + dy;
    
    set_motor_speed(left_speed, right_speed);
}

/**
 * ESP-NOW receive callback
 */
void on_receive(const uint8_t *mac_addr, const uint8_t *data, int len) {
    // Extract neighbor info
    // Format: [neighbor_id, rssi, position_x, position_y]
    if (len >= 4) {
        neighbor_count = data[0];
        avg_rssi = data[1] / 255.0f;
    }
}

/**
 * Setup
 */
void setup() {
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
}

/**
 * Main loop - runs at ~60Hz
 */
void loop() {
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
}
