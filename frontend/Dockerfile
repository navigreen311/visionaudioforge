# ---- Build stage ----
FROM node:20-alpine AS builder

LABEL maintainer="VAF Team"
LABEL version="1.0.0"
LABEL description="VAF Frontend - Next.js application"

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* is inlined into the client bundle at build time, so it has to
# be a build arg — setting it only in `environment:` at runtime has no effect
# on the shipped JavaScript. Empty is correct behind nginx: the console then
# calls the API on its own origin.
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# ---- Production stage ----
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
# Next's standalone server binds to HOSTNAME, which defaults to localhost.
# Left unset the container listens only on its own loopback, so both the
# published port and nginx get connection-refused while the app looks healthy
# from inside. This line is the difference between "running" and "reachable".
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN apk add --no-cache curl

# .next/standalone is only produced when `output: "standalone"` is set in
# next.config.mjs. It was commented out, so this COPY failed and the frontend
# image could not be built at all.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# node:20-alpine ships an unprivileged `node` user; use it rather than root.
USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:3000/login || exit 1

CMD ["node", "server.js"]
