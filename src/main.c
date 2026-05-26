#include <avr/io.h>
#include <avr/interrupt.h>
#include <delay.h>
#include <gpio.h>
#include <speedo.h>
#include <tacho.h>

#define PIN_SPEEDO PB1
#define PIN_TACHO  PD3
#define PIN_RELAY  PC0
#define PIN_LIGHTS PC1

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
    Delay(5000);

    Set_RPM(800); 
    Set_Speed(20); 

    while (1) {
   
    }
}