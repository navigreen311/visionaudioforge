#!/bin/bash
# VisionAudioForge — Create all 20 worktrees for parallel development
# Run from the main repo: bash scripts/create-worktrees.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_DIR")"

echo "=== VisionAudioForge: Creating 20 Parallel Worktrees ==="
echo "Repo: $REPO_DIR"
echo "Worktrees will be created in: $PARENT_DIR/vaf-ws*"
echo ""

WORKSTREAMS=(
  "ws01-docker-infra"
  "ws02-database-migrations"
  "ws03-auth-system"
  "ws04-health-observability"
  "ws05-vision-preprocessing"
  "ws06-vision-optical-flow"
  "ws07-vision-detection"
  "ws08-audio-spectral"
  "ws09-audio-augmentation"
  "ws10-capture-engine"
  "ws11-model-registry"
  "ws12-experiment-tracker"
  "ws13-dataset-manager"
  "ws14-faiss-search"
  "ws15-pipeline-builder"
  "ws16-copilot-agent"
  "ws17-transform-audio"
  "ws18-transform-video"
  "ws19-frontend-dashboard"
  "ws20-testing-e2e"
)

for ws in "${WORKSTREAMS[@]}"; do
  WT_DIR="$PARENT_DIR/vaf-$ws"
  BRANCH="ai-feature/$ws"

  if [ -d "$WT_DIR" ]; then
    echo "[SKIP] $WT_DIR already exists"
  else
    echo "[CREATE] $WT_DIR on branch $BRANCH"
    cd "$REPO_DIR"
    git worktree add "$WT_DIR" "$BRANCH"
  fi
done

echo ""
echo "=== All 20 worktrees created ==="
echo ""
echo "To start Claude Code in each:"
echo ""
for ws in "${WORKSTREAMS[@]}"; do
  echo "  cd $PARENT_DIR/vaf-$ws && claude"
done
echo ""
echo "Then paste the corresponding prompt from PARALLEL_WORKSTREAMS.md"
