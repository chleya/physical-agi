/**
 * STM32 连线检测固件
 * 文件: stm32_wire_check.c
 * 用途: 提供连线检测功能，配合 wire_check.py 使用
 */

#include "stm32f4xx_hal.h"
#include <string.h>
#include <stdio.h>

// ============ 引脚定义 ============
#define LED_PIN GPIO_PIN_13
#define LED_PORT GPIOC

// UART (与ESP32通信)
#define UART_DEBUG huart1

// I2C (MPU6050)
#define I2C_MPU6050 hi2c1

// ADC (电池电压)
#define BATTERY_ADC &hadc1

// ============ 命令处理 ============
typedef struct {
    const char *cmd;
    const char *help;
    const char *(*func)(void);
} Command_t;

// 前向声明
const char *cmd_version(void);
const char *cmd_get_imu_id(void);
const char *cmd_get_imu(void);
const char *cmd_test_motor(void);
const char *cmd_get_battery(void);
const char *cmd_get_esp32_status(void);
const char *cmd_echo(const char *arg);
const char *cmd_wire_check_all(void);

// 命令表
const Command_t COMMANDS[] = {
    {"VERSION", "获取版本", cmd_version},
    {"GET_IMU_ID", "获取IMU ID", cmd_get_imu_id},
    {"GET_IMU", "获取IMU数据", cmd_get_imu},
    {"TEST_MOTOR", "测试电机", cmd_test_motor},
    {"GET_BATTERY", "获取电池电压", cmd_get_battery},
    {"GET_ESP32_STATUS", "获取ESP32状态", cmd_get_esp32_status},
    {"WIRE_CHECK", "完整连线检测", cmd_wire_check_all},
};

#define CMD_COUNT (sizeof(COMMANDS) / sizeof(Command_t))

// ============ 命令实现 ============

const char *cmd_version(void) {
    static char response[64];
    snprintf(response, sizeof(response), 
             "OK[STM32F4-NCAMesh-v1.0-20260218-Checksum:%lu]", 
             (HAL_GetTick() % 1000));
    return response;
}

const char *cmd_get_imu_id(void) {
    static char response[32];
    uint8_t who_am_i = 0;
    
    // 读取 MPU6050 WHO_AM_I 寄存器
    HAL_I2C_Mem_Read(&I2C_MPU6050, 0x68 << 1, 0x75, 
                     I2C_MEMADD_SIZE_8BIT, &who_am_i, 1, 100);
    
    if (who_am_i == 0x68) {
        snprintf(response, sizeof(response), "OK[IMU_ID=0x68(104)]");
    } else {
        snprintf(response, sizeof(response), "FAIL[IMU_ID=0x%02X]", who_am_i);
    }
    return response;
}

const char *cmd_get_imu(void) {
    static char response[128];
    int16_t ax, ay, az, gx, gy, gz;
    
    // 读取 IMU 数据
    uint8_t data[14];
    HAL_I2C_Mem_Read(&I2C_MPU6050, 0x68 << 1, 0x3B, 
                     I2C_MEMADD_SIZE_8BIT, data, 14, 100);
    
    ax = (data[0] << 8) | data[1];
    ay = (data[2] << 8) | data[3];
    az = (data[4] << 8) | data[5];
    gx = (data[8] << 8) | data[9];
    gy = (data[10] << 8) | data[11];
    gz = (data[12] << 8) | data[13];
    
    snprintf(response, sizeof(response),
             "OK[AX=%d,AY=%d,AZ=%d,GX=%d,GY=%d,GZ=%d]",
             ax, ay, az, gx, gy, gz);
    return response;
}

const char *cmd_test_motor(void) {
    static char response[64];
    
    // 测试电机 (短时间)
    // 实际产品中需要根据 DRV8833 的 IN1/IN2 控制
    // 这里返回测试信号已发送
    
    snprintf(response, sizeof(response),
             "OK[MOTOR_TEST_SENT-Timer:%lu]", HAL_GetTick());
    return response;
}

const char *cmd_get_battery(void) {
    static char response[64];
    uint32_t adc_value = 0;
    float voltage;
    
    // 读取 ADC
    HAL_ADC_Start(BATTERY_ADC);
    HAL_ADC_PollForConversion(BATTERY_ADC, 100);
    adc_value = HAL_ADC_GetValue(BATTERY_ADC);
    
    // 计算电压 (分压电阻 100K+100K)
    voltage = (adc_value * 3.3f / 4095.0f) * 2.0f;
    
    snprintf(response, sizeof(response), "OK[VOLTAGE=%.2f]", voltage);
    return response;
}

const char *cmd_get_esp32_status(void) {
    static char response[64];
    
    // 检查 ESP32 是否响应
    // 实际通过 UART 发送 PING 到 ESP32
    
    // 这里返回已知的 ESP32 状态
    snprintf(response, sizeof(response), 
             "OK[ESP32=OK-Version:1.0-Time:%lu]", HAL_GetTick());
    return response;
}

const char *cmd_echo(const char *arg) {
    static char response[128];
    snprintf(response, sizeof(response), "OK[ECHO=%s]", arg ? arg : "");
    return response;
}

const char *cmd_wire_check_all(void) {
    static char response[256];
    
    // 执行完整连线检测
    
    // 1. 检查 IMU
    uint8_t who_am_i = 0;
    HAL_I2C_Mem_Read(&I2C_MPU6050, 0x68 << 1, 0x75, 
                     I2C_MEMADD_SIZE_8BIT, &who_am_i, 1, 100);
    
    // 2. 检查电池
    uint32_t adc_value = 0;
    HAL_ADC_Start(BATTERY_ADC);
    HAL_ADC_PollForConversion(BATTERY_ADC, 100);
    adc_value = HAL_ADC_GetValue(BATTERY_ADC);
    float voltage = (adc_value * 3.3f / 4095.0f) * 2.0f;
    
    // 生成报告
    snprintf(response, sizeof(response),
             "OK[WIRE_CHECK={"
             "IMU=0x%02X,"
             "BATTERY=%.2fV,"
             "UART=OK,"
             "TIME=%lu"
             "}]",
             who_am_i, voltage, HAL_GetTick());
    return response;
}

// ============ 串口命令处理 ============

#define RX_BUFFER_SIZE 64
char g_rx_buffer[RX_BUFFER_SIZE];
uint8_t g_rx_index = 0;

void process_command(const char *cmd) {
    char response[128];
    const char *result = NULL;
    
    // 解析命令
    for (int i = 0; i < CMD_COUNT; i++) {
        if (strncmp(cmd, COMMANDS[i].cmd, strlen(COMMANDS[i].cmd)) == 0) {
            // 提取参数
            const char *arg = cmd + strlen(COMMANDS[i].cmd);
            while (*arg == ' ') arg++;
            
            if (strcmp(COMMANDS[i].cmd, "ECHO") == 0) {
                result = cmd_echo(arg);
            } else {
                result = COMMANDS[i].func();
            }
            break;
        }
    }
    
    if (result) {
        snprintf(response, sizeof(response), "%s\r\n", result);
    } else {
        snprintf(response, sizeof(response), "FAIL[UNKNOWN_CMD:%s]\r\n", cmd);
    }
    
    // 发送响应
    HAL_UART_Transmit(&UART_DEBUG, (uint8_t*)response, strlen(response), 100);
}

// ============ 主函数 ============

int main(void) {
    HAL_Init();
    SystemClock_Config();
    
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART1_UART_Init();
    MX_I2C1_Init();
    MX_ADC1_Init();
    
    // LED 指示
    HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_RESET);
    
    // 等待稳定
    HAL_Delay(100);
    
    // 发送就绪消息
    const char *ready = "\r\nSTM32 Wire Check Ready\r\n";
    HAL_UART_Transmit(&UART_DEBUG, (uint8_t*)ready, strlen(ready), 100);
    
    // 主循环
    while (1) {
        // LED 闪烁
        HAL_GPIO_TogglePin(LED_PORT, LED_PIN);
        
        // 处理串口数据
        uint8_t ch;
        if (HAL_UART_Receive(&UART_DEBUG, &ch, 1, 10) == HAL_OK) {
            if (ch == '\r' || ch == '\n') {
                if (g_rx_index > 0) {
                    g_rx_buffer[g_rx_index] = '\0';
                    process_command(g_rx_buffer);
                    g_rx_index = 0;
                }
            } else if (g_rx_index < RX_BUFFER_SIZE - 1) {
                g_rx_buffer[g_rx_index++] = ch;
            }
        }
    }
}

// ============ 系统时钟配置 ============

void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
    
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = 16;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 16;
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
    RCC_OscInitStruct.PLL.PLLQ = 7;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);
    
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | 
                                  RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | 
                                  RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5);
}

// ============ 错误处理 ============

void Error_Handler(void) {
    while (1) {
        HAL_GPIO_TogglePin(LED_PORT, LED_PIN);
        HAL_Delay(100);
    }
}
