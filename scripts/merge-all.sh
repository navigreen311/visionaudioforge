#!/bin/bash
# VisionAudioForge — Merge all 20 workstreams into master
# Run from the main repo: bash scripts/merge-all.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=== VisionAudioForge: Merging All Workstreams ==="
echo ""

# Ensure we're on master
git checkout master

# Merge in dependency order
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

FAILED=()

for ws in "${WORKSTREAMS[@]}"; do
  BRANCH="ai-feature/$ws"
  echo "[MERGE] $BRANCH"

  if git merge "$BRANCH" --no-ff -m "merge: $ws into master"; then
    echo "[OK] $ws merged successfully"
  else
    echo "[CONFLICT] $ws has merge conflicts — resolve manually"
    FAILED+=("$ws")
    git merge --abort
  fi
  echo ""
done

echo "=== Merge Summary ==="
echo "Merged: $((${#WORKSTREAMS[@]} - ${#FAILED[@]})) / ${#WORKSTREAMS[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
  echo ""
  echo "FAILED (need manual resolution):"
  for f in "${FAILED[@]}"; do
    echo "  - ai-feature/$f"
  done
fi

echo ""
echo "=== Cleaning up worktrees ==="
PARENT_DIR="$(dirname "$REPO_DIR")"
for ws in "${WORKSTREAMS[@]}"; do
  WT_DIR="$PARENT_DIR/vaf-$ws"
  if [ -d "$WT_DIR" ]; then
    git worktree remove "$WT_DIR" --force 2>/dev/null && echo "[REMOVED] $WT_DIR" || echo "[SKIP] $WT_DIR"
  fi
done

echo ""
echo "Done. Run 'docker compose up' to test the integrated build."
