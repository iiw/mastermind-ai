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

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Clean success — Finalizer completed, results file written |
| `1` | Partial success — results file written but with warnings (Finalizer fallback used, executor timeout, evaluator skipped, loop guard triggered, etc.) |
| `2` | Failure — no results file; task incomplete (fatal error) |

See `references/exit-codes.md` for real-world examples and how to verify results after a partial-success exit.

## Key Design Details

- **Python 3.10+ only** — stdlib imports only, zero pip packages
- **Time-bounded** — aggressive margin logic (10% of budget, min 5s, cap 50%)
- **Watchdog thread** — hard ceiling at budget + 60s via `threading.Event`
- **Atomic writes** — `os.replace()` to `results/final-task-<time_ns>-<pid>.md`
- **File artifact detection** — snapshots working dir before/after executor for changed files
- **Duplicate instruction guard** — `INSTRUCTION_DEDUP_WINDOW=3`, normalised prefix matching
- **Retry logic** — `MAX_ATTEMPTS=2` (1 initial + 1 retry) per Hermes call
- **`chat --cli -Q` for programmatic calls** — Hermes is invoked as `hermes chat --cli -Q -q "{prompt}"` rather than via stdin pipe or a non-existent `--silent` flag. This gives clean text output (session_id + response) instead of the TUI splash screen. See `references/hermes-cli-programmatic.md` for full details.

## Execution Patterns

### Research / Analysis Pattern

Research and analysis tasks converge quickly — typically **2 iterations** (~4 min on deepseek-v4-flash):

1. **Iteration 1** — Delegator asks to explore the project/codebase (read files, understand structure)
2. **Iteration 2** — Delegator asks to write the comprehensive report as a deliverable
3. Evaluator sees the report exists and returns `"finalize"`

This is very efficient for codebase analysis, technology comparison, trend research, or architecture review tasks. Budget `--max-minutes 5` for focused analysis, `--max-minutes 10` for deeper research.

### Dual-Output Model

The orchestrator produces output in **two locations** — don't look in only one:

| Location | Writer | Content |
|---|---|---|
| `workdir/<DELIVERABLE>.md` | **Executor** | The full artifact (report, scaffold, analysis — whatever the task asked for). Can be 700+ lines / 40K+ chars. |
| `results/final-task-<ns>-<pid>.md` | **Finalizer** | A short summary / conclusion (~2-3 KB). Always written atomically last. |

When checking results after a run: **read the Executor artifact first**. The Finalizer file is a lightweight wrap-up, not the main deliverable.

## Pitfalls

| Pitfall | Solution |
|---|---|
| **`hermes --silent` doesn't exist** | The CLI flag `--silent` is unrecognized. Subprocess calls must use `hermes chat --cli -Q -q "{prompt}"`. The `-q` flag passes the prompt as a CLI argument; `-Q` suppresses the TUI banner/splash screen. |
| **Stdin pipe opens TUI** | Piping a query to `hermes` via stdin opens the full TUI (splash screen artifacts in captured output). Always use `-q "prompt"` for programmatic calls. |
| **Long prompts (~8K+ chars)** | `-q` passes the prompt as a single argv element, which is fine on Linux (ARG_MAX ~2MB). But watch for Hermes context limits — capping at `MAX_PROMPT_CHARS=8000` and `MAX_FINALIZER_PROMPT_CHARS=12000` is recommended. |
| **Buffered stdout in bg** | When run in background mode, Python buffers stdout. The orchestrator's log output won't be visible until the process finishes. This is expected — results are written atomically to a file at the end. |
| **Iteration timing is model-dependent** | The 30-45s/iteration estimate assumes a fast model (~10-15s per Hermes call). On slower models (deepseek-v4-flash, large Sonnets) each call takes ~40-50s, making each iteration **~100-150s**. Budget `--max-minutes` generously for slow models: a 10-min budget allows only ~4-6 iterations, not the 12-15 a fast model would give. |
| **Finalizer timeout on slow models** | The Finalizer receives the largest prompt of all roles (full iteration history + up to 12K chars). On slow models the 60s `ROLE_TIMEOUT_SEC` (set in `mastermind.py` line 37) can fire. The orchestrator retries once then falls back to a minimal conclusion. The actual report is usually already written by the Executor — exit code 1 (partial success) is expected in this case. If you see `finalizer_fallback_used` warnings, the report is still valid; just check the output file. |

## Running Tests

```bash
# Unit tests (no Hermes needed)
python3 ~/projects/mastermind-ai/tests/test_mastermind.py

# Integration tests with mock Hermes
MASTERMIND_HERMES_BIN=~/projects/mastermind-ai/tests/helpers/mock_hermes.py \
  ~/projects/mastermind-ai/mastermind.py --task "Test" --max-minutes 1
```

## Delivery: After the Report Is Ready

**Once Mastermind AI finishes, you MUST deliver the report to the user — don't just leave it on disk.** The orchestrator writes results to `results/final-task-<timestamp>-<pid>.md` and may also create other output files (e.g. `ANALYSIS_REPORT.md`) written by the Executor directly to the working directory.

### Delivery Checklist

1. **Find the output file(s)** — check `results/` for the newest `.md` file (sorted by mtime) and scan the working directory for any additional report files the Executor created.
2. **Verify the file** — read a few lines to confirm it's the real report, not a stub or error message. Check file size (>500 bytes is a good heuristic for a real report).
3. **Send it** — include `MEDIA:/absolute/path/to/file` in your response to deliver the file natively (images, audio, video, or markdown documents). For text reports, you can also paste a concise summary alongside the file.
4. **Clean up** — remove the generated report file(s) from disk after sending (unless the user asks to keep them). Reports are artifacts of a single run and clutter the workspace.

> 💡 **Why this matters:** The orchestrator runs in the background. The user has no way to know a file was written unless you proactively deliver it. Treat delivery as a non-negotiable part of every Mastermind AI run.

## When to Use This Skill

Use Mastermind AI when the user has a **complex, multi-step task** that would take many iterations of me working on it — something that benefits from structured plan→do→check cycles with a time budget. Examples:

- "Research X and write a comprehensive report"
- "Build a full project from scratch"
- "Analyze a codebase and document everything"
- Any task the user frames as "I want this done, figure it out step by step"

For simple one-shot tasks, just handle them directly — Mastermind AI's overhead (~3 Hermes calls per iteration + 30s per iteration overhead) only pays off on non-trivial tasks.
