# Embedded Systems Course and Labs for students from Automation and Applied Informatics from Faculty of Automation, Computers and Electronics, University of Craiova

This repository is dedicated to the Embedded Systems course and labs for students from Automation and Applied Informatics from Faculty of Automation, Computers and Electronics, University of Craiova. 

If you are a student: please fork this repository and use it for your labs, homework and course. 

Found a bug or you just want to contribute to this project ? Please raise an issue and/or send a pull request.

[![Run Tests](https://github.com/mamuleanu/embedded-systems-course-atmega328p/actions/workflows/tests.yml/badge.svg)](https://github.com/mamuleanu/embedded-systems-course-atmega328p/actions/workflows/tests.yml)


## Features

- **No Arduino Libraries**: Direct register manipulation for maximum control and efficiency.
- **Drivers:**: Modular, documented, and reusable.
    - **GPIO**: Initialization, Write, Read, Toggle.
    - **Interrupts**: External Interrupts (INT0, INT1) with callback support.
    - **Timer**: 1ms System Tick (`Millis()`) using Timer0 CTC mode.
    - **EEPROM**: Read, Write, Update (lifespan-aware).
    - **ADC**: Blocking 10-bit Analog-to-Digital conversion.
    - **PWM**: High-level wrapper for Timer1 (16-bit) and Timer2 (8-bit) PWM generation.
- **Board Support Package (BSP)**: Pin mappings for **Arduino Nano** and **Uno**.
- **Robust Build System**: `Makefile` for compilation, flashing, and testing.
- **Host-Based Unit Testing**: Run unit tests on your computer without hardware using register mocking.
- **Code Coverage**: Generate HTML reports (`lcov`) to verify test coverage.

## Roadmap

- [x] GPIO driver
- [x] ADC driver
- [x] EEPROM driver
- [x] Interrupt driver
- [x] Timer driver
- [x] PWM driver
- [ ] I2C driver
- [ ] SPI driver
- [ ] UART driver
- [ ] Unit tests

## Project Structure

```
├── bsp/            # Board definitions (uno.h, nano.h)
├── drivers/        # Hardware Abstraction Layer
│   ├── adc/
│   ├── eeprom/
│   ├── gpio/
│   ├── interrupt/
│   └── timer/
├── src/            # Application source code (main.c)
├── test/           # Unit tests & Mocks
│   ├── mocks/      # Mock AVR registers for host testing
│   ├── framework/  # Minimal test runner
│   └── test_*.c    # Unit test files
├── utils/          # Helper macros (BIT manipulations)
└── Makefile        # Build configuration
```

## Build & Flash

### Prerequisites
- `avr-gcc` toolchain
- `avrdude`
- `make`

### Commands
| Command | Description |
|---------|-------------|
| `make all BOARD=nano` | Compile the project for Arduino Nano. |
| `make flash` | Flash the firmware to the connected board. |
| `make clean` | Remove build artifacts. |

## Testing & Coverage

This project supports running unit tests on your host machine (Mac/Linux) by mocking the AVR hardware registers.

### Prerequisites (for coverage)
- `gcc`
- `lcov` (`brew install lcov`)

### Commands
| Command | Description |
|---------|-------------|
| `make test` | Compile and run all unit tests (GPIO, PWM) on the host. |
| `make coverage` | Run tests and generate usage metrics. |
| `make coverage-html` | Generate a visual HTML report of code coverage. |

![Code Coverage Example](/img/code_coverage_example.png)

## Usage Example

```c
#include "drivers/gpio/gpio.h"
#include "drivers/timer/timer0.h"
#include "bsp/nano.h"

int main(void) {
    
    Timer0_Init();
    GPIO_Init(LED_BUILTIN, GPIO_OUTPUT);

    uint32_t last_time = 0;

    while (1) {
            
        if (Millis() - last_time >= 1000) {
            last_time = Millis();
            GPIO_Toggle(LED_BUILTIN);
        }
    }
}

// PWM Usage Example
#include "drivers/pwm/pwm.h"
#include "bsp/uno.h"

int pwm_example(void) {
    // 50Hz for Servo on D9
    PWM_Init(UNO_D9, 50);
    // 1.5ms pulse (approx neutral)
    // Duty cycle calculation: (1.5ms / 20ms) * ICR1_TOP
    // Wrapper takes 0-255: (1.5/20)*255 = ~19
    PWM_SetDutyCycle(UNO_D9, 19);

    // 1kHz LED Dimming on D11
    PWM_Init(UNO_D11, 1000);
    PWM_SetDutyCycle(UNO_D11, 128); // 50%
    
    return 0;
}
```

