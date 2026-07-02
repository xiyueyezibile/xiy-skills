---
name: team-pitfalls
description: 团队踩坑与仓库业务知识收集器。只要用户提到“收集问题/踩坑/容易写错/沉淀经验/团队规范/业务黑话/术语映射/AI 找错被纠正”等，就必须调用本 skill，把可复用的通用坑或仓库级知识写入案例库。只要用户指正“上一轮输出不符合规范/不对/不符合约定/业务理解错了”，就必须先加载仓库级知识和通用规则做原则校验，再修正输出。
---

# Team Pitfalls

这个 skill 的目标有两层：

1. 把跨仓库通用、可复用的坑沉淀到通用案例库。
2. 把某个仓库内可复用的业务黑话和 AI 被纠正过的业务误判，沉淀到仓库级知识池。

为了避免 SKILL.md 过长，本 skill 采用“双层按需加载”：

- **通用层**：按类型加载 `references/*.md`
- **仓库层**：按仓库名加载 `references/repos/<repo-name>/`

## 案例索引（先读这个）

### 通用索引

先读取通用索引，用于快速判断已有通用条目、做跨文件去重与定位：

- [INDEX.md](references/INDEX.md)

### 仓库索引

如果当前任务明确落在某个仓库里，或者用户正在纠正某个仓库的业务理解，优先读取：

- `references/repos/<repo-name>/INDEX.md`

仓库目录如果还不存在，说明该仓库知识池尚未初始化，可以直接通过脚本写入时自动创建。

## 案例库文件索引（按需加载）

### 通用层文件

在开始沉淀/去重之前，先根据对话内容选一个或多个类型，然后只加载对应通用文件：

- **工具/鉴权/内部平台读取（MCP/文档/平台）**: [mcp-and-internal-content.md](references/mcp-and-internal-content.md)
- **Git/提交规范（commit/message/分支/发布）**: [git-and-commit.md](references/git-and-commit.md)
- **文档/可移植性（README/脚本/路径）**: [docs-and-portability.md](references/docs-and-portability.md)

如果现有类型都不匹配，新增一个 `references/<type>.md`（命名用英文-kebab-case），并在通用 `INDEX.md` 中追加一行映射。

### 仓库层文件

每个仓库目录下固定维护 3 个文件：

- `INDEX.md`: 当前仓库的局部索引
- `glossary.md`: 业务黑话、术语映射、缩写解释
- `corrections.md`: AI 曾经理解错、后来被用户修正的记录

## 仓库级优先级

只要命中仓库上下文，就遵循下面的顺序：

```text
仓库级校验 > 通用校验
仓库级沉淀 与 通用沉淀 可同时发生，但不能混写到同一文件
```

原因很简单：业务语义错了时，先用通用规范校验没有意义，必须先用仓库知识把语义校正。

## 类型判定（快速规则）

从候选问题里抽关键词，按命中规则选 1~2 个通用类型：

- **工具/鉴权/内部平台读取（MCP/文档/平台）**: 关键词包含 `mcp`、`飞书`、`lark`、`docx`、`wiki`、`内部平台`、`鉴权`、`sso`、`抓取`、`拿不到内容`
- **Git/提交规范（commit/message/分支/发布）**: 关键词包含 `git`、`commit`、`提交`、`conventional`、`message`、`分支`、`rebase`、`cherry-pick`
- **文档/可移植性（README/脚本/路径）**: 关键词包含 `readme`、`文档`、`安装`、`路径`、`绝对路径`、`脚本`、`可移植`

## 仓库判定（快速规则）

只要满足任一条件，就视为命中仓库级场景：

- 用户提到了明确仓库名、模块名、业务线简称
- 当前任务就在某个仓库内改代码、改文档、改配置
- 用户纠正的是某个业务术语、业务缩写、上下游指代、指标含义、流程语义
- 用户明确要求“以仓库为单位”沉淀黑话或纠错记录

仓库目录名直接使用仓库名；如果仓库名包含不适合作为目录名的字符，脚本会做最小规范化。

## 触发时机

本 skill 只有在满足下列任一触发条件时才使用：

### 收集触发（沉淀案例或仓库知识）

当用户提到以下意图之一，就进入“沉淀候选问题”流程：

- 收集问题/踩坑/经验沉淀/团队最佳实践/规范整理
- 容易写错/容易踩坑/新同学容易犯错/常见误用
- 业务黑话/术语映射/仓库知识沉淀
- AI 理解错了/AI 被纠正了/下次别再这么理解

### 校验触发（原则校验）

当用户明确指出上一轮输出有问题或不符合规范时，就进入“原则校验”流程：

- “上一轮输出不符合规范/不符合约定/不对/有问题/改一下/别这样写”
- “不要出现绝对路径/不要出现本地协议链接/内容太多/应该只输出一条…”
- “你把这个业务词理解错了/这里不是这个意思/这个仓库里 XX 不是 YY”

## 是否写入的判断标准

### 通用层写入标准

判断标准只有一句：

> 新加入团队的工程师，不看这条 SKILL，写类似功能时大概率会写错吗？是则写入，否则跳过。

**核心约束（必须满足）**：

- **必须是通用规则**：只能写入跨业务、跨项目可复用的通用模式/原则/陷阱
- 先判断是否是通用、可复用的模式，再决定是否写入
- 值得写入的：Web 开发者不会自然想到的模式、跨端/平台差异、工具链陷阱、流程陷阱、隐性约束
- **绝对不该写入通用层的内容**：
  - React/Vue 等框架基础知识（任何合格前端都应掌握的内容）
  - 特定业务系统的术语、实现细节、业务逻辑、业务约束
  - 某一个项目/页面的一次性实现细节
  - 具体的 bug fix（除非能抽象成通用陷阱模式）
  - 只对单一工程/单一仓库成立的特殊约定

### 仓库层写入标准

只要满足以下任一条件，就应该写入仓库层：

- 这是该仓库里反复出现的业务黑话、缩写、术语映射
- AI 曾经把这个概念理解错了，用户给出了更准确的定义或边界
- 同名概念在别的语境里常见，但在这个仓库里有特殊含义
- 不沉淀这条知识，下次面对同仓库或同名仓库时大概率还会再错

仓库层允许记录业务含义，但仍然要求：

- 必须是“该仓库内可复用”的知识，不是一锤子买卖
- 不记录账号、token、cookie、内部敏感参数
- 不把仓库层知识回写到通用层

## 写入流程（每次触发都执行）

1. 从最近对话里提取“候选问题”（0~3 个）
2. 先判断是否命中仓库级场景：
   - 命中则先识别仓库名，读取 `references/repos/<repo-name>/INDEX.md`
   - 按需加载 `glossary.md` 和 `corrections.md`
3. 再选择通用类型并按需加载通用案例库文件：
   - 根据候选问题的标签/主题选择 1~2 个类型
   - 只读取对应 references 文件，用于去重与对齐条目格式
4. 对每个候选问题判断去向：
   - 通用规则 → 写入通用层
   - 业务黑话/术语映射 → 写入 `glossary.md`
   - AI 错判被纠正 → 写入 `corrections.md`
5. 写入前先去重：
   - 标题或关键词高度相似 → 更新既有条目（count + 1，补充示例/线索）
   - 不相似 → 新增条目
6. 用脚本执行写入与更新（优先使用脚本，不要手工改文件）

### 通用层写入命令

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --type <mcp|git|docs> --json '<json>'
```

`<json>` 支持两套字段写法（都会被映射到条目模板）：

- **基础字段**: `title`, `tags`, `conclusion`, `reasons`, `wrong`, `right`, `min_examples`, `scope_ok`, `scope_no`
- **扩展字段（兼容写法）**:
  - `id`: 可选，形如 `P-123`，用于指定条目 ID
  - `tags`: 既支持字符串也支持数组（会自动拼成逗号分隔）
  - `one_liner` → `conclusion`
  - `why_wrong` → `reasons`
  - `anti_patterns` → `wrong`
  - `best_practices` → `right`
  - `minimal_example` → `min_examples`
  - `scope.apply` → `scope_ok`
  - `scope.not_apply` → `scope_no`

### 仓库层写入命令

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind glossary --json '<json>'
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind corrections --json '<json>'
```

仓库层 JSON 字段约定：

- `glossary`
  - `title`
  - `tags`
  - `standard_meaning`
  - `common_misunderstandings`
  - `correct_understanding`
  - `min_examples`
  - `scope.apply`
  - `scope.not_apply`
- `corrections`
  - `title`
  - `tags`
  - `wrong_understanding`
  - `user_correction`
  - `correction_conclusion`
  - `trigger_clues`
  - `min_examples`
  - `scope.apply`
  - `scope.not_apply`

7. 脚本会自动完成：
   - 新增条目：写入对应分类文件顶部（紧跟第一个 `## ...` 标题行下面）
   - 新增条目：同步追加一行到对应索引
   - 已存在条目：更新“最近出现”“出现次数”
   - 写入仓库层时，如果仓库目录缺失，会自动初始化 `INDEX.md`、`glossary.md`、`corrections.md`

8. 如果只是想预览变更，不落盘：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --dry-run --type <mcp|git|docs> --json '<json>'
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --dry-run --repo <repo-name> --kind <glossary|corrections> --json '<json>'
```

## 删除已存在的条目

### 删除通用层条目

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py --id P-001
```

或者通过标题删除：

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py --title "Commit 信息应优先给一条主线"
```

### 删除仓库层条目

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py --repo <repo-name> --kind glossary --id G-001
python3 skills/team-pitfalls/scripts/delete_pitfall.py --repo <repo-name> --kind corrections --title "AI 把 ROI 理解成图像区域"
```

## 新增位置规则（必须遵循）

当新增条目时，把新条目写在对应文件的顶部：紧跟该文件的第一个标题行（例如 `## ...`）后面，放在历史条目前面。

## 原则校验（仅在“校验触发”时执行）

当用户指出“上一轮输出不符合规范/有问题”时，在你给用户输出修正结果之前，必须先做一次“原则校验”，确保当前输出没有违反已沉淀的条目结论。

执行方法：

1. 如果命中仓库上下文，先读取 `references/repos/<repo-name>/INDEX.md`
2. 按需加载 `glossary.md` 和 `corrections.md`
3. 再读取通用 [INDEX.md](references/INDEX.md)
4. 根据本次用户问题，按“类型判定”加载 1~2 个通用分类文件
5. 从这些文件中提取所有结论，整理成校验清单
6. 检查你准备发送给用户的答复是否违反任一结论；若违反，先改写答复再发送

最低限度校验项：

- 不输出任何个人机器绝对路径或本地文件协议链接（用占位符表达路径）
- 不输出任何密钥、token、cookie 等敏感信息
- 当用户要生成 commit 信息时，默认只给一条主线 commit message（除非用户明确要求多条）
- 当用户正在某个仓库语境里纠正业务含义时，优先采用仓库级定义，不要套用其他常见语义

## 条目格式（必须遵循）

### 通用层模板

每条通用踩坑用下面模板记录：

```
### P-XXX: <一句话标题>
- **标签**: <工具/平台/流程/前端/后端/跨端/...>
- **首次出现**: YYYY-MM-DD
- **最近出现**: YYYY-MM-DD
- **出现次数**: N
- **一句话结论**: <新同学最该记住的那句话>
- **容易写错的原因**:
  - <为什么直觉会错/为什么文档不显眼/为什么环境限制导致误判>
- **错误做法（反例）**:
  - <描述反例，不贴大段一次性代码>
- **正确做法（正例）**:
  - <描述正例步骤或模式>
- **最小示例**:
  - <尽量短的命令/片段/伪代码>
- **适用范围/不适用范围**:
  - 适用: <什么情况>
  - 不适用: <什么情况>
```

### 仓库层 glossary 模板

```
### G-XXX: <一句话标题>
- **标签**: <术语/黑话/缩写/...>
- **首次出现**: YYYY-MM-DD
- **最近出现**: YYYY-MM-DD
- **出现次数**: N
- **标准含义**: <这个词在该仓库里到底指什么>
- **常见误解**:
  - <AI 或新同学容易误解成什么>
- **正确理解**:
  - <正确语义、边界、别名、反例>
- **最小示例**:
  - <尽量短的一句话示例>
- **适用范围/不适用范围**:
  - 适用: <什么场景>
  - 不适用: <什么场景>
```

### 仓库层 corrections 模板

```
### C-XXX: <一句话标题>
- **标签**: <纠错/业务理解/术语误判/...>
- **首次出现**: YYYY-MM-DD
- **最近出现**: YYYY-MM-DD
- **出现次数**: N
- **错误理解**: <AI 当时怎么理解的>
- **用户修正**: <用户明确给出的正解>
- **修正结论**: <下次遇到类似表述时应如何判断>
- **触发线索**:
  - <哪些词、路径、模块、上下文会触发这个判断>
- **最小示例**:
  - <错: ...>
  - <对: ...>
- **适用范围/不适用范围**:
  - 适用: <什么场景>
  - 不适用: <什么场景>
```

## 安全与边界

- 不记录任何密钥、token、cookie、内部敏感链接参数
- 不记录只对单一页面成立、无法复用的一次性细节
- 不把仓库级业务知识混写进通用层
