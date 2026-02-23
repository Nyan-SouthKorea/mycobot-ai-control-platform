import time
from pymycobot import MyCobotSocket
import threading


class MyCobotController:
    """
    Thin wrapper for MyCobotSocket.
    - connect/disconnect
    - power on/off
    - torque on/off (focus/release)
    - stop, home
    - move joints / move world coords
    - gripper open/close/value
    - simple pick & place sequence helpers
    """

    def __init__(self, path_ip_and_host, default_speed=40):
        # ip 정보 읽어오기
        with open(path_ip_and_host, 'r', encoding='utf-8') as f:
            f = f.read()
            ip, port = f.split(', ')
            print(f'IP주소: {ip}, 포트: {port}')

        self.ip = ip
        self.port = int(port)
        self.default_speed = int(default_speed)

        self.mc = None
        self.connected = False

        # Pick & Place 기본 파라미터 (원하면 메인에서 바꿔도 됨)
        self.approach_z = 80     # mm (물체 위 접근 높이)
        self.pick_z = 20         # mm (집는 높이)
        self.safe_z = 120        # mm (이동 중 안전 높이)

        # 자세(필요하면 네 셋업에 맞게 수정)
        self.rx = 180
        self.ry = 0
        self.rz = 0

        # send_coords mode (0: 각도 보간 기반 일반 이동, 1: 직선 보간 등)
        self.move_mode = 0

        # 동작 후 대기(너무 빠르게 연속 명령 보내는 것 방지)
        self.cmd_sleep = 0.0

        self._gripper_lock = threading.Lock()


    # ---------------- connection ----------------
    def connect(self):
        if self.connected:
            return True

        self.mc = MyCobotSocket(self.ip, self.port)
        self.connected = True

        # 연결 체크 (응답 없으면 -1)
        try:
            ic = self.mc.is_controller_connected()
            if ic == -1:
                # 연결은 됐지만 로봇이 응답이 없을 수 있음
                return False
        except Exception:
            return False

        return True

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

    def _require(self):
        if (not self.connected) or (self.mc is None):
            raise RuntimeError("Robot not connected. Call connect() first.")

    # ---------------- basic robot controls ----------------
    def power_on(self):
        self._require()
        self.mc.power_on()
        time.sleep(self.cmd_sleep)

    def power_off(self):
        self._require()
        self.mc.power_off()
        time.sleep(self.cmd_sleep)

    def torque_on(self):
        self._require()
        self.mc.focus_all_servos()
        time.sleep(self.cmd_sleep)

    def torque_off(self):
        self._require()
        self.mc.release_all_servos()
        time.sleep(self.cmd_sleep)

    def stop(self):
        self._require()
        self.mc.stop()
        time.sleep(self.cmd_sleep)

    def home(self, speed=None):
        self._require()
        if speed is None:
            speed = self.default_speed
        self.mc.go_home()
        time.sleep(self.cmd_sleep)

    # ---------------- state read ----------------
    def get_angles(self):
        self._require()
        return self.mc.get_angles()

    def get_coords(self):
        self._require()
        return self.mc.get_coords()

    # ---------------- motion ----------------
    def move_joints(self, angles_deg, speed=None):
        self._require()
        if speed is None:
            speed = self.default_speed

        if (not isinstance(angles_deg, list)) or (len(angles_deg) != 6):
            raise ValueError("angles_deg must be a list of 6 numbers")

        self.mc.send_angles(angles_deg, int(speed))
        time.sleep(self.cmd_sleep)

    # def move_world(self, x, y, z, rx=None, ry=None, rz=None, speed=None, mode=None):
    def move_world(self, points, mode, speed=None):
        if speed is None:
            speed = self.default_speed


        x, y, z, rx, ry, rz = points
        self._require()

        coords = [float(x), float(y), float(z), float(rx), float(ry), float(rz)]
        self.mc.send_coords(coords, int(speed), int(mode))
        time.sleep(self.cmd_sleep)

    # ---------------- gripper ----------------
    '''
    (generate.py 라는 코드 안에 안에 코드를 추가해놓음)
    def set_gripper_ryan(self, encoder_value, speed=100):
        return self.set_encoder(7, int(encoder_value), int(speed))
    
    '''

    def _gripper_alive(self):
        try:
            v = self.mc.get_encoder(7)
            if v is None:
                return False
            if v == -1:
                return False
            return True
        except Exception:
            return False


    def _wait_gripper_reconnect(self, timeout=30.0, sleep=0.2):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._gripper_alive():
                return True
            time.sleep(sleep)
        return False


    def _gripper_read_encoder(self):
        try:
            v = self.mc.get_encoder(7)
            return None if (v is None or v == -1) else int(v)
        except Exception:
            return None

    def _wait_gripper_motion(self, prev_enc, timeout=2.0, sleep=0.05, min_delta=200):
        t0 = time.time()
        while time.time() - t0 < timeout:
            cur = self._gripper_read_encoder()
            if cur is None:
                time.sleep(sleep)
                continue
            if prev_enc is None:
                return True
            if abs(cur - prev_enc) >= min_delta:
                return True
            time.sleep(sleep)
        return False


    def gripper_init(self):
        with self._gripper_lock:
            print('그리퍼 초기화 중...', end=' ')

            self.mc.set_gripper_calibration()
            time.sleep(0.6)
            self.mc.set_gripper_ryan(2048+800, speed=80)
            time.sleep(0.6)
            self.mc.set_gripper_calibration()
            time.sleep(0.6)

            print('완료')
            return True

    def gripper_open(self, speed=100):
        with self._gripper_lock:
            print('그리퍼 여는 중...', end=' ')

            # 1) 명령 전 엔코더 스냅샷
            prev = self._gripper_read_encoder()

            # 2) 명령 1~3회 재전송 (드롭 대비)
            ok = False
            for _ in range(3):
                self.mc.set_gripper_ryan(2048, speed=speed)
                ok = self._wait_gripper_motion(prev, timeout=1.0)
                if ok:
                    break
                time.sleep(0.1)

            print('완료' if ok else 'FAIL(씹힘)')
            return ok

    def gripper_open_retry(self, speed=100):
        while True:
            ret = self.gripper_open()
            if ret == True:
                break
            else:
                self.gripper_init()
                self.gripper_close()

    def gripper_close(self, speed=100):
        with self._gripper_lock:
            print('그리퍼 닫는 중...', end=' ')

            prev = self._gripper_read_encoder()

            ok = False
            for _ in range(3):
                self.mc.set_gripper_ryan(2048-800, speed=speed)
                ok = self._wait_gripper_motion(prev, timeout=1.0)
                if ok:
                    break
                time.sleep(0.1)

            print('완료' if ok else 'FAIL(씹힘)')
            return ok

    def gripper_close_retry(self, speed=100):
        while True:
            ret = self.gripper_close()
            if ret == True:
                break
            else:
                self.gripper_init()

    def gripper_set_value(self, value, speed=50):
        self._require()
        self.mc.set_gripper_value(int(value), int(speed))
        # time.sleep(self.cmd_sleep)
        time.sleep(0.7)

    def gripper_get_value(self):
        self._require()
        return self.mc.get_gripper_value()

    # ---------------- simple pick & place helpers ----------------
    def set_tool_rpy(self, rx, ry, rz):
        self.rx = float(rx)
        self.ry = float(ry)
        self.rz = float(rz)

    def set_pick_params(self, approach_z=None, pick_z=None, safe_z=None):
        if approach_z is not None:
            self.approach_z = float(approach_z)
        if pick_z is not None:
            self.pick_z = float(pick_z)
        if safe_z is not None:
            self.safe_z = float(safe_z)

    def go_safe(self, speed=None):
        # 현재 위치의 x,y 유지하고 z만 safe로 올리는 동작을 하고 싶으면 get_coords를 써도 됨
        self._require()
        c = self.get_coords()
        if isinstance(c, list) and len(c) == 6:
            self.move_world(c[0], c[1], self.safe_z, c[3], c[4], c[5], speed=speed)
        else:
            # 읽기 실패 시 그냥 home으로 회피
            self.home(speed=speed)

    def go_safe_z(self, speed=None):
        """
        현재 x,y,rpy는 유지하고 z만 safe_z로 올림
        """
        self._require()
        if speed is None:
            speed = self.default_speed

        c = self.get_coords()
        if not (isinstance(c, list) and len(c) == 6):
            raise RuntimeError("Failed to read current coords")

        self.move_world(
            c[0],           # x 유지
            c[1],           # y 유지
            self.safe_z,    # z만 올림
            c[3], c[4], c[5],
            speed=speed
        )

    def pick_at(self, x, y, speed=None, grip_speed=50):
        """
        매우 단순한 pick 시퀀스:
        1) safe_z로 이동(현재 x,y에서)
        2) (x,y,approach_z)로 이동
        3) (x,y,pick_z)로 하강
        4) gripper close
        5) approach_z로 상승
        6) safe_z로 상승
        """
        self._require()
        if speed is None:
            speed = self.default_speed

        # 안전 높이로 먼저 올리기
        self.go_safe(speed=speed)

        # 접근
        self.move_world(x, y, self.approach_z, speed=speed)
        # 집기 높이
        self.move_world(x, y, self.pick_z, speed=speed)

        # 그리퍼 닫기
        self.gripper_close(speed=grip_speed)

        # 상승
        self.move_world(x, y, self.approach_z, speed=speed)
        self.go_safe(speed=speed)

    def place_at(self, x, y, speed=None, grip_speed=50):
        """
        매우 단순한 place 시퀀스:
        1) safe_z
        2) (x,y,approach_z)
        3) (x,y,pick_z)로 하강(= 내려놓는 높이)
        4) gripper open
        5) approach_z 상승
        6) safe_z
        """
        self._require()
        if speed is None:
            speed = self.default_speed

        self.go_safe(speed=speed)

        self.move_world(x, y, self.approach_z, speed=speed)
        self.move_world(x, y, self.pick_z, speed=speed)

        self.gripper_open(speed=grip_speed)

        self.move_world(x, y, self.approach_z, speed=speed)
        self.go_safe(speed=speed)


