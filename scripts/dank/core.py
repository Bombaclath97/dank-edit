"""Basi audio: filtri, saturazione, cache, note, timeline a bus con export."""
import json
import os

import numpy as np
from scipy import signal

SR = 44100
_rng = np.random.default_rng(1234)


def rng():
    return _rng


def seed(s):
    global _rng
    _rng = np.random.default_rng(s)


# ----------------------------------------------------------------- note
_STEPS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def nf(name, semis=0):
    """'C5', 'A#4', 'Bb1' -> Hz (La4 = 440)."""
    st = _STEPS[name[0]]
    i = 1
    while i < len(name) and name[i] in '#b':
        st += 1 if name[i] == '#' else -1
        i += 1
    midi = (int(name[i:]) + 1) * 12 + st + semis
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def hz(midi, semis=0):
    return 440.0 * 2 ** ((midi + semis - 69) / 12.0)


# ----------------------------------------------------------------- dsp
def fade(x, a=0.004, r=0.02):
    n = len(x)
    ai, ri = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if ai > 0:
        x[:ai] *= np.linspace(0, 1, ai)
    if ri > 0:
        x[-ri:] *= np.linspace(1, 0, ri)
    return x


def lp(x, fc, o=4):
    return signal.sosfilt(signal.butter(o, min(fc, SR / 2 * .98) / (SR / 2), btype='low', output='sos'), x)


def hp(x, fc, o=4):
    return signal.sosfilt(signal.butter(o, max(fc, 20) / (SR / 2), btype='high', output='sos'), x)


def bp(x, f1, f2, o=4):
    return signal.sosfilt(signal.butter(o, [max(f1, 20) / (SR / 2), min(f2, SR / 2 * .98) / (SR / 2)],
                                        btype='band', output='sos'), x)


def peak(x, f, gain_db, q=1.0):
    """EQ a campana (biquad RBJ)."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f / SR
    al = np.sin(w) / (2 * q)
    return signal.lfilter([1 + al * A, -2 * np.cos(w), 1 - al * A],
                          [1 + al / A, -2 * np.cos(w), 1 - al / A], x)


def sat(x, d=3.0):
    return np.tanh(x * d) / np.tanh(d)


def hardclip(x, drive=4.0):
    return np.clip(x * drive, -1, 1)


def bitcrush(x, bits=5, ds=4):
    q = 2 ** (bits - 1)
    y = np.round(np.clip(x, -1, 1) * q) / q
    return np.repeat(y[::ds], ds)[:len(x)] if ds > 1 else y


def sweep(x, fc, kind='low', width=1.8, blk=96):
    """Filtro tempo-variante a blocchi (wobble, plettrate, riser)."""
    out = np.zeros(len(x))
    for i in range(0, len(x), blk):
        j = min(i + blk, len(x))
        f = float(np.clip(fc[i:j].mean(), 40, SR / 2 * 0.9))
        if kind == 'low':
            sos = signal.butter(2, f / (SR / 2), btype='low', output='sos')
        else:
            sos = signal.butter(2, [max(f * .6, 30) / (SR / 2), min(f * width, SR / 2 * .95) / (SR / 2)],
                                btype='band', output='sos')
        out[i:j] = signal.sosfilt(sos, x[i:j])
    return out


_MEMO = {}


def memo(fn):
    """Cache sui parametri: le stesse note/colpi si sintetizzano una volta sola."""
    def w(*a):
        k = (fn.__module__, fn.__name__) + tuple(round(v, 4) if isinstance(v, float) else v for v in a)
        if k not in _MEMO:
            _MEMO[k] = fn(*a)
        return _MEMO[k].copy()
    w.__name__ = fn.__name__
    return w


# ----------------------------------------------------------------- timeline
class Song:
    """Timeline a battute + bus stereo.

    song = Song(bpm=140, bars=16, tail=2.0)
    song.add('drum', kick(), song.t(4, 0))      # battuta 4, tempo 0
    song.render(out_dir, master_fn)            # -> audio.raw, audio.wav, timing.json
    """

    BUSES = ('drum', 'bass', 'music', 'lead', 'fx', 'vox')

    def __init__(self, bpm, bars, tail=2.0, beats_per_bar=4):
        self.bpm = float(bpm)
        self.beat = 60.0 / self.bpm
        self.bar = beats_per_bar * self.beat
        self.e8 = self.beat / 2
        self.s16 = self.beat / 4
        self.dur = bars * self.bar + tail
        self.n = int(self.dur * SR)
        self.bus = {k: np.zeros((self.n, 2)) for k in self.BUSES}
        self.marks = {}          # tempi notevoli da passare al video
        self.kicks = []

    def t(self, bar, beat=0.0):
        return bar * self.bar + beat * self.beat

    def mark(self, name, t):
        self.marks[name] = float(t)
        return t

    def add(self, bus, sig, start, gain=1.0, pan=0.0):
        b = self.bus[bus]
        i = int(start * SR)
        if i < 0:
            sig, i = sig[-i:], 0
        n = min(len(sig), self.n - i)
        if n <= 0:
            return
        b[i:i + n, 0] += sig[:n] * gain * np.sqrt((1.0 - pan) / 2.0) * 1.414
        b[i:i + n, 1] += sig[:n] * gain * np.sqrt((1.0 + pan) / 2.0) * 1.414

    def silence_before(self, t, length, floor=0.03):
        """La pausa prima del drop: tutti i bus scendono a zero prima di t."""
        gi, gj = int((t - length) * SR), int(t * SR)
        for b in self.bus.values():
            b[gi:gj] *= np.linspace(1, floor, gj - gi)[:, None] ** 2

    def mute(self, t0, t1, level=0.03):
        for b in self.bus.values():
            b[int(t0 * SR):int(t1 * SR)] *= level

    def sidechain(self, times, buses=('bass',), depth=0.6, rel=28.0, length=0.17):
        duck = np.ones(self.n)
        el = int(length * SR)
        shape = 1.0 - depth * np.exp(-np.arange(el) / SR * rel)
        for kt in times:
            i = int(kt * SR)
            m = min(el, self.n - i)
            if m > 0:
                duck[i:i + m] = np.minimum(duck[i:i + m], shape[:m])
        duck = lp(duck, 400)
        for k in buses:
            self.bus[k] *= duck[:, None]
        self.kicks = sorted(set(round(x, 4) for x in times))

    def duck_under_vox(self, buses=('lead', 'music', 'bass'), depth=0.45):
        """Le voci scavano nel resto del mix."""
        env = lp(np.abs(self.bus['vox']).max(1), 12, 2)
        env = np.clip(env / (env.max() or 1) * 2.0, 0, 1)
        for k in buses:
            self.bus[k] *= (1.0 - depth * env)[:, None]

    def render(self, out_dir, gains=None, master=None, fps=60, limit_drive=1.7):
        g = {'drum': .95, 'bass': .85, 'music': 1.0, 'lead': 1.05, 'fx': .9, 'vox': 1.15}
        g.update(gains or {})
        mix = sum(self.bus[k] * g[k] for k in self.BUSES)
        if master is None:
            def master(x):
                x = hp(x, 30)
                x = sat(x * 0.6, 1.9)
                return x + bp(x, 1500, 5000) * 0.22
        L, R = master(mix[:, 0]), master(mix[:, 1])
        pk = max(np.abs(L).max(), np.abs(R).max()) or 1.0
        L = np.tanh(L / pk * limit_drive) / np.tanh(limit_drive)
        R = np.tanh(R / pk * limit_drive) / np.tanh(limit_drive)
        pk = max(np.abs(L).max(), np.abs(R).max()) or 1.0
        L, R = L / pk * 0.97, R / pk * 0.97
        fr = int(0.4 * SR)
        L[-fr:] *= np.linspace(1, 0, fr)
        R[-fr:] *= np.linspace(1, 0, fr)
        os.makedirs(out_dir, exist_ok=True)
        pcm = (np.stack([L, R], 1) * 32767).astype('<i2')
        pcm.tofile(os.path.join(out_dir, 'audio.raw'))
        _write_wav(os.path.join(out_dir, 'audio.wav'), pcm)
        nfr = int(np.ceil(self.dur * fps))
        mono = (L + R) * 0.5
        w = int(SR / fps)

        def epf(x):
            e = np.array([np.sqrt(np.mean(x[i * w:min((i + 1) * w, len(x))] ** 2)) if i * w < len(x) else 0.0
                          for i in range(nfr)])
            return (e / (e.max() or 1)).tolist()
        timing = {'fps': fps, 'dur': self.dur, 'n_frames': nfr, 'bpm': self.bpm, 'beat': self.beat,
                  'bar': self.bar, 'e8': self.e8, 's16': self.s16, 'marks': self.marks, 'kicks': self.kicks,
                  'env_bass': epf(lp(mono, 160)), 'env_all': epf(mono)}
        json.dump(timing, open(os.path.join(out_dir, 'timing.json'), 'w'))
        return mono

    def report(self, mono, sections):
        """Tabella RMS per banda: serve a beccare il basso che copre tutto."""
        def band(s, f1, f2):
            return float(np.sqrt(np.mean(bp(s, f1, f2) ** 2)))
        print(f"{'sezione':10s} {'RMS':>6s} {'sub':>6s} {'bass':>6s} {'mid':>6s} {'hi':>6s}")
        for name, a, b in sections:
            s = mono[int(a * SR):int(b * SR)]
            if len(s) < 1000:
                continue
            print(f'{name:10s} {np.sqrt(np.mean(s ** 2)):6.3f} {band(s, 20, 120):6.3f} {band(s, 120, 300):6.3f} '
                  f'{band(s, 300, 2000):6.3f} {band(s, 2000, 8000):6.3f}')


def _write_wav(path, pcm):
    import wave
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
