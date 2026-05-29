# Opel Astra G — Cluster Digital pe Arduino Nano

Proiect de control al bordului original Opel Astra G (generația 1998–2008) folosind un **Arduino Nano (ATmega328P)**. Firmware-ul este scris în C pur, fără librării Arduino, cu control direct al registrelor AVR. Un simulator Python cu interfață grafică permite testarea completă fără mașină. De asemenea, aplicatiile de telemetrie vor functiona perfect.

---

## Cuprins

- [Descriere generală](#descriere-generală)
- [Pinout Arduino Nano](#pinout-arduino-nano)
- [Hardware — Conexiuni](#hardware--conexiuni)
- [Drivere](#drivere)
- [Protocol serial](#protocol-serial)
- [Simulator Python](#simulator-python)
- [Aplicatie telemetrie](#aplicatie-de-telemetrie-forza-horizon-6)
- [Build și Flash](#build-și-flash)
- [Structura proiectului](#structura-proiectului)

---

## Descriere generală

Bordul Opel Astra G folosește semnale analogice și impulsuri pentru a controla acele indicatoarelor. Acest proiect înlocuiește unitatea ECU/BCM originală cu un Arduino Nano care primește comenzi prin USART (serial USB) de la un PC sau de la orice altă sursă (Raspberry Pi, altă placă, joc etc.).

La pornirea contactului, firmware-ul execută automat o animație de sweep — acele merg la maxim și revin la zero.

---

## Pinout Arduino Nano

| Pin Arduino | Nume AVR | Funcție | Tip semnal |
|---|---|---|---|
| `D9` | `PB1` | Vitezometru | Impulsuri 5V, direct |
| `D3` | `PD3` | Turometru | Impulsuri 5V → NPN → 12V |
| `D5` | `PD5` | Temperatură lichid | PWM software → NPN → bord |
| `A0` | `PC0` | Releu contact | Digital OUT, active LOW |
| `A1` | `PC1` | Releu lumini | Digital OUT, active LOW |
| `TX/RX` | `PD0/PD1` | Serial USB (simulator) | USART 57600 baud |

> **Important:** GND-ul Arduino trebuie conectat la GND-ul bordului (masă comună). Fără asta, circuitele cu NPN nu funcționează corect.

---

## Hardware — Conexiuni

### Vitezometru — `PB1 (D9)` — conexiune directă

Vitezometrul original Opel Astra G acceptă impulsuri de 5V direct, fără conversie de tensiune. Pinul `D9` se conectează direct la pinul de semnal al vitezometrului din mufa bordului.

```
Arduino D9 (PB1) ──────────────────► Semnal vitezometru (mufă bord)
Arduino GND ────────────────────────► GND carcasă bord (masă comună)
```

Frecvența semnalului este generată de Timer1 (CTC) și este proporțională cu viteza în km/h.

---

### Turometru — `PD3 (D3)` — NPN ca level shifter + invertor la 12V

Bordul Opel Astra G **așteaptă impulsuri de 12V** pe pinul de RPM (semnal venit de la ECU în mod original). Arduino scoate doar 5V, deci NPN-ul este folosit ca **adaptor de tensiune și invertor**.

**Principiu de funcționare:**
- Arduino trimite `0V` → tranzistorul e **închis** → curentul de 12V curge prin rezistența de pull-up direct în bord → bordul vede `12V`
- Arduino trimite `5V` → tranzistorul **se deschide** → trage colectorul la GND → bordul vede `0V`

Rezultat: frecvența de 5V de la Arduino este convertită în frecvență de 12V pentru bord.

```
+12V ──[R pull-up 1kΩ]──┬──► Semnal RPM (mufă bord)
                        │
                     Colector
Arduino D3 ──[1kΩ]── Bază  NPN (ex. 2N2222 / BC547)
                     Emitor
                        │
                       GND ──────────────────────────► GND carcasă bord
```

---

### Temperatură lichid de răcire — `PD5 (D5)` — NPN pentru PWM spre masă

Manometrul de temperatură din bord folosește în original un **termistor** — rezistența variabilă dintre pinul de semnal și masă determină poziția acului. Cu NPN-ul, simulăm această rezistență variabilă prin **PWM**: tranzistorul pulsează rapid curentul spre masă, iar acul (care e lent și are inerție) vede o valoare medie stabilă.

```
Semnal temperatură (mufă bord) ──────────────┐
                                          Colector
Arduino D5 ──[1kΩ]────────────────── Bază  NPN (ex. 2N2222 / BC547)
                                          Emitor
                                             │
                                            GND ──► GND carcasă bord
```

Conversia temperatură → dutycycle PWM se face automat în `Coolant_SetTemp()` printr-o funcție de calibrare piecewise liniară (4 segmente) calibrată pe mașina reală.

---

### Relee contact și lumini — `PC0 (A0)`, `PC1 (A1)`

Două relee **active pe LOW** controlează contactul electric al bordului și iluminatul cadranelor. Se poate folosi orice modul releu de 5V cu intrare active LOW.

| Pin Arduino | Funcție |
|---|---|
| `A0` / `PC0` | Releu contact (aprinde/stinge bordul) |
| `A1` / `PC1` | Releu lumini (iluminat cadrane) |

```
Arduino A0 ──► IN1 modul releu ──► Contact bord
Arduino A1 ──► IN2 modul releu ──► Lumini bord
5V ──────────► VCC modul releu
GND ─────────► GND modul releu
```

> Pinii sunt inițializați pe `HIGH` la pornire (relee deschise). Se trag la `LOW` pentru activare.

---

## Drivere

### `drivers/speedo` — Vitezometru

- **Pin:** `PB1` (D9)
- **Timer:** Timer1 (16-bit), modul CTC — toggle pe pin la fiecare comparație
- **Formula:** `OCR1A = (242541 / kmh) - 1`, prescaler 8
- Sub 5 km/h timerul se oprește și pinul e pus pe LOW

```c
Speedo_Init();
Set_Speed(120);   // 120 km/h
```

---

### `drivers/tacho` — Turometru

- **Pin:** `PD3` (D3)
- **Timer:** Timer2 (8-bit) + contor software `tacho_extend_limit`
- **Principiu:** Contorul software `extend` decide la câte întreruperi Timer2 se face un toggle, extinzând domeniul acoperit dincolo de limitele unui singur prescaler
- **Corecție nelineară:** `rpm -= rpm² / 144000` pentru a compensa neliniaritatea acului original
- Domeniu: **400 – 7000 RPM**

```c
Tacho_Init();
Set_RPM(3000);    // 3000 RPM
```

---

### `drivers/coolant` — Temperatură lichid

- **Pin:** `PD5` (D5)
- **Timer:** Timer0 overflow ISR — PWM software
- **Principiu:** `pwm_counter` se incrementează la fiecare OVF; dacă `pwm_counter < coolant_val` → pin HIGH, altfel LOW
- `Coolant_SetTemp(temp_c)` primește **grade Celsius** și calculează intern PWM-ul printr-o funcție de calibrare piecewise liniară

| Interval | Comportament ac |
|---|---|
| sub 70°C | zona albastră (rece) |
| 70 – 85°C | tranziție spre normal |
| 85 – 95°C | zona verde (funcționare normală) |
| peste 95°C | zona roșie (supraîncălzire) |

```c
Coolant_Init();
Coolant_SetTemp(90);  // trimite °C, calibrarea e în driver
```

---

### `drivers/relays` — Relee

- **Pini:** `PC0` (A0) contact, `PC1` (A1) lumini — active LOW
- Starea internă în variabile statice → `Toggle` funcționează corect fără sincronizare externă

```c
Relays_Init();
Ignition_Set(1);
Lights_Set(1);
```

---

## Protocol serial

**57600 baud**, USB-Serial al Arduino Nano.

### Format

```
<viteză,rpm,temperatură,contact,lumini>\n
```

| Câmp | Valori |
|---|---|
| `viteză` | 0 – 220 km/h |
| `rpm` | 0 – 7000 |
| `temperatură` | 0 – 110 °C |
| `contact` | 0 sau 1 |
| `lumini` | 0 sau 1 |

**Exemplu:** `<120,3500,90,1,0>\n`

Firmware-ul aplică modificările **doar la schimbare de valoare** față de starea curentă. La `contact = 1` se execută `Dashboard_Sweep()` (sweep ace), la `contact = 0` toate acele revin la zero.

---

## Simulator Python

`simulator.py` — interfață grafică tkinter pentru testare fără hardware.

### Funcționalități

- Gauge-uri animate (viteză, turație) cu zone colorate și ace
- Mini gauge temperatură apă cu încălzire progresivă simulată
- 3 moduri de conducere: Drive, Sport, Manual
- Schimbător manual de trepte (`A` / `D`) cu protecție la supraraportare
- Cruise control cu viteză țintă reglabilă (`↑` / `↓`)
- Rev limiter real — la 7000 RPM accelerația se blochează complet în Manual
- Boost / kickdown (`Shift`) cu forță multiplicată și coborâre automată de treaptă

### Taste

| Tastă | Funcție |
|---|---|
| `E` | Contact / Pornire motor (necesită frână pentru pornire) |
| `W` | Accelerație |
| `S` | Frână |
| `A` / `D` | Treaptă jos / sus (mod Manual) |
| `M` | Schimbare mod (Drive → Sport → Manual) |
| `C` | Cruise Control on/off |
| `↑` / `↓` | Viteză țintă Cruise ±1 |
| `L` | Lumini |
| `Shift` | Boost |

### Rulare

```bash
pip install pyserial
python simulator.py
```

Dacă Arduino nu e pe `COM4`, pornește în mod **DEMO** fără serial.

---

## Aplicatie de telemetrie Forza Horizon 6

`fh6_telemetry.py` — aplicatie de telemetrie ce extrage datele din joc.

### Configurare

 - În FH6: Settings → HUD and Gameplay → Data Out → ON, setezi IP-ul PC-ului tău și portul 5300

---

## Build și Flash

```bash
make all BOARD=nano   # compilare
make flash            # flash pe placă (COM4, 57600 baud)
make clean            # curățare
```

Portul și baud rate-ul se modifică din `Makefile` (`PORT`, `BAUD`).

---

## Structura proiectului

```
Opel-Astra-G-Cluster/
├── src/
│   └── main.c              # Loop USART, Dashboard_Sweep, logică principală
├── drivers/
│   ├── speedo/             # Vitezometru — Timer1 CTC pe PB1 (D9)
│   ├── tacho/              # Turometru — Timer2 + extend pe PD3 (D3)
│   ├── coolant/            # Temperatură — PWM soft + calibrare pe PD5 (D5)
│   ├── relays/             # Relee contact + lumini pe PC0/PC1 (A0/A1)
│   ├── gpio/               # GPIO: Init, Write, Read, Toggle
│   ├── timer/              # Timer0 (Millis), Timer1, Timer2
│   ├── usart/              # USART Init, Transmit, Receive
│   ├── pwm/                # Wrapper PWM high-level
│   ├── adc/                # ADC 10-bit blocking
│   ├── eeprom/             # EEPROM Read/Write/Update
│   └── interrupt/          # Întreruperi externe INT0, INT1
├── bsp/
│   ├── nano.h              # Mapare pini Arduino Nano
│   └── uno.h               # Mapare pini Arduino Uno
├── utils/
│   └── delay.c             # Delay bazat pe Millis()
├── test/                   # Unit tests cu mock registre AVR
├── simulator.py            # Simulator GUI Python
├── fh6_telemetry.py        # Aplicatie de telemetrie Forza Horizon 6
├── Makefile
└── README.md
```

---
