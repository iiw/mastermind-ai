#!/usr/bin/env python3
"""Slow mock Hermes CLI for timeout/budget-exhaustion tests.

Adds a configurable delay before returning a canned response.

Usage:
  mock_slow_hermes.py [--silent] [--model MODEL]
  # reads stdin, sleeps for DELAY seconds, returns response

Environment variables:
  MOCK_DELAY_SEC      — seconds to sleep (default: 300 — long enough to trigger timeouts)
  MOCK_EXIT_CODE      — force non-zero exit (default: 0)
  MOCK_RESPONSE       — canned output (default: "slow response")
  MOCK_STDERR         — optional stderr output (default: "")
"""

import os
import sys
import time


def main():
    delay = float(os.environ.get("MOCK_DELAY_SEC", "300"))
    exit_code = int(os.environ.get("MOCK_EXIT_CODE", "0"))
    response = os.environ.get("MOCK_RESPONSE", "slow response")
    stderr_output = os.environ.get("MOCK_STDERR", "")

    sys.stdin.read()  # consume stdin

    if stderr_output:
        sys.stderr.write(stderr_output)
        sys.stderr.flush()

    time.sleep(delay)

    sys.stdout.write(response)
    sys.stdout.flush()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
