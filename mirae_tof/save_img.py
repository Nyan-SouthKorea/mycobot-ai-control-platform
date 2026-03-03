import sys
import queue
import ctypes
from pathlib import Path

import numpy as np
import cv2
import CubeEye as cu


# 최신 프레임만 유지 (저장 느릴 때 큐 폭주 방지)
amplitude_queue = queue.Queue(maxsize=1)


def put_latest(q, item):
    try:
        q.put_nowait(item)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass


class AmplitudeSink(cu.Sink):
    def __init__(self):
        cu.Sink.__init__(self)  # SWIG 바인딩에서 super()보다 안전한 경우가 있어 명시

    def name(self):
        return "AmplitudeOnlySink"

    # ===== 필수(또는 사실상 필수) 오버라이드: pure virtual 방지 =====
    def onCubeEyeCameraState(self, name, serialNumber, uri, state):
        # 필요 없으면 pass만 해도 됨. 디버그용 출력만 최소로 둠.
        # print(f"[STATE] {name}/{serialNumber} : {state}")
        return

    def onCubeEyeCameraError(self, name, serialNumber, uri, error):
        print(f"[ERROR] {name}/{serialNumber} : {error}")
        return
    # ==========================================================

    def onCubeEyeFrameList(self, name, serial, uri, frames):
        if frames is None:
            return

        for frame in frames:
            if not frame.isBasicFrame():
                continue
            if frame.dataType() != cu.DataType_U16:
                continue

            f16 = cu.frame_cast_basic16u(frame)

            # Amplitude만
            if f16.frameType() != cu.FrameType_Amplitude:
                continue

            h, w = frame.height(), frame.width()

            # U16 포인터 → numpy 1D view
            ptr_t = ctypes.c_uint16 * f16.dataSize()
            ptr = ptr_t.from_address(int(f16.dataPtr()))
            u16_1d = np.ctypeslib.as_array(ptr)

            # PNG 저장용 8-bit 변환 (SDK 함수 사용)
            amp_u8 = np.zeros((h, w), dtype=np.uint8)
            cu.convert2gray(u16_1d, amp_u8)

            put_latest(amplitude_queue, amp_u8)


def main():
    print("=== CubeEye Amplitude Save (Simple) ===")

    # save 폴더 (이 파일 기준)
    base_dir = Path(__file__).resolve().parent
    save_dir = base_dir / "save"
    save_dir.mkdir(exist_ok=True)

    # 항상 1부터 시작
    counter = 1

    # 카메라 검색
    sources = cu.search_camera_source()
    if sources is None or sources.size() == 0:
        print("CubeEye camera not found")
        sys.exit(1)

    # 첫 번째 카메라 사용
    camera = cu.create_camera(sources[0])
    if camera is None:
        print("Failed to create camera")
        sys.exit(1)

    # Sink 등록
    sink = AmplitudeSink()
    camera.addSink(sink)

    if camera.prepare() != cu.Result_Success:
        print("Camera prepare failed")
        cu.destroy_camera(camera)
        sys.exit(1)

    # 예제 코드와 동일하게 run(6) 사용
    if camera.run(6) != cu.Result_Success:
        print("Camera run failed")
        cu.destroy_camera(camera)
        sys.exit(1)

    print(f"[INFO] Saving amplitude images to: {save_dir}")
    print("[INFO] Press ESC to stop")

    cv2.namedWindow("Amplitude", cv2.WINDOW_NORMAL)

    try:
        while True:
            try:
                amp = amplitude_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # 파일명: 1.png, 2.png, 3.png ...
            path = save_dir / f"{counter}.png"

            # 180도 회전
            amp = cv2.rotate(amp, cv2.ROTATE_180)

            cv2.imwrite(str(path), amp)
            counter += 1

            cv2.imshow("Amplitude", amp)
            if cv2.waitKey(1) == 27:  # ESC
                break

    except KeyboardInterrupt:
        pass

    camera.stop()
    cu.destroy_camera(camera)
    cv2.destroyAllWindows()
    print("Exit")


if __name__ == "__main__":
    main()
