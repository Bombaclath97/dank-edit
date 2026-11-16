#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Bombaclath97 - https://github.com/Bombaclath97/dank-edit
#
# Installer di dank-edit. Una riga:
#   curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash
# Con i pacchetti di sistema (usa sudo):
#   curl -fsSL https://raw.githubusercontent.com/Bombaclath97/dank-edit/main/install.sh | bash -s -- --with-system-deps
#
# Opzioni:
#   --with-system-deps   installa espeak-ng, ffmpeg e font col gestore di pacchetti (sudo)
#   --dest DIR           dove installare la skill (default: ~/.claude/skills/dank-edit)
#   --no-selftest        salta il collaudo finale
# Variabili: DANK_DEST (= --dest), DANK_REPO (URL git alternativo).
set -euo pipefail

REPO="${DANK_REPO:-https://github.com/Bombaclath97/dank-edit}"
DEST="${DANK_DEST:-$HOME/.claude/skills/dank-edit}"
VENV="$HOME/.local/share/dank-edit/venv"
PIP_PKGS="numpy scipy opencv-python-headless pillow mido imageio-ffmpeg"
SYSDEPS=0
SELFTEST=1
while [ $# -gt 0 ]; do
    case "$1" in
        --with-system-deps) SYSDEPS=1 ;;
        --dest) DEST="$2"; shift ;;
        --no-selftest) SELFTEST=0 ;;
        -h|--help) sed -n '4,15p' "$0" 2>/dev/null || true; exit 0 ;;
        *) echo "opzione sconosciuta: $1" >&2; exit 2 ;;
    esac
    shift
done

step() { printf '\n== %s\n' "$*"; }
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"

# ---------------------------------------------------------------- 1. pacchetti di sistema
pkg_cmd() {
    . /etc/os-release 2>/dev/null || true
    case "${ID:-} ${ID_LIKE:-}" in
        *ubuntu*|*debian*) echo "$SUDO apt-get update && $SUDO apt-get install -y git python3 python3-venv espeak-ng ffmpeg fonts-dejavu-core" ;;
        *fedora*|*rhel*|*centos*) echo "$SUDO dnf install -y git python3 espeak-ng ffmpeg-free dejavu-sans-fonts" ;;
        *arch*|*manjaro*) echo "$SUDO pacman -S --needed --noconfirm git python espeak-ng ffmpeg ttf-dejavu" ;;
        *opensuse*|*suse*) echo "$SUDO zypper install -y git python3 espeak-ng ffmpeg-7 dejavu-fonts" ;;
        *alpine*) echo "$SUDO apk add git python3 py3-pip espeak-ng ffmpeg font-dejavu" ;;
        *) echo "" ;;
    esac
}
if [ $SYSDEPS -eq 1 ]; then
    step "Pacchetti di sistema"
    CMD="$(pkg_cmd)"
    if [ -z "$CMD" ]; then
        echo "distro non riconosciuta: installa a mano git, python3 (>=3.10), espeak-ng, ffmpeg, font DejaVu"
    else
        echo "\$ $CMD"; eval "$CMD"
    fi
fi

# ---------------------------------------------------------------- 2. la skill
step "Skill in $DEST"
if [ -d "$DEST/.git" ]; then
    git -C "$DEST" pull --ff-only
elif [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
    echo "ERRORE: $DEST esiste e non e' un clone git. Spostalo o usa --dest." >&2; exit 1
elif command -v git >/dev/null 2>&1; then
    mkdir -p "$(dirname "$DEST")"
    git clone --depth 1 "$REPO" "$DEST"
else
    echo "git non trovato: scarico l'archivio"
    mkdir -p "$DEST"
    curl -fsSL "$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$DEST" --strip-components=1
fi
chmod +x "$DEST"/install.sh "$DEST"/scripts/*.sh "$DEST"/scripts/*.py 2>/dev/null || true

# ---------------------------------------------------------------- 3. librerie Python
step "Librerie Python"
# --env esce != 0 anche se manca solo espeak: qui conta solo PY
eval "$("$DEST/scripts/check_env.sh" --env 2>/dev/null || true)"
if [ -n "${PY:-}" ]; then
    echo "ok: $PY"
else
    BASE=""
    for p in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
            BASE="$p"; break
        fi
    done
    if [ -z "$BASE" ]; then
        echo "ERRORE: serve python >= 3.10. Rilancia con --with-system-deps oppure: $(pkg_cmd)" >&2; exit 1
    fi
    echo "creo il venv $VENV con $BASE"
    mkdir -p "$(dirname "$VENV")"
    if ! "$BASE" -m venv "$VENV"; then
        echo "ERRORE: venv non disponibile. Su Debian/Ubuntu: $SUDO apt-get install -y python3-venv" >&2; exit 1
    fi
    "$VENV/bin/python" -m pip install -q --upgrade pip
    "$VENV/bin/python" -m pip install -q $PIP_PKGS
fi

# ---------------------------------------------------------------- 4. controllo e collaudo
step "Controllo ambiente"
if ! "$DEST/scripts/check_env.sh"; then
    echo
    echo "Manca qualcosa di sistema: rilancia l'installer con --with-system-deps oppure esegui i comandi sopra."
    exit 1
fi
if [ $SELFTEST -eq 1 ]; then
    step "Collaudo"
    eval "$("$DEST/scripts/check_env.sh" --env)"
    "$PY" "$DEST/scripts/selftest.py"
fi
step "Fatto. In Claude Code: /dank-edit <immagine>"
