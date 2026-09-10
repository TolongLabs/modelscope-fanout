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
     --model Qwen/Qwen3.8-27B \
     --max-turns 8 \
     --timeout 600
   ```

   Or ask Claude Code to prepare and supervise the work:

   ```text
   /modelscope-fanout Bundle these related changes into one worker using Qwen/Qwen3.8-27B, then verify the results.
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

**`Qwen/Qwen3.8-27B` is the default**, chosen for strong published coding performance, a passing local headless editing
test and a user-reported rate of **1 Magicube per call**. That rate was not independently measured in this comparison;
it is **not a proven Magicube-efficiency winner**. Honor an explicitly selected model; never silently substitute another.

Select upstream API IDs directly; no `cc` launcher or custom alias names are required. The launcher resolves an existing
proxy alias internally when necessary. `--list` prints upstream IDs with validated live ModelScope routes.
Availability and entitlement can change; run it before dispatch.

| ModelScope ID                                                                                   | Published Coding Evidence                                                           | Local Headless Result                                            |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [`Qwen/Qwen3.5-122B-A10B`](https://huggingface.co/Qwen/Qwen3.5-122B-A10B)                       | SWE-bench Verified 72.0; Terminal Bench 2: 49.4                                     | Pass; 5 reported turns                                           |
| [`Qwen/Qwen3-Coder-30B-A3B-Instruct`](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) | SWE-bench Verified 51.60 with OpenHands, per [SWE-bench](https://www.swebench.com/) | Pass; 5 turns. Earlier instruction/path failures remain relevant |
| [`Qwen/Qwen3.5-397B-A17B`](https://huggingface.co/Qwen/Qwen3.5-397B-A17B)                       | SWE-bench Verified 76.4; Terminal Bench 2: 52.5                                     | Pass; 5 turns                                                    |
| [`deepseek-ai/DeepSeek-V4-Pro-0813`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813)   | Terminal Bench 2.1: 87.9; NL2Repo 61.5                                              | Output mismatch: omitted required final newline; 5 turns         |
| [`zai-org/GLM-5.2`](https://huggingface.co/zai-org/GLM-5.2)                                     | SWE-bench Pro 62.1; Terminal Bench 2.1: 81.0 with Terminus-2                        | Pass; 5 turns                                                    |
| [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B)                                   | SWE-bench Pro 61.7; Terminal Bench 2.1: 73.0 with Terminus                          | Pass; 5 turns                                                    |
| [`zai-org/GLM-4.7-Flash`](https://huggingface.co/zai-org/GLM-4.7-Flash)                         | SWE-bench Verified 59.2; LiveCodeBench v6: 64.0                                     | Timed out at 180 seconds; no completed result                    |
| [`stepfun-ai/Step-3.5-Flash`](https://huggingface.co/stepfun-ai/Step-3.5-Flash)                 | SWE-bench Verified 74.4; Terminal-Bench 2.0: 51.0                                   | Pass; 5 turns                                                    |

Sources checked on 2026-09-10. Scores are published results, not independently reproduced here. SWE-bench Verified and
Pro are different evaluations; Terminal-Bench versions, harnesses, reasoning budgets and context management also differ.
The Coder score was visible in the official leaderboard's search index, not its fetched dynamic table. These numbers
are not one comparable leaderboard and do not establish the hosted endpoint's revision or reasoning configuration.

Qwen3.8-27B's published SWE-bench Pro result is close to GLM-5.2's, while GLM has a higher published Terminal Bench score.
Both passed the local output checks with five reported turns. There is no measured reduction in charged calls to justify
preferring GLM if its per-call rate is higher; GLM remains an explicitly selectable alternative, with its tier unverified.
One small trial per model cannot rank reliability or real-world coding quality.

DeepSeek's higher published Terminal Bench score uses a different harness; its missing newline is a small local defect,
not proof of general inferiority. All seven completed local runs reported five turns, so this test establishes no
call-efficiency advantage.

Add a missing model under the existing `modelscope` provider's `models` list, without changing credentials:

```yaml
models:
  - name: Qwen/Qwen3.8-27B
```

An optional `alias` remains supported for existing proxy configurations. No proxy configuration is rewritten by the
launcher. Only routes assigned to ModelScope in both configuration and the live catalog are eligible.

Standard inference was observed at **1 Magicube per call**, Flagship at **2**. Individual Standard billing evidence
exists for `Qwen/Qwen3-Coder-30B-A3B-Instruct`; the other models' tiers, including the default's, remain unverified.
Measure total Magicubes across attempts and repairs divided by accepted tasks. At equal quality, a 2-Magicube model
must use fewer than half as many charged calls as a 1-Magicube model to be cheaper; exactly half ties.
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
- **Small Tests Do Not Prove Every Task.** Large code changes and model-specific effort handling still need bounded
  acceptance tests and parent review. Published benchmark scores do not establish cost efficiency on this harness.

## Under the Hood

Every worker is one command, and every failure shows up around it:

<details>
<summary><b>The Dispatch Command</b></summary>

```bash
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
  --cwd "$WORKTREE" --brief "$BRIEF" --log "$LOG" \
  --model Qwen/Qwen3.8-27B --max-turns 8 --timeout 600
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

**18 offline tests passed**, covering upstream-ID selection, the default, optional aliases, routing, environment
isolation, logs, denials, errors and timeouts.

On 2026-09-10, all eight models received the same brief: read two inputs, edit one state line while preserving other
bytes, and create an uppercase labels file with a final newline. Each run allowed six turns and 180 seconds; two ran
at a time, without automatic redispatch. Parent assertions checked exact file bytes, input preservation and file names.
The test used existing proxy routes; the model table records each outcome.

Six passed all output checks. DeepSeek completed but omitted the final newline. GLM-4.7-Flash timed out without a
completed JSON result; no cause is established. All seven completed runs reported five turns and no permission denials.
That does not prove five charged calls or actual tool batching. Test spending was not measured, and no matched
light-prompt versus context-rich-prompt billing comparison was performed. After the launcher change, a separate smaller
GLM-5.2 test using the default upstream-ID selection passed exact Edit/Write and file-preservation checks in four
reported turns, without denials. After selecting Qwen3.8-27B as the default, the same smaller test also passed in four
reported turns with exact outputs and no denials. Existing shared proxy configuration was unchanged; alias-free routing
was tested offline.

Earlier `Qwen/Qwen3.5-122B-A10B` checks passed exact-output creation in two turns, two simultaneous multi-file workers
in three turns each, and Read → Edit in three turns with untargeted content preserved. Earlier Coder instruction/path
failures are not erased by its latest pass. These are smoke tests, not broad coding or reliability benchmarks.
Raw logs remain local; never publish credentials, account screenshots or private session details with test results.

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
