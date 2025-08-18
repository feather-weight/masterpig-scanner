# Build a Python image with tools for native deps (Rust, gcc)
FROM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps so packages like ed25519-blake2b can compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev pkg-config python3-dev rustc cargo \
 && rm -rf /var/lib/apt/lists/*

# Modern build tooling
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python deps first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bring in the rest of the project
COPY . .

# Make sure Python can import from /app
ENV PYTHONPATH=/app

# Document the app port (Caddy reverse-proxies to this)
EXPOSE 3000

# Default entrypoint: run your app as a module
# (no filesystem path like /app/main.py; uses the package "app")
CMD ["python", "-m", "app.main"]
