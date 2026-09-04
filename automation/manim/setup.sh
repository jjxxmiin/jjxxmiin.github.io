#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$SCRIPT_DIR/.conda"

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is required so Pango/Cairo can stay inside the project environment." >&2
  exit 1
fi

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  conda create --yes \
    --prefix "$ENV_DIR" \
    --channel conda-forge \
    --override-channels \
    python=3.11 \
    pip \
    pango \
    cairo \
    pkg-config \
    xorg-xorgproto \
    harfbuzz \
    glib
fi

export PKG_CONFIG_PATH="$ENV_DIR/lib/pkgconfig:$ENV_DIR/share/pkgconfig"
"$ENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo "ManimGL environment ready: $ENV_DIR"
