#!/usr/bin/env python3
"""TEMPLATE audio. Copialo nella cartella di lavoro e riscrivi COMPOSIZIONE.
uso: $PY make_audio.py WORK_DIR
Struttura tipica: intro (2) -> build (2) -> DROP (4) -> break (2) -> DROP 2 (4) -> fine (1).
"""
import os
import sys

sys.path.insert(0, os.path.expanduser('~/.claude/skills/dank-edit/scripts'))
from dank import instruments as I  # noqa: E402
from dank import voice as V  # noqa: E402
from dank.core import Song, nf, seed  # noqa: E402

WORK = sys.argv[1] if len(sys.argv) > 1 else '.'
seed(42)
song = Song(bpm=128, bars=8, tail=1.5)
t = song.t

# ================================================================ COMPOSIZIONE (originale!)
PROG = [('C4', 'E4', 'G4'), ('G3', 'B3', 'D4'), ('A3', 'C4', 'E4'), ('F3', 'A3', 'C4')]
ROOT = ['C2', 'G1', 'A1', 'F1']
HOOK = [['C5', None, 'E5', 'G5', 'C6', None, 'G5', 'E5']] * 4

# intro: 2 battute, campanello + voce
for bo in (0, 1):
    for s, n in enumerate(HOOK[bo]):
        if n:
            song.add('music', I.bell(nf(n), song.e8 * 2), t(bo) + s * song.e8, 0.5)
    song.add('drum', I.kick(), t(bo, 0), 0.6)
song.add('vox', V.speak('esempio', 'it', 140, 60, 1.1), t(1, 1.0), 0.9)
DROP = song.mark('drop', t(2))
song.silence_before(DROP, song.s16)

# drop: 4 battute
for bo in range(2, 6):
    for b in range(4):
        song.add('drum', I.kick(), t(bo, b), 0.62)     # cassa dritta: tanta energia sotto i 120 Hz
    for b in (1, 3):
        song.add('drum', I.clap(), t(bo, b), 0.55)
    for s in range(8):
        song.add('drum', I.hat(), t(bo) + s * song.e8, 0.3, 0.3)
    k = (bo - 2) % 4
    for b in (0, 1.5, 2.5):
        song.add('music', I.supersaw(tuple(nf(x) for x in PROG[k]), song.beat * .9), t(bo, b), 0.85)
    for b in range(0, 8):
        song.add('bass', I.sub(nf(ROOT[k]), song.e8 * .9), t(bo) + b * song.e8, 0.42)   # il sub sta sotto
    for s, n in enumerate(HOOK[k]):
        if n:
            song.add('lead', I.pluck(nf(n), song.e8 * 1.6), t(bo) + s * song.e8, 1.6)    # il carattere sta sopra
song.add('fx', I.vine_boom(), DROP, 0.6)
song.add('drum', I.crash(), DROP, 0.4)

# fine
END = song.mark('end', t(6))
song.add('drum', I.kick(), END, 1.0)
song.add('music', I.supersaw(tuple(nf(x) for x in PROG[0]), 1.4), END, 0.7)

# ================================================================ MIX
song.sidechain([t(b, k) for b in range(2, 6) for k in range(4)], buses=('bass', 'music'), depth=0.6)
song.duck_under_vox()
mono = song.render(WORK)
song.report(mono, [('intro', 0, DROP), ('drop', DROP, END), ('fine', END, song.dur)])
print('OK', WORK, f'{song.dur:.2f}s', song.marks)
