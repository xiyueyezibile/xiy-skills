# 对话总结

## 主题

将 `team-pitfalls` 从“通用踩坑库”扩展为“通用规则 + 仓库级业务知识池”。

## 已确认决策

1. 使用 `skill-creator` 修改 `team-pitfalls`。
2. 仓库级记录不落到业务仓库，继续集中写在当前 `team-pitfalls` skill 仓库内。
3. 以仓库名作为分目录主键。
4. 相同仓库名复用同一知识池。
5. 仓库级默认同时记录两类内容：
   - 业务黑话 / 术语映射
   - AI 找错后被用户修正的纠错记录
6. 推荐实现方案为“分层索引”：
   - 通用规则保留在现有 `references/*.md`
   - 新增 `references/repos/<repo-name>/`
   - 每个仓库下维护 `INDEX.md`、`glossary.md`、`corrections.md`
7. 运行优先级确定为：
   - 仓库级校验 > 通用校验
   - 仓库级沉淀和通用沉淀可以同时发生，但不能混写

## 已产出文档

- `docs/superpowers/specs/2026-07-02-team-pitfalls-repo-knowledge-design.md`

## 后续待做

1. 请用户审阅 written spec。
2. 用户确认后，进入实现计划与代码改造。
