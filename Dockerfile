FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY simulator ./simulator
RUN uv sync --no-dev
COPY app.py ./app.py
COPY configs ./configs
COPY docs ./docs
COPY .streamlit ./.streamlit
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
