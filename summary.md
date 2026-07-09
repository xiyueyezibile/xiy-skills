# 对话总结

## 主题

1. 将 `team-pitfalls` 从 skill 包内置踩坑库升级为外部 LLM Wiki root 管理。
2. 设计一个新的 `reply-generator` skill，用于基于上下文和模板生成自然回复。
3. 为仓库 `README.md` 新增一组 Ian 小黑风格的正文配图。

## 已确认决策

### team-pitfalls

1. 使用 `skill-creator` 修改 `team-pitfalls`。
2. 踩坑记录不再写入当前 `team-pitfalls` skill 包，而是写入用户指定的外部 LLM Wiki root。
3. 以 `llms.txt` 作为 LLM 入口，以 `index.md` 作为全量索引。
4. 以 `repos/<repo-name>/` 作为仓库级目录主键，相同仓库名复用同一知识池。
5. 仓库级默认同时记录两类内容：
   - 业务黑话 / 术语映射
   - AI 找错后被用户修正的纠错记录
6. 推荐实现方案为标准 LLM Wiki 结构：
   - `llms.txt`
   - `index.md`
   - `pitfalls/*.md`
   - `repos/<repo-name>/index.md`
   - `repos/<repo-name>/glossary.md`
   - `repos/<repo-name>/corrections.md`
7. 运行优先级确定为：
   - 仓库级校验 > 通用校验
   - 仓库级沉淀和通用沉淀可以同时发生，但不能混写
8. `team-pitfalls` 的使用流程升级为固定两段：
   - 对话前先检查已有坑
   - 对话结束前再复盘是否有新坑值得沉淀
9. 这次抛弃旧 `references/INDEX.md + 分类 md + repos/` 存储结构，并提供迁移脚本把旧记录导入外部 LLM Wiki root。

### reply-generator

1. 使用 `skill-creator` 创建新的回复生成 skill，目录名定为 `skills/reply-generator/`。
2. 默认输出 `2-3` 个候选回复，并明确给出一个推荐项。
3. 输入同时支持：
   - 用户直接贴聊天记录/对话片段
   - 用户只给场景和目标
   - 有原始对话时优先模仿原话
4. 模板指定支持：
   - 直接点名模板
   - 只描述风格
   - 命中模板时优先用模板，命不中按风格描述生成
5. 适用范围覆盖聊天、职场沟通、评论回复。
6. `references` 按“模板”组织，每个模板包含：
   - 适用场景
   - 不适用场景
   - 语气特征
   - 节奏与长度
   - 常用句式骨架
   - 高频表达偏好
   - 禁用表达
   - 生成约束
   - 示例
7. 采用“模板 + 风格标签映射”方案：
   - `INDEX.md` 维护模板清单
   - `style-mapping.md` 维护自然语言风格词到模板的映射
8. 生成优先级确定为：
   - 场景安全 > 上下文语气 > 指定模板 > 默认风格补全
9. 当上下文不足或风格与场景冲突时：
   - 先给一句简短风险提示
   - 仍然给 `2` 个偏保守候选
10. 通用要求：
   - 回复不能 AI 味重
   - 尽量模仿上下文中用户的说话习惯和方式
11. 为了支持后续扩展，新模板按固定骨架维护：
   - `skills/reply-generator/references/templates/TEMPLATE.md` 作为标准模板
   - 新增模板时同步更新 `INDEX.md` 和 `style-mapping.md`

### README 配图

1. 使用 `ian-xiaohei-illustrations` 为仓库 README 生成正文配图。
2. 不平均配图，只选 3 个认知锚点：
   - skills 仓库定位与发现
   - 本地安装/接入
   - reply-generator 的模板扩展
3. 采用本地 SVG 资产落盘，而不是依赖外部生图结果。
4. 资产目录固定为 `assets/readme-illustrations/`。
5. 当前已生成：
   - `01-skills-cabinet.svg`
   - `02-install-machine.svg`
   - `03-template-growth.svg`
6. README 已插入对应图片引用，后续新增 README 配图继续沿用该目录。
7. README 额外补充了第三方 skill 推荐条目：
   - `https://github.com/helloianneo/ian-xiaohei-illustrations`

## 已产出文档

- `docs/superpowers/specs/2026-07-02-team-pitfalls-repo-knowledge-design.md`
- `docs/superpowers/specs/2026-07-03-reply-generator-design.md`

## 后续待做

1. 请用户审阅已写好的 spec。
2. 用户确认 `reply-generator` 设计后，进入实现计划与代码改造。
