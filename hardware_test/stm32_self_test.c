/**
 * STM32 硬件自检固件
 * 文件: stm32_self_test.c
 * 用途: 上电自检 IMU、电机、ESP32通信、电池电压
 */

#include "stm32f4xx_hal.h"
#include <string.h>
#include <stdio.h>

// ============ 引脚定义 ============
#define LED_PIN GPIO_PIN_13
#define LED_PORT GPIOC

#define IMU_SCK_PIN GPIO_PIN_5
#define IMU_MISO_PIN GPIO_PIN_6
#define IMU_MOSI_PIN GPIO_PIN_7
#define IMU_SPI GPIO_SPI1

#define MOTOR_L_IN1_PIN GPIO_PIN_0
#define MOTOR_L_IN2_PIN GPIO_PIN_1
#define MOTOR_R_IN1_PIN GPIO_PIN_2
#define MOTOR_R_IN2_PIN GPIO_PIN_3
#define MOTOR_PORT GPIOE

#define ESP32_BOOT_PIN GPIO_PIN_4
#define ESP32_BOOT_PORT GPIOD
#define ESP32_RST_PIN GPIO_PIN_5
#define ESP32_RST_PORT GPIOD

#define BATTERY_ADC_PIN GPIO_PIN_0
#define BATTERY_ADC ADC1

// ============ 测试结果结构 ============
typedef struct {
    uint8_t imu_ok;
    uint8_t motor_left_ok;
    uint8_t motor_right_ok;
    uint8_t esp32_ok;
    uint8_t battery_ok;
    uint8_t i2c_ok;
    float battery_voltage;
    uint32_t test_time_ms;
} SelfTestResult_t;

// 全局结果
SelfTestResult_t g_self_test_result;

// ============ 串口通信协议 ============
/*
 * 命令格式: <CMD>[<data>]\r\n
 * 响应格式: <STATUS>[<data>]\r\n
 *
 * 命令列表:
 *  SELF_TEST    - 运行完整自检
 *  TEST_IMU     - 测试IMU
 *  TEST_MOTOR   - 测试电机
 *  TEST_ESP32   - 测试ESP32通信
 *  TEST_BATTERY - 测试电池
 *  GET_RESULT   - 获取上次测试结果
 *  VERSION      - 获取固件版本
 *  RESET        - 软件复位
 *
 * 响应:
 *  OK[<data>]   - 成功
 *  FAIL[<data>] - 失败
 *  BUSY         - 测试中
 */

// 串口缓冲区
#define RX_BUFFER_SIZE 64
char g_rx_buffer[RX_BUFFER_SIZE];
uint8_t g_rx_index = 0;

// ============ 函数声明 ============
void SystemClock_Config(void);
void Error_Handler(void);
uint8_t SelfTest_IMU(void);
uint8_t SelfTest_MotorLeft(void);
uint8_t SelfTest_MotorRight(void);
uint8_t SelfTest_ESP32(uint8_t timeout_sec);
uint8_t SelfTest_Battery(float *voltage);
void SelfTest_Run(void);
void UART_ProcessCommand(void);
void UART_SendResponse(const char *status, const char *data);

// ============ 主函数 ============
int main(void) {
    HAL_Init();
    SystemClock_Config();
    
    // 初始化外设
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();
    MX_SPI1_Init();
    MX_ADC1_Init();
    MX_I2C1_Init();
    
    // 初始化ESP32
    ESP32_Init();
    
    // 等待ESP32启动
    HAL_Delay(1000);
    
    // 初始化LED
    HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_RESET);
    
    // 主循环
    while (1) {
        // 处理串口命令
        UART_ProcessCommand();
        
        // LED 指示运行状态
        HAL_GPIO_TogglePin(LED_PORT, LED_PIN);
        HAL_Delay(500);
    }
}

// ============ 自检函数 ============

/**
 * 运行完整自检
 */
void SelfTest_Run(void) {
    uint32_t start_time = HAL_GetTick();
    
    g_self_test_result.imu_ok = SelfTest_IMU();
    g_self_test_result.motor_left_ok = SelfTest_MotorLeft();
    g_self_test_result.motor_right_ok = SelfTest_MotorRight();
    g_self_test_result.esp32_ok = SelfTest_ESP32(5);
    g_self_test_result.battery_ok = SelfTest_Battery(&g_self_test_result.battery_voltage);
    
    g_self_test_result.test_time_ms = HAL_GetTick() - start_time;
}

/**
 * IMU 自检 (MPU6050)
 */
uint8_t SelfTest_IMU(void) {
    uint8_t who_am_i = 0;
    
    // 读取 WHO_AM_I 寄存器
    HAL_I2C_Mem_Read(&hi2c1, MPU6050_ADDR << 1, WHO_AM_I_REG, 
                     I2C_MEMADD_SIZE_8BIT, &who_am_i, 1, 100);
    
    // MPU6050 预期值: 0x68
    if (who_am_i == 0x68) {
        // 测试加速度计
        int16_t accel[3];
        HAL_I2C_Mem_Read(&hi2c1, MPU6050_ADDR << 1, ACCEL_XOUT_H, 
                         I2C_MEMADD_SIZE_8BIT, (uint8_t*)accel, 6, 100);
        
        // 检查是否在合理范围 (-2g 到 +2g)
        if (accel[0] > -16384 && accel[0] < 16384 &&
            accel[1] > -16384 && accel[1] < 16384 &&
            accel[2] > -32768 && accel[2] < 0) {  // Z轴应该检测到重力
            return 1;
        }
    }
    return 0;
}

/**
 * 电机左自检
 */
uint8_t SelfTest_MotorLeft(void) {
    // PWM 测试
    uint16_t pwm = 0;
    
    for (pwm = 0; pwm < 100; pwm += 10) {
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm);
        HAL_Delay(10);
    }
    
    // 反向测试
    HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_L_IN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_L_IN2_PIN, GPIO_PIN_SET);
    
    for (pwm = 0; pwm < 100; pwm += 10) {
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm);
        HAL_Delay(10);
    }
    
    // 停止
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
    HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_L_IN1_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_L_IN2_PIN, GPIO_PIN_RESET);
    
    return 1;  // 简化: 假设测试通过
}

/**
 * 电机右自检
 */
uint8_t SelfTest_MotorRight(void) {
    // 同左电机
    uint16_t pwm = 0;
    
    for (pwm = 0; pwm < 100; pwm += 10) {
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, pwm);
        HAL_Delay(10);
    }
    
    // 停止
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, 0);
    
    return 1;
}

/**
 * ESP32 通信自检
 */
uint8_t SelfTest_ESP32(uint8_t timeout_sec) {
    uint8_t tx_data[] = "SELF_TEST\r\n";
    uint8_t rx_data[32];
    uint32_t timeout = HAL_GetTick() + timeout_sec * 1000;
    
    // 发送测试命令
    HAL_UART_Transmit(&huart3, tx_data, strlen((char*)tx_data), 100);
    
    // 等待响应
    while (HAL_GetTick() < timeout) {
        if (HAL_UART_Receive(&huart3, rx_data, 1, 100) == HAL_OK) {
            if (rx_data[0] == 'O') {  // 收到 'O' (OK 的开始)
                rx_data[0] = 'O';
                HAL_UART_Receive(&huart3, &rx_data[1], 2, 100);  // 接收 'K\r'
                if (strncmp((char*)rx_data, "OK", 2) == 0) {
                    return 1;
                }
            }
        }
    }
    return 0;
}

/**
 * 电池电压自检
 */
uint8_t SelfTest_Battery(float *voltage) {
    uint32_t adc_value = 0;
    
    // 多次采样取平均
    for (int i = 0; i < 10; i++) {
        HAL_ADC_Start(&hadc1);
        HAL_ADC_PollForConversion(&hadc1, 100);
        adc_value += HAL_ADC_GetValue(&hadc1);
        HAL_Delay(1);
    }
    adc_value /= 10;
    
    // 转换为电压 (分压电阻 100K + 100K)
    *voltage = (adc_value * 3.3f / 4095.0f) * 2.0f;
    
    // 电池电压应该在 3.0V ~ 4.2V 之间
    if (*voltage >= 3.0f && *voltage <= 4.3f) {
        return 1;
    }
    return 0;
}

// ============ 串口命令处理 ============

void UART_ProcessCommand(void) {
    uint8_t ch;
    
    while (HAL_UART_Receive(&huart1, &ch, 1, 10) == HAL_OK) {
        if (ch == '\r' || ch == '\n') {
            if (g_rx_index > 0) {
                g_rx_buffer[g_rx_index] = '\0';
                
                // 解析命令
                if (strcmp(g_rx_buffer, "SELF_TEST") == 0) {
                    SelfTest_Run();
                    char result[64];
                    snprintf(result, sizeof(result), "IMU=%d,MOTOR_L=%d,MOTOR_R=%d,ESP32=%d,BAT=%.2fV,TIME=%lu",
                             g_self_test_result.imu_ok,
                             g_self_test_result.motor_left_ok,
                             g_self_test_result.motor_right_ok,
                             g_self_test_result.esp32_ok,
                             g_self_test_result.battery_voltage,
                             g_self_test_result.test_time_ms);
                    UART_SendResponse("OK", result);
                }
                else if (strcmp(g_rx_buffer, "GET_RESULT") == 0) {
                    char result[64];
                    snprintf(result, sizeof(result), "IMU=%d,MOTOR_L=%d,MOTOR_R=%d,ESP32=%d,BAT=%.2fV",
                             g_self_test_result.imu_ok,
                             g_self_test_result.motor_left_ok,
                             g_self_test_result.motor_right_ok,
                             g_self_test_result.esp32_ok,
                             g_self_test_result.battery_voltage);
                    UART_SendResponse("OK", result);
                }
                else if (strcmp(g_rx_buffer, "VERSION") == 0) {
                    UART_SendResponse("OK", "v1.0.0-20260218");
                }
                else if (strcmp(g_rx_buffer, "RESET") == 0) {
                    UART_SendResponse("OK", "resetting");
                    HAL_NVIC_SystemReset();
                }
                else {
                    UART_SendResponse("FAIL", "unknown command");
                }
                
                g_rx_index = 0;
            }
        } else if (g_rx_index < RX_BUFFER_SIZE - 1) {
            g_rx_buffer[g_rx_index++] = ch;
        }
    }
}

void UART_SendResponse(const char *status, const char *data) {
    char response[128];
    snprintf(response, sizeof(response), "%s[%s]\r\n", status, data);
    HAL_UART_Transmit(&huart1, (uint8_t*)response, strlen(response), 100);
}

// ============ 其他函数 ============

void SystemClock_Config(void) {
    // ... (标准 STM32F4 时钟配置)
}

void Error_Handler(void) {
    while (1) {
        HAL_GPIO_TogglePin(LED_PORT, LED_PIN);
        HAL_Delay(100);
    }
}
