#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PANEL_BIN="${ROOT}/.venv/bin/panel"
PYTHON_BIN="${ROOT}/.venv/bin/python"
if [[ ! -x "${PANEL_BIN}" ]]; then PANEL_BIN="panel"; fi
if [[ ! -x "${PYTHON_BIN}" ]]; then PYTHON_BIN="python"; fi

mkdir -p docs/app
"${PANEL_BIN}" convert app.py --to pyodide-worker --compiled --disable-http-patch \
  --requirements scripts/pyodide_requirements.txt --out docs/app
"${PYTHON_BIN}" scripts/prepare_static_export.py

