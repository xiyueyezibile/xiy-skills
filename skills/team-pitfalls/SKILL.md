---
name: team-pitfalls
description: 所有非纯闲聊工程任务的分层团队知识前置检查与后置复盘 Skill。处理代码、仓库、领域上下文、技术方案、文档规范、经验沉淀或 AI 纠错时必须调用。
---

# Team Pitfalls

用外部 LLM Wiki 共享团队踩坑、跨仓库领域知识、仓库术语、仓库领域知识和 AI 纠错。上下文利用率优先通过固定层级提升：先读取仓库和领域索引简介，再按需打开具体 glossary、corrections 或 pitfalls 正文；不再把脚本摘要、query 召回和打分候选作为主流程。

## 快路径

每轮只保留两个固定步骤。

### 1. 前置检查

Skill 正文由平台触发时已经加载，不要再次 `cat SKILL.md`，也不要手工读取 `llms.txt` 或全量 `index.md`。立即运行：

```bash
python3 skills/team-pitfalls/scripts/begin_task.py \
  --task-id <稳定且无敏感信息的 ID> \
  --repo <repo-name> \
  --domain <domain-name>
```

- `--repo` 可选。
- `--domain` 可选且可重复；可单独用于全局领域级，也可配合 `--repo` 读取仓库领域级。
- `--query` 仅为兼容旧调用保留，只记录是否提供，不参与召回、打分或过滤。
- `begin_task.py` 只做 Wiki 基础校验、生命周期状态创建和导航入口返回，不读取正文生成条目摘要。
- 开始任务时先阅读返回的 repo/domain `index.md` 简介：仓库领域索引优先于全局领域索引，领域索引优先于仓库索引，仓库索引优先于全局通用坑位页面。
- 只有当索引简介、标题或任务线索相关时，才打开对应 `glossary.md`、`corrections.md` 或 `pitfalls/*.md` 正文。
- 如果知识属于某类业务、某个页面、某条业务链路或类似稳定范围，优先传一个或多个 `--domain`；不确定时先看 repo/domain 索引列表，再决定是否进入具体领域。
- 仓库领域级和全局领域级都相关时，优先采用仓库领域级；全局领域级可用于反向发现其他仓库同领域记录。
- 仓库级和全局级冲突时，优先采用仓库级。
- 实际采用后，调用 `record_pitfall_usage.py` 最小更新正文条目的 `使用次数`；只浏览未采用不计数。
- 不向用户复述完整预检过程，除非命中内容会改变方案或形成风险提示。

### 2. 后置复盘

任务完成后只判断本轮是否产生新的可迁移机制、仓库术语或用户纠错。

知识按 `--repo` 和 `--domain` 隔离判断是否已有：其他仓库或其他领域已有相同或相近记录，只能作为参考，不能当作当前仓库/领域“现有记录已覆盖”的理由。若本轮问题会在当前仓库领域复发，且当前仓库领域没有等价 `G-*`/`C-*`，必须优先写入 `repos/<repo-name>/domains/<domain-name>/glossary.md` 或 `repos/<repo-name>/domains/<domain-name>/corrections.md`。若该业务领域跨仓库复用，另写或更新 `domains/<domain-name>/glossary.md` 或 `domains/<domain-name>/corrections.md`。无法归属具体领域时才写入仓库级。

- 新增或更新知识条目时，默认调用 `upsert_pitfall.py`，用 `--json-file` 传入结构化 payload；脚本可执行时不要让 agent 手写正文块和索引。
- 删除知识条目时，默认调用 `delete_pitfall.py`；累计 `使用次数` 时，默认调用 `record_pitfall_usage.py`。
- 先读取 [knowledge-authoring.md](references/knowledge-authoring.md) 和 [manual-edit-template.md](references/manual-edit-template.md)，按模板生成脚本 payload，再由脚本写 Wiki Markdown 与相关索引。
- 如果脚本被沙箱、权限或工具策略拦截，降级为 agent 按 [manual-edit-template.md](references/manual-edit-template.md) 自然写入 Markdown 与索引；降级时必须明确写入失败原因，并保持正文页、`index.md`、`llms.txt` 和相关 repo/domain index 一致。
- 写入完成后，再运行 `end_task.py` 记录 `recorded`；没有新增知识时照常运行 `end_task.py --result skipped`。
- 只有脚本被拦截、脚本缺少表达能力、需要修复损坏 Markdown，或维护者明确要求手工排障时，才直接编辑 Wiki Markdown。

没有新知识：

```bash
python3 skills/team-pitfalls/scripts/end_task.py \
  --task-id <同一 ID> \
  --result skipped \
  --reason "现有记录已覆盖"
```

已经写入或更新：

```bash
python3 skills/team-pitfalls/scripts/end_task.py \
  --task-id <同一 ID> \
  --result recorded \
  --entry-id P-001
```

如果本轮只采用了已有知识并更新了使用次数，也可以用 `--used-entry-id` 记录：

```bash
python3 skills/team-pitfalls/scripts/end_task.py \
  --task-id <同一 ID> \
  --result recorded \
  --used-entry-id P-001
```

最终答复只需简短说明“已复盘，记录/不记录”，不要输出生命周期状态 JSON。

### 脚本写入示例

新增仓库领域级纠错：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --repo <repo-name> \
  --domain <domain-name> \
  --kind corrections \
  --json-file <payload.json>
```

新增通用坑位：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --type docs \
  --title "<标题>" \
  --tags "<标签1, 标签2>" \
  --conclusion "当……时，应先……，否则……" \
  --reason "<原因>" \
  --wrong "<反例>" \
  --right "<正例>" \
  --min-example "<原案例抽象>" \
  --min-example "<跨场景迁移例>" \
  --scope-ok "<适用范围>" \
  --scope-no "<不适用范围>"
```

记录已采用条目：

```bash
python3 skills/team-pitfalls/scripts/record_pitfall_usage.py --id P-001
```

补强已有条目正文时，优先用脚本重写：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --repo <repo-name> \
  --domain <domain-name> \
  --kind corrections \
  --replace-existing \
  --json-file <payload.json>
```

如果上面的脚本调用被沙箱或权限拦截，按模板降级为 agent 自然写入。

## 何时加载详细规范

仅在以下情况读取 [knowledge-authoring.md](references/knowledge-authoring.md)；新增、更新、删除知识时同时读取 [manual-edit-template.md](references/manual-edit-template.md)：

- 新增、更新或删除知识条目。
- 用户要求优化 `team-pitfalls` 本身。
- 需要判断具体案例能否升级为通用坑位。
- 需要处理复杂 JSON、产物路径或 Wiki 结构。

普通工程任务不要读取该 reference。

## 不可省略的边界

- Wiki root 固定使用 `~/.team-pitfalls-wiki`，不支持命令参数、环境变量或配置文件覆盖。
- 首次运行时自动初始化 `~/.team-pitfalls-wiki` 的基础 Wiki 结构。
- 仓库领域级知识优先于全局领域级知识，全局领域级知识优先于仓库级知识，仓库级知识优先于全局知识；四者不能混写成一条。
- 每个领域 `index.md` 必须保留简短介绍，说明业务、页面/链路范围、典型术语或指标边界；刷新索引不能覆盖人工补充的简介。
- 知识条目不记录 `出现次数`、`最近使用`、`首次出现` 和 `最近出现`；只保留 `使用次数` 这一统计字段。
- 不记录账号、token、cookie、用户正文或其他敏感信息。
- `llms.txt` 只做精选入口和读取顺序，不当 sitemap；基础结构包含 `SCHEMA.md`、`index.md`、`llms.txt`、`domains/`、`repos/` 和 `pitfalls/`。
- 脚本必须保留导航门禁职责；不能重新用 query 召回、分数排序、Top-N 截断或脚本生成条目摘要替代 agent 先读索引简介、再按需打开正文的流程。
- 常规任务中的新增、更新、删除知识，以及 `使用次数` 的累计，必须优先通过 `upsert_pitfall.py` / `delete_pitfall.py` / `record_pitfall_usage.py` 执行；只有脚本被沙箱、权限或工具策略拦截，或脚本能力确实不足时，才降级为手写 Markdown。
