import tkinter as tk
import socket
import struct
import serial
import serial.tools.list_ports
import threading
import time
import queue

BG         = "#0d0d0d"
PANEL      = "#111111"
BORDER     = "#252525"
ACCENT     = "#00b4ff"
GREEN      = "#00e676"
YELLOW     = "#ffd600"
RED        = "#ff1744"
WHITE      = "#e0e0e0"
GRAY       = "#3a3a3a"
GRAY_LIGHT = "#606060"
ORANGE     = "#ff6d00"

FORZA_PORT      = 5300
OFF_ENGINE_RPM  = 16
OFF_VELOCITY_X  = 32
OFF_VELOCITY_Y  = 36
OFF_VELOCITY_Z  = 40
OFF_SPEED       = 244
MIN_PACKET_SIZE = 44


def parse_forza(data: bytes):
    if len(data) < MIN_PACKET_SIZE:
        return None
    try:
        rpm = struct.unpack_from('<f', data, OFF_ENGINE_RPM)[0]
        if len(data) >= OFF_SPEED + 4:
            speed_ms = struct.unpack_from('<f', data, OFF_SPEED)[0]
            if speed_ms > 0.0:
                kmh = speed_ms * 3.6
            else:
                vx = struct.unpack_from('<f', data, OFF_VELOCITY_X)[0]
                vy = struct.unpack_from('<f', data, OFF_VELOCITY_Y)[0]
                vz = struct.unpack_from('<f', data, OFF_VELOCITY_Z)[0]
                kmh = (vx*vx + vy*vy + vz*vz) ** 0.5 * 3.6
        else:
            vx = struct.unpack_from('<f', data, OFF_VELOCITY_X)[0]
            vy = struct.unpack_from('<f', data, OFF_VELOCITY_Y)[0]
            vz = struct.unpack_from('<f', data, OFF_VELOCITY_Z)[0]
            kmh = (vx*vx + vy*vy + vz*vz) ** 0.5 * 3.6
        return (max(0.0, rpm), max(0.0, kmh))
    except struct.error:
        return None


def find_arduino_port():
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "cp210" in desc or "ftdi" in desc:
            return p.device
    return None


class FH6TelemetryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FH6 → Bord Opel Astra G")
        self.root.geometry("520x380")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.rpm   = 0.0
        self.kmh   = 0.0
        self.temp  = 20.0
        self.temp_warmed = False

        self.udp_sock    = None
        self.arduino     = None
        self.udp_running = False
        self.fh6_active  = False
        self.last_packet = 0.0

        self.q = queue.Queue()

        self.last_serial_send = 0.0
        self.serial_interval  = 0.05

        self.com_var  = tk.StringVar(value="COM4")
        self.port_var = tk.StringVar(value=str(FORZA_PORT))

        self._build_gui()
        self._poll_queue()
        self._update_temp()

    def _build_gui(self):
        hdr = tk.Frame(self.root, bg="#0a0a0a", height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◈  FH6 Telemetry → Bord Opel  ◈",
                 font=("Courier", 11, "bold"), bg="#0a0a0a", fg=ACCENT).pack(expand=True)

        sf = tk.Frame(self.root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        sf.pack(fill=tk.X, padx=14, pady=(10, 4))

        tk.Label(sf, text="FH6:", font=("Arial", 9, "bold"), bg=PANEL, fg=GRAY_LIGHT).grid(
            row=0, column=0, padx=(12, 4), pady=8)
        self.fh6_dot = tk.Canvas(sf, width=14, height=14, bg=PANEL, highlightthickness=0)
        self.fh6_dot.grid(row=0, column=1)
        self._fh6_oval = self.fh6_dot.create_oval(1, 1, 13, 13, fill=GRAY, outline="")
        self.fh6_lbl = tk.Label(sf, text="Asteapta date...", font=("Arial", 9),
                                bg=PANEL, fg=GRAY_LIGHT, width=20, anchor="w")
        self.fh6_lbl.grid(row=0, column=2, padx=(4, 20))

        tk.Label(sf, text="Arduino:", font=("Arial", 9, "bold"), bg=PANEL, fg=GRAY_LIGHT).grid(
            row=0, column=3, padx=(10, 4))
        self.ard_dot = tk.Canvas(sf, width=14, height=14, bg=PANEL, highlightthickness=0)
        self.ard_dot.grid(row=0, column=4)
        self._ard_oval = self.ard_dot.create_oval(1, 1, 13, 13, fill=GRAY, outline="")
        self.ard_lbl = tk.Label(sf, text="Neconectat", font=("Arial", 9),
                                bg=PANEL, fg=GRAY_LIGHT, width=14, anchor="w")
        self.ard_lbl.grid(row=0, column=5, padx=(4, 12))

        df = tk.Frame(self.root, bg=BG)
        df.pack(pady=8)

        self._make_big_display(df, "RPM", col=0)
        tk.Frame(df, bg=BORDER, width=1, height=100).grid(row=0, column=1, padx=20)
        self._make_big_display(df, "KMH", col=2)

        cf = tk.Frame(self.root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        cf.pack(fill=tk.X, padx=14, pady=(4, 6))

        tk.Label(cf, text="Port UDP:", font=("Arial", 9), bg=PANEL, fg=GRAY_LIGHT).grid(
            row=0, column=0, padx=(12, 4), pady=8)
        tk.Entry(cf, textvariable=self.port_var, width=7, bg="#1a1a1a", fg=WHITE,
                 insertbackground=WHITE, relief=tk.FLAT, font=("Courier", 10)).grid(row=0, column=1)

        tk.Label(cf, text="COM:", font=("Arial", 9), bg=PANEL, fg=GRAY_LIGHT).grid(
            row=0, column=2, padx=(20, 4))
        tk.Entry(cf, textvariable=self.com_var, width=7, bg="#1a1a1a", fg=WHITE,
                 insertbackground=WHITE, relief=tk.FLAT, font=("Courier", 10)).grid(row=0, column=3)

        auto = find_arduino_port()
        if auto:
            self.com_var.set(auto)

        btn_s = dict(font=("Arial", 9, "bold"), relief=tk.FLAT, cursor="hand2",
                     borderwidth=0, padx=10, pady=4)

        self.btn_start = tk.Button(cf, text="▶  START", bg="#003a52", fg=ACCENT,
                                   activebackground="#005070", activeforeground=ACCENT,
                                   command=self.start, **btn_s)
        self.btn_start.grid(row=0, column=4, padx=(20, 6))

        self.btn_stop = tk.Button(cf, text="■  STOP", bg="#2a0a0a", fg=RED,
                                  activebackground="#400a0a", activeforeground=RED,
                                  command=self.stop, state=tk.DISABLED, **btn_s)
        self.btn_stop.grid(row=0, column=5, padx=(0, 12))

        lf = tk.Frame(self.root, bg=BG)
        lf.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

        self.log_text = tk.Text(lf, height=5, bg="#0a0a0a", fg=GRAY_LIGHT,
                                font=("Courier", 8), relief=tk.FLAT,
                                state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self._log("Aplicatie pornita. Configureaza si apasa START.")

    def _make_big_display(self, parent, label, col):
        f = tk.Frame(parent, bg=BG)
        f.grid(row=0, column=col, padx=20)
        tk.Label(f, text=label, font=("Arial", 10, "bold"), bg=BG, fg=GRAY_LIGHT).pack()
        lbl = tk.Label(f, text="0", font=("Courier", 52, "bold"), bg=BG, fg=WHITE, width=5)
        lbl.pack()
        if label == "RPM":
            self.rpm_lbl = lbl
        else:
            self.kmh_lbl = lbl

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start(self):
        try:
            port = int(self.port_var.get())
        except ValueError:
            self._log("Port UDP invalid!")
            return

        com = self.com_var.get().strip()
        try:
            self.arduino = serial.Serial(com, 57600, timeout=0.01)
            time.sleep(1.5)
            self.ard_dot.itemconfig(self._ard_oval, fill=GREEN)
            self.ard_lbl.config(text=f"{com} OK", fg=GREEN)
            self._log(f"Arduino conectat pe {com}.")
        except Exception as e:
            self.arduino = None
            self.ard_dot.itemconfig(self._ard_oval, fill=YELLOW)
            self.ard_lbl.config(text="Fara Arduino", fg=YELLOW)
            self._log(f"Arduino negasit ({e}). Mergem fara serial.")

        try:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.bind(("", port))
            self.udp_sock.settimeout(1.0)
            self._log(f"Ascult UDP pe portul {port}. Porneste FH6 Data Out.")
        except Exception as e:
            self._log(f"Eroare socket UDP: {e}")
            return

        self.udp_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        threading.Thread(target=self._udp_loop, daemon=True).start()

    def stop(self):
        self.udp_running = False
        if self.udp_sock:
            try: self.udp_sock.close()
            except: pass
            self.udp_sock = None
        if self.arduino:
            try: self.arduino.close()
            except: pass
            self.arduino = None

        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.fh6_dot.itemconfig(self._fh6_oval, fill=GRAY)
        self.ard_dot.itemconfig(self._ard_oval, fill=GRAY)
        self.fh6_lbl.config(text="Oprit", fg=GRAY_LIGHT)
        self.ard_lbl.config(text="Neconectat", fg=GRAY_LIGHT)
        self._log("Oprit.")

    def _udp_loop(self):
        while self.udp_running:
            try:
                data, addr = self.udp_sock.recvfrom(4096)
            except socket.timeout:
                if self.fh6_active and (time.time() - self.last_packet) > 3.0:
                    self.fh6_active = False
                    self.q.put(("fh6_status", False))
                continue
            except Exception:
                break

            result = parse_forza(data)
            if result is None:
                continue

            rpm, kmh = result
            self.last_packet = time.time()

            if not self.fh6_active:
                self.fh6_active = True
                self.q.put(("fh6_status", True))
                self.q.put(("log", f"Date FH6 primite de la {addr[0]}:{addr[1]}"))

            self.q.put(("data", (rpm, kmh)))
            self._send_serial(kmh, rpm)

    def _send_serial(self, kmh, rpm):
        if not self.arduino:
            return
        now = time.time()
        if (now - self.last_serial_send) < self.serial_interval:
            return
        packet = f"<{int(round(kmh))},{int(round(rpm))},{int(self.temp)},1,0>\n"
        try:
            self.arduino.write(packet.encode("utf-8"))
            self.arduino.readline()
            self.last_serial_send = now
        except Exception as e:
            self.q.put(("log", f"Eroare serial: {e}"))
            self.arduino = None
            self.q.put(("ard_err", str(e)))

    def _update_temp(self):
        if self.fh6_active:
            if self.temp < 90.0:
                self.temp = min(90.0, self.temp + 0.03)
            else:
                import random
                self.temp += random.uniform(-0.1, 0.1)
                self.temp  = max(84.0, min(95.0, self.temp))
        self.root.after(100, self._update_temp)

    def _poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "data":
                    rpm, kmh = msg[1]
                    self.rpm = rpm
                    self.kmh = kmh
                    self.rpm_lbl.config(text=str(int(rpm)))
                    self.kmh_lbl.config(text=str(int(kmh)))
                elif kind == "fh6_status":
                    on = msg[1]
                    color = GREEN if on else GRAY
                    text  = "Conectat" if on else "Fara semnal"
                    fg    = GREEN if on else GRAY_LIGHT
                    self.fh6_dot.itemconfig(self._fh6_oval, fill=color)
                    self.fh6_lbl.config(text=text, fg=fg)
                elif kind == "log":
                    self._log(msg[1])
                elif kind == "ard_err":
                    self.ard_dot.itemconfig(self._ard_oval, fill=RED)
                    self.ard_lbl.config(text="Eroare", fg=RED)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app  = FH6TelemetryApp(root)
    root.mainloop()
