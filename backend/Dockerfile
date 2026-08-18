# ---- Build stage ----
FROM python:3.11-slim AS builder

LABEL maintainer="VAF Team"
LABEL version="1.0.0"
LABEL description="VAF Backend API - FastAPI application with ML pipeline support"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install the CPU builds of torch/torchvision first, from PyTorch's own index.
#
# `pip install torch==2.2.0` from PyPI resolves to the CUDA build on Linux and
# drags in ~1.2 GB of nvidia_* wheels — cuBLAS alone is 410 MB, cuDNN 732 MB —
# none of which this stack can use: TORCH_DEVICE is cpu and no container is
# given a GPU. Pre-installing +cpu satisfies the pin below (PEP 440: `==2.2.0`
# matches the `2.2.0+cpu` local version), so the requirements pass that follows
# leaves it alone.
#
# If this image ever needs GPU support, drop these two lines rather than adding
# a second torch — having both indexes in play produces a silently mixed
# install.
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0 torchvision==0.17.0

RUN pip install --no-cache-dir -r requirements.txt

# ---- Production stage ----
FROM python:3.11-slim

WORKDIR /app

# curl belongs in this block. It used to be installed *after* `USER appuser`,
# where apt-get cannot write to /var/lib/apt and the build failed outright —
# and the HEALTHCHECK below depends on it, as does the compose healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    libsndfile1 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY requirements.txt .
COPY app/ ./app/
# Migrations were never copied into the image, so `alembic upgrade head` could
# not run in a container even though six migrations existed. The compose
# `migrate` service runs exactly this.
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN groupadd --system appuser && useradd --system --gid appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
