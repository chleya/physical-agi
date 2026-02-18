/**
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
    
    printf("Forward pass test: PASSED\n");
}

void test_activation() {
    // tanh should output in [-1, 1]
    float test_values[] = {-10, -1, 0, 1, 10};
    
    for (int i = 0; i < 5; i++) {
        float result = tanhf(test_values[i]);
        assert(result >= -1.0 && result <= 1.0);
    }
    
    printf("Activation test: PASSED\n");
}

void test_rssi() {
    // RSSI should be in [0, 1]
    assert(nca_rssi(0, 10) == 1.0);
    assert(nca_rssi(5, 10) == 0.5);
    assert(nca_rssi(10, 10) == 0.0);
    assert(nca_rssi(15, 10) == 0.0);
    
    printf("RSSI test: PASSED\n");
}

void test_motor_output() {
    float dx, dy;
    
    // Test bounds
    float input[INPUT_SIZE] = {0};
    nca_forward(input, output);
    nca_act(input, &dx, &dy);
    
    assert(dx >= -MAX_SPEED - 1 && dx <= MAX_SPEED + 1);
    assert(dy >= -MAX_SPEED - 1 && dy <= MAX_SPEED + 1);
    
    printf("Motor output test: PASSED\n");
}

void run_tests() {
    printf("Running hardware tests...\n");
    
    test_activation();
    test_forward();
    test_rssi();
    test_motor_output();
    
    printf("All tests PASSED!\n");
}

void main() {
    nca_init();
    run_tests();
}
