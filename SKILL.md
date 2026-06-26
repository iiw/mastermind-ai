---
name: mastermind-ai
category: software-development
description: Orchestrate complex multi-step tasks using Mastermind AI — a lightweight one-file orchestrator that runs plan→do→check cycles via Hermes CLI subprocesses.
related_skills:
  - file-delivery
  - mastermind-deliver-final-report
---

# Mastermind AI — Orchestrator Agent

**Location:** `~/projects/mastermind-ai/`

Mastermind AI is a single-file Python engine (`mastermind.py`) that orchestrates Hermes through repeated **Delegator → Executor → Evaluator** cycles to accomplish a high-level task, then writes a final Markdown report.

## Delivery: After the Report Is Ready

Once Mastermind AI finishes, you MUST deliver the generated report file to the user through the configured Hermes communication platform.

Do not only paste a summary. Do not only leave the file on disk. Do not assume that the user can access the local filesystem.

Mastermind writes the report — the **outer Hermes agent** (you) is responsible for delivering it. Nested Hermes subprocesses inside Mastermind AI cannot attach files to Telegram, Discord, Slack, or other user-facing platforms.

### Delivery Flow

1. **Find output files**

   Read the structured stdout block from mastermind.py and extract the `path:` field. This points to the Finalizer result file:

       results/final-task-<time_ns>-<pid>.md

   Also scan the workspace root for larger Executor-created report files, for example:

       ANALYSIS_REPORT.md
       REPORT.md
       FINAL_REPORT.md
       *_REPORT.md
       *_ANALYSIS.md

2. **Choose the main deliverable**

   Prefer the Executor-created report if it exists and is larger/more complete.

   The file in `results/final-task-*.md` is usually the Finalizer summary. It is useful, but it may not be the main deliverable.

   Selection priority:

   1. Explicit report file requested by the task
   2. Largest recent Markdown report in the workspace root
   3. Newest recent Markdown report in the workspace root
   4. Newest `results/final-task-*.md` file

3. **Verify the selected file**

   Before sending, verify:

       test -f "$REPORT_PATH"
       test -s "$REPORT_PATH"
       wc -c "$REPORT_PATH"
       head -n 20 "$REPORT_PATH"

   The file should be a real report, not an empty stub, traceback, or placeholder. As a heuristic, a real report should usually be larger than 500 bytes.

4. **Find the delivery target**

   Use a configured delivery target. Prefer this order:

   1. `MASTERMIND_DELIVERY_TARGET` environment variable
   2. Existing known/default Hermes communication target
   3. A target discovered with `hermes send --list`

   Recommended environment variable:

       export MASTERMIND_DELIVERY_TARGET="telegram"

5. **Send the file as a native platform attachment**

   Use Hermes platform delivery explicitly:

       hermes send --to "$MASTERMIND_DELIVERY_TARGET" "MEDIA:$REPORT_PATH"

   Example:

       hermes send --to telegram "MEDIA:/home/star/projects/mastermind-ai/ANALYSIS_REPORT.md"

   If a specific platform/channel/chat is configured, use it explicitly:

       hermes send --to telegram:-1001234567890 "MEDIA:/absolute/path/to/report.md"
       hermes send --to discord:#reports "MEDIA:/absolute/path/to/report.md"
       hermes send --to slack:#reports "MEDIA:/absolute/path/to/report.md"

6. **Confirm delivery**

   If `hermes send` exits with code 0, tell the user:

       Done — I sent the report file through <target>.
       Local fallback path: <absolute path>

   If `hermes send` fails, do NOT delete the file. Tell the user:

       Mastermind AI completed and generated the report, but file delivery failed.
       Local path: <absolute path>
       Error: <short error summary>

7. **Do not delete reports automatically**

   Do not remove the generated report after sending unless the user explicitly asked for cleanup and delivery was confirmed.

   Rationale: platform delivery may fail silently or be rejected by the gateway. Keeping the local file preserves the artifact.

### Non-Negotiable Rules

- The nested Hermes subprocesses inside Mastermind AI are not responsible for user-facing delivery.
- The outer Hermes agent is responsible for delivery after mastermind.py exits.
- Do not rely on the final chat response containing `MEDIA:/path` as the only delivery mechanism.
- Use `hermes send --to <target> "MEDIA:/absolute/path/to/file"` for configured communication platforms.
- Always verify the selected file before sending.
- Prefer the main Executor-created report over the small Finalizer summary.
- Never delete the report before delivery is confirmed.
- Always include the local absolute path as a fallback in the user-facing response.

### Helper Script

Load the `mastermind-deliver-final-report` skill for the full delivery procedure and script:

```yaml
# Load this skill before delivering
related_skills:
  - mastermind-deliver-final-report
```

A shell helper script is at `scripts/deliver-latest-report.sh` in the skill's directory:

```bash
MASTERMIND_DELIVERY_TARGET=telegram \
  bash ~/.hermes/skills/file-delivery/mastermind-deliver-final-report/scripts/deliver-latest-report.sh ~/projects/mastermind-ai
```

It finds the latest report (Executor-created first, Finalizer fallback) and sends it via `hermes send`.

### Trigger Rule

When a Mastermind AI run completes, delivery is not complete until the selected report file has been sent via `hermes send --to "$MASTERMIND_DELIVERY_TARGET" "MEDIA:$REPORT_PATH"` or delivery failure has been explicitly reported to the user with the local file path.

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
| **`hermes send` not configured** | The agent fails because `MASTERMIND_DELIVERY_TARGET` is unset. Set it (e.g. `export MASTERMIND_DELIVERY_TARGET=telegram`) or pass `--to` explicitly. Run `hermes send --list` to discover available targets. |
| **Sent wrong file (Finalizer summary)** | The `results/final-task-*.md` file is a short wrap-up, not the main deliverable. Always prefer the Executor-created report in the workspace root first unless the task specifically asked for the summary. |
| **Sent empty or truncated file** | The file may be a stub, traceback, or empty placeholder. Always verify with `test -s`, `wc -c`, and `head` before sending. Real reports should be >500 bytes. |
| **Deleted report before delivery confirmed** | Platform delivery can fail silently or be rejected by the gateway. Never delete the local file unless the user explicitly asks for cleanup and you've confirmed the file was received. |

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
