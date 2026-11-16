# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
"""Video: sprite dallo screenshot, compositing in float, testi, effetti, render via ffmpeg.
Tutti i frame sono np.float32 (H, W, 3) in 0..255; si fa clip solo alla scrittura."""
import glob
import os
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
INK = (14, 14, 16)

# ================================================================ FONT
_FONT_DIRS = ['/mnt/c/Windows/Fonts', '/usr/share/fonts', os.path.expanduser('~/.fonts'),
              os.path.expanduser('~/.local/share/fonts')]
_FALLBACK = {'impact': ['impact.ttf', 'Impact.ttf', 'DejaVuSans-Bold.ttf'],
             'comic': ['comicbd.ttf', 'Comic_Sans_MS_Bold.ttf', 'DejaVuSans-Bold.ttf'],
             'sans': ['DejaVuSans-Bold.ttf'], 'serif': ['DejaVuSerif-Bold.ttf'],
             'mono': ['DejaVuSansMono-Bold.ttf']}


_FP = {}


def font_path(kind='impact'):
    if kind in _FP:
        return _FP[kind]
    for fname in _FALLBACK[kind]:
        for d in _FONT_DIRS:
            hits = glob.glob(os.path.join(d, '**', fname), recursive=True)
            if hits:
                _FP[kind] = hits[0]
                return hits[0]
    raise FileNotFoundError(f'nessun font per {kind}: installa fonts-dejavu-core')


_FC = {}


def font(kind, size):
    k = (kind, size)
    if k not in _FC:
        _FC[k] = ImageFont.truetype(font_path(kind), size)
    return _FC[k]


# ================================================================ SPRITE
def load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB')).astype(np.uint8)


def circle_alpha(w, h):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xs - (w - 1) / 2) / (w / 2)) ** 2 + ((ys - (h - 1) / 2) / (h / 2)) ** 2)
    return np.clip((1.0 - d) * min(w, h) / 3.0, 0, 1)


def upscale(p, k):
    return cv2.resize(p, (p.shape[1] * k, p.shape[0] * k), interpolation=cv2.INTER_NEAREST)


def avatar_sprite(img, box, k=12):
    """Avatar tondo: box=(x0,y0,x1,y1) quadrato attorno al cerchio."""
    x0, y0, x1, y1 = box
    p = np.ascontiguousarray(img[y0:y1, x0:x1])
    w, h = p.shape[1], p.shape[0]
    return upscale(p, k), cv2.resize(circle_alpha(w, h), (w * k, h * k), interpolation=cv2.INTER_LINEAR)


def text_sprite(img, box, k=12, lo=62.0, hi=150.0):
    """Parola dello screenshot come sprite bianco + alpha dalla luminanza: si ricolora con tint().
    lo/hi: 70/165 per testo bianco, 62/150 per i link blu."""
    x0, y0, x1, y1 = box
    p = img[y0:y1, x0:x1]
    luma = p.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    h, w = p.shape[:2]
    a = cv2.resize(np.clip((luma - lo) / (hi - lo), 0, 1), (w * k, h * k), interpolation=cv2.INTER_LINEAR)
    return np.full((h * k, w * k, 3), 255, np.uint8), a


def full_sprite(img, k=3):
    return upscale(img, k), np.ones((img.shape[0] * k, img.shape[1] * k), np.float32)


def tint(rgb, col):
    return np.clip(rgb.astype(np.float32) * (np.array(col, np.float32) / 255.0), 0, 255)


def place(rgb, a, cx, cy, sx=1.0, sy=None, rot=0.0):
    """Sprite trasformato in due layer a pieno schermo (colore, alpha)."""
    sy = sx if sy is None else sy
    h, w = rgb.shape[:2]
    tw, th = max(1, int(w * sx)), max(1, int(h * sy))
    r = cv2.resize(rgb.astype(np.float32), (tw, th), interpolation=cv2.INTER_NEAREST)
    al = cv2.resize(a, (tw, th), interpolation=cv2.INTER_LINEAR)
    if rot:
        M = cv2.getRotationMatrix2D((tw / 2, th / 2), rot, 1.0)
        cs, sn = abs(M[0, 0]), abs(M[0, 1])
        nw, nh = int(th * sn + tw * cs), int(th * cs + tw * sn)
        M[0, 2] += nw / 2 - tw / 2
        M[1, 2] += nh / 2 - th / 2
        r = cv2.warpAffine(r, M, (nw, nh), flags=cv2.INTER_NEAREST)
        al = cv2.warpAffine(al, M, (nw, nh), flags=cv2.INTER_LINEAR)
        tw, th = nw, nh
    rgbL = np.zeros((H, W, 3), np.float32)
    aL = np.zeros((H, W), np.float32)
    x0, y0 = int(cx - tw / 2), int(cy - th / 2)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x0 + tw), min(H, y0 + th)
    if x1c > x0c and y1c > y0c:
        hh, ww = y1c - y0c, x1c - x0c
        rgbL[y0c:y1c, x0c:x1c] = r[sy0:sy0 + hh, sx0:sx0 + ww]
        aL[y0c:y1c, x0c:x1c] = al[sy0:sy0 + hh, sx0:sx0 + ww]
    return rgbL, aL


def comp(dst, rgbL, aL, alpha=1.0):
    al = (aL * alpha)[:, :, None]
    return dst * (1 - al) + rgbL * al


def add_glow(dst, aL, color, strength=1.0, sigma=22.0):
    return dst + np.array(color, np.float32) * (cv2.GaussianBlur(aL, (0, 0), sigma) * strength)[:, :, None]


def sprite(dst, rgb, a, cx, cy, s=1.0, rot=0.0, shadow=10, glow=None, glow_str=1.0):
    """Sprite con ombra (e glow opzionale): resta leggibile su qualsiasi fondo."""
    if shadow:
        dst = comp(dst, *place(np.zeros_like(rgb), a, cx + shadow, cy + shadow, s, s, rot), 0.6)
    rL, aL = place(rgb, a, cx, cy, s, s, rot)
    if glow is not None:
        dst = add_glow(dst, aL, glow, glow_str, 24)
    return comp(dst, rL, aL)


def C(col):
    return tuple(float(v) for v in col)


# ================================================================ FONDALI
def grad(top, bot):
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    return np.repeat(np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g, W, axis=1)


def flat(col):
    return np.full((H, W, 3), np.array(col, np.float32))


_POLAR = {}


def rays(t, n=16, c1=(255, 210, 74), c2=(255, 140, 26), spin=0.06, center=(0.5, 0.5)):
    k = center
    if k not in _POLAR:
        ys, xs = np.mgrid[0:H:2, 0:W:2].astype(np.float32)
        _POLAR[k] = np.arctan2(ys - H * k[1] / 2, xs - W * k[0] / 2) / (2 * np.pi)
    m = ((_POLAR[k] * n + t * spin * n) % 1.0) < 0.5
    small = np.where(m[:, :, None], np.array(c1, np.float32), np.array(c2, np.float32))
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)


def checker(t, n=10, c1=(214, 30, 40), c2=(246, 244, 240)):
    xs, ys = np.meshgrid(np.arange(160), np.arange(90))
    g = ((xs / 160 * n + t).astype(np.int32) + (ys / 90 * n * .5625 + t * .5).astype(np.int32)) % 2
    small = np.where(g[:, :, None] == 0, np.array(c1, np.float32), np.array(c2, np.float32))
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)


def rainbow(t, speed=70.0, diag=2.2):
    xs, ys = np.meshgrid(np.arange(160), np.arange(90))
    h = ((xs + ys * diag) * 1.6 + t * speed) % 180
    img = np.stack([h, np.full_like(h, 235), np.full_like(h, 255)], -1).astype(np.uint8)
    return cv2.resize(cv2.cvtColor(img, cv2.COLOR_HSV2RGB), (W, H)).astype(np.float32)


def particles(dst, t, n=80, seed=3, speed=1.0, size=1.0, col=None, fall=True):
    """Coriandoli (col=None: arcobaleno), neve/cenere (col fisso)."""
    r = np.random.default_rng(seed)
    x0, y0 = r.uniform(0, W, n), r.uniform(0, H, n)
    vy = r.uniform(60, 220, n) * speed * (1 if fall else -1)
    sz = r.uniform(3, 9, n) * size
    hues = r.uniform(0, 180, n)
    for i in range(n):
        y = (y0[i] + t * vy[i]) % (H + 20) - 10
        x = (x0[i] + np.sin(t * 1.3 + i) * 26) % W
        c = col if col is not None else cv2.cvtColor(np.uint8([[[(hues[i] + t * 40) % 180, 240, 255]]]),
                                                     cv2.COLOR_HSV2RGB)[0, 0]
        cv2.circle(dst, (int(x), int(y)), max(1, int(sz[i])), C(c), -1, cv2.LINE_AA)
    return dst


# ================================================================ EFFETTI
def beat_pulse(t, beat, sharp=5.0):
    """1 sul colpo, decade a 0 entro il beat."""
    return float(np.exp(-((t % beat) / beat) * sharp))


def beat_zoom(a, z):
    if abs(z - 1.0) < 0.004:
        return a
    nw, nh = int(W * z), int(H * z)
    im = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x0, y0 = (nw - W) // 2, (nh - H) // 2
    return im[y0:y0 + H, x0:x0 + W]


def shake(a, amt, r):
    sh = int(amt)
    if sh <= 0:
        return a
    return np.roll(np.roll(a, int(r.integers(-sh, sh + 1)), 1), int(r.integers(-sh, sh + 1)), 0)


def jelly(a, amp, freq, phase):
    if amp < 0.8:
        return a
    off = (amp * np.sin(2 * np.pi * freq * np.arange(H) / H + phase)).astype(np.int32)
    return a[np.arange(H)[:, None], (np.arange(W)[None, :] - off[:, None]) % W]


def rgb_split(a, dx):
    if abs(dx) < 1:
        return a
    o = a.copy()
    o[:, :, 0] = np.roll(a[:, :, 0], int(dx), 1)
    o[:, :, 2] = np.roll(a[:, :, 2], -int(dx), 1)
    return o


def slice_glitch(a, n, maxsh, r):
    o = a.copy()
    for _ in range(n):
        hgt = int(r.integers(5, 60))
        y = int(r.integers(0, H - hgt))
        o[y:y + hgt] = np.roll(a[y:y + hgt], int(r.integers(-maxsh, maxsh + 1)), axis=1)
    return o


def pixelate(a, amt):
    if amt <= 1.01:
        return a
    s = cv2.resize(a, (max(2, int(W / amt)), max(2, int(H / amt))), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(s, (W, H), interpolation=cv2.INTER_NEAREST)


def saturate(a, s):
    g = (a @ np.array([0.299, 0.587, 0.114], np.float32))[:, :, None]
    return g + (a - g) * s


def deepfry(a, sat_=1.8, contrast=1.4, warm=0.2):
    a = saturate(a, sat_)
    a = (a - 128) * contrast + 128
    a[:, :, 0] *= 1 + 0.2 * warm
    a[:, :, 2] *= 1 - 0.15 * warm
    return a


def flash(a, amt, col=(255, 255, 255)):
    return a * (1 - amt) + np.array(col, np.float32) * amt if amt > 0.004 else a


_VIG = None


def vignette(a, amt):
    global _VIG
    if _VIG is None:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        _VIG = (np.clip(np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2) / 1.42, 0, 1) ** 1.5)[:, :, None]
    return a * (1.0 - _VIG * amt)


def grain(a, amt, r):
    n = r.normal(0, amt, (H // 2, W // 2, 1)).astype(np.float32)
    return a + cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)[:, :, None]


def scanlines(a, s, off=0):
    m = np.where((np.arange(H) + off) % 3 == 0, 1.0 - s, 1.0).astype(np.float32)
    return a * m[:, None, None]


def mirror4(a):
    q = cv2.resize(a[:H // 2, :W // 2], (W // 2, H // 2))
    o = np.empty_like(a)
    o[:H // 2, :W // 2], o[:H // 2, W // 2:] = q, q[:, ::-1]
    o[H // 2:, :W // 2], o[H // 2:, W // 2:] = q[::-1], q[::-1, ::-1]
    return o


# ================================================================ TESTO
def text_layer(text, size, col, kind='impact', stroke=0, cx=None, cy=None, left=None):
    """Testo libero (cartelli, etichette): ritorna (rgb, alpha)."""
    f = font(kind, size)
    d0 = ImageDraw.Draw(Image.new('L', (8, 8)))
    lines = text.split('\n')
    sizes, tot = [], 0
    for ln in lines:
        bb = d0.textbbox((0, 0), ln, font=f, stroke_width=stroke)
        sizes.append((bb[2] - bb[0], bb[3] - bb[1], bb[1]))
        tot += bb[3] - bb[1] + int(size * 0.12)
    cx = W // 2 if cx is None else cx
    cy = H // 2 if cy is None else cy
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    yy = cy - tot // 2
    for ln, (tw, th, oy) in zip(lines, sizes):
        dl.text((left if left is not None else cx - tw // 2, yy - oy), ln, font=f,
                fill=tuple(int(v) for v in col) + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
        yy += th + int(size * 0.12)
    arr = np.asarray(layer).astype(np.float32)
    return arr[:, :, :3], arr[:, :, 3] / 255.0


def caption(a, text, size, col=(255, 255, 255), kind='impact', rot=0.0, jit=0, r=None,
            glow=None, glow_str=1.0, bottom=True, strike=0.0):
    """La scritta meme. bottom=True: ancorata in basso, cosi' non copre lo sprite al centro."""
    f = font(kind, size)
    sw = max(5, size // 12)
    d0 = ImageDraw.Draw(Image.new('L', (8, 8)))
    lines = text.split('\n')
    sizes, tot = [], 0
    for ln in lines:
        bb = d0.textbbox((0, 0), ln, font=f, stroke_width=sw)
        sizes.append((bb[2] - bb[0], bb[3] - bb[1]))
        tot += bb[3] - bb[1] + int(size * 0.14)
    y0 = (H - tot - 46) if bottom else (H - tot) // 2
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    yy = y0
    for ln, (tw, th) in zip(lines, sizes):
        jx = int(r.integers(-jit, jit + 1)) if (jit and r is not None) else 0
        jy = int(r.integers(-jit, jit + 1)) if (jit and r is not None) else 0
        x = (W - tw) // 2 + jx
        dl.text((x, yy + jy), ln, font=f, fill=tuple(int(v) for v in col) + (255,),
                stroke_width=sw, stroke_fill=INK + (255,))
        if strike > 0:
            ym = yy + jy + th // 2 + int(size * 0.08)
            dl.line([(x - 20, ym), (x - 20 + (tw + 40) * strike, ym)], fill=(230, 20, 20, 255), width=max(8, size // 9))
        yy += th + int(size * 0.14)
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, center=(W // 2, y0 + tot // 2))
    arr = np.asarray(layer).astype(np.float32)
    aL = arr[:, :, 3] / 255.0
    if glow is not None:
        a = add_glow(a, aL, glow, glow_str, 16.0)
    return comp(a, arr[:, :, :3], aL)


def caption_fits(text, size, kind='impact', max_w=W - 60):
    f = font(kind, size)
    d0 = ImageDraw.Draw(Image.new('L', (8, 8)))
    return max(d0.textbbox((0, 0), ln, font=f, stroke_width=max(5, size // 12))[2] for ln in text.split('\n')) <= max_w


# ================================================================ SCALETTA E CONTROLLI
class Timeline:
    """scene: [(t_inizio, nome)], testi: [(t, durata, testo, size, ...)]"""

    def __init__(self, scenes, texts):
        self.scenes = sorted(scenes, key=lambda x: x[0])
        self.st = np.array([s[0] for s in self.scenes])
        self.texts = sorted(texts, key=lambda x: x[0])

    def scene_at(self, t):
        i = max(0, int(np.searchsorted(self.st, t + 1e-6) - 1))
        return self.scenes[i][1], t - self.scenes[i][0]

    def texts_at(self, t):
        return [(x, (t - x[0]) / x[1]) for x in self.texts if x[0] <= t < x[0] + x[1]]

    def check(self, kinds=None):
        """Scritte sovrapposte nel tempo e scritte troppo larghe: entrambi bug gia' visti."""
        bad = []
        for a, b in zip(self.texts, self.texts[1:]):
            if a[0] + a[1] > b[0] + 1e-6:
                bad.append(f'SOVRAPPOSTE: "{a[2]!r}" finisce {a[0] + a[1]:.2f}s, "{b[2]!r}" parte {b[0]:.2f}s')
        for x in self.texts:
            kind = x[4] if len(x) > 4 and isinstance(x[4], str) and x[4] in _FALLBACK else 'impact'
            if not caption_fits(x[2], int(x[3] * 1.2), kind):
                bad.append(f'TROPPO LARGA: "{x[2]!r}" a size {x[3]}')
        return bad


def scene_sheet(scene_fns, out_png, t0=0.0, step=0.37, extra=None):
    """Un frame per scena in un foglio 3xN: guardalo PRIMA del render completo."""
    tiles = []
    for k, (nm, fn) in enumerate(scene_fns.items()):
        t = t0 + k * step
        try:
            a = fn(t, 0.7, 1.0, 0.8) if (extra and nm in extra) else fn(t, 0.7, 1.0)
            a = caption(a, nm.upper(), 40, bottom=False)
            tiles.append(cv2.resize(np.clip(a, 0, 255).astype(np.uint8), (426, 240)))
        except Exception as e:
            print(f'ERRORE scena {nm}: {type(e).__name__}: {e}')
            tiles.append(np.zeros((240, 426, 3), np.uint8))
    rows = (len(tiles) + 2) // 3
    sheet = np.zeros((rows * 240, 3 * 426, 3), np.uint8)
    for i, ti in enumerate(tiles):
        sheet[(i // 3) * 240:(i // 3) * 240 + 240, (i % 3) * 426:(i % 3) * 426 + 426] = ti
    cv2.imwrite(out_png, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    return out_png


class Renderer:
    """with Renderer(out_mp4, audio_raw, fps, ffmpeg) as r: r.write(frame)"""

    def __init__(self, out, audio_raw, fps, ffmpeg, crf=20):
        self.cmd = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
                    '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                    '-f', 's16le', '-ar', '44100', '-ac', '2', '-i', audio_raw,
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high', '-level', '4.2', '-c:a', 'aac', '-b:a', '224k',
                    '-movflags', '+faststart', '-shortest', out]

    def __enter__(self):
        self.p = subprocess.Popen(self.cmd, stdin=subprocess.PIPE)
        return self

    def write(self, frame):
        self.p.stdin.write(np.ascontiguousarray(np.clip(frame, 0, 255).astype(np.uint8)).tobytes())

    def __exit__(self, *exc):
        self.p.stdin.close()
        rc = self.p.wait()
        if rc != 0:
            raise RuntimeError(f'ffmpeg rc={rc}')
