#!/bin/bash
set -e

cp -n .env.example .env || true
docker compose build
