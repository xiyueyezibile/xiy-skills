# team-pitfalls 仓库级业务知识池设计

## 背景

当前 `team-pitfalls` 只覆盖跨仓库通用踩坑规则，明确排除了特定业务含义。这会导致一个实际问题：当 AI 在某个业务仓库里被纠正了术语理解、流程语义或业务上下文后，这类修正无法沉淀到仓库级知识池中，后续面对相同或相似仓库时仍可能重复犯错。

本次设计目标是将 `team-pitfalls` 扩展为双层知识结构：

- 保留现有通用规则库，继续沉淀跨仓库可复用原则。
- 新增仓库级业务知识池，按仓库名分目录沉淀业务黑话和 AI 被纠正后的正确认知。

## 目标

1. 让 `team-pitfalls` 支持按仓库名归档业务知识。
2. 默认同时沉淀两类仓库级知识：
   - 业务黑话 / 术语映射
   - AI 错判 -> 用户修正 -> 后续判断规则
3. 让后续 AI 在进入某个仓库相关任务时，优先加载该仓库知识，再加载通用规则。
4. 保持最小改动原则，不引入新的存储介质，继续以 Markdown 为主。

## 非目标

1. 不将所有历史通用条目迁移到仓库级目录。
2. 不引入数据库、JSON-only 存储或服务化索引。
3. 不尝试用仓库路径、owner 或远程地址做唯一主键。
4. 不解决不同组织下同名仓库的隔离问题；按用户要求，同名仓库复用同一知识池。

## 核心决策

### 仓库主键

- 仓库级知识池以“仓库名”作为唯一主键。
- 同名仓库默认复用同一份知识池。

### 知识分层

- **通用层**：继续使用 `references/*.md`，只记录跨仓库通用规则。
- **仓库层**：新增 `references/repos/<repo-name>/`，记录只对该仓库及其同名仓库复用语境成立的知识。

### 仓库层知识类型

- **Glossary**：业务黑话、术语映射、缩写解释、上下游别名。
- **Corrections**：AI 曾经的错误理解、用户修正、后续判断规则。

## 目录设计

在现有结构基础上新增：

```text
skills/team-pitfalls/
  references/
    INDEX.md
    mcp-and-internal-content.md
    git-and-commit.md
    docs-and-portability.md
    repos/
      <repo-name>/
        INDEX.md
        glossary.md
        corrections.md
```

约束如下：

1. 原有 `references/*.md` 不改语义，继续只承载通用规则。
2. `references/repos/<repo-name>/glossary.md` 只承载术语、黑话、简称、映射关系。
3. `references/repos/<repo-name>/corrections.md` 只承载 AI 被纠正过的业务误判。
4. `references/repos/<repo-name>/INDEX.md` 只作为当前仓库局部索引，不和全局 `INDEX.md` 混用。

## 运行流程

### 1. 仓库级校验

触发条件：

- 当前任务明确落在某个仓库里。
- 用户正在纠正某个仓库相关的业务理解。

执行顺序：

1. 识别当前仓库名。
2. 读取 `references/repos/<repo-name>/INDEX.md`。
3. 按需加载 `glossary.md` 和 `corrections.md`。
4. 用仓库级知识校验当前输出。
5. 如仍涉及通用规范问题，再补充通用层校验。

### 2. 通用校验

触发条件：

- 用户指出输出不符合通用规范。
- 当前任务本身属于通用规范性输出。

执行顺序：

1. 读取全局 `references/INDEX.md`。
2. 按原有类型判定加载 1~2 个通用案例文件。
3. 只校验跨仓库通用问题。

### 3. 沉淀写入

触发条件：

- 用户显式要求沉淀黑话、经验、误判修正。
- 用户纠正了 AI 对业务概念、业务流程、术语映射的理解。

写入规则：

- 业务术语、简称、黑话、映射关系 -> 写入 `glossary.md`
- “AI 原理解错误，用户给出正解” -> 写入 `corrections.md`
- 跨仓库通用原则 -> 继续写原有通用案例库

优先级规则：

```text
仓库级校验 > 通用校验
仓库级沉淀 与 通用沉淀 可同时发生，但不能混写到同一文件
```

## 文件格式

### glossary.md

```md
## 业务黑话 / 术语映射

### G-001: XX 指的是 YY
- **标签**: 术语, 黑话, 缩写
- **首次出现**: YYYY-MM-DD
- **最近出现**: YYYY-MM-DD
- **出现次数**: N
- **标准含义**: <这个词在该仓库里到底指什么>
- **常见误解**:
  - <AI 或新同学容易误解成什么>
- **正确理解**:
  - <正确语义、上下文边界、必要时补一个反义概念>
- **最小示例**:
  - <一句话示例>
- **适用范围/不适用范围**:
  - 适用: <哪些场景>
  - 不适用: <哪些场景>
```

### corrections.md

```md
## AI 纠错记录

### C-001: AI 把 XX 理解成 YY，实际应为 ZZ
- **标签**: 纠错, 业务理解, 术语误判
- **首次出现**: YYYY-MM-DD
- **最近出现**: YYYY-MM-DD
- **出现次数**: N
- **错误理解**: <AI 当时怎么理解的>
- **用户修正**: <用户明确指出的正确说法>
- **修正结论**: <下次遇到类似表述应如何判断>
- **触发线索**:
  - <哪些词、上下文、文件路径会触发这个判断>
- **最小示例**:
  - 错: <一句>
  - 对: <一句>
- **适用范围/不适用范围**:
  - 适用: <哪些仓库语境>
  - 不适用: <哪些相似但不同的语境>
```

### INDEX.md

```md
## Repo Pitfalls Index

| ID | 类型 | 标题 | 标签 | 文件 |
|---|---|---|---|---|
```

## 脚本改造设计

### upsert_pitfall.py

保留现有通用写入逻辑，并扩展以下能力：

1. 新增 `--repo <repo-name>` 参数。
2. 新增 `--kind glossary|corrections` 参数。
3. 当传入 `--repo` 时，写入路径切到 `references/repos/<repo-name>/`。
4. 自动创建缺失的 `INDEX.md`、`glossary.md`、`corrections.md`。
5. 根据 `--kind` 选择条目模板和编号前缀：
   - `glossary` -> `G-xxx`
   - `corrections` -> `C-xxx`
6. 保留原有“标题相同或指定 ID 则更新最近出现时间和出现次数”的逻辑。
7. 更新对应仓库的局部 `INDEX.md`。

建议命令：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind glossary --json '<json>'
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind corrections --json '<json>'
```

### delete_pitfall.py

扩展以下能力：

1. 支持 `--repo <repo-name>`。
2. 支持 `--kind glossary|corrections`。
3. 删除仓库级条目时同步更新该仓库的 `INDEX.md`。
4. 保留原有通用条目删除逻辑。

## SKILL.md 改造设计

`SKILL.md` 需要做以下结构性调整：

1. 描述从“只收集通用坑”改为“通用规则 + 仓库级业务知识池”。
2. 删除“绝对不能包含特定业务含义”的硬限制，改为：
   - 通用层仍然禁止写入单一业务细节；
   - 仓库层允许写入该仓库可复用的业务黑话和纠错规则。
3. 新增仓库级触发、校验、写入说明。
4. 明确先加载仓库级知识，再加载通用规则。
5. 增加 glossary/corrections 的条目模板和命令示例。

## 兼容策略

1. 现有通用条目、全局 `INDEX.md` 和原脚本参数保持兼容。
2. 未指定 `--repo` 时，脚本行为与现状一致。
3. 只有命中仓库级场景时，才读取 `references/repos/<repo-name>/`。
4. 仓库目录不存在时按需初始化，不要求预先建仓库清单。

## 风险与约束

1. 同名仓库会共享知识池，这是本次明确接受的约束。
2. 仓库名如果包含不适合作为目录名的字符，脚本需要做最小限度规范化；规范化规则需稳定且可逆性不是目标。
3. 业务纠错记录不能包含敏感信息、账号、token、cookie 或内部链接参数。
4. 仓库级知识不能回写到通用层，避免污染全局规则。

## 验证标准

完成实现后，至少应满足：

1. 能为一个新仓库自动创建 `references/repos/<repo-name>/` 及 3 个基础文件。
2. 能成功新增一条 glossary 记录并写入仓库局部 `INDEX.md`。
3. 能成功新增一条 corrections 记录并写入仓库局部 `INDEX.md`。
4. 再次写入相同标题时，只更新最近出现时间和出现次数，不重复造条目。
5. 原有通用 `P-xxx` 写入与删除逻辑不回归。

## 后续实现范围

本次实现仅覆盖：

1. `skills/team-pitfalls/SKILL.md`
2. `skills/team-pitfalls/scripts/upsert_pitfall.py`
3. `skills/team-pitfalls/scripts/delete_pitfall.py`
4. 仓库级 references 模板与必要示例文件

不做额外测试脚手架，不扩展到其他 skill。
