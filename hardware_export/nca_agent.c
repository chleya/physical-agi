/**
 * NCA Agent Implementation for ESP32
 * Auto-generated from evolution simulator
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "nca_params_evo_agent.h"

// Forward declaration
void nca_forward(float input[NCA_INPUT_SIZE], float output[NCA_OUTPUT_SIZE]);
void nca_act(float input[NCA_INPUT_SIZE], float *dx, float *dy);

// Memory buffer for operations
static float hidden[NCA_HIDDEN_SIZE];
static float output_buf[NCA_OUTPUT_SIZE];

/**
 * Forward pass through the network
 */
void nca_forward(float input[NCA_INPUT_SIZE], float output[NCA_OUTPUT_SIZE]) {
    // Layer 1: input -> hidden with tanh activation
    for (int j = 0; j < NCA_HIDDEN_SIZE; j++) {
        float sum = b1[j];
        for (int i = 0; i < NCA_INPUT_SIZE; i++) {
            sum += input[i] * w1[i][j];
        }
        hidden[j] = tanhf(sum);  // tanh activation
    }
    
    // Layer 2: hidden -> output with tanh activation
    for (int j = 0; j < NCA_OUTPUT_SIZE; j++) {
        float sum = b2[j];
        for (int i = 0; i < NCA_HIDDEN_SIZE; i++) {
            sum += hidden[i] * w2[i][j];
        }
        output_buf[j] = tanhf(sum);
    }
    
    // Copy to output
    for (int i = 0; i < NCA_OUTPUT_SIZE; i++) {
        output[i] = output_buf[i];
    }
}

/**
 * Get action from perception
 * Maps network output to motor commands
 */
void nca_act(float input[NCA_INPUT_SIZE], float *dx, float *float) {
    float output[NCA_OUTPUT_SIZE];
    nca_forward(input, output);
    
    // Add noise for exploration (decays over time)
    float noise_scale = default_config.noise * expf(-default_config.noise * 0.01f);
    
    *dx = output[0] * default_config.speed + ((float)rand() / RAND_MAX - 0.5f) * noise_scale;
    *dy = output[1] * default_config.speed + ((float)rand() / RAND_MAX - 0.5f) * noise_scale;
    
    // Clamp to max speed
    float max_speed = default_config.speed;
    float magnitude = sqrtf(*dx * *dx + *dy * *dy);
    if (magnitude > max_speed) {
        *dx = *dx / magnitude * max_speed;
        *dy = *dy / magnitude * max_speed;
    }
}

/**
 * RSSI-based communication
 * Returns signal strength based on distance
 */
float nca_rssi(float distance, float max_distance) {
    if (distance > max_distance) return 0.0f;
    return 1.0f - (distance / max_distance);
}

/**
 * Get neighbor count within range
 */
int nca_get_neighbor_count(float distances[], int max_neighbors, float range_threshold) {
    int count = 0;
    for (int i = 0; i < max_neighbors; i++) {
        if (distances[i] < range_threshold) {
            count++;
        }
    }
    return count;
}

/**
 * Initialize agent
 */
void nca_init() {
    srand(esp_random());
}

#ifndef NCA_IMPLEMENTATION

// Include implementation when requested
#define NCA_IMPLEMENTATION
#include "nca_agent.c"

#endif

#endif // NCA_AGENT_EVO_AGENT_C
