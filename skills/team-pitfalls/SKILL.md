---
name: team-pitfalls
description: 所有非纯闲聊工程任务的团队知识前置检查与后置复盘 Skill。处理代码、仓库、技术方案、文档规范、内部平台、业务术语、经验沉淀或 AI 纠错时，即使用户没有提到“踩坑”或 team-pitfalls，也必须在任务开始时调用；完成任务前必须再次执行复盘，记录新知识或明确说明检查后不记录。
---

# Team Pitfalls

这个 skill 用于把团队踩坑、仓库业务黑话、AI 被纠正过的误判沉淀到一份用户自有的 LLM Wiki 中。

## 核心原则

`team-pitfalls` 不再在 skill 包内保存知识库正文，也不再维护旧的 `references/INDEX.md + 分类 md + repos/` 结构。

知识库必须放在用户指定的外部 LLM Wiki root 中，便于 Trae、Claude、Codex 等多个工具共享同一份记录。

## 标准 LLM Wiki 结构

外部 LLM Wiki root 固定采用下面的结构：

```text
<wiki-root>/
  llms.txt
  index.md
  pitfalls/
    tools-and-internal-platforms.md
    git-and-commit.md
    docs-and-portability.md
  repos/
    <repo-name>/
      index.md
      glossary.md
      corrections.md
```

文件职责：

- `llms.txt`: 面向 LLM 的入口文件，说明读取顺序和主要导航。
- `index.md`: 全量条目索引，包含 ID、类型、标题、标签和正文路径。
- `pitfalls/*.md`: 跨项目通用坑位，使用 `P-xxx` 编号。
- `repos/<repo-name>/glossary.md`: 仓库级业务黑话和术语映射，使用 `G-xxx` 编号。
- `repos/<repo-name>/corrections.md`: 仓库级 AI 纠错记录，使用 `C-xxx` 编号。
- `repos/<repo-name>/index.md`: 单仓库局部导航。

配置方式：

- 命令参数：`--wiki-root <path>`
- 环境变量：`TEAM_PITFALLS_LLM_WIKI_ROOT`
- 配置文件：`~/.config/team-pitfalls/config.json`

配置文件格式：

```json
{
  "wiki_root": "/path/to/team-pitfalls-wiki"
}
```

优先级固定为：命令参数 > 环境变量 > 配置文件。

没有配置外部 LLM Wiki root 时，不能假装已经完成前置检查；脚本必须中止并提醒用户主动配置 wiki root，至少给出 `--wiki-root <path>`、`TEAM_PITFALLS_LLM_WIKI_ROOT=<path>` 和 `~/.config/team-pitfalls/config.json` 三种配置方式。

## 固定执行顺序

只要本轮使用了这个 skill，必须执行两段：

1. **对话前检查**
   - 首先运行 `begin_task.py` 创建本轮生命周期状态；这是本 skill 触发后的第一项动作。
   - 在正式回答、改文件、给方案之前，先读取外部 LLM Wiki 的 `llms.txt` 和 `index.md`。
   - 根据任务关键词，只打开命中的正文页，不一次性加载全部内容。
   - 如果命中具体仓库，优先读取 `repos/<repo-name>/index.md`、`glossary.md`、`corrections.md`。
   - 对实际用于指导本轮任务的命中条目，立即执行使用计数；只因关键词相似而打开、但没有采用的条目不计数。
2. **对话后复盘**
   - 在本轮任务准备结束时，回看本轮对话和结果。
   - 判断是否有新的通用坑、仓库黑话、AI 纠错值得沉淀。
   - 有价值就写入外部 LLM Wiki；没有价值也要明确说明“本轮检查过，但不记录”。
   - 最终答复前运行 `end_task.py`，确认同一个任务已经完成前置检查，并明确本轮沉淀结果。

这个顺序是强制的，不能只做前半段，也不能只在用户追问时才补做后半段。

### 生命周期门禁

任务开始时生成一个本轮稳定、无敏感信息的 `<task-id>`，后续始终复用：

```bash
python3 skills/team-pitfalls/scripts/begin_task.py \
  --task-id <task-id> \
  --repo <repo-name>
```

`--repo` 可选。脚本只验证 Wiki 配置和基础入口文件，输出需要读取的路径并创建临时状态；它不代替模型实际读取和理解 `llms.txt`、`index.md` 及命中正文。若没有配置 Wiki root，脚本会直接提示用户先配置外部目录，不会继续创建任务状态。

任务结束时必须二选一：已经沉淀，或检查后明确跳过。不能省略结果：

```bash
# 已写入或更新知识
python3 skills/team-pitfalls/scripts/end_task.py \
  --task-id <task-id> \
  --confirmed-read llms.txt \
  --confirmed-read index.md \
  --result recorded \
  --entry-id P-001

# 检查后没有值得沉淀的新知识
python3 skills/team-pitfalls/scripts/end_task.py \
  --task-id <task-id> \
  --confirmed-read llms.txt \
  --confirmed-read index.md \
  --result skipped \
  --reason "现有条目已覆盖，本轮没有新的可迁移机制"
```

`--confirmed-read` 可以传基础文件名或 begin 输出的完整路径。`end_task.py` 在找不到对应 begin 状态、未确认读取 `llms.txt` 和 `index.md`、`recorded` 未提供条目 ID，或 `skipped` 未提供原因时失败。脚本位于 skill 内，只负责 skill 已触发后的流程完整性；是否触发主要由 frontmatter 的 description 决定。

## 读取规则

前置检查时按下面顺序读取：

1. 先按“命令参数 > 环境变量 > 配置文件”的优先级确定 `<wiki-root>`
2. `<wiki-root>/llms.txt`
3. `<wiki-root>/index.md`
4. 命中通用坑位时，读取对应 `pitfalls/*.md`
5. 命中仓库上下文时，读取：
   - `<wiki-root>/repos/<repo-name>/index.md`
   - `<wiki-root>/repos/<repo-name>/glossary.md`
   - `<wiki-root>/repos/<repo-name>/corrections.md`

仓库级知识优先级高于通用坑位：

```text
仓库级校验 > 通用校验
仓库级沉淀 与 通用沉淀 可同时发生，但不能混写到同一条记录
```

### 命中后的使用计数

“出现次数”和“使用次数”代表不同信号：

- **出现次数**：同类坑再次发生、再次被纠正或再次进入沉淀流程。
- **使用次数**：前置检查命中后，该记录实际影响了本轮判断、方案或实现。

确认采用记录后，按命中的 ID 立即执行：

```bash
python3 skills/team-pitfalls/scripts/record_pitfall_usage.py \
  --wiki-root <path> \
  --id P-001 \
  --id C-002
```

规则：

- 同一轮同一条记录最多计数一次；脚本会对重复 ID 去重。
- 一次前置检查命中多条且都被采用时，一次性传入多个 `--id`。
- 只打开正文进行排除、最终未采用时不计数。
- 计数成功后，正文中的 `最近使用` 更新为当天，`使用次数` 加一。
- 计数失败时明确说明，不能假装已经统计成功；计数失败不应阻塞原任务继续执行。

## 触发时机

### 前置检查触发

当本轮任务满足以下任一情况时，在开始正常回答或执行前先调用本 skill：

- 用户显式提到 `team-pitfalls`
- 用户要求收集问题、沉淀经验、整理规范、沉淀业务黑话
- 用户正在纠正上一轮输出，或当前任务明显容易撞到历史坑
- 你准备处理仓库内的文档、规范、术语、README、commit、内部平台读取等高频易错问题

### 收集触发

当用户提到以下意图之一，就进入沉淀候选流程：

- 收集问题/踩坑/经验沉淀/团队最佳实践/规范整理
- 容易写错/容易踩坑/新同学容易犯错/常见误用
- 业务黑话/术语映射/仓库知识沉淀
- AI 理解错了/AI 被纠正了/下次别再这么理解

### 校验触发

当用户明确指出上一轮输出有问题或不符合规范时，先做原则校验，再继续处理：

- “上一轮输出不符合规范/不符合约定/不对/有问题/改一下/别这样写”
- “不要出现绝对路径/不要出现本地协议链接/内容太多/应该只输出一条”
- “你把这个业务词理解错了/这里不是这个意思”

### 后置复盘触发

只要本轮已经调用过这个 skill，结束前都要自动执行一次“是否值得沉淀”的复盘。

## 写入判断

### 从具体案例提炼通用知识

收集触发条件保持不变。进入沉淀候选流程后，不要直接把当时的报错、文件名、页面名或修复步骤改写成条目；先完成一次“案例事实 → 失效机制 → 可迁移规则”的抽象。

按下面顺序处理：

1. **保留案例事实**：确认当时发生了什么、错误假设是什么、什么证据推翻了它。案例事实用于追溯，不等于最终的通用结论。
2. **识别失效机制**：追问“换掉仓库名、平台名和变量名后，导致错误的因果关系是否仍成立”。优先抽象状态不同步、数据口径错位、生命周期遗漏、权限与可用性混淆、文档与实现漂移、局部成功被误判为整体成功等机制。
3. **形成条件式规则**：用“当……时，应先……，否则……”表达。规则必须包含触发条件和动作，避免“注意检查”“谨慎处理”这类无法执行的结论。
4. **做跨场景迁移测试**：至少给出一个与原案例不同的场景，说明同一机制如何再次出现。找不到第二场景时，先留在仓库级记录，不升级为通用坑位。
5. **划定边界**：写清适用与不适用范围，防止把局部经验扩张成绝对规则。

抽象时保留“最小充分上下文”：删去不影响判断的专有名词，但保留决定规则是否成立的技术约束。通用化不是去掉名词，而是保留因果结构。

例如：

- 过度具体：`某页面查询 PV 时要查三个 bid`。
- 过度空泛：`查询指标时要全面检查`。
- 可迁移：`当一个逻辑页面由多个运行时入口共同承载时，应先枚举入口并分别查询，再决定是否汇总；否则单入口数据会被误当成页面全量。`

### 双层沉淀

同一次事件可以形成两条互相链接但不混写的知识：

- 仓库级 `C-*` / `G-*`：保存可验证的具体事实、专有名词和本仓库边界。
- 通用 `P-*`：保存从事实中提炼出的失效机制、触发信号、通用动作和迁移场景。

只有通过跨场景迁移测试才新增 `P-*`。如果已有通用条目覆盖该机制，更新出现次数即可，不用围绕新案例再造近义条目。

### 通用条目质量门槛

写入 `P-*` 前逐项检查：

- 标题描述失效机制或决策规则，不把仓库名、页面名、接口名作为主语。
- 一句话结论包含条件、动作和风险，不只是复述原案例的修复结果。
- “容易写错的原因”解释错误假设为何看似合理。
- 正反例体现同一判断点，不只是展示两段不同代码。
- 最小示例至少包含原场景的抽象表达和一个跨场景迁移例。
- 标签同时覆盖机制词和常见触发词，避免只能靠原项目专有词命中。
- 适用与不适用范围足以阻止机械套用。

任一项无法填写时，继续保留为候选或仓库级知识，不要用 `TODO` 生成低信息量的通用条目。

### 通用坑位

判断标准只有一句：

> 新加入团队的工程师，不看这条记录，写类似功能时大概率会写错吗？是则写入，否则跳过。

必须满足：

- 是跨业务、跨项目可复用的通用模式/原则/陷阱。
- 不是框架基础知识。
- 不是单一项目的一次性实现细节。
- 不记录账号、token、cookie、内部敏感参数。
- 已通过跨场景迁移测试，而不是只对原案例换一种说法。

写入脚本会对新通用条目执行最低质量校验：必填结论、原因、正反例和边界，并要求 `min_examples` 至少两项，分别承载原场景抽象与跨场景迁移例。已有同标题条目只累计出现次数，不受此校验影响。

### 仓库级知识

满足以下任一条件，就应该写入仓库层：

- 这是该仓库反复出现的业务黑话、缩写、术语映射。
- AI 曾经把这个概念理解错，用户给出了更准确的定义或边界。
- 同名概念在这个仓库里有特殊含义。
- 不沉淀这条知识，下次面对同仓库时大概率还会再错。

## 写入命令

### 通用坑位

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --wiki-root <path> \
  --type docs \
  --json '<json>'
```

`--type` 支持：

- `mcp` / `tools`: 写入 `pitfalls/tools-and-internal-platforms.md`
- `git`: 写入 `pitfalls/git-and-commit.md`
- `docs`: 写入 `pitfalls/docs-and-portability.md`

也可以通过 `--file pitfalls/custom.md` 指定自定义通用页面。

### 仓库术语

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --wiki-root <path> \
  --repo <repo-name> \
  --kind glossary \
  --json '<json>'
```

### 仓库纠错

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --wiki-root <path> \
  --repo <repo-name> \
  --kind corrections \
  --json '<json>'
```

### 删除条目

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py \
  --wiki-root <path> \
  --id P-001
```

### 迁移旧版 references

如果用户还保留了旧版 `references/` 目录，可以无缝迁入外部 LLM Wiki root：

```bash
python3 skills/team-pitfalls/scripts/migrate_references_to_llm_wiki.py \
  --source-references <old-references-path> \
  --wiki-root <path>
```

迁移脚本会把旧记录重新写入标准 LLM Wiki 结构，并按当前 wiki 的 `P/G/C` 序列重新分配 ID；重复执行时会按“类型 + 标题”跳过已存在记录，避免重复写入。

## 脚本行为

脚本会自动维护：

- `llms.txt`
- `index.md`
- `pitfalls/*.md`
- `repos/<repo-name>/index.md`
- `repos/<repo-name>/glossary.md`
- `repos/<repo-name>/corrections.md`
- 条目正文中的 `最近使用` 和 `使用次数`

脚本不会：

- 在 skill 包内创建知识库正文。
- 读取或写入旧 `references/` 结构。
- 记录密钥、token、cookie 等敏感信息。
- 未经用户配置就把知识写到默认路径。
- 在缺少 Wiki root 配置时静默失败；必须提示用户主动配置后再重试。
