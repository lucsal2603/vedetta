"""Rilevamento persone + posa + tracking (ultralytics YOLO pose + ByteTrack)."""
from dataclasses import dataclass
import numpy as np


@dataclass
class Detection:
    pid: int
    bbox: tuple  # x1, y1, x2, y2
    kpts: np.ndarray  # (17, 2)
    kconf: np.ndarray  # (17,)


def pick_device(pref="auto"):
    if pref and pref != "auto":
        return pref
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def check_torchvision_nms():
    """Nell'eseguibile impacchettato torchvision può caricarsi senza i suoi operatori C++.
    In quel caso lo togliamo da sys.modules: ultralytics usa allora la propria NMS in puro torch."""
    import sys
    if "torchvision" not in sys.modules:
        return True
    try:
        import torch
        import torchvision
        torchvision.ops.nms(torch.tensor([[0.0, 0.0, 1.0, 1.0]]), torch.tensor([0.9]), 0.5)
        return True
    except Exception as e:
        print("[detector] torchvision senza operatori NMS, uso la NMS interna:", str(e).splitlines()[0])
        for name in [m for m in sys.modules if m == "torchvision" or m.startswith("torchvision.")]:
            sys.modules.pop(name, None)
        return False


class PoseTracker:
    """Un'istanza per telecamera: il tracker interno tiene lo stato per sorgente."""

    def __init__(self, model_path, device="auto", imgsz=640, conf=0.35):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        check_torchvision_nms()
        self.device = pick_device(device)
        self.imgsz = imgsz
        self.conf = conf

    def track(self, frame):
        res = self.model.track(
            frame, persist=True, verbose=False, device=self.device,
            imgsz=self.imgsz, conf=self.conf, tracker="bytetrack.yaml",
        )[0]
        out = []
        if res.boxes is None or res.boxes.id is None or res.keypoints is None:
            return out
        ids = res.boxes.id.int().tolist()
        boxes = res.boxes.xyxy.cpu().numpy()
        kxy = res.keypoints.xy.cpu().numpy()
        kc = res.keypoints.conf
        kc = kc.cpu().numpy() if kc is not None else np.ones((len(ids), 17))
        for i, pid in enumerate(ids):
            out.append(Detection(int(pid), tuple(float(v) for v in boxes[i]), kxy[i], kc[i]))
        return out
