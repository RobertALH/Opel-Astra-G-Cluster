"""
Simulator simplu pentru Opel Astra G Cluster
---------------------------------------------
W = creste viteza/turatia
S = scade viteza/turatia
Q = iesire

Protocol serial: <speed,rpm>\n
"""

import serial
import msvcrt
import time
import sys
import os

# ── Configurare ──────────────────────────────────────────────────────────────
PORT     = "COM4"
BAUD     = 57600

SPEED_STEP = 10     
RPM_STEP   = 200    
MAX_SPEED  = 240
MAX_RPM    = 7000
MIN_VAL    = 0
MIN_VAL_RPM = 800
# ─────────────────────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def display(speed, rpm, status=""):
    clear()
    print("=" * 40)
    print("  OPEL ASTRA G CLUSTER - SIMULATOR")
    print("=" * 40)
    print(f"  Viteza  : {speed:>4} km/h")
    print(f"  Turatie : {rpm:>5} RPM")
    print("-" * 40)
    print("  W = creste  |  S = scade  |  Q = iesire")
    print("=" * 40)
    if status:
        print(f"  {status}")

def send(ser, speed, rpm):
    msg = f"<{speed},{rpm}>\n"
    ser.write(msg.encode())
    ser.flush()

def main():
    speed = 0
    rpm   = 800

    print(f"Se conecteaza la {PORT} @ {BAUD}...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        time.sleep(2)  # Asteapta reset Arduino
    except serial.SerialException as e:
        print(f"\nERROR: Nu s-a putut deschide {PORT}: {e}")
        print("Verifica portul si incearca din nou.")
        input("\nApasa Enter pentru a iesi...")
        sys.exit(1)

    display(speed, rpm, f"Conectat pe {PORT}")

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8", errors="ignore").lower()

            if key == "q":
                send(ser, 0, 0)
                display(0, 0, "Deconectat.")
                time.sleep(0.5)
                ser.close()
                break

            elif key == "w":
                speed = min(speed + SPEED_STEP, MAX_SPEED)
                rpm   = min(rpm   + RPM_STEP,   MAX_RPM)
                send(ser, speed, rpm)
                display(speed, rpm)

            elif key == "s":
                speed = max(speed - SPEED_STEP, MIN_VAL)
                rpm   = max(rpm   - RPM_STEP,   MIN_VAL_RPM)
                send(ser, speed, rpm)
                display(speed, rpm)

        time.sleep(0.05)

if __name__ == "__main__":
    main()
