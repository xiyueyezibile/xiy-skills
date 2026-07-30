# LLM Wiki 规则

`prd-to-tech-code` 使用用户级 LLM Wiki 记录 PRD、已有技术方案、相关上下文、资料图材料、跨轮手动纠正、仓库代码证据、关键决策和技术方案依据。

固定根目录：

```text
~/.prd-to-tech-code
```

## 目录结构

按“每一个 PRD 业务”创建独立目录：

```text
~/.prd-to-tech-code/
  llms.txt
  config.json
  index.md
  businesses/
    <business-slug>/
      index.md
      repositories.md
      sources.md
      visual-materials.md
      code-evidence.md
      requirements.md
      decisions.md
      corrections.md
      constraints.md
      technical-plan.md
```

说明：

- `llms.txt`：全局导航入口，只放精选业务入口和读取顺序
- `config.json`：当前业务归属配置，至少记录 `currentBusinessSlug`，用于判断新输入默认写入哪个业务
- `index.md`：全局索引，列出已有业务、业务别名和最近关键结论
- `businesses/<business-slug>/index.md`：单个 PRD 业务的导航页
- `repositories.md`：该业务涉及的一个或多个仓库、仓库职责、改动范围和跨仓库关系
- `sources.md`：信息来源摘要，包含 PRD、已有技术方案、聊天记录、会议纪要、其他文档、用户口头说明、仓库证据和手动纠正
- `visual-materials.md`：资料图、设计稿、PRD 截图、流程图、架构图、时序图、改造前后示意和关键表格的来源与用途
- `code-evidence.md`：从仓库代码读取到的稳定事实，例如路由、页面、组件、类型、接口封装、权限、配置、数据流和既有业务规则
- `requirements.md`：稳定需求、业务规则、用户路径和状态流转
- `decisions.md`：已确认的技术决策、取舍和决策依据
- `corrections.md`：用户手动纠正、推翻过的错误理解和后续必须遵守的结论
- `constraints.md`：技术栈、仓库边界、接口限制、权限、灰度、上线和验证约束
- `technical-plan.md`：当前最新模板技术方案或方案摘要，必须包含能直接指导代码实现的文件级代码落位清单；如果输入是已有技术方案，这里保存归一化后的版本

## Business slug

业务目录名必须稳定、可读、无敏感信息。

生成规则：

1. 优先使用用户明确给出的业务名、页面名、项目名或 PRD 标题
2. 转为小写 kebab-case，例如 `order-price-adjustment`
3. 删除账号、手机号、工单号、token、内部敏感 ID 等信息
4. 如果同名业务已存在，先读取 `index.md` 判断是否为同一业务；不是同一业务时追加短后缀

## Current business config

根目录 `config.json` 用于标注当前输入默认属于哪个 PRD 业务。后续信息来源如果没有明确声明新业务，默认写入 `currentBusinessSlug` 对应业务。

推荐结构：

```json
{
  "currentBusinessSlug": null,
  "currentBusinessName": null,
  "currentBusinessSource": "unset",
  "updatedAt": null,
  "pendingBusinessConfirmation": null
}
```

字段说明：

- `currentBusinessSlug`：当前默认业务目录名
- `currentBusinessName`：业务展示名，可为空
- `currentBusinessSource`：`user` / `auto-created` / `confirmed` / `unset`
- `updatedAt`：最后更新日期，使用 `YYYY-MM-DD`
- `pendingBusinessConfirmation`：疑似新业务但尚未确认时填写，确认后清空

归属规则：

1. 用户明确指定业务时，更新 `currentBusinessSlug`
2. 没有当前业务时，根据 PRD 标题、页面名、项目名或需求目标创建 `business-slug`，并写入配置
3. 已有当前业务时，除非用户明确说是新业务，否则后续 PRD、聊天记录、文档、用户纠正和仓库证据都先写入当前业务
4. 如果输入与当前业务目标、用户路径、核心实体或交付边界差异过大，但用户没有明确说是新业务，先写入当前业务，同时设置 `pendingBusinessConfirmation`
5. 交付时必须提示用户确认 `pendingBusinessConfirmation` 是否应拆成新业务；用户确认后再创建新业务目录并更新配置

不要仅因为新增页面、接口、仓库或一次性补充文档就切换业务。

## Source policy

信息来源不只包括 PRD。处理任务时按需整合：

- PRD、产品文档、飞书文档、Markdown、截图 OCR 文本
- 已有技术方案、技术设计、改造方案、方案草稿、任务拆解
- 聊天记录、会议纪要、评论区讨论、口头补充
- 用户在对话中的手动纠正和临时决策
- 设计稿说明、接口文档、数据表说明、埋点文档
- PRD 截图、设计稿、流程图、架构图、时序图、改造前后示意和关键表格
- 仓库代码、已有配置、类型定义、路由、接口封装和运行约束

写入 `sources.md` 时记录摘要，不默认保存完整原文。不要记录密钥、token、cookie、个人隐私、客户敏感数据或与技术落地无关的聊天细节。

推荐格式：

```md
## S-001: 来源标题

- 来源类型：PRD / 技术方案 / 聊天记录 / 用户纠正 / 仓库证据 / 接口文档
- 时间：
- 可信度：高 / 中 / 低
- 摘要：
- 影响范围：
- 原始位置：
```

## Visual materials policy

技术方案是给人评审和执行的材料，应保留能帮助理解的资料图和改造示意。

可记录的视觉材料：

- PRD 或产品文档中的截图、流程图、表格
- 设计稿截图、页面标注、交互示意
- 聊天或会议材料里的改造前后截图
- 仓库已有文档中的架构图、链路图、接口图
- 当前方案生成的 Mermaid/ASCII 流程图、架构图、时序图、状态图

`visual-materials.md` 推荐格式：

```md
## V-001: 材料标题

- 材料类型：PRD截图 / 设计稿 / 流程图 / 架构图 / 时序图 / 改造前后示意 / 表格 / Mermaid
- 来源：
- 摘要：
- 用途：
- 关联章节：
- 是否进入技术方案：是 / 否
```

记录时只保存来源、摘要和用途；如材料包含敏感信息，优先做脱敏摘要，不复制原图内容。

## Repository policy

技术方案必须读取仓库代码。PRD、聊天记录或文档只能说明“想做什么”，仓库代码负责校验“当前系统实际怎么做”。

处理每个 PRD 业务时：

1. 先识别涉及的一个或多个仓库
2. 明确每个仓库的职责：前端、后端、BFF、组件库、接口 SDK、配置仓库、文档仓库或只读依赖
3. 分仓库读取相关路由、页面、组件、服务、类型、配置、接口封装、权限逻辑、状态流转和既有测试约定
4. 在 `repositories.md` 记录仓库边界，在 `code-evidence.md` 记录可复用代码事实
5. 技术方案中区分“需要修改的仓库”和“只作为证据读取的仓库”

`repositories.md` 推荐格式：

```md
## R-001: 仓库名

- 本地路径：
- 远程地址：
- 仓库职责：前端 / 后端 / BFF / 组件库 / SDK / 配置 / 文档 / 只读依赖
- 业务范围：
- 本次角色：需要修改 / 只读参考 / 待确认
- 关键入口：
- 与其他仓库关系：
```

`code-evidence.md` 推荐格式：

```md
## E-001: 代码事实标题

- 仓库：
- 代码位置：
- 证据类型：路由 / 页面 / 组件 / 服务 / 类型 / 接口封装 / 权限 / 配置 / 数据流 / 业务规则
- 事实摘要：
- 对技术方案的影响：
- 可信度：高 / 中 / 低
```

记录代码证据时只保存摘要、路径和稳定结论，不复制大段源码，不记录密钥、token、cookie、个人隐私或敏感业务数据。

## Reading order

开始处理一个 PRD 业务时：

1. 读取 `~/.prd-to-tech-code/llms.txt`、`config.json` 和全局 `index.md`
2. 按 Current business config 规则确定、创建或沿用 `business-slug`
3. 读取业务目录下的 `index.md`
4. 读取 `repositories.md` 和 `code-evidence.md`，确认已知仓库边界与代码事实
5. 按任务需要读取 `visual-materials.md`、`corrections.md`、`requirements.md`、`decisions.md`、`constraints.md`、`sources.md`
6. 再结合当前用户输入和最新仓库代码形成技术方案或执行计划

当存在冲突时，优先级为：

```text
用户本轮明确纠正 > 业务 corrections.md > 仓库事实 > 已确认 decisions.md > 最新 PRD/技术方案/文档 > 旧聊天记录/旧草稿
```

已有技术方案参与冲突判断时，只能作为“来源”或“待校验方案”。其中的文件路径、接口、类型、埋点、权限和配置必须经过仓库代码校验后，才能进入 `technical-plan.md` 的代码落位清单。

## Writing rules

每次任务结束前判断是否需要更新业务知识库。

必须写入的情况：

- 创建、切换或确认了当前业务归属
- 输入疑似新业务但用户尚未确认，需要在 `config.json.pendingBusinessConfirmation` 记录提醒
- 用户提供了已有技术方案、技术设计、改造方案、方案草稿或任务拆解，需要作为来源摘要保存
- 用户纠正了需求理解、接口含义、业务范围、状态流转、权限或技术方案
- 识别出后续评审或实现会复用的资料图、设计稿、PRD 截图、流程图、架构图、时序图或改造前后示意
- 识别出新的相关仓库、仓库职责、跨仓库契约或代码入口
- 从仓库代码读到了后续会复用的稳定事实、约束、接口封装、类型、权限或状态流转
- 发现 PRD 与仓库事实、接口文档或历史决策冲突
- 形成了后续会复用的业务规则、技术决策、约束或验证路径
- 技术方案已经更新或已有技术方案已被归一化，且会作为后续直出代码的依据
- 形成了文件级代码落位清单，后续会按该清单继续实现

不写入的情况：

- 一次性闲聊、无稳定业务价值的临时表达
- 敏感信息、账号信息、原始 token、cookie 或私密数据
- 只属于当前补丁的临时进度，后续不可复用

写入时遵循：

1. 业务归属变化写入根目录 `config.json`
2. 新信息无缝并入对应文件，不新增噪声小节
3. 资料图材料写入 `visual-materials.md`
4. 仓库边界写入 `repositories.md`，代码事实写入 `code-evidence.md`
5. 手动纠正写入 `corrections.md`，并同步更新 `index.md` 的关键结论
6. 技术方案更新写入 `technical-plan.md`；如果输入是已有技术方案，先作为来源写入 `sources.md`，再把归一化后的模板方案写入 `technical-plan.md`
7. `technical-plan.md` 必须保留必要资料图引用和文件级代码落位清单，必要时链接到 `decisions.md`
8. 对旧结论不要直接删除，除非用户明确要求；优先标注“已被 C-xxx 修正”
9. 同一业务内去重，避免把同一纠正、资料图或代码事实拆成多条近似记录

## Initialization

如果 `~/.prd-to-tech-code` 不存在，先创建基础结构：

```text
~/.prd-to-tech-code/
  llms.txt
  config.json
  index.md
  businesses/
```

基础 `llms.txt` 至少包含：

```md
# PRD To Tech Code LLM Wiki

Read `config.json` and `index.md` first, then open the relevant `businesses/<business-slug>/index.md`.
```

基础 `config.json` 至少包含：

```json
{
  "currentBusinessSlug": null,
  "currentBusinessName": null,
  "currentBusinessSource": "unset",
  "updatedAt": null,
  "pendingBusinessConfirmation": null
}
```

基础 `index.md` 至少包含：

```md
# PRD To Tech Code Index

## Businesses
```

创建新的 `businesses/<business-slug>/` 时，至少初始化：

```text
businesses/<business-slug>/
  index.md
  repositories.md
  sources.md
  visual-materials.md
  code-evidence.md
  requirements.md
  decisions.md
  corrections.md
  constraints.md
  technical-plan.md
```

业务 `index.md` 至少包含：

```md
# <Business Name>

## Reading Order

1. repositories.md
2. code-evidence.md
3. visual-materials.md
4. corrections.md
5. requirements.md
6. decisions.md
7. constraints.md
8. sources.md
9. technical-plan.md

## Key Conclusions
```
