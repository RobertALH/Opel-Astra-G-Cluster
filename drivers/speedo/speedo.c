#include <avr/io.h>
#include <avr/interrupt.h>
#include "speedo.h"
#include "gpio.h" 

ISR(TIMER1_COMPA_vect) {
    GPIO_Toggle(GPIO_PORTB, PIN_SPEEDO);
}

void Speedo_Init(void) {
    GPIO_Init(GPIO_PORTB, PIN_SPEEDO, GPIO_OUTPUT);
    TCCR1A = (1 << WGM11) | (1 << WGM10);
    TCCR1B = (1 << WGM13) | (1 << WGM12); 
    TIMSK1 |= (1 << OCIE1A);
}

void Set_Speed(uint16_t kmh) {
    if (kmh < 5) {
        TCCR1B &= ~((1 << CS12) | (1 << CS11) | (1 << CS10)); 
        GPIO_Write(GPIO_PORTB, PIN_SPEEDO, GPIO_LOW);
        return;
    }
    uint16_t top = (242541UL / kmh) - 1;
    OCR1A = top; 
    TCCR1B |= (1 << CS11); 
}