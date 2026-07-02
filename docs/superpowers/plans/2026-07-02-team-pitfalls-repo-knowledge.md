# team-pitfalls Repo Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `team-pitfalls` 增加按仓库名分目录的业务黑话与 AI 纠错沉淀能力，同时保持原有通用坑位写入与删除逻辑兼容。

**Architecture:** 保留现有通用 `references/*.md` 和 `P-xxx` 编号体系；新增 `references/repos/<repo-name>/` 作为仓库级知识池，按 `glossary.md` 与 `corrections.md` 分文件存储，并由增强后的 upsert/delete 脚本统一维护局部索引与条目增删更新。

**Tech Stack:** Markdown, Python 3, argparse, pathlib, regex

## Global Constraints

- 所有改动遵循最小原则，只改 `team-pitfalls` 相关文件。
- 仓库级记录集中放在当前 skill 仓库中，不写入业务仓库。
- 仓库主键使用仓库名；同名仓库复用同一知识池。
- 仓库级默认同时支持业务黑话与 AI 纠错记录。
- 保持现有通用 `P-xxx` 写入与删除命令兼容。
- 本次不新增自动化测试文件，使用命令级验证。

---

### Task 1: 更新 skill 文档

**Files:**
- Modify: `skills/team-pitfalls/SKILL.md`

**Interfaces:**
- Consumes: 现有 `team-pitfalls` 通用规则描述
- Produces: 仓库级触发、校验、写入规范；新命令示例；新条目模板

- [ ] **Step 1: 改写 skill 描述与目标**

在 frontmatter 和正文开头中明确：

```md
description: 团队踩坑与仓库业务知识收集器。只要用户提到“收集问题/踩坑/容易写错/沉淀经验/团队规范/业务黑话/术语映射/AI 找错被纠正”等，就必须调用本 skill 做通用规则或仓库级知识沉淀；只要用户指正“上一轮输出不符合规范/不对/不符合约定/业务理解错了”，就必须先加载仓库级知识和通用规则做原则校验，再修正输出。
```

- [ ] **Step 2: 增加仓库级知识池章节**

补充 `references/repos/<repo-name>/INDEX.md`、`glossary.md`、`corrections.md` 的职责说明与优先级：

```md
仓库级校验 > 通用校验
仓库级沉淀与通用沉淀可同时发生，但不能混写
```

- [ ] **Step 3: 增加命令示例与模板**

补充以下命令和 `G-xxx` / `C-xxx` 模板：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind glossary --json '<json>'
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind corrections --json '<json>'
python3 skills/team-pitfalls/scripts/delete_pitfall.py --repo <repo-name> --kind glossary --id G-001
```

### Task 2: 扩展 upsert 脚本

**Files:**
- Modify: `skills/team-pitfalls/scripts/upsert_pitfall.py`

**Interfaces:**
- Consumes: 现有 `--type/--file/--json` 通用写入接口
- Produces: 新增 `--repo/--kind` 仓库级写入接口；仓库级目录初始化；局部索引维护

- [ ] **Step 1: 增加仓库级参数与路由**

实现以下参数：

```python
parser.add_argument("--repo", help="仓库名，用于写入 references/repos/<repo>/")
parser.add_argument("--kind", choices=("glossary", "corrections"))
```

规则：

- 指定 `--repo` 时进入仓库级写入流程
- 未指定 `--repo` 时保持原逻辑

- [ ] **Step 2: 增加仓库级模板与编号**

增加 `GlossaryEntry` / `CorrectionEntry` 兼容解析，或沿用统一 dataclass 但按 `--kind` 渲染不同 block。

编号规则：

```python
glossary -> G-001
corrections -> C-001
pitfalls -> P-001
```

- [ ] **Step 3: 增加仓库目录初始化**

为 `references/repos/<repo-name>/` 自动创建：

```text
INDEX.md
glossary.md
corrections.md
```

- [ ] **Step 4: 更新仓库局部索引**

仓库级 `INDEX.md` 使用：

```md
| ID | 类型 | 标题 | 标签 | 文件 |
```

- [ ] **Step 5: 保持既有兼容**

保留：

- `--type mcp|git|docs`
- `--file`
- 按标题或 ID 更新既有条目
- `--dry-run`

### Task 3: 扩展 delete 脚本

**Files:**
- Modify: `skills/team-pitfalls/scripts/delete_pitfall.py`

**Interfaces:**
- Consumes: 现有 `--id/--title` 删除接口
- Produces: 仓库级 `--repo/--kind` 删除能力；同步更新仓库局部索引

- [ ] **Step 1: 增加仓库级参数**

实现：

```python
parser.add_argument("--repo", help="仓库名")
parser.add_argument("--kind", choices=("glossary", "corrections"))
```

- [ ] **Step 2: 按上下文选择目标索引与文件目录**

规则：

- 指定 `--repo` 时，索引为 `references/repos/<repo>/INDEX.md`
- 否则继续使用全局 `references/INDEX.md`

- [ ] **Step 3: 复用删除逻辑**

保持按 `--id` 或 `--title` 查找，再同步删除：

- 条目所在 markdown block
- 对应 INDEX 行

### Task 4: 新增仓库级模板文件并做命令验证

**Files:**
- Create: `skills/team-pitfalls/references/repos/.gitkeep` 或等价占位文件
- Optional Create: `skills/team-pitfalls/references/repos/README.md`

**Interfaces:**
- Consumes: 修改后的脚本
- Produces: 可验证的仓库级目录结构与命令样例

- [ ] **Step 1: 提供仓库级目录占位**

创建 `references/repos/README.md`，说明该目录用于按仓库名存放 `INDEX.md`、`glossary.md`、`corrections.md`。

- [ ] **Step 2: 运行仓库级 dry-run 验证**

运行：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --dry-run --repo demo-repo --kind glossary --json '{"title":"ROI 在该仓库表示投放回收","tags":["术语","黑话"],"standard_meaning":"ROI 表示投放回收","common_misunderstandings":["不要理解成图像区域"],"correct_understanding":["在该仓库中指投放收益回收指标"],"min_examples":["ROI 需要按渠道拆分"],"scope":{"apply":"投放分析语境","not_apply":"计算机视觉语境"}}'
```

预期：打印 `glossary.md` 与局部 `INDEX.md` diff。

- [ ] **Step 3: 运行仓库级真实写入和更新验证**

运行两次同标题写入，确认第二次只增加出现次数并刷新最近出现。

- [ ] **Step 4: 运行仓库级删除验证**

运行删除命令，确认条目与局部索引同时删除。

- [ ] **Step 5: 运行通用回归验证**

运行一条原有 `--type git --dry-run` 命令，确认通用逻辑仍可用。
