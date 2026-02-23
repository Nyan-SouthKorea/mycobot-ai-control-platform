import cv2
import numpy as np

# ----------------------------
# 캘리브레이션 결과 로드
# ----------------------------
data = np.load("./camera_calibration/camera_calib.npz")
cameraMatrix = data["cameraMatrix"]
distCoeffs = data["distCoeffs"]

# ----------------------------
# 웹캠
# ----------------------------
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 왜곡 보정
    undistorted = cv2.undistort(frame, cameraMatrix, distCoeffs)

    # 화면 출력
    cv2.imshow("original", frame)
    cv2.imshow("undistort", undistorted)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
