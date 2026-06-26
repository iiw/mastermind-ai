#!/usr/bin/env python3
"""Mock Hermes CLI for integration tests.

Returns canned responses based on stdin content.
Supports --silent flag acceptance and --model flag.

Usage:
  mock_hermes.py [--silent] [--model MODEL]
  # reads stdin, returns canned response

Environment variables for configuration:
  MOCK_DELEGATOR_RESPONSE   — Delegator role output (default: "Search PyPI for FastAPI releases")
  MOCK_EVALUATOR_RESPONSE   — Evaluator role output (default: '{"status":"continue","reasoning":"ok"}')
  MOCK_EXECUTOR_RESPONSE    — Executor output (default: "Done.")
  MOCK_FAIL_WITH_SILENT     — set to "1" to reject --silent flag (exit 1)
  MOCK_EXIT_CODE            — force non-zero exit (default: 0)
  MOCK_OUTPUT_TRUNCATED     — set to "1" to produce truncated output ending with "..."
"""

import os
import sys
import json

# ── Canned responses ─────────────────────────────────────────
DELEGATOR_RESPONSE = os.environ.get(
    "MOCK_DELEGATOR_RESPONSE",
    "Search PyPI for the latest FastAPI release and save to research/fastapi.md",
)

EVALUATOR_RESPONSE = os.environ.get(
    "MOCK_EVALUATOR_RESPONSE",
    json.dumps({"status": "continue", "reasoning": "Looks good, continue.", "remaining_time_ok": True, "next_hint": ""}),
)

EXECUTOR_RESPONSE = os.environ.get(
    "MOCK_EXECUTOR_RESPONSE",
    "Mock executor completed the task.\nHere are the results:\n- Found FastAPI 0.111.0\n- Wrote report to output.md",
)

# ── Behaviour switches ───────────────────────────────────────
FAIL_WITH_SILENT = os.environ.get("MOCK_FAIL_WITH_SILENT", "0") == "1"
FORCE_EXIT_CODE = int(os.environ.get("MOCK_EXIT_CODE", "0"))
TRUNCATED = os.environ.get("MOCK_OUTPUT_TRUNCATED", "0") == "1"


def main():
    # If --silent is present and we're configured to reject it, bail
    if "--silent" in sys.argv and FAIL_WITH_SILENT:
        sys.stderr.write("mock_hermes: --silent not supported\n")
        sys.exit(1)

    # Read stdin to determine what role we're playing
    stdin_input = sys.stdin.read()

    # Determine response based on stdin content (heuristic)
    response = EXECUTOR_RESPONSE  # default

    if DELEGATOR_RESPONSE and "Delegator" in stdin_input and "Produce one instruction" in stdin_input:
        response = DELEGATOR_RESPONSE
    elif "Evaluator" in stdin_input and "assess the last execution result" in stdin_input:
        response = EVALUATOR_RESPONSE
    elif "Finalizer" in stdin_input and "synthesise" in stdin_input:
        response = "# Final Report — Test\n\n**Summary:** Mock run complete."
    elif "instruction" in stdin_input or "execute" in stdin_input:
        response = EXECUTOR_RESPONSE

    # Truncation simulation
    if TRUNCATED and response:
        response = response.rstrip() + "..."

    sys.stdout.write(response)
    sys.stdout.flush()
    sys.exit(FORCE_EXIT_CODE)


if __name__ == "__main__":
    main()
