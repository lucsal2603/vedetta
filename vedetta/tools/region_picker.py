"""Selettore dei riquadri sullo schermo (per la modalità cattura schermo).

    python -m vedetta.tools.region_picker [--monitor 1] [--write]

Trascina un rettangolo attorno a ogni riquadro telecamera del client.
Tasti:  u toglie l'ultimo rettangolo | s stampa (e con --write aggiunge a config.yaml) | q esci
"""
import argparse
import os
import sys
import cv2
import numpy as np
import yaml


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--negozio", help="profilo del negozio: negozi/<nome>.yaml (creato se manca)")
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--write", action="store_true", help="scrive le sorgenti nel profilo del negozio (o in config.yaml)")
    ap.add_argument("--max-width", type=int, default=1400)
    args = ap.parse_args(argv)

    import mss
    with (getattr(mss, 'MSS', None) or mss.mss)() as sct:
        mon = sct.monitors[args.monitor] if args.monitor < len(sct.monitors) else sct.monitors[0]
        shot = sct.grab(mon)
        frame = np.ascontiguousarray(np.asarray(shot, dtype=np.uint8)[:, :, :3])
    H, W = frame.shape[:2]
    # su schermi Retina lo screenshot è più grande dei pixel logici: riportiamo alle coordinate del monitor
    px_scale = W / mon["width"]
    scale = min(1.0, args.max_width / W)
    view = (int(W * scale), int(H * scale))

    rects = []
    drag = {"start": None, "cur": None}

    def on_mouse(evt, x, y, flags, param):
        if evt == cv2.EVENT_LBUTTONDOWN:
            drag["start"] = (x, y); drag["cur"] = (x, y)
        elif evt == cv2.EVENT_MOUSEMOVE and drag["start"]:
            drag["cur"] = (x, y)
        elif evt == cv2.EVENT_LBUTTONUP and drag["start"]:
            (x0, y0), (x1, y1) = drag["start"], (x, y)
            x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1))
            if x1 - x0 > 20 and y1 - y0 > 20:
                rects.append([int(x0 / scale / px_scale), int(y0 / scale / px_scale),
                              int((x1 - x0) / scale / px_scale), int((y1 - y0) / scale / px_scale)])
            drag["start"] = None

    win = "Riquadri telecamere"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, *view)
    cv2.setMouseCallback(win, on_mouse)
    print(__doc__)

    while True:
        canvas = cv2.resize(frame, view)
        for i, (x, y, w, h) in enumerate(rects):
            p0 = (int(x * px_scale * scale), int(y * px_scale * scale))
            p1 = (int((x + w) * px_scale * scale), int((y + h) * px_scale * scale))
            cv2.rectangle(canvas, p0, p1, (80, 220, 80), 2)
            cv2.putText(canvas, f"riquadro {i + 1}", (p0[0] + 4, p0[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 80), 2)
        if drag["start"]:
            cv2.rectangle(canvas, drag["start"], drag["cur"], (0, 200, 255), 2)
        cv2.rectangle(canvas, (0, 0), (view[0], 26), (0, 0, 0), -1)
        cv2.putText(canvas, f"{len(rects)} riquadri | trascina=rettangolo  u=indietro  s=salva  q=esci",
                    (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow(win, canvas)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("u") and rects:
            rects.pop()
        elif k == ord("s"):
            sources = []
            for i, r in enumerate(rects):
                name = input(f"Nome del riquadro {i + 1} (es. corsia-3): ").strip() or f"riquadro-{i + 1}"
                sources.append({"name": name, "type": "screen", "monitor": args.monitor, "region": r})
            print(yaml.safe_dump({"sources": sources}, allow_unicode=True, sort_keys=False))
            if args.write:
                from .. import config as cfgmod
                base = cfgmod.load(args.config, args.negozio)
                target = base["_store_path"] or args.config
                data = {}
                if os.path.exists(target):
                    with open(target, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                data["sources"] = [s for s in data.get("sources", []) if s.get("type") != "screen"] + sources
                os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
                print("scritto:", target)
            break
        elif k == ord("q") or k == 27:
            break
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
