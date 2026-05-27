#ifndef COOLANT_H
#define COOLANT_H

#include <stdint.h>

#define PIN_COOLANT PD5 

void Coolant_Init(void);
void Coolant_SetTemp(uint8_t val);

#endif
