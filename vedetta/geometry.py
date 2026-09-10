import math
import numpy as np
import cv2


def dist(a, b):
    return float(math.hypot(a[0] - b[0], a[1] - b[1]))


def angle_at(vertex, p1, p2):
    """Angolo in gradi al vertice, tra i segmenti vertex-p1 e vertex-p2."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 180.0
    c = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def point_in_polygon(pt, poly):
    if len(poly) < 3:
        return False
    contour = np.array(poly, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(contour, (float(pt[0]), float(pt[1])), False) >= 0
