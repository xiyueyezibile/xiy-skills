# Team Pitfalls 脚本写入与降级模板

新增、更新、删除知识，以及累计 `使用次数` 时，默认调用 `upsert_pitfall.py` / `delete_pitfall.py` / `record_pitfall_usage.py`。agent 先生成结构化 payload 并调用脚本；如果脚本被沙箱、权限或工具策略拦截，再降级为自然写入 Markdown 正文块和索引。

## 0. 先对齐目标文件风格

写入或降级前先读：

1. 目标正文文件里相邻的 1 到 3 个条目
2. 同级别另一个已存在页面（如果目标页为空）

然后遵守：

- **新增条目只保留 `使用次数`。**
- **不要再新增 `出现次数`、`最近使用`、`首次出现`、`最近出现`。**
- 若发现旧条目混有这些历史字段，更新时一并删掉。

## 1. 先决定作用域

| 作用域 | 正文文件 | 必刷索引 |
|---|---|---|
| 通用坑位 `P-*` | `pitfalls/*.md` | `index.md`, `llms.txt` |
| 全局领域术语/纠错 `domains/<domain>/` | `domains/<domain>/glossary.md` / `corrections.md` | `domains/<domain>/index.md`, `domains/index.md`, `index.md`, `llms.txt` |
| 仓库级术语/纠错 `repos/<repo>/` | `repos/<repo>/glossary.md` / `corrections.md` | `repos/<repo>/index.md`, `index.md`, `llms.txt` |
| 仓库领域级术语/纠错 `repos/<repo>/domains/<domain>/` | `repos/<repo>/domains/<domain>/glossary.md` / `corrections.md` | `repos/<repo>/domains/<domain>/index.md`, `repos/<repo>/index.md`, `domains/<domain>/index.md`, `domains/index.md`, `index.md`, `llms.txt` |

## 2. 新增条目 payload 模板

### 2.1 通用坑位 `P-*`

```json
{
  "title": "<标题>",
  "tags": ["<标签1>", "<标签2>", "<机制词>", "<触发词>"],
  "conclusion": "当……时，应先……，否则……",
  "reasons": ["<为什么这个误解看起来合理>"],
  "wrong": ["<错误动作>"],
  "right": ["<正确动作>"],
  "min_examples": ["<原案例的抽象表达>", "<一个跨场景迁移例>"],
  "scope_ok": "<适用范围>",
  "scope_no": "<不适用范围>"
}
```

调用：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --type docs --json-file <payload.json>
```

若脚本被拦截，按 payload 字段生成同结构 Markdown 正文块，并同步刷新索引。

### 2.2 术语 `G-*`

```json
{
  "title": "<标题>",
  "tags": ["<标签1>", "<标签2>"],
  "standard_meaning": "<标准定义>",
  "common_misunderstandings": ["<误解1>"],
  "correct_understanding": ["<正确理解1>"],
  "min_examples": ["<最小例子1>"],
  "scope_ok": "<适用范围>",
  "scope_no": "<不适用范围>",
  "domain_description": "<领域简介，可选>"
}
```

调用仓库领域级：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --domain <domain-name> --kind glossary --json-file <payload.json>
```

调用全局领域级：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --global-domain --domain <domain-name> --kind glossary --json-file <payload.json>
```

若脚本被拦截，按 payload 字段生成 `G-XXX` Markdown 正文块，并同步刷新目标作用域的所有索引。

### 2.3 纠错 `C-*`

```json
{
  "title": "<标题>",
  "tags": ["<标签1>", "<标签2>"],
  "wrong_understanding": "<错误理解>",
  "user_correction": "<用户修正>",
  "correction_conclusion": "当……时，应先……，否则……",
  "trigger_clues": ["<线索1>"],
  "min_examples": ["<最小例子1>"],
  "scope_ok": "<适用范围>",
  "scope_no": "<不适用范围>",
  "domain_description": "<领域简介，可选>"
}
```

调用仓库领域级：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --domain <domain-name> --kind corrections --json-file <payload.json>
```

若脚本被拦截，按 payload 字段生成 `C-XXX` Markdown 正文块，并同步刷新目标作用域的所有索引。

## 3. 更新已有条目模板

更新已有条目时，优先只做最小改动，并交给脚本执行：

- `使用次数`：仅在前置检查实际影响判断时才通过 `record_pitfall_usage.py --id <entry-id>` 或 `upsert_pitfall.py` 命中已有条目后 `+1`
- `出现次数` / `最近使用` / `首次出现` / `最近出现`：若旧条目里还有，脚本会在同次更新中删掉
- 标题、标签、结论、示例：仅在本轮确实补强了机制表达时才传 `--replace-existing` 重写正文

如果这轮只是“命中并实际采用”某条现有知识，而没有新增知识：

- 调用 `record_pitfall_usage.py --id <entry-id>`
- 同一轮同一条最多调用一次
- 然后用 `end_task.py --result recorded --used-entry-id <entry-id>` 记录
- 若 `record_pitfall_usage.py` 被沙箱、权限或工具策略拦截，agent 可自然编辑当前条目：`使用次数 +1`，并移除旧的 `出现次数` / `最近使用` / `首次出现` / `最近出现` 字段

如果需要补强已有条目正文：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --domain <domain-name> --kind corrections --replace-existing --json-file <payload.json>
```

更新时可按下面的核对清单执行：

```md
- [ ] 条目 ID 不变
- [ ] 只改当前条目块
- [ ] 只保留 `使用次数`
- [ ] `出现次数` / `最近使用` / 旧时间字段已清理
- [ ] index.md 标题/标签/文件路径仍一致
```

## 4. 删除条目

删除时先不要手写 Markdown，调用：

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py --id <entry-id>
```

若 `delete_pitfall.py` 被沙箱、权限或工具策略拦截，agent 再按下面顺序自然编辑 Markdown。

脚本会按下面顺序执行：

1. 删除正文页中对应 `### ID:` 开头的整块内容。
2. 删除 `index.md` 中对应行。
3. 刷新 `llms.txt`。
4. 刷新相关 repo/domain `index.md`。
5. 如果某个索引页没有条目了，保留页面并写：

```md
暂无条目。
```

## 5. 索引由脚本刷新

以下格式由脚本维护，只有脚本缺能力或 Wiki 损坏时才手工参考。

### 5.1 总索引 `index.md`

```md
| C-XXX | correction | <标题> | <标签1, 标签2> | <相对文件路径> |
```

kind 取值：

- `pitfall`
- `glossary`
- `correction`

### 5.2 领域索引 `domains/<domain>/index.md`

```md
# <domain> Global Domain

<领域简介>

## Related Repositories

- [<repo>](../../repos/<repo>/domains/<domain>/index.md)

## Global Domain Records

- `C-XXX` `correction` [<标题>](corrections.md)
```

### 5.3 仓库索引 `repos/<repo>/index.md`

```md
# <repo> Index

<repo> 的仓库级踩坑、术语和纠错记录。

## Domains

- [<domain>](domains/<domain>/index.md)

## Repo Records

- `G-XXX` `glossary` [<标题>](../../repos/<repo>/glossary.md)
```

### 5.4 仓库领域索引 `repos/<repo>/domains/<domain>/index.md`

```md
# <repo> / <domain> Index

<repo> 仓库 <domain> 领域的踩坑、术语和纠错记录。

- `C-XXX` `correction` [<标题>](../../../../repos/<repo>/domains/<domain>/corrections.md)
```

## 6. 最终自检

写完后至少检查：

```md
- [ ] 目标作用域正确，没有把仓库级/领域级/全局级混写
- [ ] 正文页、index.md、llms.txt 已同步
- [ ] 相关 repo/domain index 已同步
- [ ] 标题描述的是机制，不是临时案例名
- [ ] 标签包含机制词和触发词
- [ ] 结论是“当……时，应先……，否则……”
- [ ] 没有 TODO、敏感信息、绝对临时路径
```
