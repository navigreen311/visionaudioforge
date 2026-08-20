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

# The runtime user needs a home it can write to. `useradd --system` without
# --create-home left /home/appuser non-existent, and two library families
# assume a writable home and fail without one:
#
#   huggingface_hub calls os.makedirs on its cache root and raised
#     PermissionError: [Errno 13] Permission denied: '/home/appuser'
#   CLIP therefore never downloaded, the embedding model never loaded, and
#   POST /api/search/query answered 500. All text search was down.
#
#   numba caches compiled functions beside the source it compiles, and
#   site-packages here is read-only. That produced
#     cannot cache function '__o_fold': no locator available
#   and took every librosa decode down with it.
#
#   Worth stating precisely, because the comment would otherwise claim more
#   than was tested: on the pinned numba (0.67.0) that failure no longer
#   reproduces. Decoding with HOME, XDG_CACHE_HOME and NUMBA_CACHE_DIR all
#   unset was checked directly in this image and succeeds -- numba now warns
#   and compiles in memory rather than raising. NUMBA_CACHE_DIR is therefore
#   set defensively, not as a proven repair: it keeps numba off a read-only
#   site-packages by construction, so a version that hard-errors again cannot
#   silently take audio down a second time. It also buys the cache hit, which
#   the fallback path gives up on every process start.
#
# The caches are pointed at that home *explicitly* rather than left to be
# inferred from $HOME. uvicorn and the celery worker are separate entrypoints
# and a library that falls back to a relative path lands back in the
# read-only site-packages.
ENV HOME=/home/appuser \
    XDG_CACHE_HOME=/home/appuser/.cache \
    HF_HOME=/home/appuser/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/home/appuser/.cache/huggingface/hub \
    NUMBA_CACHE_DIR=/home/appuser/.cache/numba \
    MPLCONFIGDIR=/home/appuser/.cache/matplotlib

RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /home/appuser --create-home appuser \
    && mkdir -p /home/appuser/.cache/huggingface/hub \
                /home/appuser/.cache/numba \
                /home/appuser/.cache/matplotlib \
    && chown -R appuser:appuser /app /home/appuser

USER appuser

# Bake the CLIP weights into the image.
#
# Downloaded at first request instead, the first search after every deploy pays
# ~600 MB of latency, and a stack with no outbound egress never serves a search
# at all — it fails on a network call rather than on configuration. Baking
# costs image size and makes a model bump a rebuild; that trade is argued in
# docs/deploy.md.
#
# Run as appuser so the files land owned by the user that reads them.
#
# use_safetensors=True matters for size, not safety: from_pretrained otherwise
# caches *both* pytorch_model.bin and model.safetensors, 578 MB each, and only
# one is ever read. Fetching one halves what this layer costs.
RUN python -c "from transformers import CLIPModel, CLIPProcessor; \
n='openai/clip-vit-base-patch32'; \
CLIPModel.from_pretrained(n, use_safetensors=True); \
CLIPProcessor.from_pretrained(n); print('CLIP weights baked')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
