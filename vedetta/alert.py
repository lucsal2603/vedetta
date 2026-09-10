"""Suono di allarme, senza dipendenze esterne."""
import os
import platform
import struct
import subprocess
import threading
import wave
import math


def ensure_wav(path):
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rate = 22050
    frames = bytearray()
    for _ in range(3):  # tre bip
        for i in range(int(rate * 0.18)):
            v = int(12000 * math.sin(2 * math.pi * 1100 * i / rate))
            frames += struct.pack("<h", v)
        frames += b"\x00\x00" * int(rate * 0.09)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


class Alarm:
    def __init__(self, wav_path, enabled=True):
        self.path = ensure_wav(wav_path)
        self.enabled = enabled
        self.system = platform.system()

    def play(self):
        if not self.enabled:
            return
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        try:
            if self.system == "Windows":
                import winsound
                winsound.PlaySound(self.path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif self.system == "Darwin":
                subprocess.run(["afplay", self.path], check=False)
            else:
                subprocess.run(["aplay", "-q", self.path], check=False)
        except Exception as e:  # il suono non deve mai bloccare l'analisi
            print("[alert] suono non riprodotto:", e)
