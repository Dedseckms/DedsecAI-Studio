#!/usr/bin/env bash
set -euo pipefail
studio_source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
command -v pacman >/dev/null || { echo 'Use this installer on Arch Linux or an Arch-based distribution.' >&2; exit 1; }
if [[ " ${*:-} " != *" --skip-runtime "* ]] && ! command -v llama-server >/dev/null; then
    sudo pacman -S --needed python tk cmake base-devel git vulkan-headers vulkan-icd-loader shaderc
else
    sudo pacman -S --needed python tk
fi
exec python3 "$studio_source_dir/installers/install.py" "$@"
