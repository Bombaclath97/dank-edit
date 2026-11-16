#!/usr/bin/env python3
"""Foglio di controllo: frame del video ai tempi dati, con l'etichetta del tempo.

uso: sheet.py VIDEO.mp4 OUT.png 1.0 3.5 7.2 ...   (oppure --every 2.0)
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402


def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def duration(ff, path):
    out = subprocess.run([ff, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    for ln in out.splitlines():
        if 'Duration:' in ln:
            h, m, s = ln.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('out')
    ap.add_argument('times', nargs='*', type=float)
    ap.add_argument('--every', type=float, default=0)
    ap.add_argument('--cols', type=int, default=4)
    a = ap.parse_args()
    ff = ffmpeg_bin()
    times = a.times
    if a.every:
        d = duration(ff, a.video)
        times = [round(x * a.every + 0.5, 2) for x in range(int(d / a.every))]
    tmp = tempfile.mkdtemp()
    tiles = []
    for k, t in enumerate(times):
        p = os.path.join(tmp, f'{k:03d}.png')
        subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', str(t), '-i', a.video, '-frames:v', '1', p])
        if os.path.exists(p):
            tiles.append((t, Image.open(p).resize((320, 180))))
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = Image.new('RGB', (a.cols * 320, max(1, rows) * 180))
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(tiles):
        x, y = (i % a.cols) * 320, (i // a.cols) * 180
        sheet.paste(im, (x, y))
        d.text((x + 5, y + 3), f'{t:.2f}s', fill=(255, 255, 0))
    sheet.save(a.out)
    print(a.out, len(tiles), 'frame')


if __name__ == '__main__':
    main()
