#include <avr/io.h>
#include <avr/interrupt.h>
#include <delay.h>
#include <gpio.h>

#define PIN_SPEEDO PB1
#define PIN_TACHO  PD3
#define PIN_RELAY  PC0
#define PIN_LIGHTS PC1

ISR(TIMER1_COMPA_vect) {
    GPIO_Toggle(GPIO_PORTB, PIN_SPEEDO);
}

ISR(TIMER2_COMPA_vect) {
    GPIO_Toggle(GPIO_PORTD, PIN_TACHO);
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

void Tacho_Init(void) {
    GPIO_Init(GPIO_PORTD, PIN_TACHO, GPIO_OUTPUT);
    TCCR2A = (1 << WGM21);
    TCCR2B = 0;
    TIMSK2 &= ~(1 << OCIE2A); 
}

void Set_RPM(uint16_t rpm) {
    uint8_t top = (234375UL / rpm) - 1;
    OCR2A = top; 
    
    TCCR2B = (1 << CS22) | (1 << CS21) | (1 << CS20); 
    TIMSK2 |= (1 << OCIE2A); 
}

int main(void) {
    Speedo_Init();
    Tacho_Init();
    
    GPIO_Init(GPIO_PORTC, PIN_RELAY, GPIO_OUTPUT);
    GPIO_Write(GPIO_PORTC, PIN_RELAY, GPIO_HIGH);
    
    GPIO_Init(GPIO_PORTC, PIN_LIGHTS, GPIO_OUTPUT);
    GPIO_Write(GPIO_PORTC, PIN_LIGHTS, GPIO_HIGH);

    sei();

    Delay(1000);
    GPIO_Write(GPIO_PORTC, PIN_RELAY, GPIO_LOW);
    Delay(1000);
    GPIO_Write(GPIO_PORTC, PIN_LIGHTS, GPIO_LOW);
    Delay(1000);

    Set_RPM(3000);
    Set_Speed(100);
    Delay(5000);

    Set_RPM(6000); 
    Set_Speed(200);

    while (1) {
    }
}