import json
import os
from .geometry import point_in_polygon


class Zones:
    """Zone scaffale di una telecamera: poligoni in pixel del fotogramma nativo."""

    def __init__(self, shelves=None, frame_size=None):
        self.shelves = shelves or []  # [{"name": str, "points": [[x,y],...]}]
        self.frame_size = frame_size  # (w, h) del fotogramma su cui sono state disegnate

    @classmethod
    def load(cls, path):
        if not path or not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        fs = d.get("frame_size")
        return cls(d.get("shelves", []), tuple(fs) if fs else None)

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"frame_size": self.frame_size, "shelves": self.shelves}, f, indent=2)

    def scaled(self, frame_w, frame_h):
        """Se il fotogramma ha una dimensione diversa da quella di disegno, riscala."""
        if not self.frame_size or (frame_w, frame_h) == tuple(self.frame_size):
            return self
        sx = frame_w / self.frame_size[0]
        sy = frame_h / self.frame_size[1]
        shelves = [{"name": s["name"], "points": [[x * sx, y * sy] for x, y in s["points"]]} for s in self.shelves]
        return Zones(shelves, (frame_w, frame_h))

    def hit(self, pt):
        for s in self.shelves:
            if point_in_polygon(pt, s["points"]):
                return s["name"]
        return None

    def __len__(self):
        return len(self.shelves)
