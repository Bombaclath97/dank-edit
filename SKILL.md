---
name: dank-edit
description: Crea un video meme "dank" (1280x720, 60 fps, ~25-30 s) partendo da un'immagine, tipicamente uno screenshot di chat: musica sintetizzata da zero nel genere richiesto, voci TTS (espeak-ng), sprite estratti dall'immagine, scene disegnate proceduralmente, testi meme, effetti. Usala quando l'utente chiede un "edit", un "edit dank", un video meme da un'immagine, o dice "nuovo edit da N.png".
---

# dank-edit

Pipeline: **immagine -> analisi sprite -> traccia audio (+ timing.json) -> scene video -> controlli -> render -> consegna**.
Tutto il codice riusabile e' in `~/.claude/skills/dank-edit/scripts/`, i punti di partenza in `templates/`.

## 0. Ambiente (sempre per primo)

```bash
SK=~/.claude/skills/dank-edit
$SK/scripts/check_env.sh            # report + comandi d'installazione per la distro se manca qualcosa
eval "$($SK/scripts/check_env.sh --env)"   # imposta PY, FFMPEG, OUT_DIR
```
- Usa **sempre `$PY`**, mai `python3` nudo: il python di default puo' non avere le librerie.
- ffmpeg viene da `imageio-ffmpeg` (non serve sudo). `OUT_DIR` = Downloads di Windows su WSL.
- Se manca qualcosa: mostra all'utente i comandi stampati da check_env e fermati su quel punto.

## 1. Immagine

- L'utente dice "N.png" o "N.jpg" ma l'estensione puo' essere sbagliata: cerca `OUT_DIR/N.*`.
- Guarda l'immagine (Read), poi:
  ```bash
  W=~/<nome>_edit; mkdir -p $W
  $PY $SK/scripts/segment.py IMMAGINE --out $W     # segment.json + segment.png
  ```
  **Guarda `segment.png`** prima di usare le coordinate. Le parole possono uscire spezzate (es. "ru"+"n"):
  unisci i box a mano. La parola protagonista (quella che l'utente nomina) diventa lo sprite principale.
- Gli screenshot ricorrenti sono notifiche chat (avatar tondo + nome + messaggio con link sottolineato blu).

## 2. Audio (`templates/make_audio.py`)

Copia il template in `$W`, riscrivi la sezione COMPOSIZIONE, lancia `$PY make_audio.py $W`.
Produce `audio.raw`, `audio.wav`, `timing.json` (marks = tempi notevoli che il video usa per sincronizzare).

**Regole sui diritti (non negoziabili):**
- Brano commerciale/protetto richiesto (es. una canzone famosa): **non** scaricarlo, non riprodurne melodia o
  arrangiamento. Componi un pezzo **originale nel genere** e dillo all'utente in una riga.
- Brano di **pubblico dominio** richiesto ("usa X come base, non inventare"): verifica il PD (autore morto da
  >70 anni + licenza della fonte), poi prendi le note da una fonte PD (MIDI/spartito su Wikimedia Commons, API
  `imageinfo&iiprop=url|extmetadata` -> `LicenseShortName`). Confronta il MIDI con lo spartito (`dank/midi.py`:
  `load`, `midi_bars`, `print_melody`). Non ricostruire melodie a memoria: leggere uno spartito a bassa
  risoluzione sbaglia di un grado (successo: Do♭ scambiato per Si♭).
- Niente sample di terzi: tutto sintetizzato (`dank/instruments.py`), voci da espeak (`dank/voice.py`).

**Mix, cose gia' sbagliate una volta:**
- Il basso tende a coprire tutto: guarda la tabella `song.report(...)` (RMS per banda). Nel drop i medi/acuti
  devono stare almeno a ~60% del sub; il carattere va nei layer alti, il sub resta pulito.
- Voci sempre sopra: `song.duck_under_vox()`. Battute importanti in uno stop-time (`song.mute`) o dopo una pausa
  (`song.silence_before`).
- Esporta subito il wav in `OUT_DIR` se l'utente vuole ascoltare (il `.raw` non si apre su Windows).

## 3. Video (`templates/make_video.py`)

Copia il template, metti gli sprite da `segment.json`, scrivi 8-12 scene `f(t, bt, intens)`.
Tutto quello che non viene dall'immagine va **disegnato proceduralmente** (cv2/PIL): niente loghi,
personaggi o immagini di terzi.

**Persone reali** (gli screenshot contengono avatar/nomi veri): tono goliardico ma non umiliante. L'avatar si
puo' muovere, ruotare, far rimbalzare, mettere in scena. **Non** alterare la foto di una persona reale per
ridicolizzarla (trucco, costumi o deformazioni sul volto, scritte denigratorie su di lei): un edit cosi'
(trucco da clown sull'avatar + prese in giro mirate) e' stato bloccato. Se una richiesta va in quella
direzione, proponi di spostare la battuta sul testo dello screenshot o su elementi disegnati.

**Controlli prima del render completo (obbligatori):**
```bash
$PY make_video.py $W IMMAGINE --test     # stampa testi sovrapposti/troppo larghi + scene_test.png
```
Guarda `scene_test.png`. Errori gia' visti: sprite dello stesso colore del fondo (oro su oro, verde su verde)
-> ombra/glow o cambia colore; scritte sopra lo sprite -> `caption(bottom=True)`; effetti (fuoco, flash,
deepfry) che cancellano il soggetto -> dimezzali; scene troppo corte per la loro animazione (mezza battuta
= ~0.9 s) -> velocizzala; testi che si sovrappongono nel tempo -> `Timeline.check()`.

## 4. Render e consegna

- Il render completo dura **5-13 min**: lancialo con `run_in_background` e aspetta la notifica.
- Controlla i frame: `$PY $SK/scripts/sheet.py $W/master.mp4 $W/sheet.png --every 2` e guardalo
  (soprattutto i momenti chiave dei marks).
- Consegna: `$SK/scripts/finalize.sh $W nome_edit` -> `OUT_DIR/nome_edit.mp4` + `_audio.wav`, md5 verificato.

## Report finale all'utente
Percorso del file, durata, tabella dei momenti chiave (tempo -> cosa), da dove viene la musica (originale nel
genere / PD con fonte), cosa hai corretto in corsa, un solo prossimo passo concreto.

## Riferimenti
- `scripts/dank/core.py`: `Song` (timeline a battute, bus, sidechain, render, report), filtri, `nf()`.
- `scripts/dank/instruments.py`: batteria (kick, 808, metal, membrane=bongo/conga, slit_drum), bassi (sub, 808,
  tuba, wobble), melodici (pluck, mallet xylo/marimba, kalimba, bell, ks_string+amp_sim=chitarra metal,
  supersaw, organ, calliope, accordion, trumpet, kazoo, screech, alphorn, theremin, choir), fx (riser, whoosh,
  impact, vine_boom, airhorn, scratch, boing, slide_whistle, beep, honk, crickets, slow_clap, heartbeat,
  crowd_roar, wind, alarm).
- `scripts/dank/voice.py`: `speak` (urlato/clippato), `robot`, `growl`, `whisper`, `chop` (vocal chop).
- `scripts/dank/video.py`: sprite (`avatar_sprite`, `text_sprite`, `tint`, `sprite`), fondali (`grad`, `rays`,
  `checker`, `rainbow`, `particles`), effetti, `caption`, `Timeline`, `scene_sheet`, `Renderer`.
- Edit gia' fatti sulla macchina (cartelle `~/*_edit/` con `make_audio.py` e `make_video.py`): se ci sono,
  guardali per riusare scene e arrangiamenti.
