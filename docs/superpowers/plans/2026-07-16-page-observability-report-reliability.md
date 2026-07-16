# Page Observability Report Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make page-observability-report produce traceable, comparable page metrics and reliable fallback behavior across ambiguous pages, shared pages, and partial platform failures.

**Architecture:** Keep `SKILL.md` as the workflow router and completion gate. Move repository resolution rules and metric semantics into focused references, then add scenario-based evals that compare the revised skill with a snapshot of the current version.

**Tech Stack:** Markdown Agent Skills, JSON eval fixtures, shell validation with `rg`, `python3 -m json.tool`, and repository diff checks.

## Global Constraints

- Prioritize actual query success and metric-definition reliability over HTML renderer automation.
- Default time range is the previous 30 complete calendar days in `Asia/Shanghai`, excluding the current day.
- Never infer UV from PV or infer TTI from LCP, FCP, or FP.
- Preserve per-`bid` results; do not sum non-additive metrics.
- Do not build a full bytedcli query wrapper or handle platform authorization automatically.
- Keep the skill under `internal-skills/`; do not advertise remote installation.
- Do not modify third-party skill descriptions or unrelated user changes.

---

### Task 1: Capture the baseline and add failing reliability evals

**Files:**
- Create: `internal-skills/page-observability-report/evals/evals.json`
- Create: `internal-skills/page-observability-report-workspace/skill-snapshot/SKILL.md`
- Create: `internal-skills/page-observability-report-workspace/skill-snapshot/references/report-spec.md`

**Interfaces:**
- Consumes: current `SKILL.md` and `references/report-spec.md`
- Produces: immutable old-skill baseline and eval records with `id`, `prompt`, `expected_output`, `files`, and `assertions`

- [ ] **Step 1: Snapshot the old skill before changing it**

Run:

```bash
mkdir -p internal-skills/page-observability-report-workspace/skill-snapshot/references
cp internal-skills/page-observability-report/SKILL.md internal-skills/page-observability-report-workspace/skill-snapshot/SKILL.md
cp internal-skills/page-observability-report/references/report-spec.md internal-skills/page-observability-report-workspace/skill-snapshot/references/report-spec.md
```

Expected: snapshot files are byte-identical to the current skill files.

- [ ] **Step 2: Write scenario evals that expose current gaps**

Create `evals/evals.json` with six records:

```json
{
  "skill_name": "page-observability-report",
  "evals": [
    {
      "id": 1,
      "prompt": "达人详情页来自 fe-buyin/global/pages，并同时挂载到机构、达人、小店三端。请给出查询口径和报告结构。",
      "expected_output": "Uses all three query_bids, preserves per-bid values, and does not sum non-additive metrics.",
      "files": [],
      "assertions": [
        "Names buyin_jigou, buyin_daren, and buyin_shop as separate query_bids.",
        "Does not sum LCP, FCP, FP, time spent, error rate, or 2-second rate.",
        "Marks the overview partial when only some bids succeed."
      ]
    },
    {
      "id": 2,
      "prompt": "移动端选品入口会跳到另一个 H5 工程。宿主页和目标页都有 bid，请确定该查哪个页面。",
      "expected_output": "Follows the jump to the target project and queries the target runtime_path and bid.",
      "files": [],
      "assertions": [
        "Uses target-project runtime_path and bid.",
        "Does not query the target page with the host-page bid."
      ]
    },
    {
      "id": 3,
      "prompt": "仓库里搜到两个互不相关但都叫数据看板的页面，现在帮我直接查页面指标。",
      "expected_output": "Lists candidates and asks for disambiguation instead of choosing one.",
      "files": [],
      "assertions": [
        "Distinguishes independent candidates from shared mounts.",
        "Stops for user confirmation before querying metrics."
      ]
    },
    {
      "id": 4,
      "prompt": "页面只能确认 route_path，runtime_path 没找到。继续查询并说明可信度。",
      "expected_output": "Uses the documented fallback order and records match mode and uncertainty.",
      "files": [],
      "assertions": [
        "Attempts exact runtime path, confirmed URL keyword, then route path in order.",
        "Records filter_match_mode and does not invent runtime_path."
      ]
    },
    {
      "id": 5,
      "prompt": "三端页面中机构端查询成功，达人端超时，小店端无权限。请组织结果。",
      "expected_output": "Keeps the successful bid and gives distinct failures for the other bids.",
      "files": [],
      "assertions": [
        "Keeps successful data instead of failing the whole page.",
        "Distinguishes timeout from permission failure.",
        "Marks aggregate status partial."
      ]
    },
    {
      "id": 6,
      "prompt": "请查最近30天的 LCP、UV、JS Error 和2秒开率；UV和2秒开率接口没有返回。",
      "expected_output": "Uses complete-day Asia/Shanghai boundaries, p75 LCP, explicit JS error type, and no fabricated UV or rate.",
      "files": [],
      "assertions": [
        "Defines the previous 30 complete calendar days in Asia/Shanghai and excludes today.",
        "Uses p75 for LCP unless the source only exposes another named aggregation.",
        "Separates JS error event count from affected users and only computes a rate with a same-source denominator.",
        "Does not infer UV from PV or TTI from LCP, FCP, or FP."
      ]
    }
  ]
}
```

- [ ] **Step 3: Validate the eval file**

Run:

```bash
python3 -m json.tool internal-skills/page-observability-report/evals/evals.json >/dev/null
```

Expected: exit code `0`.

- [ ] **Step 4: Document baseline failures**

Run each prompt once against `page-observability-report-workspace/skill-snapshot` and save responses in these directories:

```text
iteration-1/shared-three-bids/old_skill/outputs/response.md
iteration-1/external-h5-target/old_skill/outputs/response.md
iteration-1/ambiguous-page-name/old_skill/outputs/response.md
iteration-1/runtime-path-fallback/old_skill/outputs/response.md
iteration-1/partial-bid-failure/old_skill/outputs/response.md
iteration-1/metric-definition-fallback/old_skill/outputs/response.md
```

Expected: at least the aggregation/time-boundary/provenance assertions fail against the snapshot, proving the evals discriminate.

- [ ] **Step 5: Commit the eval definitions if the internal directory is tracked; otherwise record local-only status**

Run:

```bash
git check-ignore -v internal-skills/page-observability-report/evals/evals.json || true
```

Expected: if ignored, do not force-add it; mention that the eval remains local-only.

### Task 2: Extract repository resolution rules and tighten page disambiguation

**Files:**
- Create: `internal-skills/page-observability-report/references/repo-resolution-rules.md`
- Modify: `internal-skills/page-observability-report/SKILL.md`

**Interfaces:**
- Consumes: `page_clue`, repository search evidence, and `query-page-metrics-from-code`
- Produces: confirmed or unresolved page context with `primary_bid`, `query_bids`, and proof

- [ ] **Step 1: Confirm the old skill fails the dependency-name check**

Run:

```bash
rg -n 'query_page_metrics_from_code' internal-skills/page-observability-report/SKILL.md
```

Expected: one match, demonstrating the incorrect dependency name.

- [ ] **Step 2: Write repository-specific resolution reference**

Create `references/repo-resolution-rules.md` with sections for:

```markdown
# Repository Resolution Rules

## Candidate classification

- Treat multiple package mounts of one shared page as one page with multiple query bids.
- Treat files with only a similar name but different route and behavior as independent candidates.
- For independent candidates, present page file, route, package, and bid evidence and wait for user confirmation.

## fe-buyin

- Resolve `global/pages` through every mounting router and package config.
- If the resolved primary bid is `buyin_jigou`, `buyin_daren`, or `buyin_shop`, set query bids to all three and query them separately.
- Keep per-bid results even when the user also requests an overall scale.

## fe-alliance-mobile

- Inspect `openSchema`, `pageUrl`, jump helpers, and H5 URL templates instead of treating a source directory as the runtime path.
- When an entry redirects to another project, use the target project's runtime path and config bid.
- Do not query a target page with the host page's bid.
```

- [ ] **Step 3: Reduce SKILL.md to the shared resolution state machine**

Replace the duplicated repository sections with an explicit resource route:

```markdown
Before resolving `fe-buyin` or `fe-alliance-mobile`, read `references/repo-resolution-rules.md` and apply only the matching repository section.
```

Correct the dependency name to `query-page-metrics-from-code` and require it whenever `path`, `bid`, or `app_id` is not confirmed.

- [ ] **Step 4: Verify routing and disambiguation text**

Run:

```bash
rg -n 'query-page-metrics-from-code|independent candidates|repo-resolution-rules' internal-skills/page-observability-report/SKILL.md internal-skills/page-observability-report/references/repo-resolution-rules.md
```

Expected: all three concepts appear; the underscore dependency name has no matches.

### Task 3: Define time, metric, provenance, and multi-bid contracts

**Files:**
- Create: `internal-skills/page-observability-report/references/metric-contract.md`
- Modify: `internal-skills/page-observability-report/SKILL.md`
- Modify: `internal-skills/page-observability-report/references/report-spec.md`

**Interfaces:**
- Consumes: confirmed page context plus platform results
- Produces: one metric result per `bid` with traceability and typed failure state

- [ ] **Step 1: Write the metric contract**

Create `references/metric-contract.md` defining:

```markdown
# Metric Contract

## Default time range

Use the previous 30 complete calendar days in `Asia/Shanghai`; exclude the current day. Record explicit start and end timestamps.

## Result fields

For every metric and bid record metric, bid, value, unit, status, start_at, end_at, timezone, include_current_day, aggregation, filter_match_mode, source, retrieved_at, query_evidence, error_code, and failure_reason.

## Default aggregations

- PV: total page-view events.
- UV: distinct users from a stable user identifier; never derive from PV.
- LCP/FCP/FP: p75 unless the platform exposes only another explicitly named aggregation.
- Page Time Spent: platform mean with sample definition.
- JS Error: keep event count and affected-user count separate; calculate a rate only with a same-source denominator.
- 2-second rate: same-source `tti < 2000 / total tti samples`; never infer tti from LCP/FCP/FP.

## Multi-bid semantics

Preserve one result per bid. Sum only additive metrics when user requests it and overlap assumptions are explicit. Never sum percentiles, durations, or rates.

## Failure taxonomy

Use distinct reasons for permission_denied, timeout, platform_unstable, field_unavailable, and definition_unresolved.
```

- [ ] **Step 2: Route metric queries through the contract**

In `SKILL.md`, require reading `metric-contract.md` before querying and keep only the high-level order: query per bid, probe capabilities, classify failures, generate report.

- [ ] **Step 3: Align the report spec**

Update `report-spec.md` so that:

- The page has nine explicitly numbered sections, including the final methodology section.
- Multi-bid overview cards show per-bid values or a range/list, never a fabricated single value.
- Every metric row contains time range, aggregation, match mode, source, retrieval time, status, and failure detail.
- UI labels map `success`, `partial`, and `failed` to `成功`, `部分成功`, and `失败`.

- [ ] **Step 4: Verify forbidden inference and required provenance**

Run:

```bash
rg -n 'Asia/Shanghai|p75|filter_match_mode|query_evidence|permission_denied|never infer|禁止.*反推' internal-skills/page-observability-report
```

Expected: all contract concepts are present in the focused reference or report spec.

### Task 4: Update local usage documentation

**Files:**
- Modify: `internal-skills/README.md`

**Interfaces:**
- Consumes: final skill dependencies and local-only publishing boundary
- Produces: accurate local invocation and maintenance instructions

- [ ] **Step 1: Add dependency and invocation guidance**

Document that the skill depends on:

```markdown
- `query-page-metrics-from-code` for page and bid resolution
- `bytecli` for ByteDance internal platform queries
- `team-pitfalls` when an external wiki root is configured; otherwise record the skipped pre-check and continue
```

Include one example request:

```text
根据“达人详情页”从代码反查真实路径和 query_bids，查询最近 30 个完整自然日的页面指标，并生成 HTML 报告。
```

- [ ] **Step 2: State the installation boundary accurately**

Explain that `internal-skills/` is excluded locally and cannot be installed from the public repository. Do not add an `npx skills add ...@page-observability-report` command.

- [ ] **Step 3: Verify README does not claim remote availability**

Run:

```bash
rg -n 'page-observability-report|query-page-metrics-from-code|仅限本地|不能.*远程安装' internal-skills/README.md
```

Expected: usage and local-only boundaries are present.

### Task 5: Run revised evals and complete verification

**Files:**
- Create: `internal-skills/page-observability-report-workspace/iteration-1/shared-three-bids/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/external-h5-target/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/ambiguous-page-name/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/runtime-path-fallback/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/partial-bid-failure/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/metric-definition-fallback/{with_skill,old_skill}/outputs/response.md`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/*/{with_skill,old_skill}/grading.json`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/benchmark.json`
- Create: `internal-skills/page-observability-report-workspace/iteration-1/benchmark.md`

**Interfaces:**
- Consumes: revised skill, baseline snapshot, and `evals/evals.json`
- Produces: evidence that the revised skill improves the selected reliability assertions

- [ ] **Step 1: Run all six prompts against the revised skill**

Save one response per eval beneath the matching `with_skill/outputs/` directory.

Expected: every response applies the revised contracts without inventing live metric values.

- [ ] **Step 2: Grade both versions**

For each run, create `grading.json` using the required shape:

```json
{
  "expectations": [
    {
      "text": "Assertion text copied from evals.json",
      "passed": true,
      "evidence": "Exact response evidence or missing behavior"
    }
  ]
}
```

Expected: the revised skill passes all safety and reliability assertions; the old snapshot fails at least the known time/provenance/aggregation assertions.

- [ ] **Step 3: Aggregate benchmark results**

Run:

```bash
python3 /Users/bytedance/.agents/skills/skill-creator/scripts/aggregate_benchmark.py \
  internal-skills/page-observability-report-workspace/iteration-1 \
  --skill-name page-observability-report
```

Expected: `benchmark.json` and `benchmark.md` compare `with_skill` before `old_skill` and show a positive pass-rate delta.

- [ ] **Step 4: Run structural checks**

Run:

```bash
python3 -m json.tool internal-skills/page-observability-report/evals/evals.json >/dev/null
rg -n 'query_page_metrics_from_code' internal-skills/page-observability-report && exit 1 || true
git diff --check
wc -l internal-skills/page-observability-report/SKILL.md
```

Expected: JSON is valid, old dependency name is absent, diff check passes, and `SKILL.md` remains below 500 lines.

- [ ] **Step 5: Review team pitfalls and repository scope**

Confirm whether the work revealed a new reusable pitfall not already covered by P-041/P-042. Also run:

```bash
git status --short
```

Expected: unrelated `.gitignore` and `docs/team-pitfalls-group-share.md` changes remain untouched; internal files may remain ignored by design.

- [ ] **Step 6: Commit tracked documentation changes only**

```bash
git add docs/superpowers/plans/2026-07-16-page-observability-report-reliability.md
git commit -m "docs: plan page observability reliability improvements"
```

Expected: the plan commit contains no unrelated files.
