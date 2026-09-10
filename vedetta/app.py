"""Ciclo principale: legge le sorgenti, analizza, disegna, registra, avvisa."""
import argparse
import os
import sys
import time
import cv2

from . import config as cfgmod
from .sources import make_source
from .detector import PoseTracker
from .zones import Zones
from .gesture import GestureEngine
from .events import ClipRecorder, EventLog
from .alert import Alarm
from . import ui


class Camera:
    def __init__(self, scfg, cfg):
        self.name = scfg["name"]
        self.cfg = cfg
        self.source = make_source(scfg, cfg["fps_target"], cfg["_dir"])
        self.zones_path = cfgmod.resolve(cfg, scfg["zones_file"])
        self.zones = Zones.load(self.zones_path)
        self.zones_mtime = os.path.getmtime(self.zones_path) if os.path.exists(self.zones_path) else 0
        self.tracker = PoseTracker(cfgmod.resolve(cfg, cfg["model"]), cfg["device"], cfg["imgsz"], cfg["conf"])
        self.engine = GestureEngine(cfg["gesture"], self.zones, self.name)
        rate = getattr(self.source, "rate", cfg["fps_target"])
        self.recorder = ClipRecorder(self.name, cfgmod.resolve(cfg, cfg["clips"]["dir"]),
                                     cfg["clips"]["pre_s"], cfg["clips"]["post_s"], rate, cfg["clips"]["keep_hours"])
        self.next_at = 0.0
        self.interval = 1.0 / cfg["fps_target"]
        self.last_frame = None
        self.flash_until = 0.0
        self.fps = 0.0
        self._fps_t = time.time()
        self._fps_n = 0
        self.finished = False

    def reload_zones_if_changed(self):
        if os.path.exists(self.zones_path):
            m = os.path.getmtime(self.zones_path)
            if m != self.zones_mtime:
                self.zones_mtime = m
                self.zones = Zones.load(self.zones_path)
                print(f"[{self.name}] zone ricaricate ({len(self.zones)} scaffali)")

    def step(self, now, silent):
        """Un fotogramma di analisi. Ritorna (eventi, t_media)."""
        if self.source.live and now < self.next_at:
            return [], None
        self.next_at = now + self.interval
        got = self.source.next()
        if got is None:
            self.finished = True
            return [], None
        t, frame = got
        h, w = frame.shape[:2]
        zones = self.zones.scaled(w, h)
        self.engine.set_zones(zones)
        dets = self.tracker.track(frame)
        events = self.engine.update(t, dets)

        ui.draw_zones(frame, zones)
        for d in dets:
            ui.draw_person(frame, d, self.engine.people.get(d.pid))
        if events:
            self.flash_until = now + self.cfg["alert"]["flash_s"]
        ui.draw_tile_header(frame, self.name, self.fps, silent, now < self.flash_until)
        self.recorder.push(frame)
        self.last_frame = frame

        self._fps_n += 1
        if now - self._fps_t >= 1.0:
            self.fps = self._fps_n / (now - self._fps_t)
            self._fps_t, self._fps_n = now, 0
        return events, t


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vedetta", description="Segnala i gesti di occultamento merce sulle telecamere.")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--negozio", help="profilo del negozio: negozi/<nome>.yaml")
    ap.add_argument("--headless", action="store_true", help="senza finestra (test)")
    ap.add_argument("--out", help="salva il mosaico annotato in questo file video (test)")
    ap.add_argument("--max-seconds", type=float, default=0, help="ferma dopo N secondi di media (test)")
    ap.add_argument("--silent", action="store_true", help="modalità silenziosa: registra ma non suona")
    ap.add_argument("--no-loop", action="store_true", help="non ripetere i video di prova")
    args = ap.parse_args(argv)

    cfg = cfgmod.load(args.config, args.negozio)
    if not cfg["sources"]:
        where = cfg["_store_path"] or args.config
        print(f"Nessuna sorgente in {where}. Negozi disponibili: {', '.join(cfgmod.store_names(cfg)) or 'nessuno'}")
        return 2
    from .detector import pick_device
    print(f"Vedetta: negozio {cfg['_store'] or '-'}, {len(cfg['sources'])} riquadri, modello su {pick_device(cfg['device'])}")
    if args.no_loop:
        for s in cfg["sources"]:
            s["loop"] = False
    silent = args.silent or cfg["alert"]["silent_mode"]

    cams = [Camera(s, cfg) for s in cfg["sources"]]
    alarm = Alarm(cfgmod.resolve(cfg, "assets/alert.wav"), enabled=cfg["alert"]["sound"] and not silent)
    log = EventLog(cfgmod.resolve(cfg, "events.csv"))
    writer = None
    paused = False
    n_events = 0
    last_msg = "q esci | p pausa | s silenziosa | 1 ultimo=vero | 0 ultimo=falso"
    all_files = all(not c.source.live for c in cams)

    if not args.headless:
        cv2.namedWindow("Vedetta", cv2.WINDOW_NORMAL)

    try:
        while True:
            media_t = None
            if not paused:
                for cam in cams:
                    cam.reload_zones_if_changed()
                    events, t = cam.step(time.time(), silent)
                    if t is not None:
                        media_t = t
                    for ev in events:
                        n_events += 1
                        clip = cam.recorder.trigger(ev)
                        log.add(ev, clip)
                        msg = (f"[{cam.name}] t={ev.t:.1f}s persona #{ev.pid} mano {ev.hand} -> {ev.kind} "
                               f"(scaffale: {ev.zone}, punteggio {ev.score})")
                        print("ALLARME " + msg)
                        last_msg = msg
                        if ev.score >= cfg["gesture"]["min_score"]:
                            alarm.play()
            if all(c.finished for c in cams):
                break
            if args.max_seconds and media_t is not None and media_t >= args.max_seconds:
                break

            frames = [c.last_frame for c in cams if c.last_frame is not None]
            canvas = ui.mosaic(frames, cfg["ui"]["tile_width"])
            canvas = ui.draw_footer(canvas, ("PAUSA  " if paused else "") + last_msg)
            if args.out:
                if writer is None:
                    rate = getattr(cams[0].source, "rate", cfg["fps_target"])
                    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), rate,
                                             (canvas.shape[1], canvas.shape[0]))
                writer.write(canvas)
            if not args.headless:
                cv2.imshow("Vedetta", canvas)
                delay = 1
                if all_files:
                    delay = max(1, int(1000 / cfg["fps_target"]))
                k = cv2.waitKey(delay) & 0xFF
                if k == ord("q") or k == 27:
                    break
                elif k == ord("p"):
                    paused = not paused
                elif k == ord("s"):
                    silent = not silent
                    alarm.enabled = cfg["alert"]["sound"] and not silent
                    print("modalità silenziosa:", silent)
                elif k == ord("1"):
                    log.label_last("vero"); last_msg = "ultimo evento segnato: VERO"
                elif k == ord("0"):
                    log.label_last("falso"); last_msg = "ultimo evento segnato: FALSO"
                if cv2.getWindowProperty("Vedetta", cv2.WND_PROP_VISIBLE) < 1:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        for c in cams:
            while c.recorder.pending:  # chiudi le clip in sospeso
                c.recorder.push(c.last_frame)
            c.source.release()
        if writer:
            writer.release()
        log.close()
        cv2.destroyAllWindows()
    print(f"fine: {n_events} eventi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
