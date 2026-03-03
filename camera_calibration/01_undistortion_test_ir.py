import cv2
import numpy as np

import os
import sys
import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mirae_tof.etf_wrapper import FolderCapture

# ----------------------------
# 캘리브레이션 결과 로드
# ----------------------------
data = np.load("./camera_calibration/camera_calib_ir.npz")
cameraMatrix = data["cameraMatrix"]
distCoeffs = data["distCoeffs"]

# ----------------------------
# 웹캠
# ----------------------------
cap = FolderCapture()

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    # 왜곡 보정
    undistorted = cv2.undistort(frame, cameraMatrix, distCoeffs)

    # 화면 출력
    cv2.imshow("original", frame)
    cv2.imshow("undistort", undistorted)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
