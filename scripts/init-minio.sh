#!/bin/sh
# Create the application bucket in MinIO.
#
# Run as a one-shot compose service (minio_init) after minio reports healthy.
# Idempotent: re-running against an existing bucket is a no-op, so it is safe
# on every `docker compose up`.
#
# Referenced by docs/deploy.md and by the compose smoke job in CI.

set -eu

MINIO_ALIAS="local"
MINIO_URL="http://minio:9000"
MINIO_BUCKET="${MINIO_BUCKET:-vaf-assets}"

echo "init-minio: registering alias for ${MINIO_URL}"
# `mc alias set` is retried: minio reports healthy a moment before it will
# accept admin credentials, and a one-shot job that loses that race blocks the
# whole stack behind service_completed_successfully.
attempt=1
until mc alias set "${MINIO_ALIAS}" "${MINIO_URL}" \
        "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
    if [ "${attempt}" -ge 15 ]; then
        echo "init-minio: could not reach ${MINIO_URL} after ${attempt} attempts" >&2
        exit 1
    fi
    echo "init-minio: minio not accepting credentials yet (attempt ${attempt})"
    attempt=$((attempt + 1))
    sleep 2
done

if mc ls "${MINIO_ALIAS}/${MINIO_BUCKET}" >/dev/null 2>&1; then
    echo "init-minio: bucket '${MINIO_BUCKET}' already exists"
else
    echo "init-minio: creating bucket '${MINIO_BUCKET}'"
    mc mb "${MINIO_ALIAS}/${MINIO_BUCKET}"
fi

# Assets are served to the console through presigned URLs, so the bucket
# itself stays private. Do not relax this to `public` for convenience.
mc anonymous set none "${MINIO_ALIAS}/${MINIO_BUCKET}" >/dev/null 2>&1 || true

echo "init-minio: done — ${MINIO_BUCKET} ready"
