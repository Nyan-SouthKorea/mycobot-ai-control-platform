import cv2
import numpy as np

import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mirae_tof.etf_wrapper import FolderCapture

# ----------------------------
# 캘리브레이션 로드
# ----------------------------
data = np.load("camera_calibration/camera_calib_ir.npz")
cameraMatrix = data["cameraMatrix"]
distCoeffs = data["distCoeffs"]

# ----------------------------
# 전역 변수
# ----------------------------
clicked_points = []

# ----------------------------
# 마우스 콜백
# ----------------------------
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_points.append([x, y])
        print(f"Clicked: ({x}, {y})")

# ----------------------------
# 카메라
# ----------------------------
cap = FolderCapture()
cv2.namedWindow("undistorted")
cv2.setMouseCallback("undistorted", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    # 왜곡 보정
    undistorted = cv2.undistort(frame, cameraMatrix, distCoeffs)

    # 클릭한 점 표시
    for p in clicked_points:
        cv2.circle(undistorted, tuple(p), 6, (0, 0, 255), -1)

    cv2.imshow("undistorted", undistorted)

    # 4개 찍으면 종료
    if len(clicked_points) >= 4:
        break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()

print("\nFinal pixel points:")
for i, p in enumerate(clicked_points):
    print(f"P{i}: {p}")

'''
로봇 베이스: 143mm
베이스로부터 체커보드 거리
  - x: 100mm
  - y: 100mm

아래 계산에 적용하여 오프셋값은 (143/2) + 100 이 x가 되는거고, y는 100 - (143/2) 하면 됨  
'''


'''
<체커보드 사이즈>
- 네모 하나에 17.25mm
- 가로 170mm -> 로봇 좌표 기준 y값
- 세로 120.75mm -> 로봇 좌표 기준 x값

P0: 좌상 (120.75, 170)
P1: 우상 (120.75, 0)
P2: 우하 (0, 0)
P3: 좌하 (0, 170)


<내가 기록한 픽셀값> - 260128
(로봇 시점으로 좌상, 우상, .. 방향 설정함)
P0: [142, 169]
P1: [414, 156]
P2: [448, 346]
P3: [79, 352]

<체커보드 base 오프셋값>
로봇의 x, y 0 포인트는 실제로 로봇 base에서 
x 171.5
y 28.5
'''
