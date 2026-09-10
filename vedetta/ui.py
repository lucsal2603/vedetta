"""Disegno su fotogramma e mosaico delle telecamere (OpenCV)."""
import math
import numpy as np
import cv2

SKELETON = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16), (0, 5), (0, 6)]
STATUS_COLOR = {
    "idle": (200, 200, 200), "scaffale": (255, 200, 0), "attesa": (0, 200, 255),
    "occulta": (0, 120, 255), "ALLARME": (0, 0, 255),
}
STATUS_LABEL = {"idle": "", "scaffale": "scaffale", "attesa": "attesa", "occulta": "OCCULTA", "ALLARME": "ALLARME"}


def draw_zones(frame, zones, color=(80, 220, 80)):
    for s in zones.shelves:
        pts = np.array(s["points"], dtype=np.int32).reshape(-1, 1, 2)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        cv2.polylines(frame, [pts], True, color, 2)
        x, y = pts[0][0]
        cv2.putText(frame, s["name"], (int(x) + 4, int(y) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def draw_person(frame, det, person):
    status = person.status if person else "idle"
    col = STATUS_COLOR.get(status, (200, 200, 200))
    x1, y1, x2, y2 = [int(v) for v in det.bbox]
    cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2 if status != "ALLARME" else 4)
    k, kc = det.kpts, det.kconf
    for a, b in SKELETON:
        if kc[a] > 0.3 and kc[b] > 0.3:
            cv2.line(frame, (int(k[a][0]), int(k[a][1])), (int(k[b][0]), int(k[b][1])), col, 2)
    for i in (9, 10):  # polsi
        if kc[i] > 0.3:
            cv2.circle(frame, (int(k[i][0]), int(k[i][1])), 6, (0, 255, 255), -1)
    label = f"#{det.pid} {STATUS_LABEL.get(status, '')}".strip()
    cv2.putText(frame, label, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)


def draw_tile_header(frame, name, fps, silent, flash):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 28), (0, 0, 0), -1)
    txt = f"{name}   {fps:.1f} fps" + ("   [SILENZIOSA]" if silent else "")
    cv2.putText(frame, txt, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    if flash:
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 10)
        cv2.putText(frame, "ALLARME", (w // 2 - 90, h - 24), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)


def mosaic(frames, tile_w):
    if not frames:
        return np.zeros((360, 640, 3), dtype=np.uint8)
    tiles = []
    for f in frames:
        h, w = f.shape[:2]
        th = int(h * tile_w / w)
        tiles.append(cv2.resize(f, (tile_w, th)))
    th = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
    n = len(tiles)
    cols = 1 if n == 1 else 2 if n <= 4 else 3
    rows = math.ceil(n / cols)
    blank = np.zeros_like(tiles[0])
    while len(tiles) < rows * cols:
        tiles.append(blank)
    return np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])


def draw_footer(canvas, text):
    h, w = canvas.shape[:2]
    bar = np.zeros((30, w, 3), dtype=np.uint8)
    cv2.putText(bar, text, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
    return np.vstack([canvas, bar])
