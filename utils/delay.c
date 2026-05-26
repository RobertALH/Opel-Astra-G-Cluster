#include "delay.h"
#include <avr/io.h>

// calibrated for 16MHz
// A rough estimate: 1ms = 16000 cycles
// Inner loop overhead + nop is approx 4 cycles (decrement, compare, branch, nop) => 4000 iterations
// However, C loop overhead adds up. 
// Let's start with a value and allow for tuning. 
// 16MHz / 1000ms = 16000 cycles per ms.
// A simple loop:
// for (volatile uint32_t i = 0; i < iterations; ++i) { asm volatile("nop"); }
// each iteration with volatile variable takes significant cycles.
// We will use a defined constant.

#define ITERATIONS_PER_MS 1000 // Initial guess, requires calibration or looking at disassembly

void Delay(uint32_t ms) {
    for (uint32_t i = 0; i < ms; i++) {
        for (volatile uint32_t j = 0; j < ITERATIONS_PER_MS; j++) {
            asm volatile("nop");
        }
    }
}
