#include <avr/io.h>
#include "relays.h"
#include "gpio.h"

static uint8_t ignition_state = 0;
static uint8_t lights_state   = 0;

void Relays_Init(void) {
    GPIO_Init(GPIO_PORTC, PIN_IGNITION, GPIO_OUTPUT);
    GPIO_Init(GPIO_PORTC, PIN_LIGHTS,   GPIO_OUTPUT);

    GPIO_Write(GPIO_PORTC, PIN_IGNITION, GPIO_HIGH);
    GPIO_Write(GPIO_PORTC, PIN_LIGHTS,   GPIO_HIGH);
}

void Ignition_Set(uint8_t state) {
    ignition_state = state ? 1 : 0;
    GPIO_Write(GPIO_PORTC, PIN_IGNITION, ignition_state ? GPIO_LOW : GPIO_HIGH);
}

void Ignition_Toggle(void) {
    ignition_state = !ignition_state;
    GPIO_Write(GPIO_PORTC, PIN_IGNITION, ignition_state ? GPIO_LOW : GPIO_HIGH);
}

void Lights_Set(uint8_t state) {
    lights_state = state ? 1 : 0;
    GPIO_Write(GPIO_PORTC, PIN_LIGHTS, lights_state ? GPIO_LOW : GPIO_HIGH);
}

void Lights_Toggle(void) {
    lights_state = !lights_state;
    GPIO_Write(GPIO_PORTC, PIN_LIGHTS, lights_state ? GPIO_LOW : GPIO_HIGH);
}
