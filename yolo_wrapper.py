import cv2
from ultralytics import YOLO


class YOLOWrapper:
    def __init__(self, weight_path):
        self.model = YOLO(weight_path)

        # class name mapping (ultralytics model 내부)
        # 보통 model.names가 dict 또는 list 형태로 들어있음
        self.names = None
        try:
            self.names = self.model.names
        except Exception:
            self.names = None

    def _get_class_name(self, class_no):
        if self.names is None:
            return str(class_no)

        # names가 dict인 경우: {0:"person", ...}
        if isinstance(self.names, dict):
            return self.names.get(int(class_no), str(class_no))

        # names가 list인 경우: ["person", ...]
        if isinstance(self.names, list):
            idx = int(class_no)
            if 0 <= idx < len(self.names):
                return self.names[idx]
            return str(class_no)

        return str(class_no)

    def infer(self, bgr_img, confidence_threshold=0.5):
        """
        Input: BGR image (OpenCV)
        Output: list of dict
          dict keys:
            - class_no
            - class_name
            - bbox_nor      (x1,y1,x2,y2 normalized 0~1)
            - bbox_pixel    (x1,y1,x2,y2 pixel)
            - conf
        """
        if bgr_img is None:
            return []

        h, w = bgr_img.shape[:2]

        # YOLO는 보통 RGB로 받는 게 안전하니 변환
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

        results = self.model(rgb, verbose=False)
        if results is None or len(results) == 0:
            return []

        r0 = results[0]
        if r0.boxes is None:
            return []

        out = []

        # r0.boxes: Boxes object
        # - xyxy: (N,4)
        # - conf: (N,)
        # - cls : (N,)
        boxes_xyxy = r0.boxes.xyxy
        confs = r0.boxes.conf
        clss = r0.boxes.cls

        # torch tensor일 수 있어서 .cpu().numpy() 대응
        try:
            boxes_xyxy = boxes_xyxy.cpu().numpy()
            confs = confs.cpu().numpy()
            clss = clss.cpu().numpy()
        except Exception:
            # 이미 numpy일 수도 있음
            pass

        for i in range(len(boxes_xyxy)):
            conf = float(confs[i])
            if conf < float(confidence_threshold):
                continue

            x1, y1, x2, y2 = boxes_xyxy[i].tolist()

            # clamp (이미지 범위)
            x1 = max(0.0, min(x1, w - 1.0))
            x2 = max(0.0, min(x2, w - 1.0))
            y1 = max(0.0, min(y1, h - 1.0))
            y2 = max(0.0, min(y2, h - 1.0))

            class_no = int(clss[i])
            class_name = self._get_class_name(class_no)

            bbox_pixel = [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))]
            bbox_nor = [x1 / w, y1 / h, x2 / w, y2 / h]

            out.append({
                "class_no": class_no,
                "class_name": class_name,
                "bbox_nor": bbox_nor,         # [x1,y1,x2,y2] normalized
                "bbox_pixel": bbox_pixel,     # [x1,y1,x2,y2] pixel
                "conf": conf
            })

        return out

    def draw(self, img, dic_list):
        """
        img: BGR image (OpenCV)
        dic_list: infer() 결과 list[dict]
        - 빨간 bbox
        - bbox 왼쪽 아래에: class_name + conf
        - dict에 "robot_loc": [x_mm, y_mm] 있으면 같이 표시
        return: annotated BGR image
        """
        if img is None:
            return None

        out = img.copy()

        for d in (dic_list or []):
            if "bbox_pixel" not in d:
                continue

            x1, y1, x2, y2 = d["bbox_pixel"]
            class_name = str(d.get("class_name", ""))
            conf = float(d.get("conf", 0.0))

            # bbox (red)
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), 2)

            # label text
            label = f"{class_name} {conf:.2f}"

            # optional robot location
            if "robot_loc" in d and isinstance(d["robot_loc"], (list, tuple)) and len(d["robot_loc"]) >= 2:
                rx = float(d["robot_loc"][0])
                ry = float(d["robot_loc"][1])
                label += f" | robot=({rx:.1f},{ry:.1f})mm"

            # put label near bottom-left of bbox
            # (bbox 좌하단 기준으로 약간 아래에 놓고 싶으면 y2+?도 가능하지만,
            #  화면 밖으로 나갈 수 있어서 bbox 위쪽/아래쪽 자동 처리)
            tx = x1
            ty = y2 + 20
            if ty > out.shape[0] - 10:
                ty = y1 - 10
                if ty < 15:
                    ty = y1 + 15

            cv2.putText(
                out,
                label,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )

        return out

    def bbox_center(self, bbox_pixel):
        x1, y1, x2, y2 = bbox_pixel
        cx = (x1 + x2) * 0.5
        cy = (y1 + y2) * 0.5
        return cx, cy