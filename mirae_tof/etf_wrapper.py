import os
import time
import threading
import cv2


class FolderCapture:
    """
    File-based capture that mimics OpenCV VideoCapture.read() style.

    Usage:
        cap = FolderCapture(save_dir="./save", keep_last=3, exts=(".jpg", ".png"))
        ret, img = cap.capture()  # ret=True/False, img=BGR ndarray or None
    """

    def __init__(self, save_dir='mirae_tof/save', keep_last=3, exts=(".jpg", ".jpeg", ".png", ".bmp"), clear_on_start=True):
        print(os.listdir(save_dir))
        self.save_dir = os.path.abspath(save_dir)
        self.keep_last = int(keep_last)
        self.exts = tuple(e.lower() for e in exts)
        self._lock = threading.Lock()

        os.makedirs(self.save_dir, exist_ok=True)

        if clear_on_start:
            self.clear()

    def _list_imgs_sorted(self):
        # 파일명 기준 정렬(시간순 파일명일 때 유리). 필요하면 mtime 정렬로 바꿀 수 있음.
        files = []
        for fn in os.listdir(self.save_dir):
            if fn.lower().endswith(self.exts):
                files.append(fn)
        files.sort()
        return files

    def clear(self):
        """Start clean: delete everything in save_dir (image exts only)."""
        with self._lock:
            for fn in self._list_imgs_sorted():
                try:
                    os.remove(os.path.join(self.save_dir, fn))
                except Exception as e:
                    print(f"[Warning] clear() remove failed: {fn} | {e}")

    def _del_old_imgs(self):
        """Keep only last N images."""
        with self._lock:
            files = self._list_imgs_sorted()
            if len(files) <= self.keep_last:
                return
            for fn in files[:-self.keep_last]:
                try:
                    os.remove(os.path.join(self.save_dir, fn))
                except Exception as e:
                    print(f"[Warning] _del_old_imgs() remove failed: {fn} | {e}")

    def read(self):
        files = self._list_imgs_sorted()
        if not files:
            return False, None

        img_path = os.path.join(self.save_dir, files[-1])

        try:
            img = cv2.imread(img_path)
        except Exception:
            return False, None

        if img is None:
            # 파일이 아직 쓰이는 중일 가능성
            time.sleep(0.02)
            return False, None

        threading.Thread(target=self._del_old_imgs, daemon=True).start()

        return True, img