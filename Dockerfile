# ---------------------------------------------------------------------------
# Estágio 1 — build do frontend (Node). O Vite escreve em ../backend/static
# (ver frontend/vite.config.js: outDir = "../backend/static").
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build      # gera /app/backend/static

# ---------------------------------------------------------------------------
# Estágio 2 — runtime (Python). Serve a API e o frontend buildado num
# processo só (FastAPI monta a pasta static; ver backend/main.py).
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SOURCE=wikipedia

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# traz o frontend buildado do estágio anterior
COPY --from=frontend /app/backend/static ./static

EXPOSE 8000
# Render injeta $PORT; cai em 8000 no local.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
