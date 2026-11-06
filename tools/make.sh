#!/bin/bash
# Regenerate assets/*.svg. Needs uv. Fonts (OFL) are downloaded on first run.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts
[ -f fonts/Archivo.ttf ] || curl -fsSL -o fonts/Archivo.ttf "https://github.com/google/fonts/raw/main/ofl/archivo/Archivo%5Bwdth,wght%5D.ttf"
[ -f fonts/JetBrainsMono.ttf ] || curl -fsSL -o fonts/JetBrainsMono.ttf "https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"
deps=numpy,contourpy,fonttools,brotli
uv run -q --with $deps build.py ../assets      # project tiles
uv run -q --with $deps build_code.py ../assets # header
