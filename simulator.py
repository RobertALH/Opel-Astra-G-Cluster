import tkinter as tk
import math
import random
import serial
import time

BG          = "#0d0d0d"
PANEL       = "#111111"
PANEL_DARK  = "#0a0a0a"
BORDER      = "#252525"
ACCENT      = "#00b4ff"
ACCENT_DIM  = "#003a52"
GREEN       = "#00e676"
YELLOW      = "#ffd600"
RED         = "#ff1744"
WHITE       = "#e0e0e0"
GRAY        = "#3a3a3a"
GRAY_LIGHT  = "#606060"
ORANGE      = "#ff6d00"
NEEDLE_CLR  = "#ff3030"

GAUGE_START = 225
GAUGE_SWEEP = 270
MINI_START  = 210
MINI_SWEEP  = 240


class CarSimulatorV2:
    def __init__(self, root):
        try:
            self.arduino = serial.Serial('COM4', 57600, timeout=0.01)
            print("Conectat la Arduino!")
            time.sleep(2)
        except Exception:
            self.arduino = None
            print("DEMO: Arduino nu este conectat pe COM4.")

        self.root = root
        self.root.title("Simulator Opel Astra G")
        self.root.geometry("960x600")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.lights_on       = False
        self.ignition_on     = False
        self.engine_running  = False
        self.brake_pressed   = False

        self.speed           = 0.0
        self.rpm             = 0.0
        self.car_top_speed   = 200.0
        self.dial_max_speed  = 220.0
        self.dial_max_rpm    = 7000.0

        self.water_temp      = 70.0
        self.temp_reached_90 = False

        self.gear             = 1
        self.modes            = ['Drive', 'Sport', 'Manual']
        self.current_mode_idx = 0
        self.gear_max_speeds  = {1: 54, 2: 92, 3: 140, 4: 185, 5: 235}
        self.gear_ratios      = {g: 7000 / v for g, v in self.gear_max_speeds.items()}

        self.accelerating        = False
        self.braking             = False
        self.boost               = False
        self.boost_kickdown_done = False
        self.cruise_active       = False
        self.cruise_target       = 100.0

        self.last_shift_time = 0.0
        self.shift_cooldown  = 1.2

        self.last_serial_send = time.time()
        self.serial_interval  = 0.05

        self.setup_gui()
        self.update_physics()

    def setup_gui(self):
        self._build_header()
        self._build_main_gauges_row()
        self._build_secondary_row()
        self._build_status_bar()
        self._bind_keys()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=PANEL_DARK, height=42)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◈  Simulator Opel Astra G  ◈",
                 font=("Courier", 12, "bold"), bg=PANEL_DARK, fg=ACCENT).pack(expand=True)

    def _build_main_gauges_row(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(pady=(10, 0))

        self.canvas_rpm = tk.Canvas(row, width=310, height=285, bg=BG, highlightthickness=0)
        self.canvas_rpm.grid(row=0, column=0, padx=10)

        self._build_center_panel(row)

        self.canvas_spd = tk.Canvas(row, width=310, height=285, bg=BG, highlightthickness=0)
        self.canvas_spd.grid(row=0, column=2, padx=10)

        self._draw_gauge_face(self.canvas_spd, cx=155, cy=148, r=128,
                              max_val=220, step_major=20, step_minor=10,
                              label="km/h", zones=None)
        self._draw_gauge_face(self.canvas_rpm, cx=155, cy=148, r=128,
                              max_val=7, step_major=1, step_minor=1,
                              label="×1000 rpm",
                              zones=[(0, 4/7, GREEN), (4/7, 6/7, YELLOW), (6/7, 1.0, RED)])

        self.needle_spd = self._make_needle(self.canvas_spd, 155, 148, r=104)
        self.needle_rpm = self._make_needle(self.canvas_rpm, 155, 148, r=104)

        for c in (self.canvas_spd, self.canvas_rpm):
            c.create_oval(155-13, 148-13, 155+13, 148+13, fill="#1e1e1e", outline=GRAY_LIGHT, width=1)
            c.create_oval(155-5,  148-5,  155+5,  148+5,  fill=NEEDLE_CLR, outline="")

        self.spd_text = self.canvas_spd.create_text(155, 200, text="0",
                                                     font=("Courier", 28, "bold"), fill=ACCENT)
        self.canvas_spd.create_text(155, 226, text="km/h", font=("Arial", 10), fill=GRAY_LIGHT)

        self.rpm_text = self.canvas_rpm.create_text(155, 200, text="0",
                                                     font=("Courier", 28, "bold"), fill=ACCENT)
        self.canvas_rpm.create_text(155, 226, text="rpm", font=("Arial", 10), fill=GRAY_LIGHT)

    def _build_center_panel(self, parent):
        f = tk.Frame(parent, bg=BG, width=160)
        f.grid(row=0, column=1, padx=5)
        f.grid_propagate(False)

        tk.Label(f, text="TREAPTĂ", font=("Arial", 9), bg=BG, fg=GRAY_LIGHT).pack(pady=(30, 0))

        self.gear_label = tk.Label(f, text="—", font=("Courier", 68, "bold"), bg=BG, fg=WHITE)
        self.gear_label.pack()

        self.mode_label = tk.Label(f, text="DRIVE", font=("Arial", 12, "bold"), bg=BG, fg=ORANGE)
        self.mode_label.pack(pady=(0, 10))

        tk.Frame(f, bg=BORDER, height=1).pack(fill=tk.X, padx=10, pady=6)

        self.cruise_label = tk.Label(f, text="CRUISE\nOFF", font=("Arial", 9),
                                     bg=BG, fg=GRAY_LIGHT, justify=tk.CENTER)
        self.cruise_label.pack()

    def _build_secondary_row(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(pady=(8, 0))
        self._build_mini_temp(row)
        self._build_cruise_panel(row)

    def _build_mini_temp(self, parent):
        f = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=0, column=0, padx=12, pady=4)

        tk.Label(f, text="TEMP. APĂ", font=("Arial", 9, "bold"), bg=PANEL, fg=GRAY_LIGHT).pack(pady=(8, 0))

        self.canvas_temp = tk.Canvas(f, width=165, height=92, bg=PANEL, highlightthickness=0)
        self.canvas_temp.pack()

        self._draw_mini_gauge(self.canvas_temp, cx=82, cy=82, r=62, max_val=120, step_major=30,
                              zones=[(0, 70/120, "#1565c0"), (70/120, 95/120, GREEN), (95/120, 1.0, RED)])
        self.needle_temp = self._make_needle(self.canvas_temp, 82, 82, r=50, width=2, start_deg=MINI_START)
        self.canvas_temp.create_oval(82-6, 82-6, 82+6, 82+6, fill="#1e1e1e", outline=GRAY_LIGHT, width=1)

        self.temp_lbl = tk.Label(f, text="20°C", font=("Courier", 17, "bold"), bg=PANEL, fg=ACCENT)
        self.temp_lbl.pack(pady=(2, 8))

    def _build_cruise_panel(self, parent):
        f = tk.Frame(parent, bg=PANEL, width=280, highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=0, column=1, padx=8, pady=4)
        f.pack_propagate(False)

        tk.Label(f, text="CRUISE CONTROL", font=("Arial", 9, "bold"), bg=PANEL, fg=GRAY_LIGHT).pack(pady=(10, 2))
        tk.Label(f, text="[ ↑ / ↓ ] sau butoane", font=("Arial", 8), bg=PANEL, fg=GRAY_LIGHT).pack(pady=(0, 4))

        ctrl = tk.Frame(f, bg=PANEL)
        ctrl.pack()

        btn_style = dict(font=("Arial", 18, "bold"), bg="#1e2e1e", fg=GREEN,
                         relief=tk.FLAT, activebackground="#2a3e2a", activeforeground=GREEN,
                         width=3, height=1, cursor="hand2", borderwidth=0)

        def _minus(): self.cruise_minus(); self.root.focus_set()
        def _plus():  self.cruise_plus();  self.root.focus_set()

        tk.Button(ctrl, text="−", command=_minus, **btn_style).grid(row=0, column=0, padx=8, pady=4)

        self.cruise_val_lbl = tk.Label(ctrl, text="100 km/h",
                                       font=("Courier", 20, "bold"), bg=PANEL, fg=GRAY_LIGHT, width=9)
        self.cruise_val_lbl.grid(row=0, column=1)

        tk.Button(ctrl, text="+", command=_plus, **btn_style).grid(row=0, column=2, padx=8, pady=4)

        self.cruise_status_lbl = tk.Label(f, text="● INACTIV", font=("Arial", 10, "bold"),
                                          bg=PANEL, fg=GRAY_LIGHT)
        self.cruise_status_lbl.pack(pady=(2, 8))

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=PANEL_DARK, height=72)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        tk.Frame(bar, bg=ACCENT_DIM, height=1).pack(fill=tk.X)

        inner = tk.Frame(bar, bg=PANEL_DARK)
        inner.pack(expand=True, pady=6)

        indicators = [("ign", "CONTACT", ACCENT), ("eng", "MOTOR", GREEN),
                      ("lights", "LUMINI", YELLOW), ("boost", "BOOST", RED)]
        ind_row = tk.Frame(inner, bg=PANEL_DARK)
        ind_row.pack()

        self._ind = {}
        for name, label, color in indicators:
            cell = tk.Frame(ind_row, bg=PANEL_DARK)
            cell.pack(side=tk.LEFT, padx=22)
            dot_c = tk.Canvas(cell, width=14, height=14, bg=PANEL_DARK, highlightthickness=0)
            dot_c.pack()
            dot_id = dot_c.create_oval(1, 1, 13, 13, fill=GRAY, outline="")
            self._ind[name] = (dot_c, dot_id, color)
            tk.Label(cell, text=label, font=("Arial", 8), bg=PANEL_DARK, fg=GRAY_LIGHT).pack()

        tk.Label(inner,
                 text="[E] Contact/Motor    [W] Gaz    [S] Frână    [A/D] Treaptă    [M] Mod    [C] Cruise    [↑/↓] Viteză Cruise    [L] Lumini    [Shift] Boost",
                 font=("Arial", 8), bg=PANEL_DARK, fg=GRAY_LIGHT).pack(pady=(4, 0))

    def _draw_gauge_face(self, canvas, cx, cy, r, max_val, step_major, step_minor,
                         label="", zones=None, start_deg=GAUGE_START, sweep=GAUGE_SWEEP):
        canvas.create_oval(cx-r-16, cy-r-16, cx+r+16, cy+r+16, fill="#0f0f0f", outline=BORDER, width=2)
        canvas.create_oval(cx-r-7,  cy-r-7,  cx+r+7,  cy+r+7,  fill="#111111", outline="#1e1e1e", width=1)

        track_r = r - 7
        if zones:
            for z0, z1, color in zones:
                canvas.create_arc(cx-track_r, cy-track_r, cx+track_r, cy+track_r,
                                  start=start_deg - z0*sweep, extent=-(z1-z0)*sweep,
                                  outline=color, width=8, style=tk.ARC)
        else:
            canvas.create_arc(cx-track_r, cy-track_r, cx+track_r, cy+track_r,
                              start=start_deg, extent=-sweep, outline=ACCENT_DIM, width=8, style=tk.ARC)

        canvas.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=start_deg, extent=-sweep, outline=GRAY, width=1, style=tk.ARC)

        n_minor = int(max_val / step_minor)
        for i in range(n_minor + 1):
            val  = i * step_minor
            frac = val / max_val
            a    = math.radians(start_deg - frac * sweep)
            is_m = (val % step_major == 0)
            r_out = r - 2
            r_in  = r_out - (15 if is_m else 7)
            canvas.create_line(cx + r_out*math.cos(a), cy - r_out*math.sin(a),
                               cx + r_in *math.cos(a), cy - r_in *math.sin(a),
                               fill=(WHITE if is_m else "#2e2e2e"), width=(2 if is_m else 1))
            if is_m and val > 0:
                canvas.create_text(cx + (r-32)*math.cos(a), cy - (r-32)*math.sin(a),
                                   text=str(int(val)), fill=WHITE, font=("Arial", 9, "bold"))

        canvas.create_text(cx, cy + r - 18, text=label, fill=GRAY_LIGHT, font=("Arial", 9))

    def _draw_mini_gauge(self, canvas, cx, cy, r, max_val, step_major,
                         zones=None, start_deg=MINI_START, sweep=MINI_SWEEP):
        track_r = r - 5
        if zones:
            for z0, z1, color in zones:
                canvas.create_arc(cx-track_r, cy-track_r, cx+track_r, cy+track_r,
                                  start=start_deg - z0*sweep, extent=-(z1-z0)*sweep,
                                  outline=color, width=6, style=tk.ARC)
        n = int(max_val / step_major)
        for i in range(n + 1):
            frac = (i * step_major) / max_val
            a    = math.radians(start_deg - frac * sweep)
            r_o  = r - 1;  r_i = r_o - 9
            canvas.create_line(cx + r_o*math.cos(a), cy - r_o*math.sin(a),
                               cx + r_i*math.cos(a), cy - r_i*math.sin(a), fill=WHITE, width=1)

    def _make_needle(self, canvas, cx, cy, r=104, width=3, start_deg=GAUGE_START):
        a = math.radians(start_deg)
        return canvas.create_line(cx, cy, cx + r*math.cos(a), cy - r*math.sin(a),
                                  fill=NEEDLE_CLR, width=width, capstyle=tk.ROUND)

    def _move_needle(self, canvas, needle_id, cx, cy, r, value, max_val,
                     start_deg=GAUGE_START, sweep=GAUGE_SWEEP):
        frac = min(float(value), float(max_val)) / float(max_val)
        a    = math.radians(start_deg - frac * sweep)
        canvas.coords(needle_id, cx, cy, cx + r*math.cos(a), cy - r*math.sin(a))

    def _set_led(self, name, on: bool):
        dot_c, dot_id, active_color = self._ind[name]
        dot_c.itemconfig(dot_id, fill=(active_color if on else GRAY))

    def _bind_keys(self):
        r = self.root
        r.bind('<KeyPress-w>',       lambda e: self.set_accel(True))
        r.bind('<KeyRelease-w>',     lambda e: self.set_accel(False))
        r.bind('<KeyPress-W>',       lambda e: self.set_accel(True))
        r.bind('<KeyRelease-W>',     lambda e: self.set_accel(False))
        r.bind('<KeyPress-s>',       lambda e: self.set_brake(True))
        r.bind('<KeyRelease-s>',     lambda e: self.set_brake(False))
        r.bind('<KeyPress-S>',       lambda e: self.set_brake(True))
        r.bind('<KeyRelease-S>',     lambda e: self.set_brake(False))
        r.bind('a', self.manual_shift_down); r.bind('A', self.manual_shift_down)
        r.bind('d', self.manual_shift_up);   r.bind('D', self.manual_shift_up)
        r.bind('e', self.start_stop_logic);  r.bind('E', self.start_stop_logic)
        r.bind('m', self.toggle_mode);       r.bind('M', self.toggle_mode)
        r.bind('c', self.toggle_cruise);     r.bind('C', self.toggle_cruise)
        r.bind('l', self.toggle_lights);     r.bind('L', self.toggle_lights)
        r.bind('<KeyPress-Shift_L>',   self.start_boost)
        r.bind('<KeyRelease-Shift_L>', self.stop_boost)
        r.bind('<KeyPress-Shift_R>',   self.start_boost)
        r.bind('<KeyRelease-Shift_R>', self.stop_boost)
        r.bind('<Up>',   lambda e: self.cruise_plus())
        r.bind('<Down>', lambda e: self.cruise_minus())

    def toggle_lights(self, event=None):
        self.lights_on = not self.lights_on
        self.update_gui()

    def start_stop_logic(self, event=None):
        if self.engine_running:
            self.engine_running = False
            self.ignition_on    = False
        elif self.brake_pressed:
            self.ignition_on    = True
            self.engine_running = True
        else:
            self.ignition_on = not self.ignition_on
        self.update_gui()

    def set_accel(self, state):
        if self.engine_running: self.accelerating = state
        if state: self.cruise_active = False

    def set_brake(self, state):
        self.braking = self.brake_pressed = state
        if state: self.cruise_active = False

    def start_boost(self, event=None):
        self.boost = True;  self.boost_kickdown_done = False

    def stop_boost(self, event=None):
        self.boost = False; self.boost_kickdown_done = False

    def toggle_cruise(self, event=None):
        if not self.cruise_active and self.speed >= 30.0 and self.engine_running:
            self.cruise_active = True
            self.cruise_target = round(self.speed)
        else:
            self.cruise_active = False
        self._refresh_cruise_ui()

    def cruise_plus(self):  self.cruise_target = min(200, self.cruise_target + 1); self._refresh_cruise_ui()
    def cruise_minus(self): self.cruise_target = max(30,  self.cruise_target - 1); self._refresh_cruise_ui()

    def _refresh_cruise_ui(self):
        if self.cruise_active:
            self.cruise_val_lbl.config(text=f"{int(self.cruise_target)} km/h", fg=GREEN)
            self.cruise_status_lbl.config(text="● ACTIV", fg=GREEN)
            self.cruise_label.config(text=f"CRUISE\n{int(self.cruise_target)} km/h", fg=GREEN)
        else:
            self.cruise_val_lbl.config(text=f"{int(self.cruise_target)} km/h", fg=GRAY_LIGHT)
            self.cruise_status_lbl.config(text="● INACTIV", fg=GRAY_LIGHT)
            self.cruise_label.config(text="CRUISE\nOFF", fg=GRAY_LIGHT)

    def toggle_mode(self, event=None):
        self.current_mode_idx = (self.current_mode_idx + 1) % 3
        mode = self.modes[self.current_mode_idx]
        self.mode_label.config(text=mode.upper(), fg={'Drive': ORANGE, 'Sport': RED, 'Manual': ACCENT}[mode])

    def manual_shift_up(self, event=None):
        if self.modes[self.current_mode_idx] == 'Manual' and self.gear < 5:
            self.gear += 1; self.gear_label.config(text=str(self.gear))

    def manual_shift_down(self, event=None):
        if self.modes[self.current_mode_idx] == 'Manual' and self.gear > 1:
            if (self.speed * self.gear_ratios[self.gear - 1]) <= 7000:
                self.gear -= 1; self.gear_label.config(text=str(self.gear))

    def send_serial_data(self, spd, rpm_v):
        if not self.arduino:
            return
        now = time.time()
        if (now - self.last_serial_send) < self.serial_interval:
            return

        wt = self.water_temp
        if wt < 70:    ct = (wt / 70.0) * 23
        elif wt < 75:  ct = 23  + ((wt - 70) / 5.0)  * 22
        elif wt <= 85: ct = 45  + ((wt - 75) / 10.0) * 66
        elif wt <= 95: ct = 111 + ((wt - 85) / 10.0) * 44
        else:          ct = 155 + ((wt - 95) / 15.0) * 100
        tmp_p = 255 - int(max(0, min(255, ct)))

        packet = (f"<{int(round(spd))},{int(round(rpm_v))},{tmp_p},"
                  f"{1 if self.ignition_on else 0},{1 if self.lights_on else 0}>\n")
        try:
            self.arduino.write(packet.encode('utf-8'))
            self.arduino.readline()
            self.last_serial_send = now
        except Exception as e:
            print(f"Eroare Serial: {e}")

    def update_gui(self):
        disp_spd = self.speed
        disp_rpm = min(self.rpm, 7000.0) if self.ignition_on else 0.0

        self._move_needle(self.canvas_spd, self.needle_spd, 155, 148, 104, disp_spd, 220)
        self._move_needle(self.canvas_rpm, self.needle_rpm, 155, 148, 104, disp_rpm, 7000)
        self._move_needle(self.canvas_temp, self.needle_temp, 82, 82, 50, self.water_temp, 120,
                          start_deg=MINI_START, sweep=MINI_SWEEP)

        self.canvas_spd.itemconfig(self.spd_text, text=str(int(disp_spd)))
        self.canvas_rpm.itemconfig(self.rpm_text, text=str(int(disp_rpm)))
        self.temp_lbl.config(text=f"{int(self.water_temp)}°C")

        self.gear_label.config(text=str(self.gear) if self.engine_running else "—")

        self._set_led("ign",    self.ignition_on)
        self._set_led("eng",    self.engine_running)
        self._set_led("lights", self.lights_on)
        self._set_led("boost",  self.boost)

        self.send_serial_data(disp_spd, disp_rpm)

    def update_physics(self):
        if not self.engine_running:
            self.rpm   = 0
            self.speed = max(0.0, self.speed - 0.2)
        else:
            if self.rpm < 800:
                self.rpm = 800

            if self.ignition_on:
                if not self.temp_reached_90:
                    self.water_temp += 70.0 / 2000.0
                    if self.water_temp >= 90: self.temp_reached_90 = True
                else:
                    self.water_temp += random.uniform(-0.1, 0.1)
                    self.water_temp = max(84.0, min(95.0, self.water_temp))

            throttle = 0.0
            if self.accelerating:
                throttle = 1.0
            elif self.cruise_active:
                diff = self.cruise_target - self.speed
                if diff > 0: throttle = min(1.0, diff / 5.0)

            self.rpm = max(800.0, min(7000.0, self.speed * self.gear_ratios[self.gear]))

            mode      = self.modes[self.current_mode_idx]
            now_shift = time.time()
            can_shift = (now_shift - self.last_shift_time) >= self.shift_cooldown

            if mode in ('Drive', 'Sport') and can_shift:
                shifted  = False
                up_thr   = 6000 if mode == 'Sport' else 4000
                down_thr = 2000 if mode == 'Sport' else 1500

                if self.boost and not self.boost_kickdown_done:
                    new_gear = max(1, self.gear - (2 if mode == 'Sport' else 1))
                    if new_gear < self.gear:
                        self.gear = new_gear; shifted = True
                    self.boost_kickdown_done = True

                if not shifted and self.rpm > up_thr and self.gear < 5:
                    self.gear += 1; shifted = True
                elif not shifted and self.rpm < down_thr and self.gear > 1:
                    self.gear -= 1; shifted = True

                if not shifted and throttle < 0.2 and self.gear < 5:
                    next_rpm = self.speed * self.gear_ratios[self.gear + 1]
                    if next_rpm > down_thr and self.rpm > next_rpm + 300:
                        self.gear += 1; shifted = True

                if shifted: self.last_shift_time = now_shift

            if throttle > 0:
                pull      = 0.85 * math.exp(-0.006 * self.speed)
                aero      = max(0.0, 1.0 - (self.speed / self.car_top_speed)**2)
                rpm_mult  = 1.3 if self.rpm > 3500 else (0.6 + (self.rpm / 3500) * 0.4)
                gear_force= {1: 1.4, 2: 0.9, 3: 0.6, 4: 0.4, 5: 0.2}[self.gear]
                accel     = pull * aero * rpm_mult * gear_force * throttle
                if self.boost: accel *= 4.0
                if self.rpm < 7000.0:
                    self.speed += accel
                self.rpm = min(self.rpm, 7000.0)
            elif self.braking:
                self.speed -= 1.5
            else:
                self.speed -= (0.05 + 0.15 * (self.speed / 100)**2)

        self.speed = max(0.0, min(self.speed, self.dial_max_speed))
        self.update_gui()
        self.root.after(100, self.update_physics)


if __name__ == "__main__":
    root = tk.Tk()
    app  = CarSimulatorV2(root)
    root.mainloop()
