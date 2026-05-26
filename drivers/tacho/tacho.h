#ifndef TACHO_H
#define TACHO_H

#include <stdint.h>

#define PIN_TACHO PD3 

void Tacho_Init(void);
void Set_RPM(uint16_t rpm);

#endif