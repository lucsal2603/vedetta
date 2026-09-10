"""Macchina a stati per il gesto: mano nello scaffale -> mano al corpo/borsa."""
from dataclasses import dataclass, field
from .geometry import dist, angle_at

# COCO 17 keypoints
L_SHO, R_SHO, L_ELB, R_ELB, L_WRI, R_WRI, L_HIP, R_HIP = 5, 6, 7, 8, 9, 10, 11, 12
HANDS = {"S": (L_SHO, L_ELB, L_WRI), "D": (R_SHO, R_ELB, R_WRI)}  # sinistra, destra
KP_MIN = 0.3


@dataclass
class Event:
    t: float
    source: str
    pid: int
    hand: str
    kind: str      # "corpo" | "borsa"
    zone: str
    score: float
    bbox: tuple
    reach_hand: str
    transition_s: float
    occluded: bool


@dataclass
class HandState:
    in_zone_since: float = None
    zone: str = None
    conceal_since: float = None
    conceal_kind: str = None
    last_visible_conceal: float = None


@dataclass
class Person:
    pid: int
    last_seen: float
    hands: dict = field(default_factory=lambda: {"S": HandState(), "D": HandState()})
    watch_until: float = -1.0
    watch_zone: str = None
    watch_hand: str = None
    left_zone_at: float = -1.0
    last_alert: float = -1e9
    status: str = "idle"
    status_until: float = 0.0


def body_frame(kpts, kc, bbox):
    """Ritorna (spalle_centro, fianchi_centro, larghezza_spalle, altezza_busto)."""
    x1, y1, x2, y2 = bbox
    bw, bh = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
    ok = lambda i: kc[i] > KP_MIN
    if ok(L_SHO) and ok(R_SHO):
        S = ((kpts[L_SHO][0] + kpts[R_SHO][0]) / 2, (kpts[L_SHO][1] + kpts[R_SHO][1]) / 2)
        sw = dist(kpts[L_SHO], kpts[R_SHO])
    elif ok(L_SHO) or ok(R_SHO):
        p = kpts[L_SHO] if ok(L_SHO) else kpts[R_SHO]
        S = (float(p[0]), float(p[1]))
        sw = 0.0
    else:
        S = (x1 + bw / 2, y1 + 0.2 * bh)
        sw = 0.0
    if ok(L_HIP) and ok(R_HIP):
        H = ((kpts[L_HIP][0] + kpts[R_HIP][0]) / 2, (kpts[L_HIP][1] + kpts[R_HIP][1]) / 2)
    elif ok(L_HIP) or ok(R_HIP):
        p = kpts[L_HIP] if ok(L_HIP) else kpts[R_HIP]
        H = (float(p[0]), float(p[1]))
    else:
        H = (S[0], S[1] + 0.33 * bh)
    sw = max(sw, 0.2 * bh, 0.3 * bw)
    torso_h = max(H[1] - S[1], 0.25 * bh)
    return S, H, sw, torso_h


def near_body(W, S, H, sw, torso_h):
    """Polso dentro l'involucro del corpo (busto, fianchi, tasche, borsa): non è un braccio teso verso lo scaffale."""
    chest_y = S[1] + 0.35 * torso_h
    return chest_y <= W[1] <= H[1] + 1.2 * torso_h and abs(W[0] - H[0]) <= 1.6 * sw


def conceal_kind(W, E, Sh, S, H, sw, torso_h):
    """Dove sta la mano: 'corpo' (tasca, cintura, giacca), 'borsa' (fianco, borsa) o None."""
    ang = angle_at(E, Sh, W)
    if ang > 150:
        return None  # braccio disteso: mano che pende, non un gesto
    chest_y = S[1] + 0.35 * torso_h
    dx = abs(W[0] - H[0])
    if chest_y <= W[1] <= H[1] + 0.6 * torso_h and dx <= 0.75 * sw:
        return "corpo"
    if H[1] - 0.3 * torso_h <= W[1] <= H[1] + 1.2 * torso_h and 0.75 * sw < dx <= 1.6 * sw and ang < 135:
        return "borsa"
    return None


class GestureEngine:
    def __init__(self, gcfg, zones, source_name="cam"):
        self.cfg = gcfg
        self.zones = zones
        self.source = source_name
        self.people = {}

    def set_zones(self, zones):
        self.zones = zones

    def _person(self, pid, t):
        p = self.people.get(pid)
        if p is None:
            p = Person(pid, t)
            self.people[pid] = p
        p.last_seen = t
        return p

    def expire(self, t, ttl=3.0):
        for pid in [k for k, v in self.people.items() if t - v.last_seen > ttl]:
            del self.people[pid]

    def update(self, t, detections):
        """detections: list di Detection. Ritorna la lista degli eventi generati in questo frame."""
        c = self.cfg
        events = []
        for d in detections:
            p = self._person(d.pid, t)
            S, H, sw, torso_h = body_frame(d.kpts, d.kconf, d.bbox)
            fired = False

            for hand, (i_sho, i_elb, i_wri) in HANDS.items():
                hs = p.hands[hand]
                vis = d.kconf[i_wri] > KP_MIN and d.kconf[i_elb] > KP_MIN
                W = (float(d.kpts[i_wri][0]), float(d.kpts[i_wri][1]))
                E = (float(d.kpts[i_elb][0]), float(d.kpts[i_elb][1]))
                Sh = (float(d.kpts[i_sho][0]), float(d.kpts[i_sho][1])) if d.kconf[i_sho] > KP_MIN else S

                # --- 1. mano nello scaffale ---
                zone = self.zones.hit(W) if (vis and self.zones is not None) else None
                if zone and near_body(W, S, H, sw, torso_h):
                    zone = None  # il polso è sul corpo: la zona scaffale sullo sfondo non conta
                if zone:
                    if hs.in_zone_since is None:
                        hs.in_zone_since, hs.zone = t, zone
                elif hs.in_zone_since is not None and (vis or t - hs.in_zone_since > c["occlusion_grace_s"] + c["reach_min_s"]):
                    # la mano è uscita dallo scaffale (o è sparita a lungo)
                    if t - hs.in_zone_since >= c["reach_min_s"]:
                        p.watch_until = t + c["conceal_window_s"]
                        p.watch_zone, p.watch_hand, p.left_zone_at = hs.zone, hand, t
                    hs.in_zone_since, hs.zone = None, None

                # --- 2. mano al corpo/borsa dentro la finestra di osservazione ---
                watching = t <= p.watch_until
                kind = None
                if watching and not zone:
                    if vis:
                        kind = conceal_kind(W, E, Sh, S, H, sw, torso_h)
                        if kind:
                            hs.last_visible_conceal = t
                    elif hs.conceal_since is not None and hs.last_visible_conceal is not None \
                            and t - hs.last_visible_conceal <= c["occlusion_grace_s"]:
                        kind = hs.conceal_kind  # mano sparita subito dopo il gesto: conta ancora
                if kind:
                    if hs.conceal_since is None:
                        hs.conceal_since, hs.conceal_kind = t, kind
                    held = t - hs.conceal_since
                    if held >= c["conceal_min_s"] and t - p.last_alert >= c["cooldown_s"] and not fired:
                        occluded = not vis
                        transition = hs.conceal_since - p.left_zone_at
                        score = 0.5
                        if hand == p.watch_hand:
                            score += 0.2
                        if occluded:
                            score += 0.15
                        if transition < 2.0:
                            score += 0.15
                        if kind == "borsa":
                            score -= 0.1
                        score = round(max(0.0, min(1.0, score)), 2)
                        events.append(Event(t, self.source, p.pid, hand, kind, p.watch_zone, score,
                                            d.bbox, p.watch_hand, round(transition, 2), occluded))
                        p.last_alert = t
                        p.watch_until = -1.0
                        hs.conceal_since = None
                        fired = True
                else:
                    hs.conceal_since, hs.conceal_kind = None, None

            # --- stato per la UI ---
            if fired:
                p.status, p.status_until = "ALLARME", t + 3.0
            elif p.status == "ALLARME" and t < p.status_until:
                pass
            elif any(h.conceal_since is not None for h in p.hands.values()):
                p.status = "occulta"
            elif any(h.in_zone_since is not None for h in p.hands.values()):
                p.status = "scaffale"
            elif t <= p.watch_until:
                p.status = "attesa"
            else:
                p.status = "idle"
        self.expire(t)
        return events
