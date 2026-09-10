---
name: modelscope-fanout
description: Use when independent, well-specified work needs headless Claude Code workers on ModelScope through CLIProxyAPI, especially when Magicube per-call billing makes many small agent turns wasteful.
---

# ModelScope Fan-Out

The worker does the bulk; you keep the judgement. Adapted from [Claude Fan-Out](https://github.com/TolongLabs/claude-fanout).
Same headless harness, different economics: **maximize useful work per upstream call**, within model context/output limits.

## Preflight

Run `python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py --list`.
Only models with live routes in the local `modelscope` provider qualify. Select upstream API IDs; the launcher resolves
optional existing proxy aliases internally, without any `cc` dependency. Missing route/auth means stop; never silently fall back to
OpenRouter, OAuth or the Claude plan. Keys stay in the existing proxy config, never in briefs or logs.

Default to `Qwen/Qwen3.8-27B` if listed; honor a user-selected ModelScope upstream API ID. This cost-oriented choice
combines strong published coding results with a passing local editing test; its 1-Magicube rate is user-reported,
not independently measured here. See README for benchmark sources, billing caveats and local results. A new route needs a bounded tool-edit smoke test before bulk work; catalog membership is not compatibility.

## Budget And Grouping

| Decision                       | Default                                                    |
| ------------------------------ | ---------------------------------------------------------- |
| Related small files            | One bundled worker, not one worker per file                |
| Independent substantial chunks | Two workers; at most six concurrent                        |
| Turn allowance                 | Eight per worker; lower for simple tasks                   |
| Timeout                        | 600 seconds                                                |
| Retry                          | None by the launcher; diagnose before redispatch           |
| Permissions                    | Read/Edit/Write/Glob/Grep only; parent runs commands/tests |

Standard inference was observed at **1 Magicube/call**, Flagship at **2**. **Eight turns does not guarantee eight calls
or eight Magicubes.** Harness/proxy retries, ancillary requests and compaction can add calls. `num_turns` is not billing.
Use the provider usage page for actual spending; ignore Claude JSON `total_cost_usd`.
Budget reports have exactly these fields: **workers; turn allowance; tier evidence; measured upstream calls;
measured Magicubes**. If billing was not observed, the last two values are **unmeasured**. Do not add an estimated total,
maximum, worst case or task price based on turns, file count or bundling. Unknown model tiers stay **unverified**.
Daily rewards, expiry and spending order are not guaranteed by this skill.

## Brief Contract

Each brief contains, in order:

1. Owned output paths **and nothing else**; “do not run git”.
2. Goal and relevant source excerpts, or exact input paths plus a batched-read instruction. Exclude secrets.
3. Concrete transformation rules and content to preserve verbatim.
4. Acceptance criteria and one grouped edit/write pass where dependencies allow it.
5. Short final report: changes, limitations, guesses and denied operations.

Include relevant instructions from both `CLAUDE.md` and `AGENTS.md` explicitly; do not rely on auto-discovery. Resolve
conflicting examples before dispatch: give one authoritative expected output, not lowercase examples plus an uppercase
exception. Do not pad prompts
with entire repositories. Larger prompts reduce discovery turns, not context limits. Batch independent tool calls;
retain Read-before-Edit and necessary verification. Keep architecture, security decisions and ambiguous work yourself.

### A Call-Efficient Brief

Pack useful context, not tokens. Reuse relevant facts the parent already has; do not buy a separate reconnaissance
worker to rediscover them. Include exact input paths for anything still missing. Keep enough context/output headroom
for tool results and changes; split at coherent ownership boundaries when the whole job will not fit.

For a bounded multi-file change, the execution contract is:

1. Read missing inputs together where independent. Existing files still require Read before Edit.
2. Apply independent changes in a grouped pass where supported; preserve genuine read/edit dependencies.
3. Return one short completion report; the parent runs acceptance checks and reviews consequential changes.

For example, one worker can receive this whole brief instead of separate discovery, planning and per-file workers:

```text
Own state.txt and labels.txt, and nothing else. Do not run git or shell commands.
Read input.json and state.txt before editing; batch the two independent reads if supported.
In state.txt, replace only status=pending with status=complete using Edit. Preserve all other bytes.
Write labels.txt from input.json's labels array: uppercase, original order, one per line, final newline.
Do not change input.json. Batch the independent Edit and Write where supported.
Acceptance: exact preserved state.txt content apart from the replacement; correct labels; no extra files.
Return changed paths and denied operations only. The parent will check exact bytes.
```

A brief with this task and batching guidance produced six exact-output passes out of eight tested routes; it did not
establish minimum billed calls.
Seven completed runs still reported five turns. Requesting batching does not guarantee the model or harness batches.
Parallelism saves elapsed time, not necessarily Magicubes. Avoid plan-only workers, repeated discovery and tiny follow-up
prompts for facts already known, but retain verification: a wrong one-call answer is not efficient.

Choose by total measured Magicubes across all attempts and repairs per accepted task. Compare matched tasks and tools;
track failures as spending, not just successful runs. Unknown billing stays unmeasured. At equal quality, a model billed
at twice the per-call rate must use fewer than half as many charged calls to be cheaper. Benchmarks shortlist candidates;
they do not measure this workflow's call efficiency.

## Dispatch

Give each editing worker an isolated worktree or disposable directory. Never share output ownership.

```bash
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
  --cwd "$WORKTREE" --brief "$BRIEF" --log "$LOG" \
  --model Qwen/Qwen3.8-27B --max-turns 8 --timeout 600
```

Launch independent chunks together using background Bash calls; await completion notifications, not polling.
Use `--analysis` for tool-free responses from supplied context. Logs must be new paths outside the worktree.
The launcher isolates settings/MCP/hooks and routing; **it is not an OS sandbox**. Read [README.md](README.md) before setup
or permission changes. Never expose sensitive directories to untrusted workers.

## Verify And Report

Check exit status, JSON error/denial fields, actual diff and unexpected files. Parent runs tests and reads consequential
changes. Repair small defects yourself; redispatch only a substantially wrong chunk with a corrected brief.
Report model, workers, turns, verified outputs, corrections and **Magicubes unmeasured** unless billing was observed.
Budget reasoning belongs to the parent, not workers: both tested models invented numerical spending claims even after
reading this guidance. Disregard cost estimates in `.result`; the launcher summary keeps Magicubes unmeasured.

## Common Mistakes

Token-price comparisons, six tiny workers by default, automatic retries, treating a worktree as a security sandbox,
and claiming eight turns is an eight-Magicube cap all defeat this workflow. A smaller model is not cheaper within the
same per-call tier; choose the model that finishes correctly in fewer calls, not simply the largest or smallest one.
