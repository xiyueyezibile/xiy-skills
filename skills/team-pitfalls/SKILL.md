---
name: team-pitfalls
description: 团队踩坑与仓库业务知识收集器。当前任务需要前置避坑检查、沉淀经验、整理规范、记录业务黑话或 AI 纠错时必须调用。
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

没有配置外部 LLM Wiki root 时，不能假装已经完成前置检查；应明确说明缺少 wiki root，并让用户提供路径或先跳过沉淀。

## 固定执行顺序

只要本轮使用了这个 skill，必须执行两段：

1. **对话前检查**
   - 在正式回答、改文件、给方案之前，先读取外部 LLM Wiki 的 `llms.txt` 和 `index.md`。
   - 根据任务关键词，只打开命中的正文页，不一次性加载全部内容。
   - 如果命中具体仓库，优先读取 `repos/<repo-name>/index.md`、`glossary.md`、`corrections.md`。
2. **对话后复盘**
   - 在本轮任务准备结束时，回看本轮对话和结果。
   - 判断是否有新的通用坑、仓库黑话、AI 纠错值得沉淀。
   - 有价值就写入外部 LLM Wiki；没有价值也要明确说明“本轮检查过，但不记录”。

这个顺序是强制的，不能只做前半段，也不能只在用户追问时才补做后半段。

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

### 通用坑位

判断标准只有一句：

> 新加入团队的工程师，不看这条记录，写类似功能时大概率会写错吗？是则写入，否则跳过。

必须满足：

- 是跨业务、跨项目可复用的通用模式/原则/陷阱。
- 不是框架基础知识。
- 不是单一项目的一次性实现细节。
- 不记录账号、token、cookie、内部敏感参数。

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

脚本不会：

- 在 skill 包内创建知识库正文。
- 读取或写入旧 `references/` 结构。
- 记录密钥、token、cookie 等敏感信息。
- 未经用户配置就把知识写到默认路径。
