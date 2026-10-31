#!/usr/bin/env sh
set -eu
exec uv run streamlit run app.py "$@"
