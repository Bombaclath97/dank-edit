#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
# Controlla tutto quello che serve a dank-edit e, se manca qualcosa,
# stampa i comandi d'installazione per la distro corrente.
# Uscita: 0 = pronto, 1 = manca qualcosa di obbligatorio.
# Con --env stampa solo le variabili da fare eval: PY=... FFMPEG=... OUT_DIR=...

set -u
MODE="${1:-}"
PY_MODS="numpy scipy cv2 PIL mido imageio_ffmpeg"
PIP_PKGS="numpy scipy opencv-python-headless pillow mido imageio-ffmpeg"

# ---------------------------------------------------------------- python
find_python() {
    local cands=()
    [ -n "${DANK_PY:-}" ] && cands+=("$DANK_PY")
    cands+=("$HOME/.local/share/dank-edit/venv/bin/python")
    for p in "$HOME"/.pyenv/versions/*/bin/python3; do [ -x "$p" ] && cands+=("$p"); done
    cands+=(python3 python3.13 python3.12 python3.11 python3.10 /usr/bin/python3)
    for p in "${cands[@]}"; do
        command -v "$p" >/dev/null 2>&1 || [ -x "$p" ] || continue
        if "$p" -c "import numpy, scipy, cv2, PIL, mido, imageio_ffmpeg" >/dev/null 2>&1; then
            echo "$p"; return 0
        fi
    done
    return 1
}

PY="$(find_python || true)"
FFMPEG=""
if [ -n "$PY" ]; then
    FFMPEG="$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
fi
[ -z "$FFMPEG" ] && command -v ffmpeg >/dev/null 2>&1 && FFMPEG="$(command -v ffmpeg)"

# ---------------------------------------------------------------- cartella d'uscita
OUT_DIR="${DANK_OUT_DIR:-}"
if [ -z "$OUT_DIR" ]; then
    if grep -qi microsoft /proc/version 2>/dev/null && command -v cmd.exe >/dev/null 2>&1; then
        WINPROF="$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')"
        [ -n "$WINPROF" ] && OUT_DIR="$(wslpath "$WINPROF" 2>/dev/null)/Downloads"
    fi
    [ -z "$OUT_DIR" ] || [ ! -d "$OUT_DIR" ] && OUT_DIR="$HOME/Downloads"
fi

if [ "$MODE" = "--env" ]; then
    printf 'PY=%q\nFFMPEG=%q\nOUT_DIR=%q\n' "$PY" "$FFMPEG" "$OUT_DIR"
    [ -n "$PY" ] && [ -n "$FFMPEG" ] && command -v espeak-ng >/dev/null 2>&1
    exit $?
fi

# ---------------------------------------------------------------- report
ok=1
say() { printf '  %-28s %s\n' "$1" "$2"; }
echo "== dank-edit: controllo ambiente =="
. /etc/os-release 2>/dev/null || true
DISTRO="${ID:-sconosciuta}"; LIKE="${ID_LIKE:-}"
echo "  distro: ${PRETTY_NAME:-$DISTRO}$(grep -qi microsoft /proc/version 2>/dev/null && echo ' (WSL)')"

if [ -n "$PY" ]; then say "python + librerie" "OK  $PY"
else say "python + librerie" "MANCA"; ok=0; fi
if [ -n "$FFMPEG" ]; then say "ffmpeg" "OK  $FFMPEG"
else say "ffmpeg" "MANCA"; ok=0; fi
if command -v espeak-ng >/dev/null 2>&1; then
    voices=""
    for v in it en-us de id; do espeak-ng --voices="$v" 2>/dev/null | grep -q " $v " && voices="$voices $v"; done
    say "espeak-ng" "OK  voci:$voices"
else say "espeak-ng" "MANCA"; ok=0; fi
FONT_IMPACT=""
for f in /mnt/c/Windows/Fonts/impact.ttf /usr/share/fonts/truetype/msttcorefonts/Impact.ttf \
         /usr/share/fonts/truetype/msttcorefonts/impact.ttf "$HOME/.fonts/impact.ttf"; do
    [ -f "$f" ] && FONT_IMPACT="$f" && break
done
[ -n "$FONT_IMPACT" ] && say "font Impact" "OK  $FONT_IMPACT" || say "font Impact" "manca (fallback DejaVu, ok)"
if fc-list 2>/dev/null | grep -qi "DejaVuSans-Bold"; then say "font DejaVu" "OK"
else say "font DejaVu" "MANCA"; ok=0; fi
say "cartella d'uscita" "$OUT_DIR"

[ $ok -eq 1 ] && { echo "== PRONTO =="; exit 0; }

# ---------------------------------------------------------------- comandi d'installazione
echo
echo "== Comandi per installare quello che manca =="
case "$DISTRO $LIKE" in
    *ubuntu*|*debian*)
        echo "  sudo apt update && sudo apt install -y python3-venv espeak-ng ffmpeg fonts-dejavu-core"
        echo "  # opzionale, per Impact/Comic Sans fuori da WSL:"
        echo "  sudo apt install -y ttf-mscorefonts-installer" ;;
    *fedora*|*rhel*|*centos*)
        echo "  sudo dnf install -y python3 espeak-ng ffmpeg-free dejavu-sans-fonts" ;;
    *arch*|*manjaro*)
        echo "  sudo pacman -S --needed python espeak-ng ffmpeg ttf-dejavu" ;;
    *opensuse*|*suse*)
        echo "  sudo zypper install -y python3 espeak-ng ffmpeg-7 dejavu-fonts" ;;
    *alpine*)
        echo "  sudo apk add python3 py3-pip espeak-ng ffmpeg font-dejavu" ;;
    *)
        echo "  installa con il gestore di pacchetti: python3 (>=3.10), espeak-ng, ffmpeg, font DejaVu" ;;
esac
if [ -z "$PY" ]; then
    echo "  # librerie Python in un venv dedicato (nessun sudo):"
    echo "  python3 -m venv ~/.local/share/dank-edit/venv"
    echo "  ~/.local/share/dank-edit/venv/bin/pip install $PIP_PKGS"
fi
exit 1
