"""Strumenti sintetizzati da zero (niente sample). Tutti restituiscono np.array mono.
Raccolti dagli edit fatti finora: ogni funzione e' gia' stata usata in un render vero."""
import numpy as np
from scipy import signal

from .core import SR, bp, fade, hardclip, hp, lp, memo, peak, rng, sat, sweep


def _t(dur):
    n = int(dur * SR)
    return n, np.arange(n) / SR


# ================================================================ BATTERIA
@memo
def kick(dur=0.36, punch=1.0):
    n, t = _t(dur)
    f = 50 + 150 * np.exp(-t * 38)
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    k += np.sin(2 * np.pi * 48 * t) * np.exp(-t * 8) * 0.3
    k += hp(rng().normal(0, 1, n) * np.exp(-t * 420), 2400) * 0.3 * punch
    return fade(sat(k * 1.3, 2.5), 0.0006, 0.012)


@memo
def kick_metal(dur=0.20):
    """Tanto click, poca coda: regge le doppie casse a sedicesimi."""
    n, t = _t(dur)
    k = np.sin(2 * np.pi * np.cumsum(52 + 130 * np.exp(-t * 55)) / SR) * np.exp(-t * 22)
    k += hp(rng().normal(0, 1, n), 3000) * np.exp(-t * 420) * 0.65
    k += np.sin(2 * np.pi * 3100 * t) * np.exp(-t * 300) * 0.25
    return fade(sat(k * 1.6, 2.6) * 0.8, 0.0004, 0.01)


@memo
def kick808(dur=0.4):
    n, t = _t(dur)
    k = np.sin(2 * np.pi * np.cumsum(48 + 150 * np.exp(-t * 38)) / SR) * np.exp(-t * 7)
    k += hp(rng().normal(0, 1, n) * np.exp(-t * 400), 2500) * 0.25
    return fade(sat(k * 1.6, 2.6) * 0.85, 0.0004, 0.01)


@memo
def snare(dur=0.22, tone=210.0):
    n, t = _t(dur)
    o = bp(rng().normal(0, 1, n), 1000, 8500, 4) * np.exp(-t * 24)
    o += (np.sin(2 * np.pi * tone * t) + .6 * np.sin(2 * np.pi * tone * 1.6 * t)) * np.exp(-t * 36) * .4
    return fade(sat(o, 1.8) * 0.6, 0.0005, 0.01)


@memo
def clap(dur=0.22):
    n, t = _t(dur)
    o = np.zeros(n)
    for k, d in enumerate((0, .008, .016, .025)):
        i = int(d * SR)
        o[i:] += bp(rng().normal(0, 1, n - i), 1200, 6200, 4) * np.exp(-np.arange(n - i) / SR * 50) * (1 - .15 * k)
    return fade(sat(o * .6, 1.6), 0.0005, 0.01)


@memo
def hat(dur=0.05, open_=0):
    n, t = _t(dur)
    noise = rng().normal(0, 1, n)
    metal = sum(np.sin(2 * np.pi * f * t) for f in (3300, 4900, 6500, 8400, 11000)) * 0.1
    return fade(hp(noise + metal, 7000) * np.exp(-t * (10 if open_ else 75)) * 0.45, 0.0004, 0.005)


@memo
def shaker(dur=0.085):
    n, t = _t(dur)
    return fade(bp(rng().normal(0, 1, n), 4200, 11500, 4) * np.exp(-t * 40) * (1 - np.exp(-t * 330)) * .42,
                0.001, 0.008)


@memo
def crash(dur=1.5):
    n, t = _t(dur)
    nz = rng().normal(0, 1, n)
    c = hp(nz, 3400) * np.exp(-t * 2.4) + hp(nz, 9000) * np.exp(-t * 5.8) * 0.5
    return fade(sat(c, 1.4) * 0.42, 0.001, 0.06)


@memo
def china(dur=0.9):
    n, t = _t(dur)
    c = hp(rng().normal(0, 1, n), 2500) * np.exp(-t * 5) * (1 + 0.7 * np.sin(2 * np.pi * 517 * t))
    return fade(sat(c * 1.2, 2.0) * 0.38, 0.0005, 0.05)


@memo
def tom(f=150.0, dur=0.3):
    n, t = _t(dur)
    o = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t * 30))) / SR) * np.exp(-t * 10)
    o += hp(rng().normal(0, 1, n), 1800) * np.exp(-t * 120) * 0.2
    return fade(sat(o * 1.3, 2.2) * 0.65, 0.0005, 0.02)


@memo
def woodblock(f=1150.0, dur=0.09):
    n, t = _t(dur)
    o = (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.4 * t)) * np.exp(-t * 60)
    return fade(sat(o * 1.2, 2.0) * 0.5, 0.0004, 0.006)


@memo
def membrane(f=330.0, dur=0.22, slap=0.0):
    """Bongo/conga/djembe: f alta = bongo, ~185 conga, ~92 djembe."""
    n, t = _t(dur)
    o = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t * 80))) / SR) * np.exp(-t * (26 if f > 250 else 14))
    for r, a in ((1.59, .42), (2.14, .24)):
        o += np.sin(2 * np.pi * f * r * t) * a * np.exp(-t * 34)
    o += hp(rng().normal(0, 1, n), 2200) * np.exp(-t * (240 - 120 * slap)) * (0.2 + 0.5 * slap)
    return fade(sat(o * 1.25, 2.3) * 0.62, 0.0005, 0.012)


@memo
def slit_drum(f=300.0, dur=0.32):
    """Tamburo a fessura di legno (kentongan): il 'tung'."""
    n, t = _t(dur)
    o = sum(np.sin(2 * np.pi * f * r * t) * a * np.exp(-t * d)
            for r, a, d in ((1.0, 1.0, 11), (2.47, .45, 20), (4.08, .22, 32), (0.5, .35, 9)))
    o += bp(rng().normal(0, 1, n), 800, 5000, 2) * np.exp(-t * 260) * 0.5
    return fade(sat(o * 1.3, 2.2) * 0.62, 0.0005, 0.02)


# ================================================================ BASSI
@memo
def sub(f, dur, grit=0.2):
    n, t = _t(dur)
    b = np.sin(2 * np.pi * f * t) + grit * signal.sawtooth(2 * np.pi * f * t)
    return fade(lp(sat(b * 1.1, 1.8), 240) * 0.6, 0.005, 0.02)


@memo
def bass808(f, dur):
    n, t = _t(dur)
    o = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.4 * np.exp(-t * 45))) / SR)
    return fade(lp(sat(o * 2.6, 3.0) * np.exp(-t * 2.2), 900) * 0.85, 0.001, 0.03)


@memo
def tuba(f, dur):
    n, t = _t(dur)
    o = signal.sawtooth(2 * np.pi * f * t) * 0.6 + np.sin(2 * np.pi * f * t) * 0.9
    o = sweep(o, f * (2.0 + 5.0 * np.exp(-t * 16)))
    return fade(sat(o * 1.5, 2.2) * np.minimum(1, t * 90) * np.exp(-t * 4.5) * 0.85, 0.003, 0.02)


@memo
def wobble(f, dur, lfo_hz, top=1900.0):
    """Basso wobble: lo LFO apre e chiude il filtro. Tienilo sotto e metti il
    carattere nei layer alti, altrimenti diventa fango."""
    n, t = _t(dur)
    o = signal.sawtooth(2 * np.pi * f * t) + signal.sawtooth(2 * np.pi * f * 1.004 * t + 1) * .7 + np.sin(2 * np.pi * f * t) * .9
    l = 0.5 - 0.5 * np.cos(2 * np.pi * lfo_hz * t)
    o = sweep(o, 90 + top * l, 'band', 1.9) * 1.4 + lp(o, 140) * 0.7
    return fade(sat(o * 1.6, 3.0) * 0.5, 0.004, 0.02)


# ================================================================ MELODICI
@memo
def pluck(f, dur, bright=1.0):
    """Pluck kawaii: saw+square in un lowpass che chiude subito."""
    n, t = _t(dur)
    osc = sum(signal.sawtooth(2 * np.pi * f * 2 ** (c / 1200) * t) * .5 + signal.square(2 * np.pi * f * 2 ** (c / 1200) * t, .42) * .3
              for c in (-8, 0, 8)) / 3 + np.sin(2 * np.pi * f * t) * .35
    o = sweep(osc * np.exp(-t * 26), (f * 3 + 5200 * bright) * (0.3 + 0.7 * np.exp(-t * 14)))
    return fade(sat(o * 1.5, 2.0) * 0.8, 0.001, 0.01)


@memo
def mallet(f, dur, kind='xylo'):
    """Barra libera. xylo = modi 1:2.76:5.4 (suono 'd'ossa'); marimba = 1:3.93:9.2 + risonatore."""
    n, t = _t(dur)
    modes = ((1, 1, 9), (2.76, .52, 14), (5.40, .26, 20), (8.93, .12, 28)) if kind == 'xylo' \
        else ((1, 1, 5.5), (3.93, .34, 11), (9.22, .12, 19))
    o = sum(np.sin(2 * np.pi * f * r * t) * a * np.exp(-t * d) for r, a, d in modes)
    if kind != 'xylo':
        o += np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6) * 0.45
    o += hp(rng().normal(0, 1, n), 3000) * np.exp(-t * 300) * 0.18
    return fade(sat(o * 0.55, 1.4) * 0.7, 0.0006, 0.015)


@memo
def kalimba(f, dur):
    n, t = _t(dur)
    o = np.sin(2 * np.pi * f * t) * np.exp(-t * 4.2) + np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 7) * .42
    return fade(o * 0.52, 0.0008, 0.03)


@memo
def bell(f, dur):
    """Campanello FM."""
    n, t = _t(dur)
    b = np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * f * 2 * t) * 3.2 * np.exp(-t * 11)) * np.exp(-t * 7)
    return fade(b * 0.5, 0.001, 0.02)


@memo
def ks_string(f, dur, mute=0):
    """Corda Karplus-Strong come IIR (veloce). mute=1 -> palm mute."""
    n = int(dur * SR)
    p = max(4, int(round(SR / f)))
    x = np.zeros(n)
    x[:p] = lp(rng().uniform(-1, 1, p), 3200 if mute else 7000, 2)
    fb = 0.988 if mute else 0.9985
    a = np.zeros(p + 2)
    a[0], a[p], a[p + 1] = 1.0, -0.5 * fb, -0.5 * fb
    y = signal.lfilter([1.0], a, x)
    if mute:
        y = lp(y, 1400, 2) * np.exp(-np.arange(n) / SR * 22)
    return y


def amp_sim(x, gain=34.0):
    """Ampli high-gain + cassa 4x12."""
    x = peak(hp(x, 110, 2), 900, 7.0, 0.8)
    x = np.tanh(x * gain + 0.12) - np.tanh(0.12)
    x = np.tanh(peak(x, 650, -4.0, 1.2) * 2.6)
    return peak(lp(hp(x, 75, 2), 5600, 4), 2800, 3.0, 1.5)


@memo
def power_chord(root, dur, mute=0, seed_=1):
    s = sum(ks_string(root * r, dur, mute) * g for r, g in ((1.0, 1.0), (1.4983, .8), (2.0, .6)))
    return fade(amp_sim(s * 0.9) * 0.4, 0.0008, 0.012 if mute else 0.08)


@memo
def supersaw(freqs, dur, detune=14.0, cutoff=3000.0):
    n, t = _t(dur)
    o = sum(signal.sawtooth(2 * np.pi * f * 2 ** (c / 1200) * t + rng().uniform(0, 6))
            for f in freqs for c in np.linspace(-detune, detune, 5)) / (len(freqs) * 5)
    e = np.exp(-t * 3.2) * .6 + .4 * np.exp(-t * .9)
    return fade(sat(lp(o * e, cutoff) * 1.4, 1.8) * 0.5, 0.004, 0.03)


@memo
def organ(freqs, dur, trem=1.0):
    n, t = _t(dur)
    o = sum(np.sin(2 * np.pi * f * h * t) * a for f in freqs
            for h, a in ((1, 1), (2, .55), (3, .34), (4, .26), (6, .14), (8, .1))) / (len(freqs) * 2.4)
    o *= 1 + 0.1 * trem * np.sin(2 * np.pi * 5.2 * t)
    e = np.minimum(1, t * 55) * np.minimum(1, (dur - t) * 14)
    return fade(sat(o * .9, 1.6) * e * 0.45, 0.012, 0.05)


@memo
def calliope(f, dur):
    """Organo da fiera: canne quasi sinusoidali, vibrato largo, soffio."""
    n, t = _t(dur)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 6.4 * t)
    o = sum((np.sin(ph) + .35 * np.sin(2 * ph) + .12 * np.sin(3 * ph)) * g
            for ph, g in ((2 * np.pi * np.cumsum(f * d * vib) / SR, g) for d, g in ((1.0, 1.0), (1.0042, .55))))
    o += bp(rng().normal(0, 1, n), f, f * 6, 2) * 0.12
    e = np.minimum(1, t * 120) * (0.85 + np.exp(-t * 60) * .5) * np.minimum(1, (dur - t) * 60)
    return fade(sat(o * .55, 1.6) * e * 0.42, 0.002, 0.01)


@memo
def accordion(freqs, dur):
    """Musette: tre ance a +/-14 cent, il battimento 'da baita'."""
    n, t = _t(dur)
    o = sum(signal.square(2 * np.pi * f * 2 ** (c / 1200) * t, .36) * .45 + signal.sawtooth(2 * np.pi * f * 2 ** (c / 1200) * t) * .35
            for f in freqs for c in (-14, 0, 14)) / (len(freqs) * 3)
    e = np.minimum(1, t * 70) * np.minimum(1, (dur - t) * 40)
    return fade(sat(bp(o, 220, 5200, 2) * 1.6, 1.8) * e * 0.55, 0.003, 0.02)


@memo
def trumpet(f, dur):
    n, t = _t(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 - 0.012 * np.exp(-t * 40))) / SR
    o = sweep(signal.sawtooth(ph) * .7 + np.sin(ph) * .4, f * (2.5 + 6 * np.exp(-t * 9)))
    e = np.minimum(1, t * 90) * np.minimum(1, (dur - t) * 40)
    return fade(sat(o * 1.5, 2.0) * e * 0.38, 0.003, 0.015)


@memo
def kazoo(f, dur):
    n, t = _t(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t))) / SR
    src = signal.square(ph, .3) * .6 + signal.sawtooth(ph) * .4
    o = src + bp(rng().normal(0, 1, n) * (.5 + .5 * signal.square(ph, .3)), f, 6000, 2) * .5
    o = bp(o, 300, 1400, 2) * 1.3 + bp(o, 1400, 3500, 2) * .9
    e = np.minimum(1, t * 80) * np.minimum(1, (dur - t) * 40)
    return fade(sat(o * 1.6, 3.2) * e * 0.32, 0.003, 0.015)


@memo
def screech(f0, dur, lfo_hz=8.0):
    """Screech riddim: supersaw detunato filtrato, taglia in alto."""
    n, t = _t(dur)
    osc = sum(signal.sawtooth(2 * np.pi * f0 * 2 ** (((k - 3) / 3 * 16) / 1200) * t + k * .8) for k in range(7)) / 7
    l = 0.5 - 0.5 * np.cos(2 * np.pi * lfo_hz * t)
    o = sat(sweep(osc, 800 + 3400 * l, 'band', 1.75) * 2.4, 4.5) + sat(osc * .6, 2) * .3
    return fade(hp(o, 380) * 0.5, 0.004, 0.03)


@memo
def alphorn(f, dur):
    n, t = _t(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 - 0.03 * np.exp(-t * 9))) / SR
    o = lp(sum(np.sin(ph * h) / h ** 1.15 for h in range(1, 9)), 1700, 2)
    e = np.minimum(1, t * 6) * np.minimum(1, (dur - t) * 4)
    return fade(sat(o * .9, 1.6) * e * 0.55, 0.03, 0.12)


def theremin(f0, f1, dur, vib=5.4):
    n, t = _t(dur)
    f = f0 * (f1 / f0) ** ((t / dur) ** 0.7) * (1 + 0.022 * np.sin(2 * np.pi * vib * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    o = np.sin(ph) + .16 * np.sin(2 * ph)
    return fade(o * np.minimum(1, t * 7) * np.minimum(1, (dur - t) * 5) * 0.34, 0.03, 0.08)


def choir(freqs, dur, vowel='a', voices=6, seed_=0):
    r = np.random.default_rng(400 + seed_)
    F = {'a': (720, 1150, 2600), 'o': (460, 820, 2500), 'i': (300, 2250, 3000)}[vowel]
    n, t = _t(dur)
    out = np.zeros(n)
    for f0 in freqs:
        for _ in range(voices):
            f = f0 * 2 ** (r.uniform(-18, 18) / 1200) * (1 + 0.006 * np.sin(2 * np.pi * r.uniform(4, 6) * t))
            src = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * .7 + r.normal(0, .12, n)
            out += sum(bp(src, fc * .84, fc * 1.18, 2) * g for fc, g in zip(F, (1, .6, .3)))
    e = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.6)
    return fade(sat(out / (len(freqs) * voices) * 1.8, 2.0) * e * 0.55, 0.05, 0.2)


# ================================================================ FX
def riser(dur, f0=240.0, f1=5200.0):
    n, t = _t(dur)
    p = (t / dur) ** 1.6
    ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** p) / SR
    return fade(sat((signal.sawtooth(ph) * .4 + np.sin(ph) * .4) * p ** .9, 1.7) * .34, 0.01, 0.01)


def whoosh(dur=0.45):
    n, t = _t(dur)
    p = t / dur
    nz = sweep(rng().normal(0, 1, n), 280 * (6000 / 280) ** p, 'band', 2.2, 256)
    return fade(nz * np.sin(np.pi * p) ** 1.2 * 0.38, 0.01, 0.03)


def impact(dur=2.0):
    n, t = _t(dur)
    b = np.sin(2 * np.pi * np.cumsum(32 + 120 * np.exp(-t * 14)) / SR) * np.exp(-t * 2.6)
    b += lp(rng().normal(0, 1, n), 700) * np.exp(-t * 6.5) * .6
    return fade(sat(b * 1.2 + crash(dur) * .8, 2.2), 0.001, 0.05)


def vine_boom():
    n, t = _t(1.1)
    b = np.sin(2 * np.pi * np.cumsum(42 + 130 * np.exp(-t * 17)) / SR) * np.exp(-t * 3.4)
    b += lp(rng().normal(0, 1, n), 420) * np.exp(-t * 9) * 0.5
    return fade(hardclip(b, 1.9) * 0.8, 0.001, 0.04)


def airhorn(dur=1.0, f0=233.0):
    n, t = _t(dur)
    bend = 1 + 0.055 * np.exp(-t * 10) + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    o = sum(np.sin(2 * np.pi * np.cumsum(f0 * s * bend) / SR * h) * a / s
            for s in (1.0, 1.4983, 2.0) for h, a in ((1, 1), (2, .62), (3, .45), (4, .3), (5, .22), (6, .15)))
    o = bp(hardclip(o * 0.14, 2.0), 190, 9500)
    return fade(o * np.minimum(1, t * 80) * 0.75, 0.01, 0.09)


def scratch(dur=0.32):
    n, t = _t(dur)
    spd = signal.sawtooth(2 * np.pi * 7 * t, 0.5)
    ph = 2 * np.pi * np.cumsum(240 * 1.9 ** spd) / SR
    o = signal.sawtooth(ph) * .6 + bp(rng().normal(0, 1, n), 700, 5200, 2) * np.abs(spd) * .6
    return fade(sat(o * 1.4, 3) * .42, 0.005, 0.03)


def boing(dur=0.42, f0=480.0, f1=110.0):
    n, t = _t(dur)
    f = f0 * (f1 / f0) ** (t / dur) * (1 + 0.14 * np.sin(2 * np.pi * 17 * t))
    return fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4) * .42, 0.002, 0.02)


def slide_whistle(dur=0.5, up=True):
    n, t = _t(dur)
    p = (t / dur) ** 0.8
    f = 520 * (2700 / 520) ** (p if up else 1 - p)
    return fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t * 30) * .32, 0.01, 0.05)


def beep(dur):
    """Il bip della censura."""
    n, t = _t(dur)
    return fade(np.sin(2 * np.pi * 1000 * t) * 0.42, 0.003, 0.004)


def honk(f=420.0):
    out = []
    for ff, d in ((f, 0.16), (f * .94, 0.22)):
        n, t = _t(d)
        ph = 2 * np.pi * np.cumsum(ff * (1 + .05 * np.exp(-t * 30) - .06 * t / d)) / SR
        o = signal.square(ph, .25) + .5 * signal.sawtooth(ph)
        o = sat((bp(o, 500, 1400, 2) * 1.4 + bp(o, 1800, 3200, 2) * .6) * 1.8, 3) * np.minimum(1, t * 120) * np.minimum(1, (d - t) * 60)
        out += [o, np.zeros(int(0.03 * SR))]
    return fade(np.concatenate(out) * .42, 0.002, 0.02)


def crickets(dur, seed_=0):
    r = np.random.default_rng(50 + seed_)
    n = int(dur * SR)
    out = np.zeros(n)
    t0 = 0.05
    while t0 < dur - 0.2:
        for k in range(3):
            i, m = int((t0 + k * .045) * SR), int(.03 * SR)
            tt = np.arange(m) / SR
            out[i:i + m] += np.sin(2 * np.pi * 4300 * tt) * (signal.square(2 * np.pi * 180 * tt) * .5 + .5) * np.sin(np.pi * tt / .03)
        t0 += r.uniform(.35, .55)
    return out * 0.2


def slow_clap(n_claps=4, gap=0.42):
    out = np.zeros(int((n_claps * gap + 0.4) * SR))
    for k in range(n_claps):
        c = clap(0.25) * (0.9 - 0.1 * k)
        i = int(k * gap * SR)
        out[i:i + len(c)] += c
    return out


def heartbeat():
    out = np.zeros(int(0.8 * SR))
    for st, g in ((0.0, 1.0), (0.28, 0.7)):
        i, m = int(st * SR), int(0.16 * SR)
        tt = np.arange(m) / SR
        out[i:i + m] += np.sin(2 * np.pi * np.cumsum(55 * (1 + .5 * np.exp(-tt * 40))) / SR) * np.exp(-tt * 15) * g
    return lp(out, 180) * 0.8


def crowd_roar(dur, intensity=1.0, seed_=0):
    """Folla gasata: boato + applausi + urla a formanti."""
    r = np.random.default_rng(1000 + seed_)
    n, t = _t(dur)
    roar = bp(r.normal(0, 1, n), 320, 4600, 4) * (1 + .3 * np.sin(2 * np.pi * .4 * t + r.uniform(0, 6))) * .3
    claps = np.zeros(n)
    for _ in range(int(dur * 75 * intensity)):
        i = r.integers(0, max(1, n - 2000))
        ln = int(r.uniform(.004, .012) * SR)
        claps[i:i + ln] += bp(r.normal(0, 1, ln), 1500, 7000, 2) * np.exp(-np.arange(ln) / SR * 165) * r.uniform(.25, .9)
    return sat(hp(roar + claps * .55, 160) * intensity, 1.4) * .55


def wind(dur, seed_=0):
    r = np.random.default_rng(90 + seed_)
    n, t = _t(dur)
    fc = 420 + 320 * np.sin(2 * np.pi * .11 * t) + 180 * np.sin(2 * np.pi * .29 * t + 1)
    o = sweep(r.normal(0, 1, n), fc, 'band', 2.6, 1024)
    return fade(o * (.55 + .45 * np.sin(2 * np.pi * .17 * t)) * .3, 0.3, 0.4)


def alarm(dur, rate=1.1):
    n, t = _t(dur)
    f = np.where((np.floor(t * rate * 2) % 2) == 0, 880.0, 660.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return fade(bp(signal.square(ph) * .5 + np.sin(ph) * .5, 400, 4000, 2) * .22, 0.01, 0.1)
