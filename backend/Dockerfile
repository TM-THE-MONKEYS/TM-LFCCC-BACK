# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create uploads directory
RUN mkdir -p uploads/products

EXPOSE 8000

# Entrypoint: apply migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
