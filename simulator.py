"""
Simulator GUI pentru Opel Astra G Cluster
------------------------------------------
W / ↑     = accelereaza (tine apasat)
S / ↓     = franeaza   (tine apasat)
Q / ESC   = iesire

Protocol serial: <speed,rpm>\n
"""

import tkinter as tk
import serial
import threading
import time

# ── Configurare ──────────────────────────────────────────────────────────────
PORT       = "COM4"
BAUD       = 57600

MAX_SPEED  = 240.0
MIN_SPEED  = 0.0
IDLE_RPM   = 800
MAX_RPM    = 7000

ACCEL_RATE = 18.0    
BRAKE_RATE = 30.0    
DRAG_RATE  = 6.0     
TICK_MS    = 30      



GEARS = [
    {"min":   0, "max":  28,  "ratio": 220},   # 1
    {"min":  22, "max":  52,  "ratio": 110},   # 2
    {"min":  45, "max":  88,  "ratio":  72},   # 3
    {"min":  80, "max": 130,  "ratio":  47},   # 4
    {"min": 118, "max": 240,  "ratio":  30},   # 5
]
UPSHIFT_RPM   = 5800
DOWNSHIFT_RPM = 1300
# ─────────────────────────────────────────────────────────────────────────────


def calc_rpm(speed: float, gear: int) -> int:
    g = GEARS[gear - 1]
    rpm = IDLE_RPM + max(0.0, speed - g["min"]) * g["ratio"]
    return int(max(IDLE_RPM, min(rpm, MAX_RPM)))


def auto_gear(speed: float, gear: int, rpm: int) -> int:
    g = gear
    if rpm >= UPSHIFT_RPM and g < 5:
        g += 1
    elif rpm <= DOWNSHIFT_RPM and g > 1:
        if speed <= GEARS[g - 2]["max"]:
            g -= 1
    # forteaza limitele de viteza
    while g > 1 and speed < GEARS[g - 1]["min"]:
        g -= 1
    while g < 5 and speed > GEARS[g - 1]["max"]:
        g += 1
    return g


class SimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Opel Astra G – Cluster Simulator")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")

        self.speed: float = 0.0
        self.rpm:   int   = IDLE_RPM
        self.gear:  int   = 1

        self.key_up   = False
        self.key_down = False
        self.ser      = None
        self._last_sent = (-1, -1)

        self._build_ui()
        self._connect_serial()
        self._bind_keys()
        self._tick()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        tk.Label(self.root, text="OPEL ASTRA G CLUSTER",
                 font=("Segoe UI", 14, "bold"),
                 bg="#1a1a1a", fg="#e8b400").pack(pady=(20, 5))
        tk.Frame(self.root, bg="#e8b400", height=2, width=360).pack()

        main = tk.Frame(self.root, bg="#1a1a1a")
        main.pack(padx=30, pady=20)

        # Viteza
        tk.Label(main, text="VITEZĂ", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").grid(row=0, column=0, sticky="w")
        speed_row = tk.Frame(main, bg="#1a1a1a")
        speed_row.grid(row=1, column=0, sticky="w", pady=(0, 16))
        self.speed_var = tk.StringVar(value="0")
        tk.Label(speed_row, textvariable=self.speed_var,
                 font=("Consolas", 54, "bold"),
                 bg="#1a1a1a", fg="#ffffff", width=4, anchor="e").pack(side="left")
        tk.Label(speed_row, text="km/h", font=("Segoe UI", 14),
                 bg="#1a1a1a", fg="#888888").pack(side="left", padx=(6, 0),
                                                   anchor="s", pady=(0, 10))

        # Turatie
        tk.Label(main, text="TURAȚIE", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").grid(row=2, column=0, sticky="w")
        rpm_row = tk.Frame(main, bg="#1a1a1a")
        rpm_row.grid(row=3, column=0, sticky="w", pady=(0, 10))
        self.rpm_var = tk.StringVar(value="800")
        tk.Label(rpm_row, textvariable=self.rpm_var,
                 font=("Consolas", 54, "bold"),
                 bg="#1a1a1a", fg="#ffffff", width=5, anchor="e").pack(side="left")
        tk.Label(rpm_row, text="RPM", font=("Segoe UI", 14),
                 bg="#1a1a1a", fg="#888888").pack(side="left", padx=(6, 0),
                                                   anchor="s", pady=(0, 10))

        # Treapta
        gear_frame = tk.Frame(main, bg="#1a1a1a")
        gear_frame.grid(row=0, column=1, rowspan=4, padx=(35, 0), sticky="ns")
        tk.Label(gear_frame, text="TREAPTA", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").pack()
        self.gear_var = tk.StringVar(value="N")
        tk.Label(gear_frame, textvariable=self.gear_var,
                 font=("Consolas", 60, "bold"),
                 bg="#1a1a1a", fg="#e8b400", width=2).pack()

        tk.Frame(self.root, bg="#333333", height=1, width=360).pack()

        btn_frame = tk.Frame(self.root, bg="#1a1a1a")
        btn_frame.pack(pady=14)

        s = dict(font=("Segoe UI", 10, "bold"), width=9,
                 relief="flat", cursor="hand2")

        self.btn_up = tk.Button(btn_frame, text="▲  W",
                                bg="#2a6db5", fg="#fff",
                                activebackground="#1a5da0", activeforeground="#fff", **s)
        self.btn_up.pack(side="left", padx=5)
        self.btn_up.bind("<ButtonPress-1>",   lambda e: self._set_key("up", True))
        self.btn_up.bind("<ButtonRelease-1>", lambda e: self._set_key("up", False))

        self.btn_down = tk.Button(btn_frame, text="▼  S",
                                  bg="#b52a2a", fg="#fff",
                                  activebackground="#a01a1a", activeforeground="#fff", **s)
        self.btn_down.pack(side="left", padx=5)
        self.btn_down.bind("<ButtonPress-1>",   lambda e: self._set_key("down", True))
        self.btn_down.bind("<ButtonRelease-1>", lambda e: self._set_key("down", False))

        tk.Button(btn_frame, text="✕  Q", bg="#444", fg="#fff",
                  activebackground="#333", activeforeground="#fff",
                  command=self._quit, **s).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Se conectează...")
        self.status_label = tk.Label(self.root, textvariable=self.status_var,
                                     font=("Segoe UI", 8),
                                     bg="#1a1a1a", fg="#888888")
        self.status_label.pack(pady=(0, 15))

    # ── Bucla fizica ──────────────────────────────────────────────────────────

    def _tick(self):
        dt = TICK_MS / 1000.0

        if self.key_up and not self.key_down:
            self.speed = min(self.speed + ACCEL_RATE * dt, MAX_SPEED)
        elif self.key_down and not self.key_up:
            self.speed = max(self.speed - BRAKE_RATE * dt, MIN_SPEED)
        else:
            self.speed = max(self.speed - DRAG_RATE * dt, MIN_SPEED)

        # Cutie automata
        self.gear = auto_gear(self.speed, self.gear, self.rpm)
        self.rpm  = calc_rpm(self.speed, self.gear)

        speed_i = int(self.speed)
        self.speed_var.set(str(speed_i))
        self.rpm_var.set(str(self.rpm))
        self.gear_var.set(str(self.gear) if speed_i > 0 else "N")

        if (speed_i, self.rpm) != self._last_sent:
            self._last_sent = (speed_i, self.rpm)
            self._send(speed_i, self.rpm)

        self.root.after(TICK_MS, self._tick)

    # ── Serial ───────────────────────────────────────────────────────────────

    def _connect_serial(self):
        def connect():
            try:
                self.ser = serial.Serial(PORT, BAUD, timeout=0.1)
                time.sleep(2)
                self.root.after(0, lambda: self.status_var.set(f"Conectat pe {PORT}"))
                self.root.after(0, lambda: self.status_label.config(fg="#4caf50"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"EROARE: {e}"))
                self.root.after(0, lambda: self.status_label.config(fg="#f44336"))
        threading.Thread(target=connect, daemon=True).start()

    def _send(self, speed: int, rpm: int):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"<{speed},{rpm}>\n".encode())
                self.ser.flush()
            except Exception:
                pass

    # ── Input ─────────────────────────────────────────────────────────────────

    def _set_key(self, key: str, state: bool):
        if key == "up":
            self.key_up = state
        else:
            self.key_down = state

    def _bind_keys(self):
        for k in ("<KeyPress-w>", "<KeyPress-W>", "<KeyPress-Up>"):
            self.root.bind(k, lambda e: self._set_key("up", True))
        for k in ("<KeyRelease-w>", "<KeyRelease-W>", "<KeyRelease-Up>"):
            self.root.bind(k, lambda e: self._set_key("up", False))
        for k in ("<KeyPress-s>", "<KeyPress-S>", "<KeyPress-Down>"):
            self.root.bind(k, lambda e: self._set_key("down", True))
        for k in ("<KeyRelease-s>", "<KeyRelease-S>", "<KeyRelease-Down>"):
            self.root.bind(k, lambda e: self._set_key("down", False))
        self.root.bind("<q>",      lambda e: self._quit())
        self.root.bind("<Q>",      lambda e: self._quit())
        self.root.bind("<Escape>", lambda e: self._quit())

    # ── Quit ──────────────────────────────────────────────────────────────────

    def _quit(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"<0,0>\n")
                self.ser.flush()
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SimulatorApp(root)
    root.protocol("WM_DELETE_WINDOW", app._quit)
    root.mainloop()


if __name__ == "__main__":
    main()
