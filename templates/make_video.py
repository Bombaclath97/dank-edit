#!/usr/bin/env python3
"""TEMPLATE video. Copialo nella cartella di lavoro, metti le coordinate prese da
segment.py, scrivi le scene.
uso:  $PY make_video.py WORK_DIR IMMAGINE --test   # foglio con un frame per scena + controllo testi
      $PY make_video.py WORK_DIR IMMAGINE          # render completo (lancialo in background)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser('~/.claude/skills/dank-edit/scripts'))
from dank import video as V  # noqa: E402

WORK, IMG = sys.argv[1], sys.argv[2]
TEST = '--test' in sys.argv
T = json.load(open(os.path.join(WORK, 'timing.json')))
FPS, NFR, BEAT, BAR = T['fps'], T['n_frames'], T['beat'], T['bar']
M = T['marks']
ENV = np.array(T['env_bass'])
SEG = json.load(open(os.path.join(WORK, 'segment.json')))
img = V.load_rgb(IMG)

# ================================================================ SPRITE (da segment.json)
AV = V.avatar_sprite(img, SEG['avatar_box'], 12)
FULL = V.full_sprite(img, 3)
ln = SEG['lines'][-1]                       # riga del messaggio
p, q = ln['words'][0]
WORD = V.text_sprite(img, (p - 1, ln['y'][0] - 1, q + 2, ln['y'][1] + 2), 12)

GOLD, RED = (255, 214, 90), (214, 30, 40)


# ================================================================ SCENE: f(t, bt, intens) -> frame
def sc_screen(t, bt, it):
    bg = V.grad((30, 20, 50), (8, 8, 14))
    return V.sprite(bg, *FULL, V.W / 2, V.H / 2, 1.0 + 0.03 * bt, 0.8 * np.sin(t * 1.3), shadow=14)


def sc_word(t, bt, it):
    bg = V.rays(t, 16, (40, 30, 80), (14, 10, 30))
    return V.sprite(bg, V.tint(WORD[0], GOLD), WORD[1], V.W / 2, V.H * 0.45, 1.0 + 0.1 * bt,
                    3 * np.sin(t * 2), shadow=12, glow=RED, glow_str=0.8)


def sc_bounce(t, bt, it):
    bg = V.rainbow(t)
    bg = V.particles(bg, t, 60)
    hop = abs(np.sin(np.pi * (t % BEAT) / BEAT)) * 120
    return V.sprite(bg, *AV, V.W / 2, V.H * 0.6 - hop, 0.7, t * 40)


SCENES = {'screen': sc_screen, 'word': sc_word, 'bounce': sc_bounce}
TL = V.Timeline(
    scenes=[(0.0, 'screen'), (M['drop'], 'word'), (M['drop'] + BAR, 'bounce'),
            (M['drop'] + 2 * BAR, 'word'), (M['drop'] + 3 * BAR, 'bounce'), (M['end'], 'screen')],
    texts=[(0.2, 1.6, 'ESEMPIO', 110), (M['drop'], 0.8, 'DROP', 150), (M['end'] + 0.2, 1.0, 'FINE', 120)])

if TEST:
    for problem in TL.check():
        print('!!', problem)
    print(V.scene_sheet(SCENES, os.path.join(WORK, 'scene_test.png'), M['drop']))
    sys.exit(0)

FF = os.environ.get('FFMPEG') or __import__('imageio_ffmpeg').get_ffmpeg_exe()
with V.Renderer(os.path.join(WORK, 'master.mp4'), os.path.join(WORK, 'audio.raw'), FPS, FF) as R:
    for i in range(NFR):
        t = i / FPS
        r = np.random.default_rng(1000 + i)
        it = 1.0 if t >= M['drop'] else 0.25
        bt = V.beat_pulse(t, BEAT)
        name, lt = TL.scene_at(t)
        a = SCENES[name](t, bt, it)
        a = V.beat_zoom(a, 1.0 + 0.05 * it * bt)
        if it > 0.5:
            a = V.rgb_split(a, 6 * ENV[i])
            a = V.shake(a, 8 * ENV[i] ** 1.5, r)
        a = V.vignette(a, 0.3)
        a = V.grain(a, 4, r)
        for (tt, dur, txt, size), qq in TL.texts_at(t):
            a = V.caption(a, txt, int(size * (1 + 0.2 * np.exp(-qq * 9))), rot=float(np.sin(t * 7) * 3),
                          jit=3, r=r, glow=RED)
        R.write(a)
        if i % 120 == 0:
            print(f'  {i}/{NFR} {name}', flush=True)
print('OK render')
