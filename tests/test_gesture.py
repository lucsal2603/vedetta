"""Test sintetici della macchina a stati del gesto (senza modello, senza video).

    python -m unittest tests.test_gesture -v
"""
import unittest
import numpy as np

from vedetta.gesture import GestureEngine, L_SHO, R_SHO, L_ELB, R_ELB, L_WRI, R_WRI, L_HIP, R_HIP
from vedetta.detector import Detection
from vedetta.zones import Zones

CFG = {"reach_min_s": 0.25, "conceal_window_s": 4.0, "conceal_min_s": 0.35,
       "occlusion_grace_s": 1.0, "cooldown_s": 8.0, "min_score": 0.5}
FPS = 8.0

# Persona frontale in piedi al centro di un fotogramma 640x480: spalle a y=150, fianchi a y=260.
BASE = {L_SHO: (280, 150), R_SHO: (360, 150), L_ELB: (260, 205), R_ELB: (380, 205),
        L_WRI: (255, 265), R_WRI: (385, 265), L_HIP: (295, 260), R_HIP: (345, 260)}
BBOX = (240, 90, 400, 420)
SHELF = Zones([{"name": "scaffale A", "points": [[420, 100], [640, 100], [640, 400], [420, 400]]}], (640, 480))


def det(pid, overrides=None, hidden=()):
    k = np.zeros((17, 2), dtype=np.float32)
    c = np.zeros(17, dtype=np.float32)
    pts = dict(BASE)
    pts.update(overrides or {})
    for i, (x, y) in pts.items():
        k[i] = (x, y)
        c[i] = 0.0 if i in hidden else 0.9
    return Detection(pid, BBOX, k, c)


def run(engine, frames):
    """frames: lista di Detection (una per fotogramma). Ritorna tutti gli eventi."""
    events = []
    for i, d in enumerate(frames):
        events += engine.update(i / FPS, [d])
    return events


def hold(d, seconds):
    return [d] * int(round(seconds * FPS))


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine(CFG, SHELF, "test")

    def test_prelievo_e_tasca(self):
        """Mano destra nello scaffale, poi mano alla tasca (fianco, gomito piegato): un allarme."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})  # polso sul fianco, gomito piegato
        frames = hold(det(1), 1) + hold(reach, 1) + hold(det(1), 0.5) + hold(pocket, 1) + hold(det(1), 1)
        ev = run(self.engine, frames)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].kind, "corpo")
        self.assertEqual(ev[0].zone, "scaffale A")
        self.assertEqual(ev[0].reach_hand, "D")
        self.assertGreaterEqual(ev[0].score, 0.7)

    def test_prelievo_e_giacca_con_mano_sparita(self):
        """Mano che va sotto la giacca e sparisce: l'evento scatta anche se il polso non si vede più."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        jacket = det(1, {R_WRI: (330, 215), R_ELB: (385, 215)})
        gone = det(1, {R_WRI: (330, 215), R_ELB: (385, 215)}, hidden=(R_WRI,))
        frames = hold(det(1), 1) + hold(reach, 0.5) + hold(jacket, 0.15) + hold(gone, 0.8) + hold(det(1), 1)
        ev = run(self.engine, frames)
        self.assertEqual(len(ev), 1)
        self.assertTrue(ev[0].occluded)

    def test_mano_nell_altra(self):
        """Prende con la destra, nasconde con la sinistra: allarme, punteggio più basso."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        left_pocket = det(1, {L_WRI: (300, 280), L_ELB: (262, 232)})
        frames = hold(det(1), 1) + hold(reach, 1) + hold(det(1), 0.4) + hold(left_pocket, 1)
        ev = run(self.engine, frames)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].hand, "S")
        self.assertLess(ev[0].score, 0.9)

    def test_prelievo_e_carrello_niente_allarme(self):
        """Prende dallo scaffale e mette nel carrello (mano bassa e lontana): nessun allarme."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        cart = det(1, {R_WRI: (470, 380), R_ELB: (420, 320)})
        frames = hold(det(1), 1) + hold(reach, 1) + hold(cart, 1.5) + hold(det(1), 2)
        self.assertEqual(run(self.engine, frames), [])

    def test_braccia_lungo_i_fianchi_niente_allarme(self):
        """Dopo lo scaffale la mano torna semplicemente giù distesa: nessun allarme."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        frames = hold(det(1), 1) + hold(reach, 1) + hold(det(1), 4)
        self.assertEqual(run(self.engine, frames), [])

    def test_tasca_senza_scaffale_niente_allarme(self):
        """Mano in tasca senza aver toccato lo scaffale (es. prende il telefono): nessun allarme."""
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})
        frames = hold(det(1), 1) + hold(pocket, 2) + hold(det(1), 1)
        self.assertEqual(run(self.engine, frames), [])

    def test_fuori_finestra_niente_allarme(self):
        """Tasca 6 secondi dopo lo scaffale, oltre la finestra di 4 s: nessun allarme."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})
        frames = hold(det(1), 1) + hold(reach, 1) + hold(det(1), 6) + hold(pocket, 1)
        self.assertEqual(run(self.engine, frames), [])

    def test_sfioramento_scaffale_troppo_breve(self):
        """Polso nello scaffale per un solo fotogramma (passaggio): non conta come prelievo."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})
        frames = hold(det(1), 1) + [reach] + hold(det(1), 0.3) + hold(pocket, 1)
        self.assertEqual(run(self.engine, frames), [])

    def test_mano_pendente_dentro_zona_niente_prelievo(self):
        """Zona scaffale sullo sfondo che copre anche il corpo: la mano che pende non è un prelievo."""
        everywhere = Zones([{"name": "sfondo", "points": [[0, 0], [640, 0], [640, 480], [0, 480]]}], (640, 480))
        engine = GestureEngine(CFG, everywhere, "test")
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})
        frames = hold(det(1), 2) + hold(pocket, 1) + hold(det(1), 1)
        self.assertEqual(run(engine, frames), [])
        # ...ma un braccio teso dentro la stessa zona e poi la tasca sì
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        frames = hold(det(1), 1) + hold(reach, 1) + hold(det(1), 0.3) + hold(pocket, 1)
        self.assertEqual(len(run(engine, frames)), 1)

    def test_cooldown(self):
        """Due gesti di seguito sulla stessa persona entro il cooldown: un solo allarme."""
        reach = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        pocket = det(1, {R_WRI: (350, 280), R_ELB: (380, 230)})
        seq = hold(reach, 0.5) + hold(det(1), 0.3) + hold(pocket, 0.6) + hold(det(1), 0.3)
        frames = hold(det(1), 1) + seq + seq
        self.assertEqual(len(run(self.engine, frames)), 1)

    def test_due_persone_indipendenti(self):
        """Persona 2 prende e nasconde, persona 1 fa la spesa normale: un allarme, sulla 2."""
        reach2 = det(2, {R_WRI: (480, 200), R_ELB: (420, 180)})
        pocket2 = det(2, {R_WRI: (350, 280), R_ELB: (380, 230)})
        reach1 = det(1, {R_WRI: (480, 200), R_ELB: (420, 180)})
        events = []
        seq1 = hold(det(1), 1) + hold(reach1, 1) + hold(det(1), 2.5)
        seq2 = hold(det(2), 1) + hold(reach2, 1) + hold(det(2), 0.5) + hold(pocket2, 1)
        for i, (a, b) in enumerate(zip(seq1, seq2)):
            events += self.engine.update(i / FPS, [a, b])
        self.assertEqual([e.pid for e in events], [2])


if __name__ == "__main__":
    unittest.main()
