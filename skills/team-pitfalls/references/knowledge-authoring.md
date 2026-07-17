# Team Pitfalls 知识沉淀规范

仅在写入、迁移、删除知识或维护本 Skill 时读取。

## Wiki 结构

```text
<wiki-root>/
  llms.txt
  index.md
  pitfalls/*.md
  repos/<repo-name>/index.md
  repos/<repo-name>/glossary.md
  repos/<repo-name>/corrections.md
```

- `P-*`：跨项目通用坑位。
- `G-*`：仓库术语。
- `C-*`：仓库级 AI 纠错。

## 从案例抽象通用知识

按“案例事实 → 失效机制 → 条件式规则 → 跨场景验证 → 适用边界”处理。

通用规则使用“当……时，应先……，否则……”表达。至少给出原案例的抽象表达和一个不同场景的迁移例；无法给出第二场景时，只保留为仓库级知识。

通用条目必须满足：

- 标题描述机制或决策规则，不以仓库、页面或接口名为主语。
- 结论包含条件、动作和风险。
- 原因解释错误假设为何看似合理。
- 正反例体现同一判断点。
- 标签包含机制词和常见触发词。
- 明确适用与不适用范围。

不要生成带 `TODO` 的低信息量通用条目。已有条目覆盖同一机制时，只累计出现次数。

## 安全传参

复杂 JSON 使用 UTF-8 文件，避免 shell 内联转义：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --wiki-root <path> \
  --type docs \
  --json-file "/tmp/pitfall payload.json"
```

`--json` 与 `--json-file` 互斥；`--json-file -` 从标准输入读取。文件路径含空格时必须作为单个参数传入。

仓库术语或纠错增加：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py \
  --wiki-root <path> \
  --repo <repo-name> \
  --kind glossary \
  --json-file <payload.json>
```

`--kind corrections` 写入纠错。删除使用：

```bash
python3 skills/team-pitfalls/scripts/delete_pitfall.py --wiki-root <path> --id P-001
```

迁移旧 references 使用 `migrate_references_to_llm_wiki.py`。

## 计数口径

- 出现次数：同类问题再次发生或再次被纠正。
- 使用次数：前置候选实际影响本轮判断、方案或实现。

同一轮同一条最多记录一次；候选未采用不计数。

## 产物路径

测试与自动化产物统一使用 UTF-8 相对 POSIX 路径：

```text
artifacts/repos/<repo-slug>/<file-slug>.<ext>
```

使用 `normalize_artifact_path.py` 归一化，不暴露临时绝对路径。
