#ifndef RELAYS_H
#define RELAYS_H

#include <stdint.h>

#define PIN_IGNITION PC0
#define PIN_LIGHTS   PC1

/**
 * @brief
 *        Releele sunt active pe LOW.
 */
void Relays_Init(void);

/**
 * @brief
 * @param state  1 = pornit (releu închis), 0 = oprit (releu deschis)
 */
void Ignition_Set(uint8_t state);

/**
 * @brief
 */
void Ignition_Toggle(void);

/**
 * @brief
 * @param state  1 = pornit, 0 = oprit
 */
void Lights_Set(uint8_t state);

/**
 * @brief
 */
void Lights_Toggle(void);

#endif // RELAYS_H
