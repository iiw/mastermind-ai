---
name: mastermind-ai
category: software-development
description: Orchestrate complex multi-step tasks using Mastermind AI — a lightweight one-file orchestrator that runs plan→do→check cycles via Hermes CLI subprocesses.
---

# Mastermind AI — Orchestrator Agent

**Location:** `~/projects/mastermind-ai/`

Mastermind AI is a single-file Python engine (`mastermind.py`) that orchestrates Hermes through repeated **Delegator → Executor → Evaluator** cycles to accomplish a high-level task, then writes a final Markdown report.

## Quick Start

```bash
cd ~/projects/mastermind-ai
python3 mastermind.py --task "Your high-level task" --max-minutes 10 --verbose
```

## How It Works

Each iteration makes 3 Hermes subprocess calls:

1. **Delegator** — reads: task + history + time left → writes: one concrete instruction
2. **Executor** — receives instruction verbatim → does real work (search, code, files)
3. **Evaluator** — reads: instruction + output + files → decides: continue / pivot / finalize

No API keys, no pip packages. Every "thinking" step is a separate Hermes subprocess.

## CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--task TASK` | *(required)* | The high-level task to accomplish |
| `--max-minutes N` | `10` | Wall-clock budget in minutes |
| `--model MODEL` | active profile | Override the Hermes model |
| `--max-iterations N` | `20` | Safety cap on loop iterations |
| `--hermes-bin PATH` | auto-detect | Path to the `hermes` CLI binary |
| `--profile PROFILE` | active | Hermes profile to use |
| `--workdir PATH` | current dir | Working directory for all file operations |
| `--verbose` | off | Show detailed progress on stderr |

### Environment Variables

| Variable | Overrides |
|---|---|
| `MASTERMIND_MAX_MINUTES` | `--max-minutes` |
| `MASTERMIND_MODEL` | `--model` |
| `MASTERMIND_HERMES_BIN` | `--hermes-bin` |
| `MASTERMIND_PROFILE` | `--profile` |

## Stop Conditions

| Condition | What Happens |
|---|---|
| ⏰ Time budget nearly exhausted | Finishes current evaluation → Finalizer |
| ✅ Evaluator says `"finalize"` | Immediate → Finalizer |
| 🔁 3x same instruction repeated | Loop guard → Finalizer (thrash protection) |
| 🔢 Max iterations reached | Hard cap → Finalizer |
| 💥 Fatal error (can't write file) | Error message, exit code 2 |

## Key Design Details

- **Python 3.10+ only** — stdlib imports only, zero pip packages
- **Time-bounded** — aggressive margin logic (10% of budget, min 5s, cap 50%)
- **Watchdog thread** — hard ceiling at budget + 60s via `threading.Event`
- **Atomic writes** — `os.replace()` to `results/final-task-<time_ns>-<pid>.md`
- **File artifact detection** — snapshots working dir before/after executor for changed files
- **Duplicate instruction guard** — `INSTRUCTION_DEDUP_WINDOW=3`, normalised prefix matching
- **Retry logic** — `MAX_ATTEMPTS=2` (1 initial + 1 retry) per Hermes call
- **Programmatic Hermes calls** — Hermes is called as `hermes chat --cli -Q -q "{prompt}"` (not via stdin pipe). The `--silent` flag does NOT exist in the Hermes CLI; piping via stdin opens the TUI. The `-q` flag passes the prompt as a CLI argument with `-Q` suppressing the splash banner.

## Running Tests

```bash
# Unit tests (no Hermes needed)
python3 ~/projects/mastermind-ai/tests/test_mastermind.py

# Integration tests with mock Hermes
MASTERMIND_HERMES_BIN=~/projects/mastermind-ai/tests/helpers/mock_hermes.py \
  ~/projects/mastermind-ai/mastermind.py --task "Test" --max-minutes 1
```

## When to Use This Skill

Use Mastermind AI when the user has a **complex, multi-step task** that would take many iterations of me working on it — something that benefits from structured plan→do→check cycles with a time budget. Examples:

- "Research X and write a comprehensive report"
- "Build a full project from scratch"
- "Analyze a codebase and document everything"
- Any task the user frames as "I want this done, figure it out step by step"

For simple one-shot tasks, just handle them directly — Mastermind AI's overhead (~3 Hermes calls per iteration + 30s per iteration overhead) only pays off on non-trivial tasks.
