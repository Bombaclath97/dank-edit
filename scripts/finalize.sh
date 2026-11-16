#!/usr/bin/env bash
# Consegna: comprime il master (crf 23), copia video + wav nella cartella d'uscita,
# verifica la copia con md5.  uso: finalize.sh LAVORO_DIR NOME_FINALE
set -euo pipefail
WORK="$1"; NAME="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
eval "$("$HERE/check_env.sh" --env)"
MASTER="$(ls "$WORK"/*.mp4 | grep -v '_web.mp4' | head -1)"
WEB="$WORK/${NAME}_web.mp4"
"$FFMPEG" -y -hide_banner -loglevel error -i "$MASTER" -c:v libx264 -preset slow -crf 23 \
    -pix_fmt yuv420p -profile:v high -level 4.2 -c:a copy -movflags +faststart "$WEB"
mkdir -p "$OUT_DIR"
cp "$WEB" "$OUT_DIR/${NAME}.mp4"
[ -f "$WORK/audio.wav" ] && cp "$WORK/audio.wav" "$OUT_DIR/${NAME}_audio.wav"
a=$(md5sum "$WEB" | cut -d' ' -f1); b=$(md5sum "$OUT_DIR/${NAME}.mp4" | cut -d' ' -f1)
[ "$a" = "$b" ] && echo "OK copia verificata (md5 $a)" || { echo "ERRORE: md5 diverso"; exit 1; }
"$FFMPEG" -hide_banner -i "$OUT_DIR/${NAME}.mp4" 2>&1 | grep -E "Duration|Stream" || true
ls -la "$OUT_DIR/${NAME}.mp4" "$OUT_DIR/${NAME}_audio.wav" 2>/dev/null || true
