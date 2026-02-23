import json
import numpy as np
import cv2


class PixelToRobotMapper:
    """
    Loads homography + robot offset from json and provides:
      - pixel_to_world(u,v) -> (Xw, Yw) [mm]
      - pixel_to_robot(u,v) -> (Xr, Yr) [mm]
    """

    def __init__(self, json_path: str):
        with open(json_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        H = np.array(cfg["H_pixel_to_world"], dtype=np.float64)
        if H.shape != (3, 3):
            raise ValueError(f"Invalid H shape: {H.shape}, expected (3,3)")

        self.H = H
        self.offset_x = float(cfg["robot_offset_mm"]["x"])
        self.offset_y = float(cfg["robot_offset_mm"]["y"])

    def pixel_to_world(self, u: float, v: float) -> tuple[float, float]:
        pt = np.array([[[u, v]]], dtype=np.float32)
        w = cv2.perspectiveTransform(pt, self.H)[0][0]
        return float(w[0]), float(w[1])

    def pixel_to_robot(self, u: float, v: float) -> tuple[float, float]:
        Xw, Yw = self.pixel_to_world(u, v)
        Xr = Xw + self.offset_x
        Yr = Yw + self.offset_y
        return Xr, Yr
