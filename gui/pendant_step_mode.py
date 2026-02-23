"""
Step-based Minimal Teaching Pendant for myCobot (MyCobotSocket, pymycobot 4.0.3)

Why step-based?
- jog_* is continuous motion and can feel laggy with click events over TCP.
- Step mode reads current state, computes target, and sends one motion command.

Features:
- Connect / Disconnect
- Motor Power ON/OFF
- Servo Torque ON/OFF (focus/release)
- Live Angles + Coords display
- Mode toggle: WORLD / JOINT
- 6-axis +/- step buttonsF
  - JOINT: step in degrees per click
  - WORLD: XYZ step in mm per click; RXRYRZ step in degrees per click
- Speed slider
- STOP / HOME
- Save current pose (angles+coords) to JSONL
"""

import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from pymycobot import MyCobotSocket

# ip 정보 읽어오기
with open('IP_info.txt', 'r', encoding='utf-8') as f:
    f = f.read()
    ip, port = f.split(', ')
    port = int(port)
    print(f'IP주소: {ip}, 포트: {port}')


class PendantApp(tk.Tk):
    def __init__(self, ip, port):
        super().__init__()
        self.title("myCobot Teaching Pendant (STEP mode)")
        self.geometry("1050x700")

        # Connection / robot object
        self.mc = None
        self.connected = False

        # UI state
        self.mode = tk.StringVar(value="WORLD")  # WORLD or JOINT
        # self.ip_var = tk.StringVar(value="192.168.31.239")
        # self.port_var = tk.IntVar(value=9000)

        self.ip_var = tk.StringVar(value=ip)
        self.port_var = tk.IntVar(value=port)


        self.speed_var = tk.IntVar(value=40)
        self.joint_step_deg_var = tk.DoubleVar(value=2.0)   # per click
        self.world_step_mm_var = tk.DoubleVar(value=10.0)   # per click for X/Y/Z
        self.world_step_deg_var = tk.DoubleVar(value=5.0)   # per click for RX/RY/RZ

        self.refresh_ms = 300  # live refresh rate

        self.angles_vars = [tk.StringVar(value="—") for _ in range(6)]
        self.coords_vars = [tk.StringVar(value="—") for _ in range(6)]
        self.status_var = tk.StringVar(value="DISCONNECTED")

        # Concurrency
        self._move_lock = threading.Lock()
        self._stop_refresh = False

        self._build_ui()
        self._schedule_refresh()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- UI ----------------
    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        # Connection
        conn = ttk.LabelFrame(root, text="Connection", padding=10)
        conn.pack(fill="x")

        ttk.Label(conn, text="IP:").grid(row=0, column=0, sticky="w")
        ttk.Entry(conn, textvariable=self.ip_var, width=18).grid(row=0, column=1, padx=(6, 16))

        ttk.Label(conn, text="Port:").grid(row=0, column=2, sticky="w")
        ttk.Entry(conn, textvariable=self.port_var, width=8).grid(row=0, column=3, padx=(6, 16))

        ttk.Button(conn, text="Connect", command=self.connect).grid(row=0, column=4, padx=6)
        ttk.Button(conn, text="Disconnect", command=self.disconnect).grid(row=0, column=5, padx=6)

        ttk.Label(conn, text="Status:").grid(row=0, column=6, sticky="e", padx=(20, 6))
        ttk.Label(conn, textvariable=self.status_var, width=32).grid(row=0, column=7, sticky="w")

        conn.columnconfigure(7, weight=1)

        # Main split
        mid = ttk.Frame(root)
        mid.pack(fill="both", expand=True, pady=10)

        # Left controls
        ctrl = ttk.LabelFrame(mid, text="Controls", padding=10)
        ctrl.pack(side="left", fill="y")

        ttk.Label(ctrl, text="Mode:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(ctrl, text="WORLD", variable=self.mode, value="WORLD").grid(row=0, column=1, sticky="w", padx=6)
        ttk.Radiobutton(ctrl, text="JOINT", variable=self.mode, value="JOINT").grid(row=0, column=2, sticky="w", padx=6)

        # Speed
        ttk.Label(ctrl, text="Speed:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        speed = ttk.Scale(ctrl, from_=1, to=100, orient="horizontal",
                          command=lambda v: self.speed_var.set(int(float(v))))
        speed.set(self.speed_var.get())
        speed.grid(row=1, column=1, columnspan=2, sticky="we", padx=6, pady=(12, 0))
        ttk.Label(ctrl, textvariable=self.speed_var, width=5).grid(row=1, column=3, sticky="w", pady=(12, 0))

        ttk.Separator(ctrl).grid(row=2, column=0, columnspan=4, sticky="we", pady=12)

        # Step settings
        ttk.Label(ctrl, text="STEP settings (per click):").grid(row=3, column=0, columnspan=4, sticky="w")

        # Joint step
        ttk.Label(ctrl, text="JOINT step (deg):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        joint_step = ttk.Scale(ctrl, from_=0.1, to=15.0, orient="horizontal",
                               command=lambda v: self.joint_step_deg_var.set(round(float(v), 1)))
        joint_step.set(self.joint_step_deg_var.get())
        joint_step.grid(row=4, column=1, columnspan=2, sticky="we", padx=6, pady=(8, 0))
        ttk.Label(ctrl, textvariable=self.joint_step_deg_var, width=6).grid(row=4, column=3, sticky="w", pady=(8, 0))

        # World XYZ step
        ttk.Label(ctrl, text="WORLD XYZ step (mm):").grid(row=5, column=0, sticky="w", pady=(8, 0))
        world_mm = ttk.Scale(ctrl, from_=0.5, to=50.0, orient="horizontal",
                             command=lambda v: self.world_step_mm_var.set(round(float(v), 1)))
        world_mm.set(self.world_step_mm_var.get())
        world_mm.grid(row=5, column=1, columnspan=2, sticky="we", padx=6, pady=(8, 0))
        ttk.Label(ctrl, textvariable=self.world_step_mm_var, width=6).grid(row=5, column=3, sticky="w", pady=(8, 0))

        # World RPY step
        ttk.Label(ctrl, text="WORLD RPY step (deg):").grid(row=6, column=0, sticky="w", pady=(8, 0))
        world_deg = ttk.Scale(ctrl, from_=0.5, to=30.0, orient="horizontal",
                              command=lambda v: self.world_step_deg_var.set(round(float(v), 1)))
        world_deg.set(self.world_step_deg_var.get())
        world_deg.grid(row=6, column=1, columnspan=2, sticky="we", padx=6, pady=(8, 0))
        ttk.Label(ctrl, textvariable=self.world_step_deg_var, width=6).grid(row=6, column=3, sticky="w", pady=(8, 0))

        ttk.Separator(ctrl).grid(row=7, column=0, columnspan=4, sticky="we", pady=12)

        # Power / torque
        ttk.Button(ctrl, text="Power ON", command=self.power_on).grid(row=8, column=0, columnspan=2, sticky="we", padx=2, pady=2)
        ttk.Button(ctrl, text="Power OFF", command=self.power_off).grid(row=8, column=2, columnspan=2, sticky="we", padx=2, pady=2)

        ttk.Button(ctrl, text="Torque ON (focus_all_servos)", command=self.focus_all).grid(row=9, column=0, columnspan=4, sticky="we", padx=2, pady=2)
        ttk.Button(ctrl, text="Torque OFF (release_all_servos)", command=self.release_all).grid(row=10, column=0, columnspan=4, sticky="we", padx=2, pady=2)

        ttk.Separator(ctrl).grid(row=11, column=0, columnspan=4, sticky="we", pady=12)

        ttk.Button(ctrl, text="STOP", command=self.stop).grid(row=12, column=0, columnspan=2, sticky="we", padx=2, pady=2)
        ttk.Button(ctrl, text="HOME", command=self.go_home).grid(row=12, column=2, columnspan=2, sticky="we", padx=2, pady=2)

        ttk.Separator(ctrl).grid(row=13, column=0, columnspan=4, sticky="we", pady=12)

        ttk.Button(ctrl, text="Save Pose (angles+coords)", command=self.save_pose).grid(row=14, column=0, columnspan=4, sticky="we", padx=2, pady=2)

        for i in range(4):
            ctrl.columnconfigure(i, weight=1)

        # Right side: live data + step pad
        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        disp = ttk.LabelFrame(right, text="Live Data", padding=10)
        disp.pack(fill="x")

        ttk.Label(disp, text="Angles (deg):").grid(row=0, column=0, sticky="w")
        for i in range(6):
            ttk.Label(disp, text=f"J{i+1}").grid(row=1, column=i, padx=4)
            ttk.Label(disp, textvariable=self.angles_vars[i], width=12).grid(row=2, column=i, padx=4)

        ttk.Label(disp, text="Coords (x,y,z,rx,ry,rz):").grid(row=3, column=0, sticky="w", pady=(10, 0))
        labels = ["X", "Y", "Z", "RX", "RY", "RZ"]
        for i, lab in enumerate(labels):
            ttk.Label(disp, text=lab).grid(row=4, column=i, padx=4, pady=(0, 2))
            ttk.Label(disp, textvariable=self.coords_vars[i], width=12).grid(row=5, column=i, padx=4)

        # Step pad
        pad = ttk.LabelFrame(right, text="STEP Pad (+ / -)  (One click = one step)", padding=10)
        pad.pack(fill="both", expand=True, pady=(10, 0))

        world_axes = ["X", "Y", "Z", "RX", "RY", "RZ"]
        ttk.Label(pad, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(pad, text="- STEP").grid(row=0, column=1)
        ttk.Label(pad, text="+ STEP").grid(row=0, column=2)
        ttk.Label(pad, text="Behavior: WORLD→coords step, JOINT→angle step").grid(row=0, column=3, sticky="w", padx=(10, 0))

        for r in range(6):
            ttk.Label(pad, text=f"{world_axes[r]} / J{r+1}").grid(row=r+1, column=0, sticky="w", pady=6)

            b_minus = ttk.Button(pad, text="  -  ", width=8,
                                 command=lambda idx=r: self.step_move(idx, sign=-1))
            b_plus = ttk.Button(pad, text="  +  ", width=8,
                                command=lambda idx=r: self.step_move(idx, sign=+1))

            b_minus.grid(row=r+1, column=1, padx=6, sticky="w")
            b_plus.grid(row=r+1, column=2, padx=6, sticky="w")

        pad.columnconfigure(3, weight=1)

    # ---------------- Connection ----------------
    def _require(self):
        if not self.connected or self.mc is None:
            raise RuntimeError("Not connected. Click Connect first.")

    def connect(self):
        if self.connected:
            return
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get())
        try:
            self.mc = MyCobotSocket(ip, port)
            self.connected = True
            self.status_var.set("CONNECTED")
            # quick health note
            ic = self.mc.is_controller_connected()
            if ic == -1:
                self.status_var.set("CONNECTED (robot not responding)")
        except Exception as e:
            self.connected = False
            self.mc = None
            messagebox.showerror("Connect failed", str(e))
            self.status_var.set("DISCONNECTED")

    def disconnect(self):
        try:
            if self.mc:
                try:
                    self.mc.stop()
                except Exception:
                    pass
                try:
                    self.mc.close()
                except Exception:
                    pass
        finally:
            self.mc = None
            self.connected = False
            self.status_var.set("DISCONNECTED")

    def on_close(self):
        self._stop_refresh = True
        try:
            self.disconnect()
        finally:
            self.destroy()

    # ---------------- Basic actions ----------------
    def power_on(self):
        try:
            self._require()
            self.mc.power_on()
        except Exception as e:
            messagebox.showerror("Power ON error", str(e))

    def power_off(self):
        try:
            self._require()
            self.mc.power_off()
        except Exception as e:
            messagebox.showerror("Power OFF error", str(e))

    def focus_all(self):
        try:
            self._require()
            self.mc.focus_all_servos()
        except Exception as e:
            messagebox.showerror("Torque ON error", str(e))

    def release_all(self):
        try:
            self._require()
            self.mc.release_all_servos()
        except Exception as e:
            messagebox.showerror("Torque OFF error", str(e))

    def stop(self):
        try:
            self._require()
            self.mc.stop()
        except Exception as e:
            messagebox.showerror("Stop error", str(e))

    def go_home(self):
        try:
            self._require()
            self.mc.go_home()
        except Exception as e:
            messagebox.showerror("Home error", str(e))

    # ---------------- STEP Move (threaded) ----------------
    def step_move(self, axis_index: int, sign: int):
        """
        axis_index: 0..5 representing:
          - WORLD: X,Y,Z,RX,RY,RZ
          - JOINT: J1..J6
        sign: -1 or +1
        """
        try:
            self._require()
        except Exception as e:
            messagebox.showerror("Not connected", str(e))
            return

        # Avoid spamming concurrent moves if user clicks too fast.
        if self._move_lock.locked():
            # Optional: silently ignore or show status
            self.status_var.set("BUSY (wait for last step)")
            return

        threading.Thread(
            target=self._step_move_worker,
            args=(axis_index, sign),
            daemon=True
        ).start()

    def _step_move_worker(self, axis_index: int, sign: int):
        with self._move_lock:
            try:
                speed = int(self.speed_var.get())

                if self.mode.get() == "JOINT":
                    step_deg = float(self.joint_step_deg_var.get()) * sign

                    angles = self.mc.get_angles()
                    if not (isinstance(angles, list) and len(angles) == 6):
                        self._set_status_safe("READ FAIL (angles)")
                        return

                    target = angles[:]
                    target[axis_index] = float(target[axis_index]) + step_deg

                    # Send one absolute command
                    self.mc.send_angles(target, speed)
                    self._set_status_safe(f"JOINT STEP: J{axis_index+1} {'+' if sign>0 else '-'}{abs(step_deg):.1f}° @ {speed}")

                else:
                    # WORLD
                    coords = self.mc.get_coords()
                    if not (isinstance(coords, list) and len(coords) == 6):
                        self._set_status_safe("READ FAIL (coords)")
                        return

                    target = coords[:]

                    if axis_index <= 2:
                        step_mm = float(self.world_step_mm_var.get()) * sign
                        target[axis_index] = float(target[axis_index]) + step_mm
                        label = f"{['X','Y','Z'][axis_index]} {'+' if sign>0 else '-'}{abs(step_mm):.1f}mm"
                    else:
                        step_deg = float(self.world_step_deg_var.get()) * sign
                        target[axis_index] = float(target[axis_index]) + step_deg
                        label = f"{['RX','RY','RZ'][axis_index-3]} {'+' if sign>0 else '-'}{abs(step_deg):.1f}°"

                    # mode=0 is generally safer than linear mode=1 for quick teaching steps
                    self.mc.send_coords(target, speed, 0)
                    self._set_status_safe(f"WORLD STEP: {label} @ {speed}")

            except Exception as e:
                self._show_error_safe("STEP move error", str(e))

    # ---------------- Save pose ----------------
    def save_pose(self):
        try:
            self._require()
            angles = self.mc.get_angles()
            coords = self.mc.get_coords()
            record = {
                "ts": time.time(),
                "angles_deg": angles,
                "coords": coords
            }
            path = "teach_poses.jsonl"
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.status_var.set(f"Saved pose -> {path}")
        except Exception as e:
            messagebox.showerror("Save pose error", str(e))

    # ---------------- Live refresh ----------------
    def _schedule_refresh(self):
        if not self._stop_refresh:
            self.after(self.refresh_ms, self._refresh_loop)

    def _refresh_loop(self):
        if self.connected and self.mc:
            try:
                angles = self.mc.get_angles()
                coords = self.mc.get_coords()

                if isinstance(angles, list) and len(angles) == 6:
                    for i in range(6):
                        self.angles_vars[i].set(f"{float(angles[i]):.2f}")
                else:
                    for i in range(6):
                        self.angles_vars[i].set("—")

                if isinstance(coords, list) and len(coords) == 6:
                    for i in range(6):
                        self.coords_vars[i].set(f"{float(coords[i]):.2f}")
                else:
                    for i in range(6):
                        self.coords_vars[i].set("—")

                ic = self.mc.is_controller_connected()
                if ic == -1:
                    self.status_var.set("CONNECTED (robot not responding)")
                else:
                    # If busy, keep busy message; else show connected
                    if not self._move_lock.locked() and "STEP" not in self.status_var.get():
                        self.status_var.set("CONNECTED")

            except Exception:
                # Don't crash GUI; just mark stale
                for i in range(6):
                    self.angles_vars[i].set("—")
                    self.coords_vars[i].set("—")
                self.status_var.set("CONNECTED (read error)")

        self._schedule_refresh()

    # ---------------- Thread-safe UI helpers ----------------
    def _set_status_safe(self, text: str):
        self.after(0, lambda: self.status_var.set(text))

    def _show_error_safe(self, title: str, msg: str):
        def _show():
            messagebox.showerror(title, msg)
            self.status_var.set("ERROR")
        self.after(0, _show)


if __name__ == "__main__":
    app = PendantApp(ip, port)
    app.mainloop()
