# Team Pitfalls 手工编辑模板

新增、更新、删除知识，以及累计 `使用次数` 时，agent 直接编辑 `~/.team-pitfalls-wiki` 下的 Markdown 页面，不走 `upsert_pitfall.py` / `delete_pitfall.py` / `record_pitfall_usage.py` 默认写链路。

## 0. 先对齐目标文件风格

动手前先读：

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

## 2. 新增条目模板

### 2.1 通用坑位 `P-*`

```md
### P-XXX: <标题>
- **标签**: <标签1, 标签2, 机制词, 触发词>
- **使用次数**: 0
- **一句话结论**: 当……时，应先……，否则……
- **容易写错的原因**:
  - <为什么这个误解看起来合理>
  - <第二条原因，没有就删掉整行>
- **错误做法（反例）**:
  - <错误动作>
  - <第二个反例，没有就删掉整行>
- **正确做法（正例）**:
  - <正确动作>
  - <第二个正例，没有就删掉整行>
- **最小示例**:
  - <原案例的抽象表达>
  - <一个跨场景迁移例>
- **适用范围/不适用范围**:
  - 适用: <适用范围>
  - 不适用: <不适用范围>
```

### 2.2 术语 `G-*`

```md
### G-XXX: <标题>
- **标签**: <标签1, 标签2>
- **使用次数**: 0
- **标准含义**: <标准定义>
- **常见误解**:
  - <误解1>
  - <误解2，没有就删掉整行>
- **正确理解**:
  - <正确理解1>
  - <正确理解2，没有就删掉整行>
- **最小示例**:
  - <最小例子1>
  - <最小例子2，没有就删掉整行>
- **适用范围/不适用范围**:
  - 适用: <适用范围>
  - 不适用: <不适用范围>
```

### 2.3 纠错 `C-*`

```md
### C-XXX: <标题>
- **标签**: <标签1, 标签2>
- **使用次数**: 0
- **错误理解**: <错误理解>
- **用户修正**: <用户修正>
- **修正结论**: 当……时，应先……，否则……
- **触发线索**:
  - <线索1>
  - <线索2，没有就删掉整行>
- **最小示例**:
  - <最小例子1>
  - <最小例子2，没有就删掉整行>
- **适用范围/不适用范围**:
  - 适用: <适用范围>
  - 不适用: <不适用范围>
```

## 3. 更新已有条目模板

更新已有条目时，优先只做最小改动：

- `使用次数`：仅在前置检查实际影响判断时才 `+1`
- `出现次数` / `最近使用` / `首次出现` / `最近出现`：若旧条目里还有，这次一并删掉
- 标题、标签、结论、示例：仅在本轮确实补强了机制表达时再改

如果这轮只是“命中并实际采用”某条现有知识，而没有新增知识：

- 有 `使用次数` 就 `+1`
- 没有 `使用次数` 就补一行 `- **使用次数**: 1`
- 如果还残留 `出现次数` / `最近使用` 等旧字段，顺手删掉

更新时可按下面的核对清单执行：

```md
- [ ] 条目 ID 不变
- [ ] 只改当前条目块
- [ ] 只保留 `使用次数`
- [ ] `出现次数` / `最近使用` / 旧时间字段已清理
- [ ] index.md 标题/标签/文件路径仍一致
```

## 4. 删除条目模板

删除时不要整页删除，按下面顺序：

1. 删除正文页中对应 `### ID:` 开头的整块内容。
2. 删除 `index.md` 中对应行。
3. 刷新 `llms.txt`。
4. 刷新相关 repo/domain `index.md`。
5. 如果某个索引页没有条目了，保留页面并写：

```md
暂无条目。
```

## 5. 索引模板

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
