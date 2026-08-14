# ---- build the frontend ----
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # writes to /backend/static via vite.config.js outDir

# ---- runtime ----
FROM python:3.11-slim
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface
WORKDIR $HOME/app

COPY --chown=user backend/requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download the model at BUILD time so cold starts are fast
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

COPY --chown=user backend/ ./
COPY --chown=user --from=frontend /backend/static ./static

EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]