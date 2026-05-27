#include <avr/io.h>
#include <avr/interrupt.h>
#include <delay.h>
#include <gpio.h>
#include <speedo.h>
#include <tacho.h>
#include <coolant.h>
#include <relays.h>

int main(void) {
    Speedo_Init();
    Tacho_Init();
    Coolant_Init();
    Relays_Init();

    sei();

    Delay(1000);
    Ignition_Set(1);
    Delay(1000);
    Lights_Set(1);
    Delay(1000);

    Set_RPM(3000);
    Set_Speed(100);
    Coolant_SetTemp(128);
    Delay(5000);

    Set_RPM(6000);
    Set_Speed(200);
    Coolant_SetTemp(128);
    Delay(5000);

    Set_RPM(800);
    Set_Speed(20);
    Coolant_SetTemp(128);

    while (1) {

    }
}
