---
name: team-pitfalls
description: 所有非纯闲聊工程任务的分层团队知识前置检查与后置复盘 Skill。处理代码、仓库、领域上下文、技术方案、文档规范、经验沉淀或 AI 纠错时必须调用。
---

# Team Pitfalls

用外部 LLM Wiki 共享团队踩坑、跨仓库领域知识、仓库术语、仓库领域知识和 AI 纠错。上下文利用率优先通过固定层级提升：仓库领域级先于全局领域级，全局领域级先于仓库级，仓库级先于全局级；不再把 query 召回和打分候选作为主流程。

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
- `--domain` 可选；可单独用于全局领域级，也可配合 `--repo` 读取仓库领域级。
- `--query` 仅为兼容旧调用保留，不参与召回、打分或过滤。
- 开始任务时按固定顺序读取：仓库领域级 `repos/<repo>/domains/<domain>/` → 全局领域级 `domains/<domain>/` → 仓库级 `repos/<repo>/` → 全局级 `pitfalls/`。
- 默认返回每一层的 `ID + Kind + Title + Tags + File + 结论` 摘要，不做 query 召回、分数排序或 Top-N 截断。
- 如果知识属于某类业务、某个页面、某条业务链路或类似稳定范围，必须传 `--domain`。
- 仓库领域级和全局领域级都命中时，优先采用仓库领域级；全局领域级可用于反向发现其他仓库同领域记录。
- 仓库级和全局级冲突时，优先采用仓库级。
- 实际采用后调用一次 `record_pitfall_usage.py --id <ID>`；只浏览未采用不计数。
- 不向用户复述完整预检过程，除非命中内容会改变方案或形成风险提示。

### 2. 后置复盘

任务完成后只判断本轮是否产生新的可迁移机制、仓库术语或用户纠错。

知识按 `--repo` 和 `--domain` 隔离判断是否已有：其他仓库或其他领域已有相同或相近记录，只能作为参考，不能当作当前仓库/领域“现有记录已覆盖”的理由。若本轮问题会在当前仓库领域复发，且当前仓库领域没有等价 `G-*`/`C-*`，必须优先写入 `repos/<repo-name>/domains/<domain-name>/glossary.md` 或 `repos/<repo-name>/domains/<domain-name>/corrections.md`。若该业务领域跨仓库复用，另写或更新 `domains/<domain-name>/glossary.md` 或 `domains/<domain-name>/corrections.md`。无法归属具体领域时才写入仓库级。

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

最终答复只需简短说明“已复盘，记录/不记录”，不要输出生命周期状态 JSON。

## 何时加载详细规范

仅在以下情况读取 [knowledge-authoring.md](references/knowledge-authoring.md)：

- 新增、更新、删除或迁移知识条目。
- 用户要求优化 `team-pitfalls` 本身。
- 需要判断具体案例能否升级为通用坑位。
- 需要处理复杂 JSON、产物路径或 Wiki 结构。

普通工程任务不要读取该 reference。

## 不可省略的边界

- Wiki root 优先级：命令参数 > `TEAM_PITFALLS_LLM_WIKI_ROOT` > `~/.config/team-pitfalls/config.json` > `~/.team-pitfalls-wiki`。
- 用户未配置时自动使用 `~/.team-pitfalls-wiki` 并初始化基础 Wiki 结构；只有需要团队共享或迁移既有知识库时才引导用户覆盖路径。
- 仓库领域级知识优先于全局领域级知识，全局领域级知识优先于仓库级知识，仓库级知识优先于全局知识；四者不能混写成一条。
- 知识条目不记录 `首次出现` 和 `最近出现`；只保留出现次数和使用次数。
- 不记录账号、token、cookie、用户正文或其他敏感信息。
- `llms.txt` 只做精选入口和读取顺序，不当 sitemap；基础结构包含 `SCHEMA.md`、`index.md`、`llms.txt`、`domains/`、`repos/` 和 `pitfalls/`。
- 脚本必须保留分层顺序；不能用 query 召回、分数排序或 Top-N 截断替代仓库领域级 → 全局领域级 → 仓库级 → 全局级查找。
