# syntax=docker/dockerfile:1

# Stage 1: build the React frontend into frontend/dist.
FROM node:24-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: install Python dependencies into a virtualenv with uv.
# (The tradele project itself is "virtual" - not installed as a package -
# so the app source is copied straight into the runtime image below.)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS python-build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Stage 3: slim runtime image with the venv, app source, and built frontend.
FROM python:3.13-slim
WORKDIR /app
COPY --from=python-build /app/.venv /app/.venv
COPY --from=frontend-build /frontend/dist /app/frontend/dist
COPY app/ app/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
