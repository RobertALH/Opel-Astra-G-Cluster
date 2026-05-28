"""
Simulator GUI pentru Opel Astra G Cluster
------------------------------------------
W / ↑ = creste viteza/turatia
S / ↓ = scade viteza/turatia
Q / ESC = iesire

Protocol serial: <speed,rpm>\n
"""

import tkinter as tk
import serial
import threading
import time
import sys

# ── Configurare ──────────────────────────────────────────────────────────────
PORT       = "COM4"
BAUD       = 57600

SPEED_STEP  = 10
RPM_STEP    = 200
MAX_SPEED   = 240
MAX_RPM     = 7000
MIN_SPEED   = 0
MIN_RPM     = 800
# ─────────────────────────────────────────────────────────────────────────────


class SimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Opel Astra G – Cluster Simulator")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")

        self.speed = 0
        self.rpm   = 800
        self.ser   = None
        self.running = True

        self._build_ui()
        self._connect_serial()
        self._bind_keys()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = dict(padx=20, pady=10)

        title = tk.Label(
            self.root, text="OPEL ASTRA G CLUSTER",
            font=("Segoe UI", 14, "bold"),
            bg="#1a1a1a", fg="#e8b400"
        )
        title.pack(pady=(20, 5))

        sep = tk.Frame(self.root, bg="#e8b400", height=2, width=320)
        sep.pack()

        frame = tk.Frame(self.root, bg="#1a1a1a")
        frame.pack(padx=30, pady=20)

        # Viteza
        tk.Label(frame, text="VITEZĂ", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").grid(row=0, column=0, sticky="w")

        self.speed_var = tk.StringVar(value="0")
        speed_row = tk.Frame(frame, bg="#1a1a1a")
        speed_row.grid(row=1, column=0, sticky="w", pady=(0, 15))
        tk.Label(speed_row, textvariable=self.speed_var,
                 font=("Consolas", 48, "bold"),
                 bg="#1a1a1a", fg="#ffffff", width=4, anchor="e").pack(side="left")
        tk.Label(speed_row, text="km/h",
                 font=("Segoe UI", 14),
                 bg="#1a1a1a", fg="#888888").pack(side="left", padx=(6, 0), anchor="s", pady=(0, 8))

        # Turatie
        tk.Label(frame, text="TURAȚIE", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").grid(row=2, column=0, sticky="w")

        self.rpm_var = tk.StringVar(value="800")
        rpm_row = tk.Frame(frame, bg="#1a1a1a")
        rpm_row.grid(row=3, column=0, sticky="w", pady=(0, 10))
        tk.Label(rpm_row, textvariable=self.rpm_var,
                 font=("Consolas", 48, "bold"),
                 bg="#1a1a1a", fg="#ffffff", width=5, anchor="e").pack(side="left")
        tk.Label(rpm_row, text="RPM",
                 font=("Segoe UI", 14),
                 bg="#1a1a1a", fg="#888888").pack(side="left", padx=(6, 0), anchor="s", pady=(0, 8))

        sep2 = tk.Frame(self.root, bg="#333333", height=1, width=320)
        sep2.pack()

        # Butoane
        btn_frame = tk.Frame(self.root, bg="#1a1a1a")
        btn_frame.pack(pady=15)

        btn_style = dict(font=("Segoe UI", 10, "bold"), width=8,
                         relief="flat", cursor="hand2",
                         activeforeground="#ffffff")

        self.btn_up = tk.Button(
            btn_frame, text="▲  W", bg="#2a6db5", fg="#ffffff",
            activebackground="#1a5da0",
            command=self._increase, **btn_style
        )
        self.btn_up.pack(side="left", padx=5)

        self.btn_down = tk.Button(
            btn_frame, text="▼  S", bg="#b52a2a", fg="#ffffff",
            activebackground="#a01a1a",
            command=self._decrease, **btn_style
        )
        self.btn_down.pack(side="left", padx=5)

        self.btn_quit = tk.Button(
            btn_frame, text="✕  Q", bg="#444444", fg="#ffffff",
            activebackground="#333333",
            command=self._quit, **btn_style
        )
        self.btn_quit.pack(side="left", padx=5)

        # Status
        self.status_var = tk.StringVar(value="Se conectează...")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 8), bg="#1a1a1a", fg="#888888"
        )
        self.status_label.pack(pady=(0, 15))

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

    def _send(self):
        if self.ser and self.ser.is_open:
            msg = f"<{self.speed},{self.rpm}>\n"
            self.ser.write(msg.encode())
            self.ser.flush()

    # ── Acțiuni ──────────────────────────────────────────────────────────────

    def _increase(self):
        self.speed = min(self.speed + SPEED_STEP, MAX_SPEED)
        self.rpm   = min(self.rpm   + RPM_STEP,   MAX_RPM)
        self._update_display()
        self._send()

    def _decrease(self):
        self.speed = max(self.speed - SPEED_STEP, MIN_SPEED)
        self.rpm   = max(self.rpm   - RPM_STEP,   MIN_RPM)
        self._update_display()
        self._send()

    def _quit(self):
        if self.ser and self.ser.is_open:
            try:
                msg = "<0,0>\n"
                self.ser.write(msg.encode())
                self.ser.flush()
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()

    def _update_display(self):
        self.speed_var.set(str(self.speed))
        self.rpm_var.set(str(self.rpm))

    # ── Taste ────────────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.root.bind("<w>", lambda e: self._increase())
        self.root.bind("<W>", lambda e: self._increase())
        self.root.bind("<Up>", lambda e: self._increase())
        self.root.bind("<s>", lambda e: self._decrease())
        self.root.bind("<S>", lambda e: self._decrease())
        self.root.bind("<Down>", lambda e: self._decrease())
        self.root.bind("<q>", lambda e: self._quit())
        self.root.bind("<Q>", lambda e: self._quit())
        self.root.bind("<Escape>", lambda e: self._quit())


def main():
    root = tk.Tk()
    app = SimulatorApp(root)
    root.protocol("WM_DELETE_WINDOW", app._quit)
    root.mainloop()


if __name__ == "__main__":
    main()
