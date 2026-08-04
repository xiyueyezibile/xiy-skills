# Team Pitfalls 知识沉淀规范

仅在写入、删除知识或维护本 Skill 时读取。

常规任务中，新增、更新、删除知识，以及累计 `使用次数`，都优先通过脚本修改 `~/.team-pitfalls-wiki` 下的 Markdown 页面和索引。`upsert_pitfall.py`、`delete_pitfall.py` 与 `record_pitfall_usage.py` 是默认写入链路；agent 只负责判断作用域、生成结构化 payload 和调用脚本。若脚本被沙箱、权限或工具策略拦截，agent 可降级为自然写入 Markdown 与索引。

## Wiki 结构

```text
~/.team-pitfalls-wiki/
  SCHEMA.md
  llms.txt
  index.md
  domains/index.md
  domains/<domain-name>/index.md
  domains/<domain-name>/glossary.md
  domains/<domain-name>/corrections.md
  pitfalls/*.md
  repos/<repo-name>/index.md
  repos/<repo-name>/glossary.md
  repos/<repo-name>/corrections.md
  repos/<repo-name>/domains/<domain-name>/index.md
  repos/<repo-name>/domains/<domain-name>/glossary.md
  repos/<repo-name>/domains/<domain-name>/corrections.md
```

- `P-*`：跨项目通用坑位。
- `G-*`：仓库或领域术语。
- `C-*`：仓库或领域 AI 纠错。
- `domains/<domain-name>/`：跨仓库的全局领域级知识，用于描述某类业务在多个仓库中的共同规则，并反向关联相关仓库。
- `repos/<repo-name>/domains/<domain-name>/`：当前仓库内的领域级知识，用于描述该仓库里某类业务、某个页面、某条链路或相近范围的规则。

每个领域的 `index.md` 必须有一段简短介绍，说明该领域覆盖的业务、页面/链路范围、典型术语或指标边界。写入领域级条目时，优先通过 payload 的 `domain_description` 补充；未提供时使用默认简介，后续人工补充的简介不得被刷新逻辑覆盖。

`llms.txt` 遵循 LLM 入口文件的轻量约定：一个 H1、简短摘要、少量上下文说明和 H2 分组链接；它是 curated map，不是 sitemap。`SCHEMA.md` 作为结构与维护规则入口，`index.md` 是全量条目索引，具体页面保持自包含、可整页读取，不依赖 chunk 拼接。

## 从案例抽象通用知识

按“案例事实 → 失效机制 → 条件式规则 → 跨场景验证 → 适用边界”处理。

通用规则使用“当……时，应先……，否则……”表达。至少给出原案例的抽象表达和一个不同场景的迁移例；无法给出第二场景时，只保留为领域级或仓库级知识。

通用条目必须满足：

- 标题描述机制或决策规则，不以仓库、页面或接口名为主语。
- 结论包含条件、动作和风险。
- 原因解释错误假设为何看似合理。
- 正反例体现同一判断点。
- 标签包含机制词和常见触发词。
- 明确适用与不适用范围。

不要生成带 `TODO` 的低信息量通用条目。已有通用条目覆盖同一机制时，只累计 `使用次数`。

## 领域级与仓库级记录隔离

领域术语和领域级 AI 纠错只在同一个 `repos/<repo-name>/domains/<domain-name>/` 下判断是否已有。仓库术语和仓库级 AI 纠错只在同一个 `repos/<repo-name>/` 下判断是否已有。其他仓库或其他领域已有相同或相近机制时，只能作为撰写当前记录的参考，不能阻止当前仓库/领域新增记录。

应该放进领域级的知识：

- 这部分知识属于某类业务，例如达人、选品、招商、订单、结算、投放、观测等。
- 这个坑属于某个页面、页面簇、路由、业务入口或端内链路。
- 这个术语、接口、埋点、指标或配置只在某个业务域内有稳定含义。
- 类似问题会在同一业务域内反复出现，但不一定影响整个仓库。

应该放进全局领域级的知识：

- 同一个业务领域跨多个仓库存在共同规则、术语、页面口径或坑位。
- 需要从一个仓库反向发现其他仓库的同领域记录。
- 领域规则不属于单个仓库实现细节，但又没有通用到所有项目。

当本轮纠错或术语会在当前领域复发时：

- 当前领域已有等价 `G-*`/`C-*`：更新 `使用次数`，不新增。
- 只有当前仓库或其他领域已有等价记录：在当前领域新增 `G-*`/`C-*`，并按当前领域的页面、接口、业务术语或链路重写适用范围。
- 规则跨仓库复用但未达到全局通用：另写或更新 `domains/<domain-name>/glossary.md` 或 `domains/<domain-name>/corrections.md`，用于全局领域级反查。
- 无法归属具体领域但会在当前仓库复发：写入仓库级 `repos/<repo-name>/glossary.md` 或 `repos/<repo-name>/corrections.md`。
- 机制足够跨项目复用且满足通用条目标准：可另行沉淀 `P-*`，但不能替代必要的当前仓库记录。

领域级和仓库级新增记录必须填写标签、错误理解/常见误解、用户修正/正确理解、结论、触发线索、最小示例、适用范围和不适用范围；不要留下 `TODO` 占位。

知识条目默认只保留 `使用次数` 这一统计字段；不要再新增 `出现次数`、`最近使用`、`首次出现`、`最近出现`。更新已有条目时，如果旧记录里还存在这些字段，应在同次更新中移除。

## 脚本写入

新增、更新、删除知识时：

1. 先按作用域决定目标文件：`pitfalls/`、`domains/<domain>/`、`repos/<repo>/` 或 `repos/<repo>/domains/<domain>/`。
2. 打开 [manual-edit-template.md](manual-edit-template.md)，按对应模板组织 `upsert_pitfall.py` 的 JSON payload 或 CLI 参数。
3. 调用脚本写正文页，并由脚本同步刷新 `index.md`、`llms.txt`、相关 repo/domain `index.md`。
4. 更新已有条目时只做最小改动：脚本按同作用域同标题或显式 `id` 命中后默认只累计 `使用次数`，并删除旧的 `出现次数`、`最近使用`、`首次出现`、`最近出现` 字段；确实需要补强正文时传 `--replace-existing`。
5. 删除条目时调用 `delete_pitfall.py` 移除正文块和索引行；若某个 repo/domain 索引暂无条目，脚本保留页面并写 `暂无条目。`
6. 采用已有条目时调用 `record_pitfall_usage.py --id <entry-id>`，不要手工改计数字段。
7. 如果第 3 到 6 步的脚本调用被沙箱、权限或工具策略拦截，按 [manual-edit-template.md](manual-edit-template.md) 降级为 agent 自然写入，并在最终答复里说明降级原因。
8. 完成后再运行 `end_task.py` 记录 `recorded` 或 `skipped`。

Wiki root 固定使用 `~/.team-pitfalls-wiki`；不支持 `--wiki-root`、环境变量或配置文件覆盖。

## 默认写入脚本

以下脚本是常规任务默认链路：

- `upsert_pitfall.py`：根据 JSON/CLI 参数写入或更新条目，并刷新相关索引；命中已有条目时默认只累计使用次数，传 `--replace-existing` 才重写正文。
- `delete_pitfall.py`：按 `ID` 或 `title` 删除条目，并刷新相关索引。
- `record_pitfall_usage.py`：按 `ID` 批量累计 `使用次数`，并清理旧统计字段。

只有脚本被沙箱、权限或工具策略拦截、脚本缺少表达能力、需要修复损坏 Markdown，或维护者明确要求排障时，才直接编辑 Wiki Markdown。手工编辑后仍必须保持正文页、`index.md`、`llms.txt` 和相关 repo/domain index 一致。

## 计数口径

- 使用次数：前置分层记录实际影响本轮判断、方案或实现。

同一轮同一条最多记录一次；分层记录未采用不计数。

## 产物路径

测试与自动化产物统一使用 UTF-8 相对 POSIX 路径：

```text
artifacts/repos/<repo-slug>/<file-slug>.<ext>
```

使用 `normalize_artifact_path.py` 归一化，不暴露临时绝对路径。
