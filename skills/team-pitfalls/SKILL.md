---
name: team-pitfalls
description: 所有非纯闲聊工程任务的召回优先团队知识前置检查与后置复盘 Skill。处理代码、仓库、技术方案、文档规范、内部平台、业务术语、经验沉淀或 AI 纠错时必须调用；脚本扫描全量知识但只向模型返回相关摘要，禁止重复加载完整 Skill 或全量 Wiki 索引。
---

# Team Pitfalls

用外部 LLM Wiki 共享团队踩坑、仓库术语和 AI 纠错。召回准确性优先于 Token、时延和步骤数；确定性全量扫描交给本地脚本，模型只消费所有相关候选的摘要。

## 快路径

每轮只保留两个固定步骤。

### 1. 前置检查

Skill 正文由平台触发时已经加载，不要再次 `cat SKILL.md`，也不要手工读取 `llms.txt` 或全量 `index.md`。立即运行：

```bash
python3 skills/team-pitfalls/scripts/begin_task.py \
  --task-id <稳定且无敏感信息的 ID> \
  --query "<不超过 256 字符的原词、同义词和失效机制关键词>" \
  --repo <repo-name>
```

- `--repo` 可选。
- `--query` 不写自然语言摘要；提供 5-12 个逗号分隔关键词，同时包含用户原词、常见同义词、技术机制和可能的错误表现。
- 默认返回全部正相关候选的 `ID + 标题 + 一句话结论 + 范围 + 分数 + 命中字段/词`，不做 Top-N 截断。
- 审阅全部候选时优先看 `matches.title_tags` 和 `matches.conclusion`；仅正文弱命中的记录仍保留供复核，但不能仅凭分数机械采用。
- 匹配范围覆盖标题、标签、结论和正文，并对中文短语做 2-4 字切分，减少措辞差异造成的漏召回。
- 指定仓库时只检索该仓库专属记录与通用记录，其他仓库记录不参与竞争。
- 默认最低分只过滤“正文碰巧出现一个弱词”的噪声；标题、标签或结论命中仍可进入。
- 只有用户明确接受漏召回风险时才传 `--max-candidates` 限流。
- 首轮零候选时必须扩展同义词和失效机制后用同一 task-id 加 `--force` 重试一次；第二轮仍为零才继续用户任务。
- 候选结论足够指导任务时直接采用；只有结论无法判断边界时，才打开对应正文块，禁止读取整页。
- 实际采用后调用一次 `record_pitfall_usage.py --id <ID>`；只浏览未采用不计数。
- 不向用户复述完整预检过程，除非命中内容会改变方案或形成风险提示。

### 2. 后置复盘

任务完成后只判断本轮是否产生新的可迁移机制、仓库术语或用户纠错。

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

- Wiki root 优先级：命令参数 > `TEAM_PITFALLS_LLM_WIKI_ROOT` > `~/.config/team-pitfalls/config.json`。
- 缺少配置时脚本应中止并给出上述三种配置方式；不能假装完成检查。
- 仓库级知识优先于通用知识，但两者不能混写成一条。
- 不记录账号、token、cookie、用户正文或其他敏感信息。
- 脚本必须扫描完整索引与条目文本后再判断相关性；不能为了省成本跳过仓库级或通用级候选。
