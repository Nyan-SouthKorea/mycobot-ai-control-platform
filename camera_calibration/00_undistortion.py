import cv2
import glob
import numpy as np

# ----------------------------
# 체커보드 설정
# ----------------------------
CHECKERBOARD = (9, 6)        # inner corners
SQUARE_SIZE = 17.25          # mm

# ----------------------------
# 준비
# ----------------------------
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

objpoints = []  # 3D (world)
imgpoints = []  # 2D (image)

images = glob.glob("camera_calibration/checkerboard_imgs/*.jpg")

# ----------------------------
# 코너 검출
# ----------------------------
for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

    if ret:
        corners = cv2.cornerSubPix(
            gray, corners, (11, 11), (-1, -1),
            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        )
        objpoints.append(objp)
        imgpoints.append(corners)

# ----------------------------
# 캘리브레이션
# ----------------------------
ret, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print("Camera Matrix:\n", cameraMatrix)
print("Dist Coeffs:\n", distCoeffs)

# 저장
np.savez("camera_calib.npz",
         cameraMatrix=cameraMatrix,
         distCoeffs=distCoeffs)
