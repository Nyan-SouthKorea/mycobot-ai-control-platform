import cv2
import numpy as np

# ----------------------------
# 1) 캘리브레이션 로드 (undistort용)
# ----------------------------
data = np.load("camera_calibration/camera_calib.npz")
K = data["cameraMatrix"]
dist = data["distCoeffs"]

# ----------------------------
# 2) 네가 검증한 4점 (하드코딩)
#    - image_points: 픽셀 좌표
#    - world_points: 로봇 world(mm) 좌표 (체커보드 기준)
# ----------------------------
image_points = np.array([
    [463, 439],  # P0
    [54, 450],  # P1
    [56, 169],  # P2
    [449, 156],  # P3
], dtype=np.float32)

world_points = np.array([
    [120.75, 170.0],  # P0
    [120.75,   0.0],  # P1
    [  0.00,   0.0],  # P2
    [  0.00, 170.0],  # P3
], dtype=np.float32)

# 로봇 base 기준 오프셋 반영
ROBOT_OFFSET_X = 150
ROBOT_OFFSET_Y = -86.25

# ----------------------------
# 3) Homography 계산 (pixel -> world(mm))
# ----------------------------
H, _ = cv2.findHomography(image_points, world_points)
if H is None:
    raise RuntimeError("Homography 계산 실패: 4점 매칭을 확인하세요.")

last_click = None
last_text_lines = []

def pixel_to_mm(u, v):
    """pixel (u,v) -> world(mm) using homography"""
    pt = np.array([[[u, v]]], dtype=np.float32)
    w = cv2.perspectiveTransform(pt, H)[0][0]  # (X, Y)
    return float(w[0]), float(w[1])

def mouse_callback(event, x, y, flags, param):
    global last_click, last_text_lines
    if event == cv2.EVENT_LBUTTONDOWN:
        u, v = x, y

        Xw, Yw = pixel_to_mm(u, v)  # 체커보드 기준 world(mm)
        Xb = Xw + ROBOT_OFFSET_X     # 로봇 base 기준 보정
        Yb = Yw + ROBOT_OFFSET_Y

        last_click = (u, v)
        last_text_lines = [
            f"pixel  : ({u}, {v})",
            f"world  : (X={Xw:.2f} mm, Y={Yw:.2f} mm)",
            f"robot   : (X={Xb:.2f} mm, Y={Yb:.2f} mm)  [offset +{ROBOT_OFFSET_X}, {ROBOT_OFFSET_Y}]"
        ]

        print("\n".join(last_text_lines))
        print("-" * 50)

# ----------------------------
# 4) 카메라 + UI
# ----------------------------
cap = cv2.VideoCapture(0)
cv2.namedWindow("undistorted")
cv2.setMouseCallback("undistorted", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    und = cv2.undistort(frame, K, dist)

    # 기준점 4개를 화면에 표시 (확인용)
    for p in image_points.astype(int):
        cv2.circle(und, (p[0], p[1]), 6, (0, 255, 255), -1)  # 노란색 점

    # 마지막 클릭 위치 표시
    if last_click is not None:
        cv2.circle(und, last_click, 6, (0, 0, 255), -1)

        # 텍스트 표시 (좌상단)
        y0 = 25
        for i, line in enumerate(last_text_lines):
            cv2.putText(
                und, line, (10, y0 + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA
            )

    cv2.imshow("undistorted", und)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
