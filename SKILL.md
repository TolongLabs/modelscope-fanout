---
name: modelscope-fanout
description: Use when independent, well-specified work needs headless Claude Code workers on ModelScope through CLIProxyAPI, especially when Magicube per-call billing makes many small agent turns wasteful.
---

# ModelScope Fan-Out

The worker does the bulk; you keep the judgement. Adapted from [Claude Fan-Out](https://github.com/TolongLabs/claude-fanout).
Same headless harness, different economics: **maximize useful work per upstream call**, within model context/output limits.

## Preflight

Run `python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py --list`.
Only live aliases in the local `modelscope` provider qualify. Missing route/auth means stop; never silently fall back to
OpenRouter, OAuth or the Claude plan. Keys stay in the existing proxy config, never in briefs or logs.

Default to `ms-qwen3.5-122b` if listed; honor a user-selected ModelScope alias. Other aliases require a bounded tool-edit
smoke test before bulk work. Catalog membership is not inference entitlement or agent compatibility.

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

## Dispatch

Give each editing worker an isolated worktree or disposable directory. Never share output ownership.

```bash
python3 ~/.claude/skills/modelscope-fanout/scripts/worker.py \
  --cwd "$WORKTREE" --brief "$BRIEF" --log "$LOG" \
  --model ms-qwen3.5-122b --max-turns 8 --timeout 600
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
