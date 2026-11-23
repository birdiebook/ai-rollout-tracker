#!/usr/bin/env bash
# Create a worktree for a parallel agent track that reads the shared base table (docs/drift.md, "Delad data").
#
#   scripts/new_track.sh <name> <branch-prefix> [base-ref]     e.g. scripts/new_track.sh a1-rpo auto5
#
# -> worktree $AI_TRACKER_WT_ROOT/<name> (default /home/user/wt) on a new branch <branch-prefix>/<name> from
#    base-ref (default main) of $AI_TRACKER_MAIN (default /home/user/ai-rollout-tracker); copies .env (secrets,
#    gitignored) and writes .env.local (gitignored) with AI_TRACKER_SHARED_DATA=<main>/data and
#    AI_TRACKER_SHARED_RAW=<main>/data/raw. config.get reads .env.local, so every python -m ai_tracker.* in the
#    worktree sees base ∪ track and writes only to the worktree's own data/.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <name> <branch-prefix> [base-ref]" >&2
  exit 2
fi
name=$1
prefix=${2%/}
ref=${3:-main}
main=${AI_TRACKER_MAIN:-/home/user/ai-rollout-tracker}
root=${AI_TRACKER_WT_ROOT:-/home/user/wt}
wt=$root/$name
branch=$prefix/$name

case $name in
  */*|.*|"") echo "bad track name: $name" >&2; exit 2 ;;
esac
if [ -e "$wt" ]; then
  echo "$wt exists; refusing to touch it" >&2
  exit 1
fi

mkdir -p "$root"
git -C "$main" worktree add --quiet -b "$branch" "$wt" "$ref"
if [ -f "$main/.env" ]; then
  cp "$main/.env" "$wt/.env"
  chmod 600 "$wt/.env"
fi
cat > "$wt/.env.local" <<ENV
# Written by scripts/new_track.sh: shared read-only base table, writes go to this worktree's data/
AI_TRACKER_SHARED_DATA=$main/data
AI_TRACKER_SHARED_RAW=$main/data/raw
ENV
mkdir -p "$wt/data" "$main/data/raw"

echo "worktree $wt (branch $branch from $ref)"
echo "reads   $main/data (base) + $wt/data (track); writes $wt/data"
echo "merge   python -m ai_tracker.datamerge $wt/data --into $main/data   (from a checkout with the track's code)"
