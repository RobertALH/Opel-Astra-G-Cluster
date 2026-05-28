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

static uint8_t Coolant_TempToPWM(uint8_t temp_c) {
    uint16_t ct;
    if (temp_c < 70)
        ct = ((uint16_t)temp_c * 23) / 70;
    else if (temp_c < 75)
        ct = 23 + ((uint16_t)(temp_c - 70) * 22) / 5;
    else if (temp_c <= 85)
        ct = 45 + ((uint16_t)(temp_c - 75) * 66) / 10;
    else if (temp_c <= 95)
        ct = 111 + ((uint16_t)(temp_c - 85) * 44) / 10;
    else
        ct = 155 + ((uint16_t)(temp_c - 95) * 100) / 15;

    if (ct > 255) ct = 255;
    return (uint8_t)(255 - ct);
}

void Coolant_SetTemp(uint8_t temp_c) {
    coolant_val = Coolant_TempToPWM(temp_c);
}
