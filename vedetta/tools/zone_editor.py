"""Editor delle zone scaffale: clic per aggiungere punti, INVIO chiude il poligono.

    python -m vedetta.tools.zone_editor --source mele [--seek 5]

Tasti:  INVIO chiude il poligono corrente | u toglie l'ultimo punto | d cancella l'ultimo scaffale
        s salva | q esci senza salvare (chiede conferma se ci sono modifiche)
"""
import argparse
import os
import sys
import cv2
import numpy as np

from .. import config as cfgmod
from ..sources import make_source
from ..zones import Zones


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--negozio", help="profilo del negozio: negozi/<nome>.yaml")
    ap.add_argument("--source", required=True, help="nome della sorgente (riquadro)")
    ap.add_argument("--seek", type=float, default=0, help="secondi da cui prendere il fotogramma (solo video)")
    ap.add_argument("--max-width", type=int, default=1400)
    args = ap.parse_args(argv)

    cfg = cfgmod.load(args.config, args.negozio)
    scfg = next((s for s in cfg["sources"] if s["name"] == args.source), None)
    if not scfg:
        print("riquadro non trovato:", args.source, "| disponibili:", ", ".join(s["name"] for s in cfg["sources"]) or "nessuno")
        return 2
    src = make_source(scfg, cfg["fps_target"], cfg["_dir"])
    if args.seek and hasattr(src, "seek"):
        src.seek(args.seek)
    got = src.next()
    src.release()
    if got is None:
        print("nessun fotogramma"); return 1
    _, frame = got
    H, W = frame.shape[:2]
    scale = min(1.0, args.max_width / W)
    view_size = (int(W * scale), int(H * scale))

    zpath = cfgmod.resolve(cfg, scfg["zones_file"])
    zones = Zones.load(zpath).scaled(W, H)
    zones.frame_size = (W, H)
    shelves = [dict(s) for s in zones.shelves]
    current = []
    dirty = [False]

    def on_mouse(evt, x, y, flags, param):
        if evt == cv2.EVENT_LBUTTONDOWN:
            current.append([x / scale, y / scale])
            dirty[0] = True

    win = f"Zone: {args.source}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, *view_size)
    cv2.setMouseCallback(win, on_mouse)
    print(__doc__)

    while True:
        canvas = cv2.resize(frame, view_size)
        for s in shelves:
            pts = np.array([[x * scale, y * scale] for x, y in s["points"]], dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(canvas, [pts], True, (80, 220, 80), 2)
            cv2.putText(canvas, s["name"], (pts[0][0][0] + 4, pts[0][0][1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 80), 2)
        if current:
            pts = np.array([[x * scale, y * scale] for x, y in current], dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(canvas, [pts], False, (0, 200, 255), 2)
            for p in pts:
                cv2.circle(canvas, tuple(p[0]), 4, (0, 200, 255), -1)
        cv2.rectangle(canvas, (0, 0), (view_size[0], 26), (0, 0, 0), -1)
        cv2.putText(canvas, f"{len(shelves)} scaffali | clic=punto  INVIO=chiudi  u=indietro  d=cancella ultimo  s=salva  q=esci",
                    (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow(win, canvas)
        k = cv2.waitKey(30) & 0xFF
        if k in (13, 10):
            if len(current) >= 3:
                shelves.append({"name": f"scaffale {len(shelves) + 1}", "points": [list(p) for p in current]})
                current.clear()
        elif k == ord("u") and current:
            current.pop()
        elif k == ord("d") and shelves:
            shelves.pop(); dirty[0] = True
        elif k == ord("s"):
            Zones(shelves, (W, H)).save(zpath)
            dirty[0] = False
            print("salvato:", zpath, f"({len(shelves)} scaffali)")
        elif k == ord("q") or k == 27:
            if dirty[0] and shelves != zones.shelves:
                print("Modifiche non salvate: premi s per salvare, oppure q di nuovo per uscire senza salvare.")
                dirty[0] = False
                continue
            break
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
