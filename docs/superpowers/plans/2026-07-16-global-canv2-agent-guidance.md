# Global canv2 Agent Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every new Codex root session inherit the complete canv2 role and workflow instructions.

**Architecture:** Copy the `developer_instructions` body from the existing personal custom-agent file into the personal global `~/.codex/AGENTS.md`. Preserve the source custom agent and any pre-existing global guidance, then verify both static equality and observable behavior in a fresh session.

**Tech Stack:** Codex global `AGENTS.md`, TOML source configuration, shell verification.

## Global Constraints

- Preserve the complete canv2 instruction body verbatim.
- Do not modify `~/.codex/agents/canv2.toml`.
- Preserve any pre-existing content in `~/.codex/AGENTS.md`.
- Do not modify repository-level `AGENTS.md` files.

---

### Task 1: Install and verify global canv2 guidance

**Files:**
- Read: `/Users/bytedance/.codex/agents/canv2.toml`
- Create or modify: `/Users/bytedance/.codex/AGENTS.md`

**Interfaces:**
- Consumes: the exact text inside the `developer_instructions = """..."""` block.
- Produces: global root-session instructions discovered by Codex through `/Users/bytedance/.codex/AGENTS.md`.

- [ ] **Step 1: Inspect the destination before changing it**

Run:

```bash
if test -f /Users/bytedance/.codex/AGENTS.md; then sed -n '1,260p' /Users/bytedance/.codex/AGENTS.md; else printf '__MISSING__\n'; fi
```

Expected: existing content, or exactly `__MISSING__`.

- [ ] **Step 2: Add the complete canv2 instructions**

Use `apply_patch` to create the destination when missing. If it exists, append a `# canv2 全局主会话规则` section without altering prior content. Copy every line between the TOML triple quotes in `/Users/bytedance/.codex/agents/canv2.toml`, including the `CAN：` prefix rule, `team-pitfalls` requirements, failure-record rules, minimal-change rules, test rule, clarification behavior, and delivery behavior.

- [ ] **Step 3: Verify static coverage**

Run a whitespace-preserving comparison that extracts the TOML multiline body and confirms every non-empty source line occurs in `/Users/bytedance/.codex/AGENTS.md`.

Expected: exit code `0` and `canv2 guidance complete`.

- [ ] **Step 4: Verify a fresh Codex root session**

Run:

```bash
codex exec -C /tmp "只回复一句简短问候。"
```

Expected: a Chinese response beginning with `CAN：`. If authentication or network access prevents the run, record that limitation and retain the successful static verification result.

- [ ] **Step 5: Confirm unrelated files remain unchanged**

Run:

```bash
git -C /Users/bytedance/Desktop/my/xiy-skills status --short
```

Expected: only the user's pre-existing workspace changes remain; the global file is outside this repository.
