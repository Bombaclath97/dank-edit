# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
"""Brani di pubblico dominio: leggere le note da un MIDI PD invece di inventarle.

Flusso verificato (Entrata dei gladiatori, Fučík 1897):
  1. verifica PD su Commons (API imageinfo extmetadata -> LicenseShortName)
  2. scarica il MIDI PD e confrontalo con una scansione PD dello spartito
  3. usa midi_bars() per separare melodia / controcanto / basso / accordi
"""
import collections

import mido

NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def name(n):
    return f'{NAMES[n % 12]}{n // 12 - 1}'


def load(path, track=None):
    """Ritorna [(inizio_beat, fine_beat, nota_midi)] di tutte le tracce (o di una)."""
    m = mido.MidiFile(path)
    tpb = m.ticks_per_beat
    out = []
    tracks = m.tracks if track is None else [m.tracks[track]]
    for tr in tracks:
        t, on = 0, {}
        for msg in tr:
            t += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                on[msg.note] = t
            elif msg.type in ('note_off', 'note_on') and msg.note in on:
                out.append((on.pop(msg.note) / tpb, t / tpb, msg.note))
    return sorted(out)


def midi_bars(notes, b0, b1, beats_per_bar=4, mel_floor=64, bass_ceil=55):
    """Note delle battute [b0, b1), divise per ruolo, tempi relativi in beat:
    mel = voce piu' alta >= mel_floor, harm = altre voci alte,
    bass = nota piu' bassa < bass_ceil sui tempi pari, chord = il resto."""
    by = collections.defaultdict(list)
    for s, e, n in notes:
        if b0 * beats_per_bar <= s < b1 * beats_per_bar:
            by[s].append((n, e - s))
    out = {'mel': [], 'harm': [], 'bass': [], 'chord': []}
    for s in sorted(by):
        rel = s - b0 * beats_per_bar
        ns = sorted(by[s])
        hi = [x for x in ns if x[0] >= mel_floor]
        lo = [x for x in ns if x[0] < mel_floor]
        if hi:
            out['mel'].append((rel,) + hi[-1])
            out['harm'] += [(rel,) + x for x in hi[:-1]]
        if lo:
            if lo[0][0] < bass_ceil and (rel % 2) < 1e-6:
                out['bass'].append((rel,) + lo[0])
                lo = lo[1:]
            out['chord'] += [(rel,) + x for x in lo]
    return out


def print_melody(notes, b0, b1, beats_per_bar=4):
    """Stampa la voce superiore battuta per battuta: controllala contro lo spartito."""
    p = midi_bars(notes, b0, b1, beats_per_bar)
    bar, line = -1, []
    for rel, n, d in p['mel']:
        if int(rel // beats_per_bar) != bar:
            if line:
                print(f'  bar {b0 + bar}: ' + ' '.join(line))
            bar, line = int(rel // beats_per_bar), []
        line.append(f'{name(n)}({d:.2g})')
    if line:
        print(f'  bar {b0 + bar}: ' + ' '.join(line))
