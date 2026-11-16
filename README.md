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

Una riga:

```bash
curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash
```

Clona la skill in `~/.claude/skills/dank-edit`, crea un venv con le librerie Python se servono (senza sudo),
controlla l'ambiente e fa il collaudo. Se mancano pacchetti di sistema (espeak-ng, ffmpeg, font) ti stampa i
comandi per la tua distro; per installarli direttamente aggiungi `--with-system-deps` (usa sudo):

```bash
curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash -s -- --with-system-deps
```

Rilanciare lo stesso comando aggiorna la skill. A mano:

```bash
git clone https://github.com/Bombaclath97/dank-edit ~/.claude/skills/dank-edit
~/.claude/skills/dank-edit/scripts/check_env.sh     # report + comandi d'installazione per distro
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
| `install.sh` | installer da una riga |
| `AGENTS.md` | come installare, usare e modificare la skill, per agent di coding |
| `scripts/check_env.sh` | controllo dipendenze + comandi d'installazione per distro |
| `scripts/selftest.py` | collaudo di tutta la libreria (~5 s) |
| `scripts/segment.py` | analisi dello screenshot: avatar, righe, parole (esclude la sottolineatura dei link) |
| `scripts/sheet.py` | foglio di controllo con i frame del video |
| `scripts/finalize.sh` | compressione, copia nella cartella d'uscita, verifica md5 |
| `scripts/dank/` | libreria: sintesi (`instruments`), voci (`voice`), MIDI PD (`midi`), mix (`core`), video (`video`) |
| `templates/` | edit minimo audio + video da cui partire |

## Licenza

[AGPL-3.0-or-later](LICENSE). Puoi usare, modificare e ridistribuire; se distribuisci una versione modificata
(anche offrendola come servizio in rete) devi pubblicarne il sorgente con la stessa licenza.
