"""Voci via espeak-ng: parlato, robot da laboratorio, growl, sussurro, vocal chop.
Voci utili: 'it', 'en-us', 'de', 'id' (espeak-ng --voices per l'elenco)."""
import os
import shutil
import subprocess
import tempfile
import wave

import numpy as np
from scipy import signal

from .core import SR, bitcrush, bp, fade, hp, lp, rng, sat

ESPEAK = shutil.which('espeak-ng') or shutil.which('espeak')
_CACHE = {}


def raw(text, voice='it', speed=140, pitch=50, gap=1):
    key = (text, voice, speed, pitch, gap)
    if key not in _CACHE:
        if ESPEAK is None:
            raise RuntimeError('espeak-ng non trovato: lancia scripts/check_env.sh')
        fd, path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        subprocess.run([ESPEAK, '-v', voice, '-s', str(speed), '-p', str(pitch), '-a', '180',
                        '-g', str(gap), '-w', path, text], check=True, capture_output=True)
        with wave.open(path) as w:
            sr0, data = w.getframerate(), w.readframes(w.getnframes())
        os.unlink(path)
        x = np.frombuffer(data, dtype='<i2').astype(np.float64) / 32768.0
        _CACHE[key] = signal.resample(x, max(8, int(len(x) * SR / sr0)))
    return _CACHE[key]


def _trim(v, thr=0.02):
    nz = np.nonzero(np.abs(v) > thr)[0]
    return v[max(0, nz[0] - 200):nz[-1] + 400] if len(nz) else v


def _norm(v, peak=0.9):
    m = np.abs(v).max() or 1.0
    return fade(v / m * peak, 0.004, 0.025)


def pitch(v, mult):
    """Cambia intonazione (e durata insieme: piu' dank)."""
    return signal.resample(v, max(8, int(len(v) / max(mult, 0.05))))


def speak(text, voice='it', speed=140, pitch_=50, pm=1.0, drive=2.6, crush=None):
    """Parlato che buca il mix. drive alto = clippato/urlato; crush=(bit, ds)."""
    v = pitch(_trim(raw(text, voice, speed, pitch_)), pm)
    v = v + bp(v, 1000, 3800, 2) * 1.2
    v = sat(v * 1.3, drive)
    if crush:
        v = bitcrush(v, *crush)
    return _norm(hp(v, 130))


def robot(text, voice='en-us', speed=135, pitch_=30):
    """IA da laboratorio / annunciatore: ring modulation + bitcrush leggero."""
    v = _trim(raw(text, voice, speed, pitch_))
    t = np.arange(len(v)) / SR
    v = v * (0.55 + 0.45 * np.sin(2 * np.pi * 58 * t))
    v = bitcrush(v * 2, 6, 1)
    v = v + bp(v, 1200, 4000, 2)
    return _norm(hp(sat(v, 2.0), 160))


def growl(text, voice='it', speed=120, pitch_=10, pm=0.6, drive=5.0):
    v = pitch(_trim(raw(text, voice, speed, pitch_)), pm)
    env = lp(np.abs(v), 40)
    v = sat((v * 1.4 + bp(rng().normal(0, 1, len(v)), 300, 3500, 2) * env * 3) * 1.8, drive)
    return _norm(hp(v + lp(v, 250) * 0.6, 70))


def whisper(text, voice='en-us', speed=105, pitch_=10, pm=0.8):
    v = pitch(_trim(raw(text, voice, speed, pitch_)), pm)
    env = lp(np.abs(v), 45)
    v = bp(rng().normal(0, 1, len(v)), 600, 6500, 2) * env * 4 + v * 0.22
    return _norm(hp(sat(v * 1.3, 2.0), 130))


def chop(word, idx, target_hz, dur, voice='it', base_hz=210.0, slices=6):
    """Vocal chop: fetta idx di `word`, ripitchata su target_hz."""
    src = raw(word, voice, 150, 45)
    sl = len(src) // slices
    seg = src[(idx % slices) * sl:(idx % slices) * sl + sl]
    seg = signal.resample(seg, max(8, int(len(seg) / (target_hz / base_hz))))
    n = int(dur * SR)
    seg = np.pad(seg, (0, max(0, n - len(seg))))[:n]
    seg = sat((seg + bp(seg, 900, 4500, 2) * .8) * 1.5, 2.5)
    return _norm(seg, 0.7)
