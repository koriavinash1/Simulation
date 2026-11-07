#!/usr/bin/env sh
set -eu
uv sync --group dev
printf '\nReady. Start the UI with:\n  uv run streamlit run app.py\n'
