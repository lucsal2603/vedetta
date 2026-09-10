"""Sorgenti video: file, webcam, porzione di schermo."""
import time
import numpy as np
import cv2


class VideoFileSource:
    live = False

    def __init__(self, path, fps_target, loop=True):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Impossibile aprire il video: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.stride = max(1, int(round(self.fps / fps_target)))
        self.rate = self.fps / self.stride  # fotogrammi analizzati al secondo
        self.loop = loop
        self.idx = 0
        self.loops = 0
        self.duration = (self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / self.fps

    def seek(self, seconds):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(seconds * self.fps))
        self.idx = int(seconds * self.fps)

    def next(self):
        """Ritorna (t_media_secondi, frame) o None a fine video."""
        while True:
            ok = self.cap.grab()
            if not ok:
                if not self.loop:
                    return None
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.loops += 1
                self.idx = 0
                continue
            self.idx += 1
            if (self.idx - 1) % self.stride == 0:
                ok, frame = self.cap.retrieve()
                if not ok:
                    continue
                t = self.loops * self.duration + (self.idx - 1) / self.fps
                return t, frame

    def release(self):
        self.cap.release()


class WebcamSource:
    live = True

    def __init__(self, index, fps_target):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Webcam {index} non disponibile")
        self.rate = fps_target

    def next(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        return time.time(), frame

    def release(self):
        self.cap.release()


class ScreenSource:
    """Cattura una regione dello schermo con mss. region = [x, y, w, h] in pixel."""
    live = True

    def __init__(self, region, fps_target, monitor=1):
        import mss
        self.sct = (getattr(mss, 'MSS', None) or mss.mss)()
        mon = self.sct.monitors[monitor] if monitor < len(self.sct.monitors) else self.sct.monitors[0]
        x, y, w, h = region
        self.box = {"left": mon["left"] + int(x), "top": mon["top"] + int(y), "width": int(w), "height": int(h)}
        self.rate = fps_target

    def next(self):
        shot = self.sct.grab(self.box)
        frame = np.asarray(shot, dtype=np.uint8)[:, :, :3]  # BGRA -> BGR
        return time.time(), np.ascontiguousarray(frame)

    def release(self):
        self.sct.close()


def make_source(scfg, fps_target, base_dir="."):
    import os
    kind = scfg.get("type", "video")
    if kind == "video":
        p = scfg["path"]
        if not os.path.isabs(p):
            p = os.path.join(base_dir, p)
        return VideoFileSource(p, fps_target, loop=scfg.get("loop", True))
    if kind == "webcam":
        return WebcamSource(int(scfg.get("index", 0)), fps_target)
    if kind == "screen":
        return ScreenSource(scfg["region"], fps_target, int(scfg.get("monitor", 1)))
    raise ValueError(f"Tipo sorgente sconosciuto: {kind}")
