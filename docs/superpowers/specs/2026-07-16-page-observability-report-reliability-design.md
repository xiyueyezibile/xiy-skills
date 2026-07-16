# Page Observability Report 查询可靠性优化设计

## 背景

`internal-skills/page-observability-report` 已经约束了“先从代码反查页面，再查询指标”和“共享页按 `bid` 分端展示”，但仍缺少统一的指标口径、查询证据字段、歧义处理和可回归验证的测试场景。这会导致不同执行者得到不可比较的结果，或在路径、端归属和平台能力不完整时给出误导性结论。

本轮优先提升实际查询成功率和口径可靠性。HTML 自动生成器、完整 bytedcli 编排器和缓存重试系统不在本轮范围内。

## 目标

- 页面定位结论可追溯，并能正确处理共享页、外链页和同名页面。
- 每项指标都有明确的时间、聚合、过滤和来源口径。
- 查询失败时按确定的回退链路继续，且不伪造数据。
- 多 `bid` 页面始终保留分端结果，部分失败不会覆盖成功端。
- 通过最小 eval 集合验证关键行为，降低后续修改造成的回归。
- 保持 `SKILL.md` 精炼，将仓库专属规则和详细契约按需加载。

## 非目标

- 不封装完整的 bytedcli 查询客户端。
- 不自动处理内部平台授权。
- 不承诺所有指标在所有 `bid` 上都可查询。
- 不把当前内部 skill 迁移为公开可安装 skill。
- 不修改第三方 skill 或其 README 介绍。

## 方案选择

采用“查询契约化 + 最小测试集”。

相比只修正文案，该方案能把路径降级、多端拆分和失败披露变成可检查行为；相比完整查询编排器，它不绑定易变化的内部 CLI 返回格式，维护成本更低。

## 页面定位状态机

页面定位必须先调用或明确采用 `query-page-metrics-from-code` 的规则，依次确认：

1. 页面候选文件与路由。
2. 共享页面的实际挂载 package。
3. 入口页是否跳转到另一个真实目标工程。
4. 目标工程配置中的 `primary_bid`。
5. 查询阶段使用的 `query_bids`。
6. 需要 TEA 或自定义性能数据时使用的 `app_id`。

若出现多个候选：

- 同一页面的多端挂载继续归并分析。
- 不同页面仅名称相同时，列出候选证据并请求用户确认，不能擅自选择。

路径过滤按以下顺序降级：

1. `path` 严格匹配 `runtime_path`。
2. URL 包含已确认关键词。
3. `route_path` 匹配。

每次降级都记录 `filter_match_mode` 和不确定性说明。无法确认时使用 `unresolved`，不构造猜测值。

## 查询上下文契约

页面反查完成后，先形成结构化上下文。字段包括：

- `workspace_root`
- `repo_name`
- `page_clue`
- `page_file`
- `route_file`
- `route_path`
- `runtime_path`
- `package_name`
- `config_file`
- `primary_bid`
- `query_bids`
- `app_id`
- `proof`

条件字段采用三态：

- `confirmed`：值和证据均已确认。
- `not_required`：本次查询不需要该字段。
- `unresolved`：需要但尚未确认，并附原因。

## 指标结果契约

每个 `bid`、每项指标形成独立结果，至少包含：

- `metric`
- `bid`
- `value`
- `unit`
- `status`: `success | partial | failed`
- `start_at`
- `end_at`
- `timezone`
- `include_current_day`
- `aggregation`
- `filter_match_mode`
- `source`
- `retrieved_at`
- `query_evidence`
- `error_code`
- `failure_reason`

`query_evidence` 保存脱敏后的查询命令或等价参数，不记录 token、cookie 和账号信息。查询时同时记录实际 bytedcli 版本，避免 `latest` 行为漂移后无法复现。

## 默认指标口径

默认时间范围为最近 30 个完整自然日，时区为 `Asia/Shanghai`，不包含查询当天。若用户另有要求，以用户口径为准并写入报告。

默认聚合：

- PV：页面访问次数总和。
- UV：去重用户数；无法确认稳定用户标识时标记失败，不用 PV 推算。
- LCP/FCP/FP：使用平台页面性能指标的 p75；若平台只提供其他聚合值，保留实际聚合名，不改写为 p75。
- Page Time Spent：使用平台提供的页面停留时长平均值；同时标注样本口径。平台无稳定值时标记失败。
- JS Error：分别记录错误事件数和受影响用户数；只能取得其中之一时，不把它泛化成“错误率”。错误率仅在分子、分母同源且明确时计算。
- 2 秒开率：优先使用同源 `tti < 2000 / tti 总样本`。只有同源分解字段存在时才重建 tti；不能从 LCP/FCP/FP 推算。

## 多 `bid` 展示语义

所有指标先按 `bid` 保存和展示。

- 全部端成功：总览展示分端值；只有用户明确要求时才增加可加总指标的汇总。
- 部分端失败：总览状态为 `partial`，保留成功值，并逐端说明失败原因。
- 全部端失败：状态为 `failed`，显示“未取到”和逐端原因。
- LCP、FCP、FP、停留时长、错误率和 2 秒开率等非可加总指标禁止直接求和。
- PV、UV 也只有在确认各端用户口径不会重复或用户接受近似口径时才可汇总；否则只展示分端值。

## 查询与回退流程

1. 用明确的 `bid`、时间范围和页面过滤条件查询基础指标。
2. 对多个 `query_bids` 逐端执行，单端失败不终止其他端。
3. UV 或 2 秒开率失败时，先探测事件类型，再探测字段，确认可用的数据链路。
4. 若代码埋点属于 `sendLog`、`commonSendLog`、BTM 或 AppLog，静态事件可以列出，但不得声称已经通过 Slardar custom 在线确认；需要占比时转到 TEA/事件分析口径。
5. 权限不足、CLI 超时、平台不稳定、字段不存在和口径未确认使用不同失败原因，不合并成笼统的“查询失败”。

## 文件组织

- `SKILL.md`：保留触发条件、主状态机、强制交付门槛和资源路由。
- `references/repo-resolution-rules.md`：保存 `fe-buyin`、`fe-alliance-mobile` 等仓库专属反查规则。
- `references/metric-contract.md`：保存时间、聚合、结果字段、多端语义和回退规则。
- `references/report-spec.md`：继续定义 HTML 展示结构，并与指标契约对齐。
- `evals/evals.json`：保存真实任务风格的回归场景和断言。
- `internal-skills/README.md`：补充依赖、调用示例和仅限本地使用的说明。

本轮不新增 renderer 或查询脚本。若测试表明执行者持续遗漏结构字段，再单独设计确定性 validator。

## 测试设计

最小 eval 集覆盖：

1. `fe-buyin/global/pages` 三端共享页：三个 `query_bids` 均保留，非可加总指标不合并。
2. `fe-alliance-mobile` 入口跳外部 H5：使用目标工程的 `runtime_path` 和 `bid`，不用宿主页口径。
3. 两个同名独立页面：输出候选并请求确认，不擅自查询。
4. `runtime_path` 缺失：按 URL 关键词、`route_path` 降级并记录匹配方式。
5. 部分 `bid` 查询失败：成功端保留，总览为 `partial`。
6. UV 和 2 秒开率不可取：输出公式、探测过程和失败原因，不生成估值。
7. 业务日志埋点：区分静态代码事件与线上已确认字段。
8. 时间与聚合口径：检查完整自然日、时区、p75 和 JS Error 统计类型。

评测以旧版 skill 快照为基线，重点检查新版是否减少口径缺失、错误合并和无依据推断。

## README 与发布边界

该 skill 位于被本地排除的 `internal-skills/`，不能声明可通过仓库远程安装。README 只提供本机路径、依赖、调用示例和复制/软链建议。若未来需要公开分发，应另行迁移到 tracked `skills/` 并同步根 README 的下载方式。

## 完成标准

- 依赖 skill 名称正确，页面反查不能被跳过。
- 默认时间和指标聚合口径明确。
- 同名页面、共享页和外链页均有确定处理规则。
- 每项指标具备可追溯字段和细分失败原因。
- 多端结果不会被错误汇总。
- eval 覆盖至少上述八类风险中的六类，并能与旧版比较。
- `internal-skills/README.md` 与实际使用方式一致。
- 不修改用户已有的无关工作区改动。
