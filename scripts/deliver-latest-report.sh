#!/usr/bin/env bash
# deliver-latest-report.sh
# Find and send the latest Mastermind AI report via Hermes communication platform.
#
# Usage:
#   MASTERMIND_DELIVERY_TARGET=telegram \
#     ~/projects/mastermind-ai/scripts/deliver-latest-report.sh ~/projects/mastermind-ai
#
# The script prefers Executor-created report files (*report*.md, *analysis*.md)
# in the workspace root over the Finalizer summary in results/.

set -euo pipefail

WORKDIR="${1:-$PWD}"
TARGET="${MASTERMIND_DELIVERY_TARGET:-telegram}"

cd "$WORKDIR"

# Priority 1: Executor-created report files in the workspace root.
REPORT_PATH="$(
  find "$WORKDIR" -maxdepth 1 -type f \
    \( -iname '*report*.md' -o -iname '*analysis*.md' \) \
    -printf '%T@ %s %p\n' 2>/dev/null \
  | sort -nr \
  | awk 'NR==1 {print $3}'
)"

# Priority 2: Newest Finalizer result file as fallback.
if [ -z "${REPORT_PATH:-}" ]; then
  REPORT_PATH="$(
    find "$WORKDIR/results" -maxdepth 1 -type f -name 'final-task-*.md' \
      -printf '%T@ %s %p\n' 2>/dev/null \
    | sort -nr \
    | awk 'NR==1 {print $3}'
  )"
fi

# Fail if nothing found
if [ -z "${REPORT_PATH:-}" ] || [ ! -s "$REPORT_PATH" ]; then
  echo "No non-empty report file found in $WORKDIR" >&2
  exit 2
fi

BYTES="$(wc -c < "$REPORT_PATH")"
if [ "$BYTES" -lt 500 ]; then
  echo "Warning: selected report is small (${BYTES} bytes): $REPORT_PATH" >&2
fi

echo "Sending report to $TARGET: $REPORT_PATH" >&2
hermes send --to "$TARGET" "MEDIA:$REPORT_PATH"

echo "Delivered: $REPORT_PATH"
