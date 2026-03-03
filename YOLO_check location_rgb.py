# demo_00-yolo_check_mapper.py
# YOLO 감지 bbox 중심 픽셀(u,v)을 Homography에 태워 robot 좌표(mm)를 화면에 표시하는 확인용 코드

# base
import time

# pip install
import cv2

# custom
from camera_calibration.calibration_undistort_img import Undistorter
from camera_calibration.homography_pixel_to_robot_mapper import PixelToRobotMapper
from yolo_wrapper import YOLOWrapper


# ===== 하드코딩 설정 =====
CAM_ID = 0

CALIB_NPZ_PATH = './camera_calibration/camera_calib.npz'
HOMO_JSON_PATH = './camera_calibration/homography_robot_map.json'

YOLO_WEIGHT_PATH = "YOLO_train/Dice/runs/detect/train/weights/best.pt"

CONF_TH = 0.5


# ===== 객체 생성 =====
und = Undistorter(CALIB_NPZ_PATH)
mapper = PixelToRobotMapper(HOMO_JSON_PATH)
yolo = YOLOWrapper(YOLO_WEIGHT_PATH)


# ===== 카메라 열기 =====
cap = cv2.VideoCapture(CAM_ID)
if not cap.isOpened():
    raise RuntimeError(f"Failed to open camera: {CAM_ID}")

# (선택) 화면 표시용
WIN_NAME = "YOLO + Homography Check"
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)


def _bbox_center(bbox_pixel):
    x1, y1, x2, y2 = bbox_pixel
    cx = (x1 + x2) * 0.5
    cy = (y1 + y2) * 0.5
    return cx, cy


try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame.")
            time.sleep(0.05)
            continue

        # ===== 왜곡 보정 (중요: homography가 undistorted 기준이라고 json에 명시됨) =====
        und_frame = und.undistort(frame)

        # ===== YOLO 추론 =====
        dets = yolo.infer(und_frame, confidence_threshold=CONF_TH)

        # ===== bbox 중심 -> robot 좌표 변환 =====
        for d in (dets or []):
            if "bbox_pixel" not in d:
                continue

            cx, cy = _bbox_center(d["bbox_pixel"])

            # homography 입력은 pixel(u,v) (undistorted image 좌표)
            rx, ry = mapper.pixel_to_robot(cx, cy)

            # draw()에서 출력될 수 있도록 키 추가
            d["robot_loc"] = [rx, ry]
            d["center_uv"] = [cx, cy]

        # ===== 시각화 =====
        vis = yolo.draw(und_frame, dets)

        # bbox 중심점(초록) 표시 + uv 표기(선택)
        if vis is not None:
            for d in (dets or []):
                if "center_uv" not in d:
                    continue
                cx, cy = d["center_uv"]
                cv2.circle(vis, (int(round(cx)), int(round(cy))), 4, (0, 255, 0), -1)

        cv2.imshow(WIN_NAME, vis if vis is not None else und_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # q 또는 ESC
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
