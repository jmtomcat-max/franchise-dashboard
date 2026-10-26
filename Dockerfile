# Multi-stage / Lightweight Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for healthcheck and sqlite runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Restore the 490MB SQLite DB from git chunks during image build
RUN python scripts/restore_db.py

ENV PORT=8000
ENV ENVIRONMENT=production
EXPOSE 8000

# Start unified FastAPI + React SPA server
CMD ["sh", "-c", "uvicorn src.stage4e.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
