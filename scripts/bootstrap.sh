#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-avfm}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "== avfm bootstrap =="
conda --version
if ! conda env list | grep -qE "^${ENV_NAME}[[:space:]]"; then
  echo "Creating conda env '${ENV_NAME}' (conda-forge, Python 3.11)..."
  conda create -n "${ENV_NAME}" python=3.11 -c conda-forge -y
else
  echo "Conda env '${ENV_NAME}' already exists."
fi

conda run -n "${ENV_NAME}" python -m pip install -U pip
conda run -n "${ENV_NAME}" python -m pip install -e ".[dev,mediapipe]"

if [[ "${SKIP_MODELS:-0}" != "1" ]]; then
  conda run -n "${ENV_NAME}" avfm models download --all
fi

conda run -n "${ENV_NAME}" avfm selftest
echo "Done. Activate with: conda activate ${ENV_NAME}"
