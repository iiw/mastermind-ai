# Mastermind AI — Minimalist Orchestrator

A lightweight, single-file Python engine that takes a high-level task and
orchestrates an AI agent (Hermes) through repeated **plan → do → check**
cycles, then writes a final report.

```
                 ┌── plan ──▶  Delegator produces an instruction
                 │
Task ──▶ Loop ──┼── do  ──▶  Executor carries out the instruction
                 │            (searches, writes files, runs code)
                 │
                 └── check ──▶  Evaluator decides: continue, pivot, or stop
                                    │
                                    ▼
                              Finalizer writes results/report
```

No API keys. No config files. No external dependencies beyond Python's standard
library. Everything goes through the `hermes` CLI that you already have.

---

## Quick Start

```bash
cd ~/projects/mastermind-ai

python3 mastermind.py \
  --task "Research the fastest Python web frameworks in 2026 and write a comparison" \
  --max-minutes 10 \
  --verbose
```

That's it. The orchestrator will iterate for up to 10 minutes, each time:
1. Asking Hermes (as **Delegator**) what to do next
2. Letting Hermes (as **Executor**) do the work
3. Asking Hermes (as **Evaluator**) if the result is good enough

When time runs out (or the Evaluator says it's done), a **Finalizer** writes a
markdown report to `results/final-task-<timestamp>-<pid>.md`.

---

## Example

```bash
python3 mastermind.py --task "Say hello and exit" --max-minutes 1 --verbose
```

This is the simplest smoke test. It should complete in ~30 seconds, produce a
results file, and exit cleanly.

---

## CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--task TASK` | *(required)* | The high-level task to accomplish |
| `--max-minutes N` | `10` | Wall-clock budget in minutes |
| `--model MODEL` | *(active profile)* | Override the Hermes model |
| `--max-iterations N` | `20` | Safety cap on loop iterations |
| `--hermes-bin PATH` | auto-detect | Path to the `hermes` CLI binary |
| `--profile PROFILE` | *(active)* | Hermes profile to use |
| `--workdir PATH` | current dir | Working directory for all file operations |
| `--verbose` | off | Show detailed progress on stderr |
| `--version` | — | Print version and exit |

Environment variables (CLI takes precedence):

| Variable | Overrides |
|---|---|
| `MASTERMIND_MAX_MINUTES` | `--max-minutes` |
| `MASTERMIND_MODEL` | `--model` |
| `MASTERMIND_HERMES_BIN` | `--hermes-bin` |
| `MASTERMIND_PROFILE` | `--profile` |

---

## How It Works

### The Loop

Each iteration makes **3 Hermes subprocess calls**:

```
  Iteration i
  ┌─────────────────────────────────────────────┐
  │                                             │
  │  1. Hermes-as-Delegator                     │
  │     → reads: task + history + time left     │
  │     → writes: one concrete instruction      │
  │                                             │
  │  2. Hermes-as-Executor                      │
  │     → receives: instruction verbatim        │
  │     → does real work (search, code, files)  │
  │                                             │
  │  3. Hermes-as-Evaluator                     │
  │     → reads: instruction + output + files   │
  │     → decides: continue / pivot / finalize  │
  │                                             │
  │  4. Check time → loop or stop               │
  └─────────────────────────────────────────────┘
```

The orchestrator has **no integrated LLM** — it never calls an API directly. Every
"thinking" step is a separate Hermes subprocess with a role-specific prompt.

### When Does It Stop?

| Condition | What Happens |
|---|---|
| ⏰ Time budget nearly exhausted | Finishes current evaluation → Finalizer |
| ✅ Evaluator says `"finalize"` | Immediate → Finalizer |
| 🔁 3x same instruction repeated | Loop guard → Finalizer (thrash protection) |
| 🔢 Max iterations reached | Hard cap → Finalizer |
| 💥 Fatal error (can't write file) | Error message, exit code 2 |

### Time Management

The orchestrator is aggressive about time:

- **Margin**: 10% of budget (min 5s, max 50%) — once elapsed exceeds `budget - margin`,
  the loop finishes the current step and exits
- **3 checkpoints per iteration**: after Delegator, after Executor, after Evaluator
- **Watchdog thread**: cooperative daemon that signals if the hard ceiling (budget + 1 min) is breached
- **Tiny budgets**: if `--max-minutes` is so small that even one iteration can't finish,
  it goes straight to Finalizer

---

## File Structure

```
~/projects/mastermind-ai/
├── mastermind.py       ← The orchestrator (single file, stdlib only)
├── SDD.md              ← Software Design Document (specification)
├── COMPLETENESS.md     ← Traceable acceptance checklist (208 criteria)
├── TEST_CASES.md       ← Automated test catalogue
├── README.md           ← This file
├── results/            ← Output directory (created on first run)
│   ├── final-task-1.md
│   └── ...
└── tests/
    ├── test_mastermind.py          ← 38 unit tests
    └── helpers/
        ├── mock_hermes.py          ← Canned responses for integration tests
        └── mock_slow_hermes.py     ← Configurable delay for timeout tests
```

> 💡 **Hermes Skill** — You can add this skill to your Hermes Agent by copying `SKILL.md` into `~/.hermes/skills/software-development/mastermind-ai/SKILL.md` (or just drop the whole repo path `~/projects/mastermind-ai` into your Hermes skill search path). Your agent will then know how to orchestrate complex multi-step tasks through Mastermind AI out of the box.

---

## Design Principles

| Principle | What it means |
|---|---|
| **Minimalist** | Single Python file, zero pip packages |
| **Hermes-native** | Every "role" is a Hermes CLI subprocess — no API keys |
| **Time-bounded** | Wall-clock budget, hard stop, mid-call time checks |
| **Role-pure** | Delegator, Executor, Evaluator, Finalizer have distinct prompts and outputs |
| **Self-contained** | CLI args + env vars only — no config files |
| **Idempotent writes** | Results files are atomic and never overwrite each other |

---

## Development

### Running Tests

```bash
# Unit tests (no Hermes needed)
python3 tests/test_mastermind.py

# With pytest
python3 -m pytest tests/ -v

# Integration tests (need hermes CLI or mock)
MASTERMIND_HERMES_BIN=tests/helpers/mock_hermes.py \
  python3 mastermind.py --task "Test" --max-minutes 1
```

### Key Specs

- **Python**: 3.10+ (stdlib only)
- **Version**: 1.5.2
- **Requirements**: just the `hermes` CLI binary on your PATH
