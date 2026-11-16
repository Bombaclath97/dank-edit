# AGENTS.md

Istruzioni per agent di coding (Claude Code, Codex, Cursor, Aider…) che devono **installare**, **usare** o
**modificare** dank-edit. Per gli umani c'e' il [README](README.md); per il flusso creativo completo che segue
l'agent durante un edit c'e' [SKILL.md](SKILL.md).

## Cos'e'

Una skill di Claude Code (ma i suoi script girano con qualsiasi agent che sappia lanciare comandi shell) che da
un'immagine produce un video meme 1280×720 / 60 fps / ~25–30 s. Tutto e' generato in locale: musica sintetizzata
(numpy/scipy), voci espeak-ng, frame disegnati con OpenCV/Pillow, codifica con ffmpeg. Nessun servizio esterno,
nessun sample, nessun asset di terzi.

## Installare

Una riga (clona in `~/.claude/skills/dank-edit`, crea un venv se servono le librerie Python, fa il collaudo):

```bash
curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash
```

Se mancano pacchetti di sistema (espeak-ng, ffmpeg, font) l'installer si ferma e stampa i comandi per la
distro. Per installarli direttamente (usa `sudo`, **chiedi prima all'utente**):

```bash
curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash -s -- --with-system-deps
```

Opzioni: `--dest DIR` (altra cartella), `--no-selftest`. Rilanciare l'installer su un'installazione esistente
fa `git pull`.

Requisiti: Linux o WSL, python >= 3.10, espeak-ng, font DejaVu. ffmpeg arriva dal pacchetto pip
`imageio-ffmpeg`, quello di sistema e' opzionale. Le librerie Python stanno in
`~/.local/share/dank-edit/venv` se il python di sistema non le ha.

**Agent diversi da Claude Code:** la cartella `~/.claude/skills/` serve solo a Claude Code per trovare la
skill. Con un altro agent installa dove vuoi (`--dest`) e fagli leggere `SKILL.md` come istruzioni di lavoro.

## Verificare

```bash
eval "$(~/.claude/skills/dank-edit/scripts/check_env.sh --env)"   # imposta PY, FFMPEG, OUT_DIR
$PY ~/.claude/skills/dank-edit/scripts/selftest.py                # ~5 s, uscita 0 = ok
```

`check_env.sh` senza argomenti stampa un report leggibile e i comandi d'installazione mancanti.
**Usa sempre `$PY`**: il `python3` di default puo' non avere le librerie (pyenv, venv, conda…).

## Usare

In Claude Code: `/dank-edit 9.png` o "nuovo edit da 9.png, stile X". La skill segue `SKILL.md`:

1. `check_env.sh` → ambiente
2. `scripts/segment.py IMMAGINE --out WORK` → `segment.json` + `segment.png` (da guardare)
3. copia `templates/make_audio.py` in WORK, componi, lancia → `audio.raw`, `audio.wav`, `timing.json`
4. copia `templates/make_video.py`, scrivi le scene, `--test` → controlli + `scene_test.png`
5. render completo **in background** (5–13 min)
6. `scripts/sheet.py` sul master → controlla i frame
7. `scripts/finalize.sh WORK nome` → `OUT_DIR/nome.mp4` + `nome_audio.wav`, md5 verificato

`OUT_DIR`: Downloads di Windows su WSL, altrimenti `~/Downloads`; si sovrascrive con `DANK_OUT_DIR`.

## Struttura del codice

```
install.sh                 installer (una riga via curl)
SKILL.md                   istruzioni operative per l'agent durante un edit
scripts/check_env.sh       dipendenze; --env stampa PY/FFMPEG/OUT_DIR da fare eval
scripts/selftest.py        collaudo di tutta la libreria
scripts/segment.py         screenshot -> avatar, righe, parole (esclude la sottolineatura dei link)
scripts/sheet.py           frame del video -> foglio di controllo
scripts/finalize.sh        compressione crf 23, copia, md5
scripts/dank/core.py       Song (timeline a battute, bus, sidechain, render, report), filtri, nf()
scripts/dank/instruments.py  49 strumenti/fx sintetizzati (tutti -> np.ndarray mono, SR 44100)
scripts/dank/voice.py      espeak-ng: speak, robot, growl, whisper, chop
scripts/dank/midi.py       brani di pubblico dominio: note da MIDI PD, separazione per ruolo
scripts/dank/video.py      sprite, compositing float32, fondali, effetti, caption, Timeline, Renderer
templates/                 edit minimo audio + video, punto di partenza di ogni edit
```

Convenzioni: frame video `np.float32 (720, 1280, 3)` in 0..255, clip solo in scrittura; strumenti con `@memo`
(cache sugli argomenti, quindi argomenti hashabili: tuple, non liste); commenti e messaggi in italiano.

## Regole (valgono anche per chi modifica la skill)

- **Diritti d'autore**: mai scaricare o riprodurre brani protetti. Se l'utente ne nomina uno, si compone un
  pezzo originale nel genere e glielo si dice. Pubblico dominio solo verificato (autore morto da >70 anni +
  licenza della fonte) e con le note prese da un MIDI/spartito PD, non ricostruite a memoria.
- **Asset**: niente loghi, personaggi o immagini di terzi; tutto cio' che non viene dall'immagine dell'utente
  si disegna proceduralmente.
- **Persone reali**: gli screenshot contengono avatar e nomi veri. Tono goliardico ma non umiliante; non alterare
  la foto di una persona per ridicolizzarla (trucco, costumi o deformazioni sul volto).
- **Azioni con sudo**: `--with-system-deps` installa pacchetti di sistema; un agent deve chiedere prima.

## Contribuire

- Licenza **AGPL-3.0-or-later** (vedi [LICENSE](LICENSE)). Ogni file sorgente nuovo inizia con
  `SPDX-License-Identifier: AGPL-3.0-or-later` e la riga di copyright, come quelli esistenti.
- Strumento nuovo in `instruments.py`: aggiungi gli argomenti di prova in `ARGS` di `selftest.py` se non ha
  default, poi `selftest.py` deve dare `TUTTO OK`.
- Prima di un commit: `bash -n` sugli script, `python -m py_compile` sui `.py`, `selftest.py`.
- Niente file generati nel repo (`__pycache__`, mp4, wav, raw).
