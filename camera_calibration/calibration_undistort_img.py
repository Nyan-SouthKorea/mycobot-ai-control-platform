import cv2
import numpy as np


class Undistorter:
    """
    Usage:
      und = Undistorter("camera_calib.npz")
      und_frame = und.undistort(frame)
    """

    def __init__(self, calib_npz_path: str):
        data = np.load(calib_npz_path)
        self.K = data["cameraMatrix"]
        self.dist = data["distCoeffs"]

    def undistort(self, frame):
        """Return undistorted frame (same size as input)."""
        return cv2.undistort(frame, self.K, self.dist)

    def undistort_from_camera(self, cam_id=0):
        """
        Read one frame from camera and return undistorted frame.
        (Convenience helper)
        """
        cap = cv2.VideoCapture(cam_id)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("Failed to read from camera.")
        return self.undistort(frame)
