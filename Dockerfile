FROM python:3.12-slim

# Avoid buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MEMORIAGRAPH_HOME=/app

WORKDIR /app

# Install system dependencies (build-essential, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download FastEmbed ONNX Int8 model into image for instant offline startup
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

# Copy application source
COPY . .

# Create directory structure for persistent data and logs
RUN mkdir -p /app/data /app/events /app/logs /app/backups

# Expose HTTP API & Cockpit port
EXPOSE 8085

# Default command starts the HTTP Microservice & AI Gateway
CMD ["python", "http_service.py"]
