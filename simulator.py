import tkinter as tk
import math
import random
import serial
import time

class CarSimulator:
    def __init__(self, root):
        try:
            self.arduino = serial.Serial('COM4', 57600, timeout=0.01)
            print("Conectat la Arduino!")
            time.sleep(2)
        except:
            self.arduino = None
            print("Eroare: Arduino nu este conectat pe COM4.")

        self.root = root
        self.root.title("Simulator Opel Astra G")
        self.root.geometry("850x700")
        self.root.configure(bg="#1a1a1a")

        self.lights_on = False
        self.ignition_on = False
        self.engine_running = False
        self.brake_pressed = False

        self.last_serial_send_time = time.time()
        self.serial_update_interval = 0.1

        self.speed = 0.0
        self.rpm = 0.0
        self.car_top_speed = 200.0
        self.dial_max_speed = 220.0
        self.dial_max_rpm = 7000.0

        self.water_temp = 70.0
        self.target_temp = 90.0
        self.temp_reached_90 = False

        self.gear = 1
        self.modes = ['Drive', 'Sport', 'Manual']
        self.current_mode_idx = 0
        self.gear_max_speeds = {1: 54, 2: 92, 3: 140, 4: 185, 5: 235}
        self.gear_ratios = {g: 7000 / v for g, v in self.gear_max_speeds.items()}

        self.accelerating = False
        self.braking = False
        self.boost = False
        self.cruise_active = False
        self.cruise_target = 100.0

        self.setup_gui()
        self.update_physics()

    def setup_gui(self):
        gauges_frame = tk.Frame(self.root, bg="#1a1a1a")
        gauges_frame.pack(pady=20)

        self.canvas_speed = tk.Canvas(gauges_frame, width=280, height=140, bg="#1a1a1a", highlightthickness=0)
        self.canvas_speed.grid(row=0, column=0, padx=20)
        self.canvas_speed.create_arc(10, 10, 270, 270, start=0, extent=180, outline="#333", width=8, style=tk.ARC)
        self.needle_speed = self.canvas_speed.create_line(140, 130, 40, 130, width=4, fill="#ff4444")
        tk.Label(gauges_frame, text="VITEZĂ", font=("Arial", 10), bg="#1a1a1a", fg="white").grid(row=1, column=0)
        self.speed_display = tk.Label(gauges_frame, text="0 km/h", font=("Courier", 20, "bold"), bg="#1a1a1a", fg="#00ff00")
        self.speed_display.grid(row=2, column=0)

        self.canvas_rpm = tk.Canvas(gauges_frame, width=280, height=140, bg="#1a1a1a", highlightthickness=0)
        self.canvas_rpm.grid(row=0, column=1, padx=20)
        self.canvas_rpm.create_arc(10, 10, 270, 270, start=0, extent=180, outline="#333", width=8, style=tk.ARC)
        self.needle_rpm = self.canvas_rpm.create_line(140, 130, 40, 130, width=4, fill="#ff4444")
        tk.Label(gauges_frame, text="RPM x1000", font=("Arial", 10), bg="#1a1a1a", fg="white").grid(row=1, column=1)
        self.rpm_display = tk.Label(gauges_frame, text="0", font=("Courier", 20, "bold"), bg="#1a1a1a", fg="#00ff00")
        self.rpm_display.grid(row=2, column=1)

        cruise_frame = tk.Frame(self.root, bg="#1a1a1a")
        cruise_frame.pack(pady=5)
        self.btn_cruise_minus = tk.Button(cruise_frame, text="- 1", font=("Arial", 12, "bold"), bg="#333", fg="white", command=self.cruise_minus)
        self.btn_cruise_minus.grid(row=0, column=0, padx=10)
        self.cruise_label = tk.Label(cruise_frame, text="CRUISE: OFF (100)", font=("Arial", 14, "bold"), bg="#1a1a1a", fg="gray", width=20)
        self.cruise_label.grid(row=0, column=1)
        self.btn_cruise_plus = tk.Button(cruise_frame, text="+ 1", font=("Arial", 12, "bold"), bg="#333", fg="white", command=self.cruise_plus)
        self.btn_cruise_plus.grid(row=0, column=2, padx=10)

        aux_frame = tk.Frame(self.root, bg="#222", bd=2, relief=tk.RIDGE)
        aux_frame.pack(pady=20, padx=20, fill=tk.X)

        water_frame = tk.Frame(aux_frame, bg="#222")
        water_frame.pack(side=tk.LEFT, padx=40, pady=10)
        tk.Label(water_frame, text="TEMP. APĂ", font=("Arial", 10, "bold"), bg="#222", fg="white").pack()
        self.water_label = tk.Label(water_frame, text="20°C", font=("Courier", 22, "bold"), bg="#222", fg="#3498db")
        self.water_label.pack()

        ctrl_frame = tk.Frame(self.root, bg="#1a1a1a")
        ctrl_frame.pack(pady=10)
        self.mode_label = tk.Label(ctrl_frame, text="MOD: DRIVE", font=("Arial", 14, "bold"), bg="#1a1a1a", fg="#f39c12")
        self.mode_label.grid(row=0, column=0, padx=30)

        self.root.bind('<KeyPress-w>',       lambda e: self.set_accel(True))
        self.root.bind('<KeyRelease-w>',     lambda e: self.set_accel(False))
        self.root.bind('<KeyPress-W>',       lambda e: self.set_accel(True))
        self.root.bind('<KeyRelease-W>',     lambda e: self.set_accel(False))
        self.root.bind('<KeyPress-s>',       lambda e: self.set_brake(True))
        self.root.bind('<KeyRelease-s>',     lambda e: self.set_brake(False))
        self.root.bind('<KeyPress-S>',       lambda e: self.set_brake(True))
        self.root.bind('<KeyRelease-S>',     lambda e: self.set_brake(False))
        self.root.bind('a', self.manual_shift_down)
        self.root.bind('A', self.manual_shift_down)
        self.root.bind('d', self.manual_shift_up)
        self.root.bind('D', self.manual_shift_up)
        self.root.bind('e', self.start_stop_logic)
        self.root.bind('E', self.start_stop_logic)
        self.root.bind('m', self.toggle_mode)
        self.root.bind('M', self.toggle_mode)
        self.root.bind('c', self.toggle_cruise)
        self.root.bind('C', self.toggle_cruise)
        self.root.bind('<KeyPress-Shift_L>',   self.start_boost)
        self.root.bind('<KeyRelease-Shift_L>', self.stop_boost)
        self.root.bind('<KeyPress-Shift_R>',   self.start_boost)
        self.root.bind('<KeyRelease-Shift_R>', self.stop_boost)
        self.root.bind('l', self.toggle_lights)
        self.root.bind('L', self.toggle_lights)

    def toggle_lights(self, event=None):
        self.lights_on = not self.lights_on
        print(f"Lights {'ON' if self.lights_on else 'OFF'}")
        self.update_gui()

    def start_stop_logic(self, event):
        if self.engine_running:
            self.engine_running = False
            self.ignition_on = False
            print("Engine STOP")
        elif self.brake_pressed:
            self.ignition_on = True
            self.engine_running = True
            print("Engine START")
        else:
            self.ignition_on = not self.ignition_on
            print(f"Ignition {'ON' if self.ignition_on else 'OFF'}")
        self.update_gui()

    def set_accel(self, state):
        if self.engine_running: self.accelerating = state
        if state: self.cruise_active = False

    def set_brake(self, state):
        self.braking = state
        self.brake_pressed = state
        if state: self.cruise_active = False

    def start_boost(self, event): self.boost = True
    def stop_boost(self, event):  self.boost = False

    def toggle_cruise(self, event=None):
        if not self.cruise_active and self.speed >= 30.0 and self.engine_running:
            self.cruise_active = True
            self.cruise_target = round(self.speed)
        else:
            self.cruise_active = False
        self.update_cruise_ui()

    def cruise_plus(self):  self.cruise_target = min(200, self.cruise_target + 1); self.update_cruise_ui()
    def cruise_minus(self): self.cruise_target = max(30,  self.cruise_target - 1); self.update_cruise_ui()

    def update_cruise_ui(self):
        color = "#00ff00" if self.cruise_active else "gray"
        txt = f"CRUISE: {int(self.cruise_target)} km/h" if self.cruise_active else f"CRUISE: OFF ({int(self.cruise_target)})"
        self.cruise_label.config(text=txt, fg=color)

    def toggle_mode(self, event):
        self.current_mode_idx = (self.current_mode_idx + 1) % 3
        self.mode_label.config(text=f"MOD: {self.modes[self.current_mode_idx].upper()}")

    def manual_shift_up(self, event):
        if self.modes[self.current_mode_idx] == 'Manual' and self.gear < 5: self.gear += 1

    def manual_shift_down(self, event):
        if self.modes[self.current_mode_idx] == 'Manual' and self.gear > 1:
            if (self.speed * self.gear_ratios[self.gear - 1]) <= 7000: self.gear -= 1

    def send_serial_data(self, speed_val, rpm_val):
        if not self.arduino:
            return
        current_time = time.time()
        if (current_time - self.last_serial_send_time) >= self.serial_update_interval:
            spd_i = int(round(speed_val))
            rpm_i = int(round(rpm_val))

            wt = self.water_temp
            if wt < 70:    calc_t = (wt / 70.0) * 23
            elif wt < 75:  calc_t = 23  + ((wt - 70) / 5.0)  * 22
            elif wt <= 85: calc_t = 45  + ((wt - 75) / 10.0) * 66
            elif wt <= 95: calc_t = 111 + ((wt - 85) / 10.0) * 44
            else:          calc_t = 155 + ((wt - 95) / 15.0) * 100
            tmp_p = 255 - int(max(0, min(255, calc_t)))

            ign_val = 1 if self.ignition_on else 0
            lgt_val = 1 if self.lights_on else 0

            pachet = f"<{spd_i},{rpm_i},{tmp_p},{ign_val},{lgt_val}>\n"
            try:
                self.arduino.write(pachet.encode('utf-8'))
                self.last_serial_send_time = current_time
            except Exception as e:
                print(f"Eroare Serial: {e}")

    def update_gui(self):
        self.speed_display.config(text=f"{int(self.speed)} km/h")
        self.rpm_display.config(text=f"{int(self.rpm)}")
        self.water_label.config(text=f"{int(self.water_temp)}°C")

        disp_speed = self.speed
        disp_rpm = min(self.rpm, 7500)
        if not self.ignition_on and not self.engine_running:
            disp_rpm = 0

        a_s = math.radians(180 - (disp_speed / self.dial_max_speed) * 180)
        self.canvas_speed.coords(self.needle_speed, 140, 130, 140 + 110*math.cos(a_s), 130 - 110*math.sin(a_s))

        a_r = math.radians(180 - (disp_rpm / self.dial_max_rpm) * 180)
        self.canvas_rpm.coords(self.needle_rpm, 140, 130, 140 + 110*math.cos(a_r), 130 - 110*math.sin(a_r))

        self.send_serial_data(disp_speed, disp_rpm)

    def update_physics(self):
        if not self.engine_running:
            self.rpm = 0
            self.speed = max(0, self.speed - 0.2)
        else:
            if self.rpm < 800: self.rpm = 800

            if self.ignition_on:
                if not self.temp_reached_90:
                    self.water_temp += (70.0 / 2000.0)
                    if self.water_temp >= 90: self.temp_reached_90 = True
                else:
                    self.water_temp += random.uniform(-0.1, 0.1)
                    self.water_temp = max(84.0, min(95.0, self.water_temp))

            throttle_input = 0.0
            if self.accelerating: throttle_input = 1.0
            elif self.cruise_active:
                diff = self.cruise_target - self.speed
                if diff > 0: throttle_input = min(1.0, diff / 5.0)

            calculated_rpm = self.speed * self.gear_ratios[self.gear]
            self.rpm = max(800.0, calculated_rpm)

            mode = self.modes[self.current_mode_idx]
            if mode == 'Drive':
                if self.rpm > 4000 and self.gear < 5: self.gear += 1
                elif self.rpm < 1500 and self.gear > 1: self.gear -= 1
            elif mode == 'Sport':
                if self.rpm > 6000 and self.gear < 5: self.gear += 1
                elif self.rpm < 2000 and self.gear > 1: self.gear -= 1

            if throttle_input > 0:
                pull = 0.85 * math.exp(-0.006 * self.speed)
                aero = max(0.0, 1.0 - (self.speed / self.car_top_speed)**2)
                rpm_m = 1.3 if self.rpm > 3500 else (0.6 + (self.rpm/3500)*0.4)
                g_f = {1:1.4, 2:0.9, 3:0.6, 4:0.4, 5:0.2}[self.gear]
                accel_val = (pull * aero * rpm_m * g_f) * throttle_input
                if self.boost: accel_val *= 4.0
                self.speed += accel_val
                if self.rpm >= 7000: self.speed -= 0.5
            elif self.braking:
                self.speed -= 1.5
            else:
                self.speed -= (0.05 + 0.15 * (self.speed/100)**2)

        self.speed = max(0.0, min(self.speed, self.dial_max_speed))
        self.update_gui()
        self.root.after(100, self.update_physics)

if __name__ == "__main__":
    root = tk.Tk()
    app = CarSimulator(root)
    root.mainloop()
