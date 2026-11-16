#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
"""Analizza uno screenshot di chat (dark mode): avatar, righe di testo, parole.

uso: segment.py IMMAGINE [--out DIR]
scrive DIR/segment.json e DIR/segment.png (ogni parola ritagliata e ingrandita, da GUARDARE).

Lezioni incorporate:
- i link sono sottolineati: la sottolineatura riempie le colonne vuote fra le lettere,
  quindi la riga di sottolineatura va esclusa prima di cercare gli spazi fra parole;
- gap >= 3 px separa le parole, ma alcune coppie di lettere (es. "ru|n") hanno
  gap 3: controlla il foglio e unisci i pezzi a mano se serve;
- l'avatar si trova come zona satura a sinistra (sat>70, val>60).
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw


def runs(mask_1d, start=0):
    out, inr = [], False
    for x in range(start, len(mask_1d)):
        if mask_1d[x] and not inr:
            st, inr = x, True
        elif not mask_1d[x] and inr:
            out.append((st, x - 1))
            inr = False
    if inr:
        out.append((st, len(mask_1d) - 1))
    return out


def group(rs, gap=3):
    if not rs:
        return []
    out, cur = [], list(rs[0])
    for a, b in rs[1:]:
        if a - cur[1] - 1 >= gap:
            out.append(tuple(cur))
            cur = [a, b]
        else:
            cur[1] = b
    out.append(tuple(cur))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--out', default='.')
    ap.add_argument('--thr', type=float, default=95.0, help='soglia luminanza del testo')
    a = ap.parse_args()
    src = Image.open(a.image).convert('RGB')
    im = np.asarray(src)
    H, W, _ = im.shape
    luma = im.astype(float) @ [0.299, 0.587, 0.114]
    hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
    sat, val = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)

    res = {'image': os.path.abspath(a.image), 'size': [W, H]}
    # ---- avatar: zona satura nella colonna sinistra
    m = (sat > 70) & (val > 60)
    m[:, int(W * 0.25) if W > 200 else 60:] = False
    ys, xs = np.where(m)
    left_edge = 0
    if len(xs) > 50:
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        side = max(x1 - x0, y1 - y0) + 3
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        res['avatar_box'] = [max(0, cx - side // 2), max(0, cy - side // 2),
                             min(W, cx + side // 2 + 1), min(H, cy + side // 2 + 1)]
        left_edge = x1 + 6
    # ---- righe di testo
    rows = (luma[:, left_edge:] > a.thr).sum(1)
    bands = [(s, e) for s, e in runs(rows > 0) if e - s >= 3]
    lines = []
    for (y0, y1) in bands:
        seg = luma[y0:y1 + 1, left_edge:]
        per_row = (seg > a.thr).sum(1)
        # riga di sottolineatura: molto piu' piena della media e sottile
        underline = [y0 + i for i, c in enumerate(per_row) if c > 2.2 * np.median(per_row[per_row > 0])]
        gy0, gy1 = y0, y1
        if underline and underline[-1] >= y1 - 2:
            gy1 = underline[0] - 1
        cols = ((luma[gy0:gy1 + 1] > a.thr).sum(0) > 0)
        words = group(runs(cols, left_edge), 3)
        lines.append({'y': [int(y0), int(y1)], 'glyph_y': [int(gy0), int(gy1)],
                      'underline_y': [int(u) for u in underline],
                      'words': [[int(p), int(q)] for p, q in words]})
    res['lines'] = lines
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'segment.json'), 'w'), indent=1)

    # ---- foglio da guardare
    tiles = []
    if 'avatar_box' in res:
        x0, y0, x1, y1 = res['avatar_box']
        tiles.append(('avatar %s' % res['avatar_box'], src.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 5, (y1 - y0) * 5), Image.NEAREST)))
    for li, ln in enumerate(lines):
        y0, y1 = ln['y']
        for wi, (p, q) in enumerate(ln['words']):
            k = 5
            tiles.append((f'riga{li} parola{wi}: x{p}-{q} y{y0}-{y1}',
                          src.crop((p - 1, y0 - 1, q + 2, y1 + 2)).resize(((q - p + 3) * k, (y1 - y0 + 3) * k), Image.NEAREST)))
    Wd = max(c.width for _, c in tiles) if tiles else 100
    Ht = sum(c.height + 20 for _, c in tiles) if tiles else 100
    sh = Image.new('RGB', (max(Wd, 320), Ht), (18, 18, 18))
    d = ImageDraw.Draw(sh)
    y = 0
    for lab, c in tiles:
        sh.paste(c, (0, y + 16))
        d.text((4, y + 2), lab, fill=(0, 255, 120))
        y += c.height + 20
    sh.save(os.path.join(a.out, 'segment.png'))

    print(json.dumps({k: v for k, v in res.items() if k != 'lines'}))
    for li, ln in enumerate(lines):
        print(f"riga {li}: y{ln['y']} glifi y{ln['glyph_y']} sottolineatura {ln['underline_y'] or '-'}")
        print('   parole:', ln['words'])
    print('foglio:', os.path.join(a.out, 'segment.png'))


if __name__ == '__main__':
    sys.exit(main())
