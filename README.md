# dank-edit

Skill per [Claude Code](https://claude.com/claude-code) che trasforma un'immagine (tipicamente uno screenshot di
chat) in un **video meme "dank"**: 1280×720, 60 fps, ~25–30 secondi.

- **Musica sintetizzata da zero** nel genere richiesto (dubstep, kawaii bass, polka con jodel, djent, circo…):
  nessun sample, nessun brano protetto. I brani di pubblico dominio si usano leggendo le note da un MIDI/spartito PD.
- **Voci TTS** con espeak-ng (italiano, inglese, tedesco, indonesiano…): urlate, robotiche, growl, sussurri.
- **Sprite estratti dall'immagine**: avatar, parole del messaggio (anche i link sottolineati), ricolorabili.
- **Scene disegnate proceduralmente** + testi meme + effetti (shake, glitch, RGB split, zoom sul beat…).
- **Controlli automatici** prima della consegna: bilanciamento del mix, testi sovrapposti, foglio dei frame.

## Installazione

```bash
git clone https://github.com/Bombaclath97/dank-edit ~/.claude/skills/dank-edit
~/.claude/skills/dank-edit/scripts/check_env.sh
```

`check_env.sh` controlla Python + librerie, ffmpeg, espeak-ng e font, e se manca qualcosa stampa i comandi per la
tua distro (apt / dnf / pacman / zypper / apk). Su Debian/Ubuntu:

```bash
sudo apt update && sudo apt install -y python3-venv espeak-ng ffmpeg fonts-dejavu-core
python3 -m venv ~/.local/share/dank-edit/venv
~/.local/share/dank-edit/venv/bin/pip install numpy scipy opencv-python-headless pillow mido imageio-ffmpeg
```

Su WSL il video finito viene copiato nei Download di Windows; altrove in `~/Downloads`
(sovrascrivibile con `DANK_OUT_DIR`).

## Uso

In Claude Code:

```
/dank-edit 9.png, stile polka apocalittica
```

oppure semplicemente *"nuovo edit da 9.png"*. Un render completo richiede 5–13 minuti.

## Struttura

| percorso | cosa |
|---|---|
| `SKILL.md` | flusso di lavoro e regole che Claude segue |
| `scripts/check_env.sh` | controllo dipendenze + comandi d'installazione per distro |
| `scripts/segment.py` | analisi dello screenshot: avatar, righe, parole (esclude la sottolineatura dei link) |
| `scripts/sheet.py` | foglio di controllo con i frame del video |
| `scripts/finalize.sh` | compressione, copia nella cartella d'uscita, verifica md5 |
| `scripts/dank/` | libreria: sintesi (`instruments`), voci (`voice`), MIDI PD (`midi`), mix (`core`), video (`video`) |
| `templates/` | edit minimo audio + video da cui partire |
