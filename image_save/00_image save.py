import cv2
import os

# =========================
# 하드코딩 설정
# =========================
SAVE_DIR = "captured_images"
CAM_ID = 0
START_INDEX = 0
# =========================

os.makedirs(SAVE_DIR, exist_ok=True)

cap = cv2.VideoCapture(CAM_ID)
idx = START_INDEX

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Webcam", frame)

    key = cv2.waitKey(1) & 0xFF

    # s 키 → 이미지 저장
    if key == ord('s'):
        filename = f"{idx:04d}.jpg"
        path = os.path.join(SAVE_DIR, filename)
        cv2.imwrite(path, frame)
        print(f"saved: {path}")
        idx += 1

    # q 키 → 종료
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
