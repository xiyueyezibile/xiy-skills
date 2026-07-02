## Repo-Level Knowledge

这个目录用于按仓库名维护 `team-pitfalls` 的仓库级知识池。

每个仓库目录固定包含：

- `INDEX.md`: 当前仓库的局部索引
- `glossary.md`: 业务黑话、术语映射、缩写解释
- `corrections.md`: AI 被纠正过的业务理解记录

目录由脚本按需自动创建：

```bash
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind glossary --json '<json>'
python3 skills/team-pitfalls/scripts/upsert_pitfall.py --repo <repo-name> --kind corrections --json '<json>'
```
