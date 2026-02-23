# base
import time
from copy import deepcopy
import threading

# pip install
import cv2

# custom
from camera_calibration.calibration_undistort_img import Undistorter
from camera_calibration.homography_pixel_to_robot_mapper import PixelToRobotMapper
from mycobot_wrapper import MyCobotController
from yolo_wrapper import YOLOWrapper

class YOLO_thread:
    def __init__(self, model_path, calib_path, homo_path, cam_id):
        self.model = YOLOWrapper(model_path)
        self.und = Undistorter(calib_path)
        self.mapper = PixelToRobotMapper(homo_path)
        self.cam_id = cam_id

        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        cap = cv2.VideoCapture(self.cam_id)
        while True:
            # 카메라 이미지 수신
            ret, img = cap.read()
            if ret == False:
                print('카메라 수신이 안됩니다.')
                time.sleep(0.5)
                continue

            # Undistortion 수행
            img = self.und.undistort(img)

            # 사물 인식
            results = self.model.infer(img, confidence_threshold=0.5)

            # 가장 conf 높은 한 놈 고르기
            results = sorted(results, key=lambda x: x["conf"], reverse=True)
            for i, result in enumerate(results):
                # bbox 중심 -> robot 좌표 변환
                cx, cy = self.model.bbox_center(result['bbox_pixel'])
                # homography 입력은 pixel(u,v) (undistorted image 좌표)
                rx, ry = self.mapper.pixel_to_robot(cx, cy)
                # draw()에서 출력될 수 있도록 키 추가
                results[i]["robot_loc"] = [rx, ry]
            
            # 외부 로봇 활용 용도
            self.results = deepcopy(results)

            # 시각화
            vis = self.model.draw(img, results)
            cv2.imshow('Vis Robot Object Detection', vis)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q 또는 ESC
                break

def apply_offset(pos, offset):
    new_pos = deepcopy(pos)
    new_pos[0] += offset['x']
    new_pos[1] += offset['y']
    return new_pos

# ===== 하드코딩 설정 =====
CAM_ID = 0
CALIB_NPZ_PATH = './camera_calibration/camera_calib.npz'
HOMO_JSON_PATH = './camera_calibration/homography_robot_map.json'
YOLO_WEIGHT_PATH = "YOLO_train/Dice/runs/detect/train/weights/best.pt"
ROBOT_IP_PATH = './IP_info.txt'

# 로봇 이동 속도 (%)
ROBOT_SPEED = 50
MOVE_DELAY = 0.3

yolo_thread = YOLO_thread(YOLO_WEIGHT_PATH, CALIB_NPZ_PATH, HOMO_JSON_PATH, CAM_ID)
robot = MyCobotController(ROBOT_IP_PATH, default_speed=ROBOT_SPEED)

# (선택) 로봇 연결/전원은 여기서만 해두고, 실제 동작 로직은 아래에서 작성해도 됨
robot.connect()
robot.power_on()
robot.torque_on()
robot.gripper_init()
time.sleep(1)


# ===== 주사위 원점(Robot 좌표) =====
# YOLO_check location.py를 키고 잡을 위치에 물체를 둔 다음에 x, y를 측정하여 기입.
OBJECT_ORIGIN_MM = {'x':254.7, 'y':3.8}

# ===== 로봇 포지션 설정(상수) =====
# Pick Approach (Z값)
PICK_APPROACH = 120

# 카메라 대기 위치
LOC_ORIGIN_mm = [170, 0, 290, -92, 44, -90]

# Pick
LOC_pick_mm = [240, 0, 124, 180, 5, -132]

# Pick Approach
LOC_pick_appro_mm = deepcopy(LOC_pick_mm)
LOC_pick_appro_mm[2] += PICK_APPROACH

# 물체 버리는 위치
LOC_THROW_mm = deepcopy(LOC_pick_mm)
LOC_THROW_mm[0] -= 0
LOC_THROW_mm[2] += 20



# 반복문 시작
while True:
    # 기본 자세 이동
    robot.move_world(LOC_ORIGIN_mm, 1)
    time.sleep(MOVE_DELAY*2)

    # 인식된 주사위가 1개 이상 있는지 확인
    results_from_thread = deepcopy(yolo_thread.results)
    if len(results_from_thread) == 0:
        continue

    # 인식된 주사위의 위치 확인(conf 1등만)
    result = results_from_thread[0]
    obj_loc = {'x':result['robot_loc'][0], 'y':result['robot_loc'][1]}

    # 물체 위치 + 물체 등록 오프셋값 반영
    offset = {
        'x': obj_loc['x'] - OBJECT_ORIGIN_MM['x'],
        'y': obj_loc['y'] - OBJECT_ORIGIN_MM['y']
    }
    
    # Pick approach
    robot.move_world(apply_offset(LOC_pick_appro_mm, offset), 1)
    time.sleep(MOVE_DELAY)

    # Pick
    robot.move_world(apply_offset(LOC_pick_mm, offset), 1)
    time.sleep(MOVE_DELAY)

    # 그리퍼 닫기
    robot.gripper_close_retry()

    # Pick Depart
    robot.move_world(apply_offset(LOC_pick_appro_mm, offset), 1)
    time.sleep(MOVE_DELAY)

    # 버리는 곳으로 이동
    robot.move_world(LOC_THROW_mm, 1)
    time.sleep(MOVE_DELAY)

    # 그리퍼 놓기
    robot.gripper_open_retry()




# 로직 종료
cap.release()
cv2.destroyAllWindows()
robot.disconnect()







