#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
"""Collaudo rapido (~30 s): ogni strumento, ogni voce, i primitivi video e un mini render.
Uscita 0 = tutto ok. Da lanciare dopo l'installazione o dopo una modifica alla libreria."""
import inspect
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dank import core, instruments as I, video as Vd, voice as V  # noqa: E402

ARGS = {
    'tom': (150.0,), 'membrane': (330.0,), 'sub': (55.0, 0.3), 'bass808': (55.0, 0.5), 'tuba': (65.4, 0.4),
    'wobble': (55.0, 0.8, 6.0), 'pluck': (523.0, 0.3), 'mallet': (523.0, 0.4), 'kalimba': (523.0, 0.5),
    'bell': (880.0, 0.5), 'ks_string': (55.0, 0.3, 1), 'power_chord': (55.0, 0.3, 1),
    'supersaw': ((261.6, 329.6, 392.0), 0.4), 'organ': ((220.0, 261.6), 0.6), 'calliope': (523.0, 0.3),
    'accordion': ((261.6, 329.6), 0.3), 'trumpet': (523.0, 0.3), 'kazoo': (523.0, 0.3),
    'screech': (880.0, 0.4), 'alphorn': (196.0, 0.8), 'theremin': (440.0, 660.0, 0.8),
    'choir': ((110.0, 164.8), 1.0), 'riser': (1.0,), 'beep': (0.3,), 'crickets': (1.0,),
    'crowd_roar': (1.0,), 'wind': (1.0,), 'alarm': (1.0,), 'amp_sim': (np.random.default_rng(0).normal(0, .1, 4410),),
}
fails = []


def check(label, fn):
    try:
        y = fn()
        if isinstance(y, np.ndarray) and (not np.isfinite(y).all() or len(y) == 0):
            raise ValueError('segnale vuoto o non finito')
        print(f'  ok   {label}')
    except Exception as e:                       # noqa: BLE001
        fails.append(label)
        print(f'  FAIL {label}: {type(e).__name__}: {e}')


print('== strumenti')
for name, fn in inspect.getmembers(I, inspect.isfunction):
    if fn.__module__ == 'dank.instruments' and not name.startswith('_'):
        check(name, lambda fn=fn, name=name: fn(*ARGS.get(name, ())))

print('== voci (espeak-ng)')
for name, a in (('speak', ('ciao', 'it')), ('robot', ('hello',)), ('growl', ('ciao',)),
                ('whisper', ('hello',)), ('chop', ('prova', 1, 440.0, 0.3))):
    check(name, lambda name=name, a=a: getattr(V, name)(*a))

print('== video')
check('font impact/sans/mono', lambda: [Vd.font(k, 40) for k in ('impact', 'sans', 'mono')] and None)
img = np.zeros((60, 220, 3), np.uint8)
img[15:50, 8:44] = (90, 140, 200)
img[35:46, 60:120] = 230
AV = Vd.avatar_sprite(img, (8, 15, 44, 51), 8)
TX = Vd.text_sprite(img, (58, 33, 122, 48), 8, 70, 165)
frame = Vd.rays(0.3)
check('sprite + glow + caption', lambda: Vd.caption(Vd.sprite(frame, *AV, 640, 360, 1.0, 10, glow=(255, 0, 0)),
                                                    'TEST', 120, glow=(255, 0, 0)))
check('effetti', lambda: Vd.grain(Vd.vignette(Vd.mirror4(Vd.slice_glitch(Vd.rgb_split(Vd.jelly(frame, 8, 2, 0), 6), 3, 40,
                                                                           np.random.default_rng(1))), .3), 4,
                                  np.random.default_rng(2)))
tl = Vd.Timeline([(0, 'a'), (1, 'b')], [(0, 1.0, 'A', 100), (0.5, 1.0, 'B', 100)])
check('Timeline.check trova la sovrapposizione', lambda: None if tl.check() else (_ for _ in ()).throw(AssertionError('non rilevata')))

print('== mini render (audio + video)')
with tempfile.TemporaryDirectory() as d:
    def mini():
        song = core.Song(bpm=120, bars=1, tail=0.2)
        song.add('drum', I.kick(), 0.0)
        song.add('vox', V.speak('ok', 'it'), 0.3)
        song.render(d)
        import imageio_ffmpeg
        out = os.path.join(d, 'm.mp4')
        with Vd.Renderer(out, os.path.join(d, 'audio.raw'), 30, imageio_ffmpeg.get_ffmpeg_exe()) as R:
            for k in range(30):
                R.write(Vd.caption(Vd.rays(k / 30), 'OK', 120))
        assert os.path.getsize(out) > 10000, 'mp4 troppo piccolo'
    check('Song.render + Renderer -> mp4', mini)

print()
if fails:
    print(f'FALLITI {len(fails)}: {", ".join(fails)}')
    sys.exit(1)
print('TUTTO OK')
