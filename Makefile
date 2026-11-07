.PHONY: install app test cli
install:
	uv sync --extra dev
app:
	uv run streamlit run app.py
test:
	uv run pytest
cli:
	uv run tuna-sim --years 30 --replicates 100 --vessels 7000 --bond-size 15
