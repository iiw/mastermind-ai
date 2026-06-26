---
name: mastermind-ai
category: software-development
description: Orchestrate complex multi-step tasks using Mastermind AI — a lightweight one-file orchestrator that runs plan→do→check cycles via Hermes CLI subprocesses.
related_skills:
  - file-delivery
---

# Mastermind AI — Orchestrator Agent

**Location:** `~/projects/mastermind-ai/`

Mastermind AI is a single-file Python engine (`mastermind.py`) that orchestrates Hermes through repeated **Delegator → Executor → Evaluator** cycles to accomplish a high-level task, then writes a final Markdown report.

## 🚨 CRITICAL: File Delivery Protocol (Read Before Every Run)

Mastermind runs in the background. If you do not explicitly send the file, the user never sees it. **This is the #1 failure mode.** Follow this checklist in exact order:

### Pre-Flight Checklist

- [ ] Before starting the run, identify where the output file will be written (workdir or `results/`)
- [ ] Budget time for delivery: include `read the file, then present it via MEDIA:` in the Executor instruction for the last iteration
- [ ] After the run completes, DO NOT delete or clean up files until after you've confirmed delivery

### Delivery Checklist (execute after the run completes)

```
1.  Find the output files
    └─ Check results/ for newest .md AND scan workdir for Executor artifacts
2.  Verify the file  
    └─ read_file() — confirm content is real (not a stub), check size >500 bytes
3.  [NON-NEGOTIABLE] Include MEDIA:/absolute/path/to/file in your response
    └─ The literal string "MEDIA:/path/to/file" MUST appear in your response text
    └─ Describing the contents without MEDIA: does NOT send the file — this is the bug
4.  [CRITICAL] Wait for user confirmation that they received the file
    └─ Do NOT clean up files in the same turn as the MEDIA: directive
    └─ Cleanup runs in a separate follow-up turn after user acknowledges delivery
    └─ If user says they didn't get it, re-send immediately — do not delete first
5.  Clean up (ONLY after confirmed delivery)
    └─ rm the generated files from disk (unless user asks to keep them)
```

> ⚠️ **Known failure mode:** pasting a summary saying "full report below 👇" without the `MEDIA:` path — the user gets the summary but never receives the actual file. Always check your response for the `MEDIA:` directive before submitting.
>
> ⚠️ **Another failure mode:** starting a background `rm` in the same turn as the `MEDIA:` directive — deletion races with delivery and the file is gone before the platform sends it. Cleanup must be a SEPARATE turn.

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
| **💥 MEDIA: race with cleanup** | Never start a background `rm` in the same turn as a `MEDIA:` directive. File deletion races with platform delivery. Keep a copy until the user confirms receipt. |
| **💥 MEDIA: not in response text** | Including `MEDIA:` in your *thought process* or describing the file contents in prose does NOT send it. The literal string must appear in your submitted response. |

## Running Tests

```bash
# Unit tests (no Hermes needed)
python3 ~/projects/mastermind-ai/tests/test_mastermind.py

# Integration tests with mock Hermes
MASTERMIND_HERMES_BIN=~/projects/mastermind-ai/tests/helpers/mock_hermes.py \
  ~/projects/mastermind-ai/mastermind.py --task "Test" --max-minutes 1
```

## When to Use This Skill

**🚨 PRIMARY TRIGGER — time-bounded tasks:** Whenever the user says **"research X for N minutes"**, **"do Y for N minutes"**, or any equivalent ("spend 5 minutes on...", "take 10 minutes to..."), you MUST delegate to Mastermind AI instead of running web searches yourself. The `--max-minutes N` flag maps directly to the user's time budget. This ensures structured plan→do→check cycles with proper time management rather than ad-hoc manual tool calls that can exceed the budget.

Other use cases:

- "Research X and write a comprehensive report"
- "Build a full project from scratch"
- "Analyze a codebase and document everything"
- Any task the user frames as "I want this done, figure it out step by step"

For simple one-shot tasks, just handle them directly — Mastermind AI's overhead (~3 Hermes calls per iteration + 30s per iteration overhead) only pays off on non-trivial tasks.
