#include <avr/io.h>
#include <avr/interrupt.h>
#include "tacho.h"
#include "gpio.h"

volatile uint8_t tacho_extend_limit = 1;

ISR(TIMER2_COMPA_vect) {
    static uint8_t extend = 0;
    extend++;
    if (extend >= tacho_extend_limit) {
        GPIO_Toggle(GPIO_PORTD, PIN_TACHO);
        extend = 0;
    }
}

void Tacho_Init(void) {
    GPIO_Init(GPIO_PORTD, PIN_TACHO, GPIO_OUTPUT);
    
    TCCR2A = (1 << WGM21); 
    TCCR2B = 0;
    TIMSK2 &= ~(1 << OCIE2A); 
}

void Set_RPM(uint16_t rpm) {
    if (rpm > 1000) {
        uint32_t corectie = ((uint32_t)rpm * rpm) / 144000UL;
        if (rpm > corectie) {
            rpm = rpm - corectie;
        }
    }

    if (rpm < 400) {
        TCCR2B = 0;               
        TIMSK2 &= ~(1 << OCIE2A); 
        GPIO_Write(GPIO_PORTD, PIN_TACHO, GPIO_LOW);
        return;
    }
    
    uint8_t temp_ext;
    uint32_t magic_precalc; 

    if (rpm >= 4900) {
        temp_ext = 3;
        magic_precalc = 1250000UL;
    } else if (rpm >= 3700) {
        temp_ext = 4;
        magic_precalc = 937500UL;
    } else if (rpm >= 2500) {
        temp_ext = 6;
        magic_precalc = 625000UL;
    } else if (rpm >= 1850) {
        temp_ext = 8;
        magic_precalc = 468750UL;
    } else if (rpm >= 1250) {
        temp_ext = 12;
        magic_precalc = 312500UL;
    } else if (rpm >= 950) {
        temp_ext = 16;
        magic_precalc = 234375UL;
    } else if (rpm >= 600) {
        temp_ext = 24;
        magic_precalc = 156250UL;
    } else {
        temp_ext = 32;
        magic_precalc = 117187UL;
    }

    uint8_t top = (magic_precalc / rpm) - 1;
    
    tacho_extend_limit = temp_ext;
    OCR2A = top; 
    TCCR2B = (1 << CS22); 
    TIMSK2 |= (1 << OCIE2A); 
}