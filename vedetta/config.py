import copy
import os
import sys
import yaml

DEFAULTS = {
    "model": "yolo11n-pose.pt",
    "device": "auto",
    "imgsz": 640,
    "conf": 0.35,
    "fps_target": 8,
    "sources": [],
    "gesture": {
        "reach_min_s": 0.25,
        "conceal_window_s": 4.0,
        "conceal_min_s": 0.35,
        "occlusion_grace_s": 1.0,
        "cooldown_s": 8.0,
        "min_score": 0.5,
    },
    "clips": {"dir": "clips", "pre_s": 8, "post_s": 4, "keep_hours": 12},
    "alert": {"sound": True, "silent_mode": False, "flash_s": 3.0},
    "ui": {"tile_width": 800},
}


def _merge(cfg, path):
    with open(path, "r", encoding="utf-8") as f:
        user = yaml.safe_load(f) or {}
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v


def load(path="config.yaml", store=None):
    """Carica config.yaml e, se indicato, il profilo del negozio (negozi/<store>.yaml) sopra di esso."""
    cfg = copy.deepcopy(DEFAULTS)
    if path and not os.path.exists(path) and getattr(sys, "frozen", False):
        alt = os.path.join(os.path.dirname(sys.executable), os.path.basename(path))
        if os.path.exists(alt):
            path = alt
    if path and os.path.exists(path):
        _merge(cfg, path)
    cfg["_dir"] = os.path.dirname(os.path.abspath(path)) if path else os.getcwd()
    cfg["_store"] = None
    cfg["_store_path"] = None
    if store:
        store = store.strip()
        sp = store if store.endswith(".yaml") else os.path.join(cfg["_dir"], "negozi", f"{store}.yaml")
        cfg["_store"] = os.path.splitext(os.path.basename(sp))[0]
        cfg["_store_path"] = sp
        if os.path.exists(sp):
            _merge(cfg, sp)
        else:
            cfg["sources"] = []
    zdir = os.path.join("zones", cfg["_store"]) if cfg["_store"] else "zones"
    for s in cfg["sources"]:
        s.setdefault("zones_file", os.path.join(zdir, f"{s['name']}.json"))
    return cfg


def store_names(cfg):
    d = os.path.join(cfg["_dir"], "negozi")
    if not os.path.isdir(d):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".yaml"))


def resolve(cfg, p):
    """Percorso relativo alla cartella del config."""
    if os.path.isabs(p):
        return p
    return os.path.join(cfg["_dir"], p)
