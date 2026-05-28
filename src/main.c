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

int main(void) {
    USART_Init_Default();
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

    char buffer[MAX_SIZE_RECEIVE_USART];
    int n_speed, n_rpm;

    while (1) {
        int bytes = USART_Receive(buffer);

        if (bytes > 0) {
            char *start = strchr(buffer, '<');
            if (start != NULL) {
                start++;
                char *end = strchr(start, '>');
                if (end != NULL) {
                    *end = '\0';
                    if (sscanf(start, "%d,%d", &n_speed, &n_rpm) == 2) {
                        Set_Speed(n_speed);
                        Set_RPM(n_rpm);

                    }
                }
            }
        }
    }
}
