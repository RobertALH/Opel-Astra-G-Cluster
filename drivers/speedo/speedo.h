#ifndef SPEEDO_H
#define SPEEDO_H

#include <stdint.h>

#define PIN_SPEEDO PB1 

void Speedo_Init(void);
void Set_Speed(uint16_t kmh);

#endif