#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_DIR="$SCRIPT_DIR/.conda"
WORK_DIR="$SCRIPT_DIR/media"
OUTPUT_DIR="$ROOT_DIR/assets/media/manim"
OUTPUT_NAME="ratio-268-of-285"

if [[ ! -x "$ENV_DIR/bin/manimgl" ]]; then
  echo "Run $SCRIPT_DIR/setup.sh first." >&2
  exit 1
fi

mkdir -p "$WORK_DIR" "$OUTPUT_DIR"

export PKG_CONFIG_PATH="$ENV_DIR/lib/pkgconfig:$ENV_DIR/share/pkgconfig"
export LD_LIBRARY_PATH="$ENV_DIR/lib:${LD_LIBRARY_PATH:-}"

manim_command=(
  "$ENV_DIR/bin/manimgl"
  "$SCRIPT_DIR/ratio_268_of_285.py"
  Ratio268Of285
  -w
  -r 1920x1080
  --video_dir "$WORK_DIR"
  --file_name "$OUTPUT_NAME"
  --vcodec libx264
  --pix_fmt yuv420p
  --quiet
)

if [[ -z "${DISPLAY:-}" ]]; then
  if ! command -v xvfb-run >/dev/null 2>&1; then
    echo "Headless rendering requires xvfb-run." >&2
    exit 1
  fi
  xvfb-run -a \
    -s "-screen 0 1920x1080x24 +extension GLX +render -noreset" \
    "${manim_command[@]}"
else
  "${manim_command[@]}"
fi

rendered_file="$(find "$WORK_DIR" -type f -name "$OUTPUT_NAME.mp4" -print -quit)"
if [[ -z "$rendered_file" ]]; then
  echo "ManimGL finished but $OUTPUT_NAME.mp4 was not found in $WORK_DIR." >&2
  exit 1
fi

ffmpeg -hide_banner -loglevel error -y \
  -i "$rendered_file" \
  -map 0:v:0 \
  -an \
  -c:v libx264 \
  -preset slow \
  -crf 18 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$OUTPUT_DIR/$OUTPUT_NAME.mp4"

ffmpeg -hide_banner -loglevel error -y \
  -i "$OUTPUT_DIR/$OUTPUT_NAME.mp4" \
  -frames:v 1 \
  "$OUTPUT_DIR/$OUTPUT_NAME-poster.png"

echo "Rendered $OUTPUT_DIR/$OUTPUT_NAME.mp4"
echo "Rendered $OUTPUT_DIR/$OUTPUT_NAME-poster.png"
