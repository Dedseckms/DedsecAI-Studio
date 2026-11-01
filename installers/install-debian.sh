#!/usr/bin/env bash
set -euo pipefail
studio_source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
command -v apt-get >/dev/null || { echo 'Use this installer on Debian or Ubuntu.' >&2; exit 1; }
sudo apt-get update
if [[ " ${*:-} " != *" --skip-runtime "* ]] && ! command -v llama-server >/dev/null; then
    sudo apt-get install python3 python3-tk build-essential cmake git libvulkan-dev glslc xdg-utils xterm
else
    sudo apt-get install python3 python3-tk xdg-utils
fi
exec python3 "$studio_source_dir/installers/install.py" "$@"
