# ---- build the frontend ----
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # WORKDIR is /build, and outDir "../static" resolves
                            # relative to that, so this writes to /static

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

# Pre-compute the corpus embeddings at BUILD time too, same reason as the model
# pre-download above: embeddings_cache.npz is gitignored (it's a derived
# artifact, not source data), so without this step every Render deploy would
# recompute embeddings for the whole corpus at container startup — a memory
# spike well past the 512Mi free-tier limit, even though steady-state serving
# only needs ~220MiB. Building NYSCBot() here runs the exact same corpus/cache
# logic as runtime, so there's no risk of the baked cache hash not matching.
RUN python -c "from app.bot import NYSCBot; NYSCBot()"

COPY --chown=user --from=frontend /static ./static

EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]