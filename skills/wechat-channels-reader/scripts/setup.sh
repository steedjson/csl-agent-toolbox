#!/usr/bin/env bash
# Usage: bash setup.sh [--model tiny|base|small|medium|none]
#   [--model-source auto|modelscope|hf-mirror|hf] [--model-dir PATH]
#   [--model-timeout SECONDS] [--with-funasr]
# Runtime state lives in user cache/config directories, never beside the scripts.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${WCR_VENV:-${WECHAT_CHANNELS_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wechat-channels-reader/venv}}"
MODEL=small; SOURCE="${WCR_MODEL_SOURCE:-auto}"; MODEL_DIR=""; FUNASR=0; MODEL_TIMEOUT=300; PARTIAL=0
value() { if [[ $# -lt 2 || -z "$2" ]]; then echo "Missing value for $1" >&2; exit 2; fi; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) value "$@"; MODEL="$2"; shift 2;;
    --model-source) value "$@"; SOURCE="$2"; shift 2;;
    --model-dir) value "$@"; MODEL_DIR="$2"; shift 2;;
    --model-timeout) value "$@"; MODEL_TIMEOUT="$2"; shift 2;;
    --with-funasr) FUNASR=1; shift;;
    -h|--help) sed -n '2,6p' "$0"; echo "Venv: $VENV"; exit 0;;
    *) echo "Unknown argument: $1" >&2; exit 2;;
  esac
done
case "$MODEL" in tiny|base|small|medium|none) ;; *) echo "Invalid --model" >&2; exit 2;; esac
case "$SOURCE" in auto|modelscope|hf-mirror|hf) ;; *) echo "Invalid --model-source" >&2; exit 2;; esac
case "$MODEL_TIMEOUT" in ''|*[!0-9]*) echo "Invalid --model-timeout" >&2; exit 2;; esac
[[ "$MODEL_TIMEOUT" -gt 0 ]] || { echo "--model-timeout must be positive" >&2; exit 2; }
for tool in python3 ffmpeg ffprobe; do
  command -v "$tool" >/dev/null || { echo "Missing $tool; install it using your platform package manager first." >&2; exit 1; }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "Python 3.9+ required" >&2; exit 1; }
if [[ ! -x "$VENV/bin/python" ]]; then
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi
PY="$VENV/bin/python"
"$PY" -m pip install 'faster-whisper>=1.1' 'playwright>=1.45' numpy
if [[ "$FUNASR" == 1 ]]; then
  if [[ "$(uname -s)" == Linux ]]; then
    "$PY" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  fi
  "$PY" -m pip install torch torchaudio funasr
fi
CHROME="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); from sph_fetch import chrome_path; print(chrome_path() or "")' "$DIR")"
if [[ -n "$CHROME" ]]; then
  echo "Using system Chrome: $CHROME; skipping Chromium download."
else
  "$PY" -m playwright install chromium
fi
MARGS=(--model-source "$SOURCE" --model-timeout "$MODEL_TIMEOUT")
[[ -z "$MODEL_DIR" ]] || MARGS+=(--model-dir "$MODEL_DIR")
if [[ "$MODEL" != none ]]; then
  "$PY" "$DIR/sph_fetch.py" --download-model "$MODEL" "${MARGS[@]}" || PARTIAL=1
fi
if [[ "$FUNASR" == 1 ]]; then
  "$PY" "$DIR/sph_fetch.py" --download-model funasr --model-source modelscope --model-timeout "$MODEL_TIMEOUT" || PARTIAL=1
fi
"$PY" -m pip freeze > "$VENV/installed-packages.txt"
if [[ "$PARTIAL" == 1 ]]; then
  echo "Runtime installed, model preparation incomplete. Retry download or use --no-asr." >&2
  exit 5
fi
echo "Ready: $PY $DIR/sph_fetch.py --help"
