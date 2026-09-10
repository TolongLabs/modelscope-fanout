![ModelScope Fan-Out](assets/modelscope-fanout-banner.png)

# ModelScope Fan-Out

![Claude Code skill](https://img.shields.io/badge/Claude_Code_skill-D97757?style=for-the-badge&logo=claude&logoColor=white)
![CLIProxyAPI](https://img.shields.io/badge/CLIProxyAPI-000000?style=for-the-badge)
![MIT licence](https://img.shields.io/badge/MIT_licence-blue?style=for-the-badge)

**Fan work out to headless Claude Code workers on ModelScope, up to six at once.**

> The worker does the bulk, you keep the judgement.

_Fan-out_ is dispatching many independent workers at once and reviewing what comes back.

## Table of Contents

<details>
  <summary>Expand</summary>
  <ol>
    <li><a href="#what-it-does">What It Does</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#which-model-to-use">Which Model to Use</a></li>
    <li><a href="#how-it-stays-safe">How It Stays Safe</a></li>
    <li><a href="#what-it-cannot-do">What It Cannot Do</a></li>
    <li><a href="#under-the-hood">Under the Hood</a></li>
    <li><a href="#go-deeper">Go Deeper</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#licence">Licence</a></li>
  </ol>
</details>

## What It Does

- **Headless Claude Code Workers on ModelScope.** Each worker is the full Claude Code agent in one directory,
  pointed at CLIProxyAPI so inference uses the configured ModelScope account.
- **You Write the Brief, It Writes the Files, You Review.** Supply the task, relevant repository instructions and
  exact output requirements upfront. The worker handles the bounded work; you check what comes back.
- **Fewer Calls, More Work per Brief.** ModelScope's observed inference tiers bill per call. Bundle related files
  into one worker rather than paying for repeated discovery across many small jobs.
- **Up to Six at Once.** Start with two independent workers, each with its own brief, log and worktree. Never let
  two workers write the same file.
- **A Real Harness.** The launcher provides a turn allowance, timeout, exit status and separate JSON and stderr logs.

If a task needs your judgement or your conversation context, you do not need this skill.

## Quick Start

1. **Check the Prerequisites.** You need Claude Code, a running CLIProxyAPI configured with a ModelScope provider,
   Python 3 with PyYAML, and Git for worktrees. The launcher was tested on Linux; macOS is untested.

   ```bash
   python3 -c 'import yaml'
   ```

   If PyYAML is missing, install your OS's `python3-yaml` package or use a virtual environment:

   ```bash
   python3 -m venv ~/.modelscope-fanout-python
   ~/.modelscope-fanout-python/bin/pip install 'PyYAML>=6,<7'
   ```

   Use that environment's Python instead of `python3` in the examples below.

1. **Clone Into the Global Skills Directory**, then restart Claude Code if the skill is not listed. It is available
   as `/modelscope-fanout` from then on.

   ```bash
   git clone https://github.com/TolongLabs/modelscope-fanout ~/.claude/skills/modelscope-fanout
   ```

1. **Bring the Proxy Up and Choose a Model.** Start CLIProxyAPI with your normal service command, then list the
   ModelScope models it serves. Only the `modelscope` provider in the local config counts. Never print either key.

   ```bash
   python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py --list
   ```

   The launcher reads `~/.cli-proxy-api/config.yaml`; use `--config` for another location. It expects the provider's
   base URL to be `https://api-inference.modelscope.ai/v1`, a valid upstream key and a local token under `api-keys`.
   It does not install, restart or modify your proxy.

1. **Dispatch Your First Worker.** Prepare an isolated worktree or disposable directory, write a brief with exact
   output paths and requirements, and choose a new log path outside that directory. Set `WORKTREE`, `BRIEF` and `LOG`
   to those paths before running:

   ```bash
   python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
     --cwd "$WORKTREE" \
     --brief "$BRIEF" \
     --log "$LOG" \
     --model ms-qwen3.5-122b \
     --max-turns 8 \
     --timeout 600
   ```

   Or ask Claude Code to prepare and supervise the work:

   ```text
   /modelscope-fanout Bundle these related changes into one worker using ms-qwen3.5-122b, then verify the results.
   ```

1. **Verify.** Read the JSON report, check the actual diff and unexpected files, and run the tests yourself. A successful
   worker exit does not prove its output is correct. Ignore `total_cost_usd` and any worker-generated spending estimate.

   ```bash
   python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print({k:r.get(k) for k in ("result","num_turns","is_error","permission_denials")})' "$LOG"
   git -C "$WORKTREE" status --porcelain
   git -C "$WORKTREE" diff --check
   git -C "$WORKTREE" diff
   ```

## Which Model to Use

Only configured aliases that the live proxy catalog identifies as ModelScope models are offered.
**`ms-qwen3.5-122b` is the default**: it passed exact-output creation, two simultaneous multi-file workers and a
Read → Edit test. Availability and entitlement can change; run `--list` before dispatch.

| ModelScope ID                       | Alias                | Notes                                                           |
| ----------------------------------- | -------------------- | --------------------------------------------------------------- |
| `Qwen/Qwen3.5-122B-A10B`            | `ms-qwen3.5-122b`    | **Default.** Passed bounded headless worker tests               |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | `ms-qwen3-coder`     | Coder-tuned; instruction and path failures occurred in testing  |
| `Qwen/Qwen3.5-397B-A17B`            | `ms-qwen3.5-397b`    | Direct inference tested; headless tool compatibility unverified |
| `deepseek-ai/DeepSeek-V4-Pro-0813`  | `ms-deepseek-v4-pro` | Direct inference tested; headless tool compatibility unverified |
| `zai-org/GLM-5.2`                   | `ms-glm-5.2`         | Direct inference tested; headless tool compatibility unverified |
| `Qwen/Qwen3.8-27B`                  | `ms-qwen3.8-27b`     | Direct inference tested; headless tool compatibility unverified |
| `zai-org/GLM-4.7-Flash`             | `ms-glm-4.7-flash`   | Direct inference tested; headless tool compatibility unverified |
| `stepfun-ai/Step-3.5-Flash`         | `ms-step-3.5-flash`  | Direct inference tested; headless tool compatibility unverified |

These mappings were checked on 2026-09-10, not asserted as a universal catalog. Add missing mappings under your existing
`modelscope` provider's `models` list, without changing its credentials. For the default:

```yaml
models:
  - name: Qwen/Qwen3.5-122B-A10B
    alias: ms-qwen3.5-122b
```

Standard inference was observed at **1 Magicube per call**, Flagship at **2**. Individual Standard billing evidence
exists for `ms-qwen3-coder`; the other models' individual tiers, including the default's, remain unverified.
Check actual spending on [ModelScope Usage](https://www.modelscope.ai/magicube/usage?tab=consume).

## How It Stays Safe

The launcher provides two modes and never enables `bypassPermissions`:

| Mode                        | Available Tools                  | Use When                                                                          |
| --------------------------- | -------------------------------- | --------------------------------------------------------------------------------- |
| `acceptEdits`               | Read, Edit, Write, Glob and Grep | **The default.** Bounded file work; the parent runs shell commands, tests and git |
| `default` with `--analysis` | None                             | Answering from the supplied brief without file access                             |

- **Give a Worker a `git worktree`, Never Your Checkout.** Each editing worker gets isolated output ownership.
  A worktree is not an OS sandbox; use only trusted inputs and keep sensitive files out of reach.
- **Say `do not run git` in Every Brief.** Name every permitted output path and say “and nothing else”.
- **Keep Routing and Credentials Separate.** The launcher clears inherited provider overrides, validates ModelScope
  aliases and passes only the local proxy token to the worker. Keep proxy configuration stable during runs; preflight
  cannot guarantee routing if another process changes the proxy afterward.
- **Isolate Worker Settings.** Workers use `~/.modelscope-fanout`, restricted tools, disabled hooks and restricted MCP
  configuration. User, project and local settings sources are excluded; managed policies still apply.

## What It Cannot Do

- **Turn Limits Are Not Billing Caps.** Eight turns does not guarantee eight upstream calls or eight Magicubes.
  Retries, ancillary requests and compaction can add calls. `num_turns` is not a billing record.
- **Worker Cost Estimates Are Not Reliable.** Both tested models invented numerical spending claims. Budget reasoning
  stays with the parent; the launcher reports `Magicubes=unmeasured` unless you separately check provider billing.
  Daily rewards, expiry and spending order are not guaranteed by this skill.
- **Long Prompts Are Not Unlimited.** Relevant context upfront can save discovery calls, but context windows, output
  limits, latency, accuracy and rate limits still apply. A smaller model does not save Magicubes within the same tier
  if it needs the same number of calls.
- **Six Concurrent Workers Is the Ceiling.** This is a workflow limit, not a tested six-worker throughput guarantee.
  Small related tasks belong in one bundled worker; dependent chunks run sequentially.
- **A Worker Has None of Your Context.** Include relevant `CLAUDE.md` and `AGENTS.md` instructions explicitly. Do not
  rely on auto-discovery, and resolve conflicting examples before dispatch.
- **Small Tests Do Not Prove Every Task.** Large code changes, model-specific effort handling and the unverified models
  still need bounded acceptance tests and parent review.

## Under the Hood

Every worker is one command, and every failure shows up around it:

<details>
<summary><b>The Dispatch Command</b></summary>

```bash
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
  --cwd "$WORKTREE" --brief "$BRIEF" --log "$LOG" \
  --model ms-qwen3.5-122b --max-turns 8 --timeout 600
```

- **The Brief Goes Through stdin.** The launcher reads the file and states the working directory explicitly before
  invoking `claude -p`. Credentials never appear in the command arguments or brief.
- **Logs Stay Separate.** JSON goes to `LOG`, stderr to `LOG.stderr`, with restrictive permissions. Existing logs are
  never overwritten. Keep both outside the worktree and out of version control.
- **The Timeout Stops the Worker.** The default is 600 seconds. Exit 124 means timeout; review partial files before
  deciding whether another run is needed.
- **Eight Turns Is the Default Allowance.** Lower it for simple tasks; increase it deliberately for a larger bounded
  brief. The launcher does not redispatch, but internal CLI and proxy retries can still occur.
- **Independent Workers Run Together.** Launch separate background commands with non-overlapping worktrees and wait
  for completion notifications rather than polling.

Run `worker.py --help` for the full argument list.

</details>

<details>
<summary><b>Failure Modes</b></summary>

| Symptom                                          | Cause And Fix                                                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Exit 2 during preflight                          | Missing or invalid config, auth or live route. Check the local ModelScope provider; no fallback is attempted   |
| Exit 124                                         | Timeout. Review partial files and private stderr before retrying                                               |
| Exit 1 after a zero-exit worker                  | Invalid result JSON, a reported error or permission denial. Inspect the logs and actual outputs                |
| `permission_denials` is non-empty                | The worker attempted an unavailable operation or an incorrect path. Correct the brief or do that step yourself |
| Files exist but contents are wrong               | The worker's report is not verification. Compare exact output requirements and fix the defect                  |
| Model appears in the catalog but inference fails | Catalog membership does not establish entitlement. Run a bounded smoke test before bulk work                   |
| Worker reports a Magicube estimate               | Ignore it. Use observed provider billing, not model-generated arithmetic or Claude's USD estimate              |

Other nonzero worker exits are preserved. The launcher prints neither raw provider errors nor worker content into the
parent's terminal; inspect private logs deliberately.

</details>

<details>
<summary><b>Verification</b></summary>

```bash
python3 -m unittest discover -s ~/.claude/skills/modelscope-fanout/tests -v
```

**14 offline tests passed**, covering routing, environment isolation, logs, denials, errors and timeouts.
Live `ms-qwen3.5-122b` checks passed an exact-output creation test in two turns, two simultaneous multi-file workers
in three turns each, and a Read → Edit test in three turns with untargeted content preserved. The parallel workers
produced no extra files or permission denials. Test spending was not measured.

These are bounded smoke tests, not evidence for large tasks or every model. Raw logs remain local; never publish
credentials, account screenshots or private session details with test results.

</details>

## Go Deeper

| Read                                     | When                                                                               |
| ---------------------------------------- | ---------------------------------------------------------------------------------- |
| [`SKILL.md`](SKILL.md)                   | You are preparing a brief: grouping, budgets, dispatch, verification and reporting |
| [`scripts/worker.py`](scripts/worker.py) | You need the provider validation, isolation or dispatch implementation             |
| [`tests/`](tests/)                       | You are checking launcher behavior before changing it                              |

## Contributing

Issues and pull requests are welcome.

## Licence

[MIT](LICENSE). Copyright 2026 TolongLabs.
