#ifndef COOLANT_H
#define COOLANT_H

#include <stdint.h>

#define PIN_COOLANT 5 // PORTD 5 (D5)

void Coolant_Init(void);
void Coolant_SetTemp(uint8_t val);

#endif
