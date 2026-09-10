![ModelScope Fan-Out](assets/modelscope-fanout-banner.png)

# ModelScope Fan-Out

![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-D97757)
![CLIProxyAPI](https://img.shields.io/badge/CLIProxyAPI-Local_Proxy-blue)
![MIT Licence](https://img.shields.io/badge/Licence-MIT-blue)

**Headless Claude Code workers on ModelScope. Bundle the work, not the bill.**

> The worker does the bulk, you keep the judgement.

Adapted from [TolongLabs/claude-fanout](https://github.com/TolongLabs/claude-fanout), preserving its brief → isolated worker
→ parent verification workflow. This variant optimizes for observed Magicube **per-call** billing rather than
OpenRouter's per-token pricing. It is an independent community skill, not an official ModelScope product.

## What It Does

- Runs headless Claude Code against an existing local CLIProxyAPI ModelScope provider.
- Bundles related small files into one brief; defaults to eight turns and a ten-minute timeout.
- Supports independent background workers with separate directories and logs; start with two, ceiling six.
- Restricts tools to Read/Edit/Write/Glob/Grep. The parent runs shell commands, tests and git.
- Validates provider routing and reports failures without falling back to another provider.

## Quick Start

Requires Linux/macOS, Python 3 with PyYAML, Claude Code and a running CLIProxyAPI with a ModelScope provider.
The initial tests used Linux. macOS has not been tested. Managed Claude Code policies still apply.

```bash
git clone https://github.com/TolongLabs/modelscope-fanout ~/.claude/skills/modelscope-fanout
python3 -c 'import yaml'
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py --list
```

If PyYAML is missing, install your OS's `python3-yaml` package or use a virtual environment:

```bash
python3 -m venv ~/.modelscope-fanout-python
~/.modelscope-fanout-python/bin/pip install 'PyYAML>=6,<7'
```

Use that environment's Python instead of `python3` in the examples. The skill is available globally as
`/modelscope-fanout` once Claude Code refreshes its skill inventory; restart if it is not listed.

Example request:

```text
/modelscope-fanout Transform these related files as one bundled job using ms-qwen3.5-122b.
Use one worker, at most eight turns, and verify the results yourself.
```

### Existing Proxy Setup

The helper reads `~/.cli-proxy-api/config.yaml` (override with `--config`). It does not install, restart, rewrite or revoke
anything in your proxy. Start CLIProxyAPI with its normal service command before running `--list`.

Your local configuration must contain a provider named `modelscope` under `openai-compatibility`, with
`base-url: https://api-inference.modelscope.ai/v1`, a valid upstream key and unique model aliases. The local proxy must
require an API token through `api-keys`. Keep both credentials private. Example model mapping, **without credentials**:

```yaml
models:
  - name: Qwen/Qwen3.5-122B-A10B
    alias: ms-qwen3.5-122b
  - name: Qwen/Qwen3-Coder-30B-A3B-Instruct
    alias: ms-qwen3-coder
```

The helper accepts only configured aliases also reported as owned by ModelScope in the live proxy catalog. It rejects
ambiguous configured provider aliases. This is preflight validation, not a security guarantee against a proxy being
reconfigured concurrently or other undocumented routing behavior. Keep the shared proxy configuration stable during runs.

## Dispatch

Prepare an isolated worktree for edits to a git repository, or a disposable directory for standalone outputs. Resolve
all instructions in the parent and put exact expected output into the brief. Do not rely on auto-loading `AGENTS.md` or
`CLAUDE.md`; the initial live test did not reliably honor an on-disk casing rule.

```bash
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
  --cwd "$WORKTREE" \
  --brief "$BRIEF" \
  --log "$LOG" \
  --model ms-qwen3.5-122b \
  --max-turns 8 \
  --timeout 600
```

Each run needs a new log path outside the worktree. JSON and stderr are separate; private logs are created with restrictive
permissions. `--analysis` disables tools for answers from supplied context. Run `--help` for all options.

For parallel work, launch independent commands together through background Bash tools, each with its own brief, log and
worktree. Await completion notifications. Do not launch tiny workers simply because parallelism is available. Never give
two workers overlapping output ownership. Dependency chains stay sequential.

## Call Economics

| Item                    | Meaning                                                 |
| ----------------------- | ------------------------------------------------------- |
| Standard                | Observed at 1 Magicube per billed inference call        |
| Flagship                | Observed at 2 Magicubes per billed inference call       |
| One worker              | Can make multiple upstream calls                        |
| One turn                | Not a guaranteed upstream-call count                    |
| Eight-turn allowance    | Behavioral limit, not an eight-Magicube spending cap    |
| Claude `total_cost_usd` | Not authoritative provider billing; ignore it           |
| Balance and rewards     | Account-specific; not queried or promised by this skill |

For a hypothetical ten upstream calls, Standard costs ten Magicubes and Flagship twenty. Do not infer calls from file
count or user-message count. Provider/harness retries and other requests can change actual usage. The launcher does not
redispatch automatically, but it does not disable all internal CLI/proxy retries.

Larger relevant briefs can avoid discovery calls. Context windows, output limits, latency, accuracy and rate limits still
matter. Prompt length is **not unlimited**. A smaller model does not save Magicubes within the same tier if it needs the
same number of calls. Pick the model that completes the task correctly with fewer round trips.

Actual spending must come from [ModelScope Usage](https://www.modelscope.ai/magicube/usage?tab=consume). Do not publish
account screenshots or credentials with worker results. Daily reward eligibility, expiry and allocation order remain
outside this skill's guarantees.

## Model Evidence

The configured aliases below were observed locally on 2026-09-10; this is not a universal catalog or endorsement.

| Alias                | Evidence And Limitations                                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `ms-qwen3-coder`     | Prior individual Standard billing evidence; live file writes work, but instruction/path failures occurred in this skill's tests |
| `ms-qwen3.5-122b`    | Default: passed exact-output smoke and two simultaneous multi-file workers; individual billing tier not established             |
| `ms-qwen3.5-397b`    | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |
| `ms-deepseek-v4-pro` | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |
| `ms-glm-5.2`         | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |
| `ms-qwen3.8-27b`     | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |
| `ms-glm-4.7-flash`   | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |
| `ms-step-3.5-flash`  | Direct inference previously succeeded; individual tier and headless tool compatibility unverified                               |

Use a bounded exact-output smoke test for a new model before bulk dispatch. `GLM-5.3-Flash` hub-card existence did not
establish inference access in earlier probes. Do not use a dead Ambassador mapping as a silent substitute.

## Safety And Verification

The helper clears inherited provider/model environment overrides, sets model aliases explicitly, uses a separate
`~/.modelscope-fanout` config directory, disables hooks, excludes project/local/user settings sources, and restricts MCP
and tools. It does **not** use `bypassPermissions`. It does not copy the upstream ModelScope key to the worker environment.

**A worktree and a separate config directory are not an OS sandbox.** A worker with filesystem tools can see permitted
files outside its task. Only dispatch trusted inputs, never include secrets, and use OS isolation when needed. Instruction
files, managed policy and future CLI changes can affect behavior. Removing settings does not imply every possible
customization is absent on every Claude Code version.

A success status means the harness returned success without recorded denials, **not that the task is correct**. Parent
verification is mandatory:

1. Inspect result JSON, `is_error`, `permission_denials` and turn count.
2. Read the diff and unexpected-file list; verify exact output contracts.
3. Run parent-owned tests. Do not trust only worker-written tests.
4. Fix small defects locally; reconsider model or brief before rerunning a failed chunk.

Exit 124 means timeout. Exit 1 means invalid/error JSON, a denial or another worker failure. Exit 2 means setup/validation
failure. Other nonzero worker exits are preserved. Review partial outputs in all failure cases. The helper intentionally
does not print worker content or raw provider errors into the parent's terminal.

## Tests And Current Status

```bash
python3 -m unittest discover -s ~/.claude/skills/modelscope-fanout/tests -v
```

Offline routing/environment/result tests pass. Live ModelScope catalog validation passes. The coder produced files,
but initial exact-content tests failed and later attempts guessed home-directory paths; permission checks blocked those
writes. A revised launcher now supplies the actual directory explicitly. The behavioral budget test improved grouping
and rejected a turn-to-Magicube guarantee, but both tested models still invented numerical task estimates or lower bounds.
Budget reasoning is therefore **not delegated**: the launcher's summary always says `Magicubes=unmeasured`, and the parent
must disregard worker cost claims. These tests do not establish reliable autonomous operation or large-code-task quality.

Raw test logs remain local because they contain machine paths and session identifiers. No account balance or credentials
are published. The revised launcher with `ms-qwen3.5-122b` passed one exact-output smoke test in two turns and two simultaneous
multi-file workers in three turns each, with no permission denials or extra files. A Read → Edit test also passed in three turns, preserving the untargeted content exactly. These are small smoke tests,
not evidence for large edits, full coding tasks, six-worker saturation or model-specific effort handling.

## Contributing

Issues and pull requests are welcome. Keep changes focused on the original headless-worker workflow. Do not add
credentials, generated sessions or private proxy configs. Test provider isolation and actual outputs, not just exit codes.

## Licence

[MIT](LICENSE). Copyright 2026 TolongLabs. Derived from [Claude Fan-Out](https://github.com/TolongLabs/claude-fanout).
