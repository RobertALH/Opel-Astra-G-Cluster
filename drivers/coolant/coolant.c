#include <avr/io.h>
#include <avr/interrupt.h>
#include "coolant.h"
#include "gpio.h"

volatile uint8_t coolant_val = 0;
volatile uint8_t pwm_counter = 0;

ISR(TIMER0_OVF_vect) {
    pwm_counter++;

    if (pwm_counter < coolant_val) {
        GPIO_Write(GPIO_PORTD, PIN_COOLANT, GPIO_HIGH);
    } else {
        GPIO_Write(GPIO_PORTD, PIN_COOLANT, GPIO_LOW);
    }
}

void Coolant_Init(void) {
    GPIO_Init(GPIO_PORTD, PIN_COOLANT, GPIO_OUTPUT);
    TCCR0A = 0x00;
    TCCR0B = (1 << CS01);
    TIMSK0 |= (1 << TOIE0);
}

void Coolant_SetTemp(uint8_t val) {
    coolant_val = val;
}
