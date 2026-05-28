#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdio.h>
#include <string.h>
#include <delay.h>
#include <gpio.h>
#include <speedo.h>
#include <tacho.h>
#include <coolant.h>
#include <relays.h>
#include <usart.h>

void Dashboard_Sweep(void) {
    const uint32_t max_rpm   = 7000;
    const uint32_t max_speed = 240;
    const uint32_t steps     = 30;
    const uint8_t  step_delay = 10;

    for (uint32_t i = 0; i <= steps; i++) {
        Set_RPM((max_rpm * i) / steps);
        Set_Speed((max_speed * i) / steps);
        Delay(step_delay);
    }

    Delay(100);

    for (int32_t i = steps; i >= 0; i--) {
        Set_RPM((max_rpm * i) / steps);
        Set_Speed((max_speed * i) / steps);
        Delay(step_delay);
    }

    Set_RPM(0);
    Set_Speed(0);
}

int main(void) {
    USART_Init_Default();
    Speedo_Init();
    Tacho_Init();
    Coolant_Init();
    Relays_Init();

    sei();

    char buffer[MAX_SIZE_RECEIVE_USART];

    int n_speed, n_rpm, n_temp, n_ign, n_lights;
    int current_speed  = -1, current_rpm    = -1;
    int current_temp   = -1;
    int current_ign    = -1, current_lights = -1;

    while (1) {
        int bytes = USART_Receive(buffer);

        if (bytes > 0) {
            char *start = strchr(buffer, '<');
            if (start != NULL) {
                start++;
                char *end = strchr(start, '>');
                if (end != NULL) {
                    *end = '\0';
                    if (sscanf(start, "%d,%d,%d,%d,%d",
                               &n_speed, &n_rpm, &n_temp,
                               &n_ign, &n_lights) == 5) {

                        if (n_ign != current_ign) {
                            Ignition_Set(n_ign);
                            if (n_ign == 1) {
                                Delay(150);
                                Dashboard_Sweep();
                            } else {
                                Set_RPM(0);
                                Set_Speed(0);
                                Coolant_SetTemp(0);
                            }
                            current_ign = n_ign;
                        }

                        if (n_lights != current_lights) {
                            Lights_Set(n_lights);
                            current_lights = n_lights;
                        }

                        if (n_speed != current_speed) { Set_Speed(n_speed);      current_speed = n_speed; }
                        if (n_rpm   != current_rpm)   { Set_RPM(n_rpm);          current_rpm   = n_rpm;   }
                        if (n_temp  != current_temp)  { Coolant_SetTemp(n_temp); current_temp  = n_temp;  }

                    }
                }
            }
        }
    }
}
