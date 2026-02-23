import json
import numpy as np
import cv2

# ----------------------------
# 네가 검증한 값 (하드코딩)
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
ROBOT_OFFSET_X = 125
ROBOT_OFFSET_Y = -86.25


OUT_JSON = "homography_robot_map.json"

# ----------------------------
# Homography 계산
# ----------------------------
H, _ = cv2.findHomography(image_points, world_points)
if H is None:
    raise RuntimeError("Homography 계산 실패: 4점 매칭/순서 확인 필요")

payload = {
    "description": "pixel(u,v) -> world(mm) via H, then world -> robot(mm) via offset",
    "image_points_uv": image_points.tolist(),
    "world_points_mm": world_points.tolist(),
    "H_pixel_to_world": H.tolist(),  # 3x3
    "robot_offset_mm": {"x": ROBOT_OFFSET_X, "y": ROBOT_OFFSET_Y},
    "notes": {
        "pixel_points_are_on_undistorted_image": True,
        "click_order": "P0,P1,P2,P3 must match between image_points and world_points"
    }
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"Saved: {OUT_JSON}")
