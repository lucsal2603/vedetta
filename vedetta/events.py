"""Registrazione clip (prima/dopo l'evento) e registro eventi."""
import csv
import os
import time
from collections import deque
from datetime import datetime
import cv2


class ClipRecorder:
    def __init__(self, source_name, out_dir, pre_s, post_s, rate, keep_hours=12):
        self.source = source_name
        self.dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.rate = max(1.0, float(rate))
        self.buf = deque(maxlen=int(pre_s * self.rate) + 1)
        self.post_frames = int(post_s * self.rate)
        self.pending = []  # [ {frames, remaining, path} ]
        self.keep_hours = keep_hours
        self._last_cleanup = 0

    def push(self, frame):
        self.buf.append(frame)
        for p in self.pending:
            p["frames"].append(frame)
            p["remaining"] -= 1
        done = [p for p in self.pending if p["remaining"] <= 0]
        for p in done:
            self._write(p)
            self.pending.remove(p)
        self._cleanup()

    def trigger(self, event):
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(self.dir, f"{stamp}_{self.source}_p{event.pid}.mp4")
        self.pending.append({"frames": list(self.buf), "remaining": self.post_frames, "path": path})
        return path

    def _write(self, p):
        if not p["frames"]:
            return
        h, w = p["frames"][0].shape[:2]
        vw = cv2.VideoWriter(p["path"], cv2.VideoWriter_fourcc(*"mp4v"), self.rate, (w, h))
        for f in p["frames"]:
            if f.shape[0] != h or f.shape[1] != w:
                f = cv2.resize(f, (w, h))
            vw.write(f)
        vw.release()
        print(f"[clip] salvata {p['path']}")

    def _cleanup(self):
        now = time.time()
        if now - self._last_cleanup < 600:
            return
        self._last_cleanup = now
        limit = self.keep_hours * 3600
        for name in os.listdir(self.dir):
            fp = os.path.join(self.dir, name)
            if name.endswith(".mp4") and now - os.path.getmtime(fp) > limit:
                try:
                    os.remove(fp)
                except OSError:
                    pass


class EventLog:
    FIELDS = ["quando", "sorgente", "persona", "mano", "tipo", "zona", "punteggio",
              "mano_scaffale", "transizione_s", "mano_sparita", "clip", "esito"]

    def __init__(self, path):
        self.path = path
        new = not os.path.exists(path)
        self.f = open(path, "a", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=self.FIELDS)
        if new:
            self.w.writeheader()
        self.last_row = None

    def add(self, ev, clip_path):
        row = {
            "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sorgente": ev.source, "persona": ev.pid, "mano": ev.hand, "tipo": ev.kind,
            "zona": ev.zone, "punteggio": ev.score, "mano_scaffale": ev.reach_hand,
            "transizione_s": ev.transition_s, "mano_sparita": int(ev.occluded),
            "clip": os.path.basename(clip_path) if clip_path else "", "esito": "",
        }
        self.w.writerow(row)
        self.f.flush()
        self.last_row = row
        return row

    def label_last(self, esito):
        """Segna l'ultimo evento come 'vero' o 'falso' (riga aggiuntiva, così il file resta append-only)."""
        if not self.last_row:
            return
        row = dict(self.last_row)
        row["esito"] = esito
        self.w.writerow(row)
        self.f.flush()

    def close(self):
        self.f.close()
