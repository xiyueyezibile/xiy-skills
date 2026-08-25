
## Skills List

![skills cabinet](assets/readme-illustrations/01-skills-cabinet.svg)

### xiy-llm-wiki

个人 LLM Wiki Skill：维护一个独立的 Git Wiki 仓库，将原始资料和对话结论编译成结构化、可交叉链接的个人知识库，并识别当前正在处理的业务仓库和工作内容。

`~/.xiy/config.json` 只保存 Wiki 仓库路径、remote 和业务仓库关联；配置指向的 Git 仓库根目录就是完整 Wiki，不再在业务仓库内创建 `llm-wiki/` 子目录。普通编码和其他 Skill 执行不会自动记录，只有手动调用时更新；每次使用前先 `git pull --ff-only` 拉取远端最新改动，确认本地 Wiki 干净后才继续；`record` 或 `sync` 更新后自动 commit 并 push。若有本地未提交改动、冲突或无法快进，会停止保护本地内容。

安装：

```bash
npx skills add xiyueyezibile/xiy-skills@xiy-llm-wiki -g -y
```

使用：

```bash
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py init \
  --wiki-repo /path/to/llm-wiki
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py link
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py status
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py record \
  --category decision \
  --note "记录已经确认的决策"
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py sync
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py watch --action extract
python3 ~/.trae-cn/skills/xiy-llm-wiki/scripts/llm_wiki.py hooks install
```

初始化后 Wiki 仓库包含 `raw/`、`wiki/`、`WIKI_SCHEMA.md` 和 `log.md`，并自动提交 push 初始骨架；`record` 会更新知识页面、索引、当前工作标识和日志，然后自动执行 `git add -A`、提交和 push。自动 push 使用本机 Git 已配置的 remote 和凭据，不在 `~/.xiy` 保存 token、cookie、密码或私钥。

该 Skill 参考 [Karpathy LLM Wiki pattern](https://github.com/MinhMPA/llm-wiki/blob/master/llm-wiki.md)：LLM Wiki 是持续编译和维护的结构化、可交叉链接知识库，不是简单的原文归档或每次查询临时拼接的 RAG 结果。

给外部机器人使用时，提供 [外部机器人 LLM Wiki 读取协议](skills/xiy-llm-wiki/references/external-agent-guide.md)。协议要求机器人每次回答前读取 Wiki 规则、`wiki/current-work.md`、索引和相关页面，并在回答开头标识“当前工作”；外部机器人默认只读，不会自动修改或提交 Wiki。

Skill 包内同时提供 [机器人 Agent 能力配置](skills/xiy-llm-wiki/agents/agent.md)，用于合并到机器人现有的 `AGENT.md`、`SOUL.md` 或 system prompt。它只增加 `/ask`、`/llm` 和从当前仓库解析、读取 LLM Wiki 的规则，不会覆盖既有人设、命令菜单、表情包、画图或自动回复配置。[openai.yaml](skills/xiy-llm-wiki/agents/openai.yaml) 仅作为支持 Skill Agent 元数据的 UI / harness 入口。读取默认不修改或提交 Wiki；运行环境仍需允许 `git pull --ff-only` 更新 Git 元数据，严格文件只读 sandbox 应由外部任务预先同步 Wiki。

支持按仓库配置 Codex/Trae 会话监听：运行 `watch --action extract` 配置目标仓库，再运行 `hooks install` 安装命令型 hooks。安装 Codex hooks 后需要重启 Codex，或启动一次普通交互式 `codex` 完成新增 hook 的信任登记；已打开的任务不会热加载。`extract` 会在 Codex 会话结束时启动独立的只读 Codex 进程，静默提取有依据、可复用的结论、决策、规则和踩坑，不向用户展示收尾提示或续跑当前任务；它会过滤普通进度、推测与敏感信息，仅在有新内容且通过结构校验时调用 `record` 写入 Wiki，并自动 commit + push。`status` 是只读模式，`sync` 是每个匹配事件自动同步模式。Trae 还需分别传入 `--path ~/.trae/hooks.json` 与 `--path ~/.trae-cn/hooks.json` 安装 hooks。

`wiki/current-work.md` 会记录结构化工作现场：仓库路径、分支与 HEAD、upstream 领先/落后关系、暂存/未暂存/未跟踪文件、改动范围与规模，以及最近 3 次提交；摘要只归纳 Git 可验证事实，不根据文件名脑补业务目标。

### find skills

```bash
npx skills add vercel-labs/skills@find-skills -g -y
```

没有 find-skills 之前：

- 手动在 GitHub 搜索相关技能
- 逐个复制、安装、配置
- 反复调试适配

有了 find-skills 之后：

- 一句话描述需求
- AI 自动搜索最匹配的技能
- 一键安装，立即可用

### commit-message-generator

自动分析代码改动并生成符合规范的commit信息

```bash
npx skills add xiyueyezibile/xiy-skills@commit-message-generator -g -y
```



功能特性：

- 自动分析git diff的代码改动
- 识别改动类型（feat, fix, docs, style, refactor等）
- 遵循Conventional Commits规范
- 生成一条综合的commit信息（而非多条）
- 支持多文件、多类型改动分析
- 按优先级确定主type（feat > fix > refactor > ...）

### crypto-news-selector-pack

消息面选币多 Skill 协作包：把公开消息与市场热点取证、Binance U 本位永续/股票代币行情结构、纯分析 HTML 报告、账户风控/本地流水、半自动确认式执行拆成多个可独立触发的 Skill，并保留 `crypto-news-selector` 作为完整单 Skill 和共享脚本运行时。适合需要“一键安装整套消息面选币能力”，或希望只单独安装新闻、行情、报告、风控、执行某一环节的场景。

一键安装完整协作包：

```bash
npx skills add xiyueyezibile/xiy-skills -g -y --skill crypto-news-selector-pack crypto-news-analysis-report crypto-news-intel crypto-market-structure crypto-risk-ledger crypto-trade-executor crypto-news-selector
```

> 如果 `npx skills` 因 Node 版本过低报错，请先切换到 Node.js 22+ 后重试；不要直接复制他人机器的绝对路径。

单独安装某一成员（只安装 `crypto-news-selector-pack` 表示只装总控说明；完整协作能力请用上方一键命令）：

```bash
npx skills add xiyueyezibile/xiy-skills@crypto-news-selector-pack -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-news-analysis-report -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-news-intel -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-market-structure -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-risk-ledger -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-trade-executor -g -y
npx skills add xiyueyezibile/xiy-skills@crypto-news-selector -g -y
```

协作成员：

- `crypto-news-selector-pack`：总控编排，先审计账户/流水，再协调消息、行情、风控和执行
- `crypto-news-analysis-report`：只组合消息面与公共行情结构，输出不含账户、仓位和下单的逐币 HTML 深度报告；生成后必须在最终回复返回可直接点击打开的 `file://` 链接和 HTML 绝对路径
- `crypto-news-intel`：公开消息、公告、监管、交易所事件、市场热点、公开传闻增量监控和催化剂质量取证
- `crypto-market-structure`：Binance 公共行情、1d/4h/1h/15m 结构、ATR 止损和入场触发
- `crypto-risk-ledger`：`<项目根目录>/.crypto` 本地知识、Binance 私有只读快照、持仓流水对账、数量杠杆和组合风险
- `crypto-trade-executor`：两阶段确认式执行；只在用户回复精确 `确认执行 TOKEN` 后处理单笔市价开仓和保护单
- `crypto-news-selector`：原完整全流程 Skill，包含可复用脚本；也可继续单独使用

功能特性：

- 一条安装命令装完整协作包，也支持每个子 Skill 独立安装和独立触发
- 默认只读，任何真实交易写接口都必须先有账户审计、订单草案和逐单精确确认
- 筛选顺序固定为“先信息差池、再行情验证”：优先找未来 1–30 天未完全落地的公告、解锁、升级、监管、财报、产品和代币经济节点；涨幅榜、跌幅榜、成交额榜只能作为验证雷达或补漏线索，不能作为核心候选主入口
- 每轮增加“市场热点参考”：统计 BTC/ETH 环境、涨跌广度、成交额集中度、衍生品环境及主题的 `萌芽/扩散/拥挤/退潮` 阶段，用于补漏、共振、降权和风险聚类；热点不能单独升级候选或替代消息、结构和风险门禁
- 全市场选币先运行 `crypto-news-selector/scripts/build_universe_catalog.py` 刷新 Binance U 本位完整底池，再扫描全部普通永续和 TradFi 永续；当前快照为 700 个可交易合约，生成清单会随 Binance 上下线自动变化，不能用 `scan --limit 30/40` 代替全量扫描
- 全量清单写入 `crypto-news-selector/references/binance-usdm-universe.md` 和 `.json`，逐项标注加密币、美股/ETF/ADR、韩股、港股、A 股、商品、Pre-IPO、合约类型、24h 成交额及对应消息渠道网址
- “全量扫描”不等于“700 个逐币深度分析”：目录和 24h ticker 覆盖完整底池；完成状态、合约类型、稳定币、重复季度合约、流动性和确认下架等机械排除后，剩余每个标的都必须真实访问对应消息渠道并保存逐项审计记录，不能依据已有排期、历史上下文或少量搜索先挑熟悉标的
- 报告必须分别披露目录、行情初筛、机械过滤幸存、实际消息核验和深度分析数量；逐项审计记录包含实际渠道/URL、查询词、检索时间、最新事件或未发现、状态和原因，数量未闭合时不得宣称完成
- 所有经逐项核验发现的机会都必须列入报告，不设置 Top-N 或篇幅上限；只有最终交易计划数量继续受账户、相关性和组合风险限制
- 每个候选和 active 持仓固定展示资产背景：资产类型、一级行业/赛道、细分模块、核心业务/协议用途、主要价格驱动、同风险簇和背景介绍；例如 NVDA 标为“半导体 / AI GPU 与加速计算”、MRVL 标为“半导体 / 定制 ASIC 与数据中心网络互连”、SAMSUNG 标为“半导体与消费电子 / DRAM、NAND 与晶圆代工”，用于识别看似不同标的背后的集中暴露
- 报告必须拆分 `提前埋伏池` 与 `已启动确认池`：前者要求未来节点明确且未明显抢跑；后者说明消息已被资金部分交易，只能等回踩承接或突破后回踩确认
- `初步落地` / `基本落地` 不等于淘汰：仍有未完成传导或后续节点时必须进入 `已启动确认池` 继续分析，写明已完成/未完成传导、下一验证节点、二阶段触发、保守目标、失效位、扣费后剩余净盈亏比和行情耗尽信号
- 每个逐币深度分析和交易复盘固定执行“新闻事实 -> 成本/收入/供需 -> 公司利润或代币价值捕获 -> 市场是否已交易 -> 基本面定价还是杠杆清算 -> 结构确认 -> 逻辑失效 -> 扣费后净盈亏比”的闭合链；必须记录 `news_fact`、`economic_channel`、`value_capture`、`pricing_status`、`move_attribution`、`structure_trigger`、`invalidation`、`net_payoff_check`、`chain_status`、`chain_missing`，链条不完整时只能观察，不能生成订单草案
- 额外维护 `传闻观察池`：每次触发先读取 `.crypto/rumor-watch/watchlist.json`，增量核验政策人物、名人品牌、项目生态和认证社媒公开传闻；状态按 `lead -> corroborated -> confirmed` 升级，直接来源冲突、否认或超过窗口则转为 `disputed/rejected/expired`
- 传闻不会直接变成交易信号：`lead`、`corroborated` 和 `disputed` 固定只观察，只有监管、交易所、项目方或公司等直接来源确认后，才有资格进入核心候选并继续接受行情结构、已定价风险和盈亏比门禁
- `crypto-news-intel/scripts/rumor_watch.py` 负责跨轮保存、去重、证据合并和过期处理；它只在 Skill、cron 或 Agent 调度器实际调用时运行，没有调度时不会宣称 24 小时后台监控
- 回复消息面结论时必须逐条带发布时间、事件/生效时间、检索时间、距当前多久、时效性等级和有效窗口；时间不明的消息只能做线索，不能作为核心催化
- 新闻、行情、风险、执行四类结论分层输出，便于复核某一环节是否缺证据
- 默认报告交付：用户只说“用 skill 选币 / 帮我选币 / 看消息面机会 / 给观察清单”时，也必须先生成 HTML 报告，再在最终答复最前面给 `[打开 HTML 报告](file:///absolute/path/report.html)` 和 HTML 绝对路径；除非用户明确说不要文件/不要 HTML，不能只给聊天正文
- 报告采用 v5 固定模板：桌面端左侧目录可跳转到热点、持仓和每个标的；正文顺序为 `数据时间` -> `结论摘要` -> `市场热点参考` -> `风险与落地速览` -> `逐项研究审计` -> `已开仓催化落地跟踪` -> `逐币消息面深度分析` -> `股票代币 / TradFi 合约信息` -> `摘要矩阵` -> `来源列表` -> `声明`；必须通过 `crypto-news-analysis-report/scripts/render_report.py` 生成，不手写其他 HTML 模板
- 纯分析 HTML 报告生成后，最终答复直接给 `[打开 HTML 报告](file:///absolute/path/report.html)`，避免只给相对路径或口头说明；如果报告生成失败，必须说明失败命令和原因，并给完整 Markdown 版报告兜底
- 用户声明已经开仓后进入 `position_followup` 持仓跟踪状态：能从只读账户唯一确认的写正式 ledger；缺少方向、入场价、数量时不伪造流水，而是在 `<项目根目录>/.crypto/position-watch/` 建立待补成交细节的跟踪清单，并持续复核相关新闻、未来催化落地/延期/取消、反向消息和关键失效位
- 用户声明开仓但未提供精确成交价时，默认使用声明时记录的 `observed_price_at_tracking` 作为 `entry`，并标记 `entry_source=user_declared_open_tracking_price`；它是复盘基线，不等同于交易所实际成交回报
- 跟单、子账户、其他交易所或机器人仓位不一定出现在当前 Binance 主账户 API 快照中；用户未明确说平仓前，`position-watch` 中的 active 跟踪不能因快照无持仓而关闭。后续生成 HTML 报告时必须追加“已开仓催化落地跟踪”区块，展示上次开仓催化当前是否落地
- 下架、停止开仓、自动结算类题材即使最终盈利，也必须复盘中途最大不利浮动、短挤、流动性和退出纪律；不能把最终盈利反推为入场质量好
- 网络升级、硬分叉、治理执行、产品发布等事件抢跑仓出现浮盈后，必须提前定义 TP1、移动止损或关键位跌破退出，避免一根阴线把浮盈打回保本
- 多币篮子、中长线波段和单币精选共享同一 `<项目根目录>/.crypto` 生命周期与复盘闭环
- 子 Skill 未安装时，总控会按对应职责降级处理并标明缺少的自动化能力

使用示例：

- “用消息面选币协作包，先审计账户，再筛最近 72 小时的 5 个 U 本位候选”
- “刷新完整合约清单，扫描全部加密币和 TradFi 永续，分别标注美股、韩股、港股、A 股、商品与 Pre-IPO，再按消息面和结构筛选”
- “先找未来 1–30 天未落地的信息差事件，再用成交额和 1d/4h/1h/15m 结构验证，不要先按涨幅榜倒推”
- “选币时增加市场热点分析，说明主题处于萌芽、扩散、拥挤还是退潮，但热点只作参考”
- “监控政策人物、名人项目和认证社媒的公开传闻做选币；未确认的只进传闻观察池，官方确认后再升级”
- “只分析不看仓位和开仓，结合消息面和行情结构整理一份 HTML 报告”
- “只跑 news-intel，帮我查 OP 最近一个月有没有持续催化”
- “只跑 market-structure，分析 BTC/ETH/SOL 现在有没有市价或近价限价结构”
- “用 risk-ledger 按当前账户和已有持仓算这 3 个计划的数量和组合风险”
- “把 PLAN-001 生成确认单，我确认后再执行”

### crypto-news-analysis-report

消息面选币纯分析报告 Skill：只组合 `crypto-news-intel` 和 `crypto-market-structure`，用于基于公开消息、市场热点与 Binance U 本位公共行情做候选分析，并整理成可本地打开的 HTML 报告；不读取账户、不看仓位、不计算个人仓位、不生成订单草案、不调用任何交易写接口。

```bash
npx skills add xiyueyezibile/xiy-skills@crypto-news-analysis-report -g -y
```

如需连同消息/行情子 Skill 一起安装：

```bash
npx skills add xiyueyezibile/xiy-skills -g -y --skill crypto-news-analysis-report crypto-news-intel crypto-market-structure
```

功能特性：

- 只使用公开新闻、公告和 Binance 公共行情，适合“只分析不交易”的场景
- 新增新浪财经公开新闻源脚本 `scripts/sina_finance_news.py`，可按关键词从财经、股票、美股、港股、行业滚动新闻中补充中文消息
- 全市场报告固定以 24h 成交额 `>= 1000 万 USDT` 为流动性门槛；payload 必须保存完整 `liquidity_survivors` 明细并与 `research_audit` 逐币匹配，通过门槛的全部标的都必须逐项真实取证并完成 1d/4h/1h/15m 分析，集合或计数不一致时渲染器拒绝生成报告
- 每条逐项审计必须给出标准化追进去风险与消息/结构分析摘要；风险为 `低/中低/中/中高` 的全部标的必须进入候选矩阵和逐币深度章节，遗漏任一标的时渲染器拒绝生成报告；`高/极高` 标的可只保留在审计表
- 强制每条消息写明发布时间、事件/生效时间、检索时间、距当前多久、时效性等级和有效窗口
- 默认先找信息差再看行情：未落地未来节点优先，Binance 涨跌幅/成交额榜只用于确认流动性、判断是否已抢跑和发现补漏候选；不得先看榜单再倒推泛泛消息
- 增加跨报告新颖性控制：新候选默认冷却最近 3 份报告或 72 小时，同一催化 7 天内重复只保留二阶段跟踪；最近 5 份报告的重复出现会累计 `repeat_penalty`，重复标的不得用于填充提前埋伏池
- 报告区分 `新候选`、`深度观察`、`冷却中`、`重复观察` 和 `active 持仓跟踪`；active 持仓只进入跟踪区，不重新包装成新候选。每个重复标的记录 `repeat_count`、`repeat_penalty`、`prior_reports`、`cooldown_until` 和 `selection_reason`
- 新增独立“市场热点参考”区块：展示市场状态、涨跌广度、成交额集中度、衍生品环境、主题阶段与拥挤风险；热点用于补漏和风险聚类，不能单独触发候选或开仓
- 支持公开传闻增量监控：读取 `.crypto/rumor-watch/watchlist.json`，按来源层级记录首次发现、最后核验、支持/否认证据、价格触发、失效条件和复核时间；未获直接来源确认时只能放入“传闻观察池”
- 用 `crypto-news-intel` 判断催化剂质量与已定价风险，用 `crypto-market-structure` 判断 1d/4h/1h/15m 结构
- 支持股票代币 / TradFi perpetual 专用流程：区分底层股票公司消息和 Binance 合约/交易工具消息，标注底层资产、股票市场、`TRADIFI_PERPETUAL` 合约类型、交易时段错位和消息传导路径
- 可选接入 `finviz-screener` 作为美股候选池辅助，但主驱动仍是消息面；FinViz 的主题、财务或技术过滤结果不能替代新闻/公告催化
- 风险标签必须按用户执行语义校准：`低` / `中低` / `中` 会被用户视为高概率开仓信号；若消息只是财报前预期、分析师观点、媒体解读、主题扩散，或还在“等突破/等回踩承接/可继续跟踪”阶段，`追进去风险` 至少写 `中高`，并把操作倾向写成 `等触发` 或 `只观察`
- 逐币新闻解释必须有深度：每个核心标的都要写清新闻事实、原始来源可靠性、关键数字、利多/利空因果链、反向解释、落地/定价证据和后续验证点；股票代币必须额外拆分底层公司消息、Binance 合约工具消息和正股交易时段确认，不能只给标题式结论
- 新报告必须设置 `meta.report_contract="v5"` 并提供 `market_hotspots`；每个逐币和持仓条目必须通过 `news_evidence` 或 `source_refs` 绑定原始消息，章节内直接展示可点击来源、来源层级、可靠性、发布时间、事件时间、检索时间和关键事实，缺失时渲染器拒绝生成；历史 v4 payload 仍可重渲染
- 逐币章节和已开仓跟踪区块在新闻之前展示资产画像：资产类型、行业/赛道、细分模块、核心业务/协议、价格驱动、同风险簇与背景介绍；摘要矩阵和 TradFi 信息表同步展示行业、细分模块和风险簇，字段缺失时渲染器拒绝生成报告
- 用户在对话中声明“已开”“新开了”“按上一份报告开了”的标的必须进入 active 跟踪；若缺方向、入场价或数量，也要在 `.crypto/position-watch/` 记录待补字段，并在后续 HTML 报告的“已开仓催化落地跟踪”区块展示，不能只作为新候选
- 支持 `pre_landing` 未落地催化埋伏模式：当用户要求“未落地之前的消息”“提前埋伏”“未来催化”时，只把未来 1–30 天有明确节点、尚未完全兑现且有复核时间的事件作为核心候选；已完成且没有下一阶段的新闻只作背景，不冒充埋伏机会
- 已经初步/基本落地但尚未完全兑现的消息不会停止分析：统一转入 `已启动确认池`，只有效应已充分兑现且没有后续路径，或扣费后剩余净盈亏比 `<= 1`，才允许淘汰
- 支持把 B 站等二级内容作为方法论学习来源：只沉淀可验证的视频元数据、简介要点和选币方法，不把 UP 主观点、标题或评论区当作交易核心事实；所有候选仍需回到官方公告、交易所公告、链上数据、公司财报/IR 或监管文件验证
- 候选只标注 `可继续跟踪`、`等触发`、`只观察`、`淘汰`，不输出账户相关数量和杠杆
- 报告中的“落地”指利好/利空效应是否已经通过供需、基本面、价格结构、成交量/OI/资金费率或交易限制兑现，不是事件本身是否发生；事件排期或完成状态应单独写在 `事件/生效时间`、`未来催化节点`、`当前阶段`
- 随包提供 `scripts/render_report.py`，把结构化分析结果渲染为 `.tmp/crypto-news-analysis-report/<timestamp>-skill-selection-report.html`；摘要后先给“市场热点参考”，再给红黄绿“风险与落地速览”，已开仓标的置顶展示风险、失效位和当前动作；正文按“单个币一章”写，每章开头突出 `方向判断`、`利好/利空落地`、`追进去风险`、`操作倾向`，再展示消息依据和完整传导分析
- 报告交付是硬门禁：只要已经产出选币、候选、观察清单或逐币分析结论，就必须先生成 HTML 文件并确认存在；最终回复第一屏必须返回可直接点击打开的 Markdown 链接，例如 `[打开 HTML 报告](file:///Users/you/project/.tmp/crypto-news-analysis-report/20260821-2336-report.html)`，并同时列出 HTML 绝对路径，不能只写“报告已生成”
- 只有用户明确说“不要报告 / 不要 HTML / 只在聊天里给简版”，或渲染脚本/文件系统实际失败时，才允许不返回 HTML；失败时必须用“报告生成失败”说明命令、错误原因和已完成数据范围，并给完整 Markdown 版报告兜底

使用示例：

- “只分析不看仓位，帮我把最近 72 小时消息面机会做成 HTML 报告”
- “用 skill 帮我选币”（默认也会返回 HTML 报告）
- “结合市场热点做选币参考，区分主题扩散和已经拥挤的追涨风险”
- “结合 news-intel 和 market-structure，整理 BTC/ETH/SOL/XRP 的消息和结构报告”
- “只看 Binance 股票代币，分析 UNITREE/KUAISHOU/CXMT 的底层公司消息和合约结构，出 HTML 报告”
- “不要调用账户接口，只给公开信息和行情结构，输出 HTML”
- “找未落地之前的消息去埋伏，只要未来催化和提前布局条件，出 HTML 报告”
- “把 TRUMP、ZEC 这类政策人物/ETF/认证社媒传闻加入观察池，持续核验来源，确认前不要给开仓结论”

### crypto-news-selector

结合近期可追溯消息、Binance U 本位永续真实行情及账户余额筛选候选币，并行运行短周期滚动篮子与持有 3–21 天的中长线波段，给出市价/近价限价开仓、逐仓/全仓模式、数量、杠杆、止盈和止损计划。默认只读；用户单独开启最小化合约交易权限后，支持“生成短时订单草案 → 用户逐单精确确认 → 自动市价开仓并按行情动态分配 1–3 级止盈数量、挂剩余仓位止损”的半自动模式。支持以月收益 100%+ 作为研究目标，但不承诺收益，并通过硬性回撤闸门约束尾部风险

```bash
npx skills add xiyueyezibile/xiy-skills@crypto-news-selector -g -y
```

该安装会同时包含全量目录生成器以及当前 Binance U 本位合约 Markdown/JSON 快照，无需单独下载清单。

功能特性：

- 先查项目方、交易所、监管机构、公司 IR/财报等公开消息建立信息差候选池，再用 1d / 4h / 1h / 15m 技术结构确认是否已被市场定价；涨跌幅榜和成交额榜只做行情雷达，不做核心候选主入口
- 用户要求“埋伏/启动前”时强制使用事件优先漏斗：先扫描未来 `7–30` 天一手排期，再映射 Binance 合约、排除已有仓位和已抢跑标的，最后才做四周期结构与盈亏比验证；报告披露事件总数、可交易事件数、未启动事件数和可埋伏数
- `提前埋伏池` 默认要求 24h 绝对涨跌幅 `< 5%`、相对事件公开前基准区累计偏离 `< 10%`、未出现日线/4h 放量扩张或短周期拥挤，并且结构失效位近、扣费后保守净盈亏比 `> 1`；不合格时宁可明确“当前无可埋伏标的”，不能用已启动热点填充
- 报告主次顺序固定为 `提前埋伏池 -> 待回踩埋伏池 -> 已启动确认池 -> 传闻观察池 -> 全市场审计附录`；已启动对象不能冒充提前埋伏，但必须保留二阶段分析，满足触发和剩余净盈亏比门禁时仍可进入候选
- `已启动确认池` 不只是淘汰说明区：利好/利空初步或基本落地但仍有剩余空间的标的必须继续完成四周期、衍生品和净盈亏比分析；二阶段触发确认且剩余净盈亏比 `> 1` 时仍可成为候选
- 跨报告重复控制：最近 3 份报告或 72 小时内出现过的新候选默认进入冷却；最近 5 份报告重复出现累计惩罚，同一催化 7 天内不得重复作为核心候选。没有合格新标的时明确写“本轮无合格新候选”，不使用旧币凑数
- 同步分析市场热点：记录 BTC/ETH 环境、涨跌广度、成交额集中度、衍生品环境和主题阶段，用于补漏、判断共振与识别同风险簇拥挤，不把热度本身当作开仓理由
- 每轮区分 `提前埋伏池`、`已启动确认池` 和 `传闻观察池`，避免把已经涨跌幅前列、利好利空部分落地的币误写成提前埋伏，也避免把未经确认的传闻写成事实
- 每次触发增量核验公开传闻状态；`lead/corroborated` 只观察，监管、交易所、项目方或公司直接确认后才允许升级为普通消息面候选
- 新增独立 `medium_long` 中长线轨道：1d 定趋势、4h 建结构、1h 择时，默认持有 3–21 天，使用更宽结构止损、更小数量和 2x–4x 低杠杆，并与短篮子分开复盘
- 内置 Binance 公共只读行情脚本，无需 API Key，可获取永续合约列表、24h 行情和多周期 K 线指标
- 内置全市场目录生成器 `scripts/build_universe_catalog.py`：从 Binance 公共接口刷新全部 U 本位可交易合约，并生成 `references/binance-usdm-universe.md/.json`；每个合约都带市场类型和消息源路由，全市场扫描不再依赖涨跌榜 Top-N
- 默认把普通加密永续与 TradFi 永续一起纳入筛选，显式区分加密币、美股/ETF/ADR、韩股、港股、A 股、商品和 Pre-IPO；季度合约只进入覆盖审计，不与同底层永续重复推荐
- 支持已触发后的市价入场，以及距离最新价不超过 `min(0.5%, 0.25×15m ATR)` 的结构近价限价单；限价单默认 30 分钟失效并要求重新分析
- 支持 8–15 币的全仓篮子探索模式：2–4 个核心仓搭配多个小风险侦察仓，用少数高收益尾部机会覆盖小额止损并积累可复盘样本
- 篮子按批次记录 `batch-id`、核心/侦察层级、叙事桶和风险贡献，并统计前 20% 盈利贡献、相关止损与费用占比
- 读取账户权益、可用余额与已有风险敞口，按结构止损和默认单笔风险反推名义仓位、交易数量、逐仓杠杆及保证金占用
- 止盈止损由行情结构、ATR、消息持续性和流动性决定，不使用固定赚亏金额；TP1 保证金收益率约 50% 仅作为偏好，强趋势可保留移动止损尾仓
- 使用扣费后的保守净盈亏比，必须严格大于 1；净盈亏比 1–1.5 通常风险不超过 0.5%，1.5–3 通常为 0.75%，A+ 且 ≥3 时最高 1.25%
- 设置组合 2.5%、单日亏损 3%、滚动 7 日回撤 6% 和月度高点回撤 12% 等硬性闸门
- 篮子模式单腿风险降至 0.15%–0.6%，组合计划止损风险上限 4%，同方向高 Beta 风险上限 2.75%，避免把十几个相关山寨仓误当成真正分散
- 可在账户快照与全组合压力测试通过后建议全仓，但全仓不等于满仓，建议数量仍由结构止损和账户风险反推
- 使用至少 20 笔完整交易滚动统计胜率、盈亏 R、期望值和最大回撤，以基准/乐观/压力情景检验月度目标，不靠加杠杆伪造策略期望
- 输出方向、市价参考和最大成交偏差、结构止损、分级止盈、风险收益比、失效条件和置信度
- 自动过滤稳定币相关标的、非交易状态合约和低流动性候选，不为凑数给出低质量机会
- 所有新闻要求标明来源、发布时间、事件/生效时间、检索时间、距当前多久、时效性等级、有效窗口和链接，行情或消息过期时不提供立即入场结论
- 可在用户明确授权后以 `0600` 权限保存 Binance 密钥到 `<项目根目录>/.crypto`；真实交易需要 Binance 合约交易权限和每笔精确确认令牌，始终禁止提现/转账权限
- `<项目根目录>/.crypto/` 已加入 `.gitignore`，用于保存 Binance 凭证、本地流水、学习 Wiki 和确认草案；也可通过 `CRYPTO_ROOT=/path/to/.crypto` 显式覆盖
- 半自动执行支持单笔市价计划；先生成默认 10 分钟有效的草案，只有用户回复 `确认执行 TOKEN` 才按当时市价设置杠杆/保证金模式、开仓并通过 `algoOrder` 挂 `MARK_PRICE` 触发的止盈止损，不再使用价格漂移拒单门槛
- 自动下单检测单/双向持仓模式、交易规则、同币已有仓位和最小名义金额；止损保护失败会尝试紧急 reduce-only 平仓，超时或未知订单状态不会自动重试
- 每次触发 Skill 都自动对比 Binance 当前持仓、差异币种的近期成交与 `<项目根目录>/.crypto` 未平仓流水，主动发现漏记开仓、加减仓和疑似平仓；能唯一重建时补记并复盘，存在歧义时才询问最少信息
- `<项目根目录>/.crypto/llm-wiki` 保存用户提供的学习资料、已验证优势、重复坑位和条件式规则；每次建议前必须读取
- `<项目根目录>/.crypto/rumor-watch/watchlist.json` 保存跨轮传闻观察项；该能力需要实际触发 Skill 或配置外部 cron/Agent 调度，不是默认常驻后台进程
- 用户确认实际开仓时追加开仓记录，并把消息催化、技术与衍生品确认、仓位杠杆依据、止盈止损、净盈亏比、失效条件、置信度、数据截止时间和来源完整嵌入流水，保证换对话后仍可按原始理由复盘
- 用户确认全部平仓后计算结果、复盘盈亏归因，并将可迁移经验沉淀进 LLM Wiki

刷新并查看完整底池：

```bash
python3 skills/crypto-news-selector/scripts/build_universe_catalog.py
```

生成文件：

- `skills/crypto-news-selector/references/binance-usdm-universe.md`：人工可读列表和逐类型消息渠道链接
- `skills/crypto-news-selector/references/binance-usdm-universe.json`：供后续消息检索、流动性过滤和报告覆盖审计使用
- 自动市价执行支持 1–3 级动态数量止盈与剩余仓位整仓止损；各级数量由目标确定性和趋势空间决定，不写死比例。近价限价、加仓、反手和移动止损仍由用户自行完成

使用示例：

- “结合最近 72 小时消息，选 3 个适合关注的 U 本位合约币种”
- “优先给我提前埋伏池，再给已启动确认池；涨跌幅榜只做补充验证”
- “选币时把当前市场热点和退潮主题也列出来作参考，但不要因为热门就追”
- “分析 BTC、ETH 和 SOL；如果现在满足条件，按我的账户余额给出市价开仓数量、逐仓杠杆与止盈止损”
- “最近有什么消息驱动的做空机会？先检查消息是否已被定价”
- “按月收益 100%+ 的进攻目标筛选，但严格执行回撤闸门；如果没有合格机会就观望”
- “可以给我推荐全仓或距离现价不超过 0.5% 的近价挂单，但先核算整个账户风险”
- “给我做一个 10–12 个币的全仓埋伏篮子，分核心仓和侦察仓，并按批次记录理由”
- “篮子策略继续跑，再给我筛 3 个能持有一到三周的中长线机会”
- “我已经按 PLAN-001 开多 BTC，实际成交价 64000、数量 0.01，帮我记下来”
- “把这个市价计划生成确认单，我确认后帮我开仓并挂止盈止损”
- “确认执行 AbCd1234Token”
- “T-xxx 已经在 66000 全部平仓，手续费 1.2 USDT，帮我复盘并沉淀经验”

首次使用时，让 Agent 执行 `python3 scripts/crypto_memory.py init` 初始化 `<项目根目录>/.crypto`。需要加入账户风险判断时，再执行 `python3 scripts/crypto_memory.py configure-binance`，通过隐藏输入保存 Binance 凭证。启用半自动执行时，只打开 U 本位合约交易，继续关闭现货、提现和转账并限制可信 IP；每笔真实订单仍必须使用 10 分钟精确确认令牌。

### component-validation-mock

为前端组件在目标页面首屏创建可复现 Mock，并生成浏览器操作 JSON、执行简单交互和截图验证

```bash
npx skills add xiyueyezibile/xiy-skills@component-validation-mock -g -y
```

功能特性：

- 从用户 URL 反查真实页面入口，可复用已有 mock 数据和组件封装，但必须挂载回该页面
- 高清模式默认使用 macOS 系统原生截图；Chrome 在副屏时直接按显示器编号捕获该屏，再从原始 PNG 无缩放裁切，无需把窗口拉回主屏
- Chrome/Browser 若只导出 CSS 像素尺寸 JPEG，即使页面 DPR 正确也判为普通截图，不会转 PNG 或放大后冒充高清
- 移动端高清截图复用用户预先准备的 Chrome DevTools 设备页面；页面或权限未准备时给出一次性准备提醒
- 写回 Wiki/飞书表格单元格时使用最终交付原图尺寸，默认移动端 `390×844` 原图直出，不用缩略图替代表格内验收图
- 用户明确不需要高清时回退普通浏览器截图，并清楚标记为非系统高清截图
- 用户给出的 URL 仅用于锁定目标页面，不假设该地址原本就能看到组件
- 在目标 URL 对应的真实页面入口增加临时 Mock，打开用户给定或实际确认的同一个 URL 验证，不为触发 Mock 追加 `componentMock` 等新参数
- Mock 数据优先复用真实调用点、类型、fixture/story 和业务文案，合理填充组件内的文本、图片、金额、状态与列表，避免只求渲染成功而影响观感
- 在用户目录记录 Mock 改动文件、位置、锚点、前后片段和哈希；取消 Mock 时先与当前源码及 Git diff 对比，再做最小撤销
- 将用户目标页面 URL 持久记录到 `~/.component-validation/page-urls.json`，不会用临时验证参数覆盖
- 禁止擅自切换到独立 story/demo，用同一目标页面首屏截图
- 生成可机器校验的 `browser-actions.json`
- 支持桌面端以及移动端 viewport、触摸和 user agent 模拟
- 默认使用系统原生高清截图；普通浏览器截图兜底时才按 DPR 和 PNG 输出像素校验
- 支持点击、输入、按键、下拉选择、滚动等简单交互
- 自动打开目标页面，并在初始状态和关键交互后截图
- Mock 改动清单、操作 JSON、截图和验证报告统一保存到 `~/.component-validation/cases/`，不写入业务仓库
- 按修改时间全局只保留最近 `500` 张截图
- 内置 JSON 校验脚本，禁止任意脚本执行、危险截图路径和敏感会话数据

使用示例：

- “把 CouponCard 放到优惠券列表页首屏并截图”
- “用 390x844 移动端验证 SkuPanel，点开规格后再截图”
- “给空态组件做个 mock，输入关键词并按 Enter 后验证”

### app-component-upgrade-mock-screenshot（internal）

APP/H5 组件升级 Mock 截图硬流程：在真实业务页面中 mock 目标组件或状态，优先用 Chrome DevTools iPhone 12 Pro 移动端截图，并把截图写回组件升级验证文档；当用户要求组件升级截图、文档行截图回填或真实页面 Mock 验证时使用。

本仓库内置路径：

```bash
internal-skills/app-component-upgrade-mock-screenshot
```

同步到 Trae：

```bash
rsync -a --delete internal-skills/app-component-upgrade-mock-screenshot/ ~/.trae-cn/skills/app-component-upgrade-mock-screenshot/
```

功能特性：

- 用生命周期脚本强制记录开始检查、目标定位、mock 实施、移动端验证、截图校验、文档回写和清理状态
- 默认走 Chrome DevTools iPhone 12 Pro 设备栏，切设备后必须刷新并校验 `innerWidth`、DPR、ready 标记和移动端布局
- DevTools 自动化失败时，先打开可由用户操作的 Chrome/DevTools 界面，让用户手动调到 iPhone 12 Pro 移动端并刷新；用户确认后仍由 Agent 读取运行时证据并继续截图
- 只有用户协助预调也不可用、无法验证移动端 ready，或用户明确接受时，才进入 CDP 兜底
- 截图后必须打开图片自检，确认目标组件完整可见、无遮挡、不是 PC 布局、不是半张图，且 mock 数据符合真实业务语义

### lightweight-cdp-screenshot（internal）

轻量 CDP 移动端截图 Skill：仅面向 `fe-alliance-mobile` 和 `alliance-mobile-mono` 两个移动端仓库，在真实业务页面里做轻量 Mock 并串行截图，默认使用独立 Chrome CDP、`390×844` CSS viewport、DPR `3`，输出高 DPR PNG；当用户只要轻量 Mock/页面截图、不需要生命周期报告或文档回写时使用。

本仓库内置路径：

```bash
internal-skills/lightweight-cdp-screenshot
```

同步到 Trae：

```bash
rsync -a --delete internal-skills/lightweight-cdp-screenshot/ ~/.trae-cn/skills/lightweight-cdp-screenshot/
```

功能特性：

- 零 npm 依赖，使用 Node 24 原生 `fetch`/`WebSocket` 调 Chrome CDP
- 只适用于 `fe-alliance-mobile` 和 `alliance-mobile-mono`，不作为通用网页截图工具
- 轻量 Mock 必须挂在目标组件真实业务页面里，禁止 demo 页、孤立组件页或脱离业务链路的 shell
- 每张截图独立 page，串行执行，并通过 `about:blank` 隔离上一张状态
- 默认校验 `innerWidth=390`、`devicePixelRatio=3`、PNG `1170×2532`
- 随包提供移动端参考图和 meta，默认校验展示尺寸接近 `390×844`、宽高偏差不超过 `8%`、宽高比偏差不超过 `3%`
- 默认拦截 `undefined`、`NaN` 等明显 Mock 失真文本
- 保留高清源图，不为了展示尺寸先降采样
- 输出 `manifest.json` 记录 URL、文件、viewport、DPR、PNG 尺寸和 ready 证据

### mobile-page-state-mock-screenshot（internal）

移动端页面全状态 Mock 截图 Skill：先从生产代码分析 loading/content/empty/error、按钮可用/禁用、深浅氛围、组件显隐、浮层开关等视觉状态及其依赖与互斥关系，再在真实业务页面中逐态 Mock；使用带约束的状态覆盖集避免拼出线上不可能存在的组合，并统一调用 `lightweight-cdp-screenshot` 输出高 DPR 截图。

本仓库内置路径：

```bash
internal-skills/mobile-page-state-mock-screenshot
```

同步到 Trae：

```bash
rsync -a --delete internal-skills/mobile-page-state-mock-screenshot/ ~/.trae-cn/skills/mobile-page-state-mock-screenshot/
```

功能特性：

- 只适用于 `fe-alliance-mobile` 和 `alliance-mobile-mono`，并保留目标组件的真实页面外壳与业务打开链路
- 从条件渲染、store/reducer、请求分支、props、主题、权限、实验和按钮 `disabled` 表达式收集状态证据
- 用 `state-model.json` 表达状态维度、依赖、互斥、强制截图场景和待确认关系；证据不足的组合不会进入截图计划
- 随包提供 `scripts/state_matrix.py`，枚举合法组合并生成覆盖每个合法状态值、每对可共存状态值和高风险强制场景的精简截图集
- 视觉完全相同的状态可合并，但必须记录代码证据；存在三维以上联动时用 `must_capture` 显式覆盖
- 每个场景只在真实数据/环境边界做最小 Mock，不新增 demo 页、孤立组件页或私有 URL 参数
- 截图强制复用 `lightweight-cdp-screenshot`：独立 CDP page、串行执行、默认 `390×844` CSS viewport、DPR `3`、高 DPR PNG 和 manifest 校验
- 逐图检查互斥状态串图、主题/按钮/组件显隐一致性、裁切遮挡、破图和 Mock 数据语义
- 状态证据、模型、计划、截图和报告统一保存在 `~/.page-screenshot/`，不污染业务仓库

使用示例：

- “分析这个移动端列表页的所有状态，合法组合都 mock 并截图”
- “把空态、加载态、展示态、错误态和按钮禁用态都截出来，但代码没有的状态不要编造”
- “顶部有深浅两种氛围，卡片也可能显示或隐藏，先梳理哪些能共存再批量截图”

### mock-video-verification（internal）

基于轻量 CDP 截图逻辑的 Mock 视频验证 Skill：仅面向 `fe-alliance-mobile` 和 `alliance-mobile-mono`，在真实业务页面中做最小 Mock，按声明式点击/输入/断言步骤录制移动端 WebM 视频，并同步交付高 DPR 关键帧、交互 trace 和 manifest；当用户需要录制 Mock 交互过程并证明关键状态时使用。

本仓库内置路径：

```bash
internal-skills/mock-video-verification
```

同步到 Trae：

```bash
rsync -a --delete internal-skills/mock-video-verification/ ~/.trae-cn/skills/mock-video-verification/
```

功能特性：

- 复用独立 Chrome CDP、`about:blank -> 目标 URL` 状态隔离、iPhone 等效 `390×844` viewport 和 DPR `3` 的质量约束
- 只接受 JSON 中声明的 `tap`、`click`、`input`、`key`、`scroll`、`wait`、`assert` 和 `snapshot`，不执行动作文件里的任意 JavaScript
- 使用 Chrome `MediaRecorder` 把 CDP 连续帧编码为无音频 WebM，不依赖 npm 或 ffmpeg，也不会录入浏览器地址栏、DevTools 或桌面窗口
- 默认在 ready 和每个交互后输出 `1170×2532` 高 DPR PNG，保留可逐状态复验的图片证据
- 校验 `innerWidth=390`、`devicePixelRatio=3`、拒绝文本、WebM 容器/尺寸/时长/帧数，并输出动作时间线、关键帧路径和文件哈希到 trace/manifest
- 强制 Mock 挂在目标组件真实业务页面和原有打开链路中，禁止 demo、playground、孤立组件页或脱离业务链路的 mock shell

使用示例：

```bash
PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH" \
node internal-skills/mock-video-verification/scripts/cdp_record_video.mjs \
  --url "http://localhost:4000/pages/coupon" \
  --name coupon-sheet-flow \
  --actions /tmp/coupon-sheet-actions.json \
  --ready-selector "[data-component-validation-ready='coupon-sheet']" \
  --out-dir /tmp/mock-video-verification
```

### upgrade-alliance-h5（internal）

H5 业务升级到 `@ecom/auxo-mobile-alliance@2.1.3` 的硬流程：处理换包或升版本、`appnameAlliance` 配置判断、已删除导出迁移、Button/Input/Textarea/Empty/NavigationBar breaking change 审计，并交付带截图证据的三表组件升级清单；当用户要求 Alliance H5 组件库升级或真实业务回归交付时使用。

本仓库内置路径：

```bash
internal-skills/upgrade-alliance-h5
```

同步到 Trae：

```bash
rsync -a --delete internal-skills/upgrade-alliance-h5/ ~/.trae-cn/skills/upgrade-alliance-h5/
```

功能特性：

- 用生命周期脚本强制记录升级基线、模式判定、影响扫描、三表清单、实施升级、验证结果和最终交付
- 三表组件升级清单固定拆成“受升级影响页面相关组件”、“用户指定升级页面相关组件”和“公共组件关联受影响页面”
- 三张组件表保留组件截图（升级前/升级后）列；主页面截图和二级页面/路由截图放入新增的独立“升级页面截图清单”，不扩展组件表列
- 最终组件升级清单必须严格符合 `component-upgrade-checklist-template.md`，并通过 `lifecycle.py validate-checklist-doc` 校验标题、顺序、核心表头和单组件单行
- 未执行或阻塞的截图项必须在表格单元格内写明原因，不能留空或口头补充

### prd-to-tech-code

把 PRD、聊天记录、其他文档、手动纠正和一个或多个仓库的代码证据转成可执行技术方案，并在信息足够时继续完成代码实现

```bash
npx skills add xiyueyezibile/xiy-skills@prd-to-tech-code -g -y
```

功能特性：

- 从 PRD、已有技术方案、聊天记录、会议纪要、其他文档、用户纠正、接口/设计/埋点文档和仓库证据中提取业务目标、功能范围、用户路径、数据模型、接口契约、异常分支和非功能要求
- 支持直接输入已有技术方案、技术设计、改造方案或任务拆解，先归一化成模板技术方案，再继续生成代码
- 固定使用 `~/.prd-to-tech-code` 作为 LLM Wiki 根目录，按每一个 PRD 业务创建独立知识区
- 使用 `~/.prd-to-tech-code/config.json` 标记当前业务；没有当前业务时自动创建标识，后续默认沿用，除非用户明确说明是新业务
- 当前输入与原业务差异过大但用户未明确新业务时，先写入原业务并在交付时提示用户确认是否拆成新业务
- 技术方案必须读取仓库代码，业务可跨多个仓库，并区分需要修改的仓库和只读参考仓库
- 技术方案保留必要资料图、流程图、架构图、时序图、改造前后示意、PRD/设计稿截图引用和关键表格，方便评审者阅读
- 完善已有评审 Wiki / 多需求技术方案时，默认采用“参考文档与证据来源 + 按需求点逐章展开”的格式：每个需求点就地包含现状图/目标图、差异表、现状代码、技术实现、文件落位、状态异常、依赖与验收
- `references/technical-plan-template.md` 已按该评审格式重写，默认结构为：负责人范围、范围与共用基线、按页面分组的需求点章节、跨页面联调上线、写作与更新硬规则
- 总览中必须列“涉及代码仓库与页面清单”，但只列用户/负责人范围内要改的页面、模块和对应协议生成配置；非负责人范围页面即使是只读参考也不要列成“涉及页面”
- 每个需求点必须给“设计稿与视觉资源位”留位置；即使设计稿暂缺，也要标注待补链接、关键切图/标注和视觉验收项，避免用 PRD 截图或数据来源证据替代最终设计稿
- 回写 PRD 图、设计稿图或截图时必须保持原图宽高比例，不把所有图片统一写成 `512×512` 等固定正方形；回写后需回读校验展示尺寸未被拉伸
- 后续根据用户纠正、源技术方案或新增仓库证据修正文档时，必须拆回对应需求点或共用基线章节，不把具体实现规则追加到文末“补充说明/校准补充”汇总章节
- 业务知识区记录来源摘要、资料图材料、仓库边界、代码证据、稳定需求、技术决策、用户纠正、约束和最新技术方案
- 读取到的稳定代码事实、接口封装、类型、权限、配置、数据流和跨仓库契约可写入业务 Wiki 复用
- 按“信息收集 -> 当前业务配置读取 -> 业务知识库读取 -> 仓库代码阅读 -> 澄清缺口 -> 模板技术方案 -> 执行计划 -> 代码实现 -> 知识库沉淀 -> 交付说明”推进
- 用户明确要求直接执行且信息足够时，不停留在方案层，会继续落代码
- 在已有仓库中优先复用现有目录结构、请求封装、类型系统、组件模式和错误处理
- 技术方案转代码时保持最小改动，只修改需求必需文件；新生成的源文件需要在文件顶部或核心导出附近写必要注释，说明文件职责、适用场景、主要输入输出或对应需求点
- 不做无关重构、无关格式化、无关文件移动、无关依赖升级；修改已有文件时只在复杂状态机、降级策略、跨仓库协议适配或非显然业务规则处补充简洁注释
- 技术方案转代码后必须生成 HTML 代码改动报告，默认路径 `.tmp/prd-to-tech-code/code-change-report.html`；报告左侧展示代码改动（文件树、diff、关键片段），右侧逐改动说明为什么改、旧逻辑、新增逻辑、影响范围、对应技术方案点和验证点
- 仅在关键约束缺失会影响架构、数据契约、用户可见行为或上线风险时追问
- 技术方案必须能直接指导代码落位，详细到仓库、文件路径、现有锚点、改动类型、要编写的代码职责、依赖、输入输出、异常状态和验证点
- 技术方案覆盖背景目标、资料图与改造示意、需求拆解、当前系统理解、代码落位清单、数据与接口、前后端实现、异常降级、风险取舍和执行计划
- 代码实现保持最小改动，避免宽泛类型，不擅自新增接口、字段、埋点、权限规则或全局配置
- 交付时说明修改文件、核心行为变化、运行方式、人工验证路径、假设和残余风险

使用示例：

- “这是订单改价 PRD，帮我出技术方案并实现前端入口”
- “这几段聊天记录还是刚才那个业务，整理进技术方案”
- “这是另一个新业务，重新建一个业务知识区”
- “这个需求涉及前端仓库和 BFF 仓库，读完代码后把仓库证据也记到知识库”
- “先出一版技术方案，要详细到每个文件该写什么代码”
- “这是已有技术方案，先补成模板技术方案，然后按方案落代码”
- “根据这个技术设计直接实现，但先帮我校验仓库代码和代码落位”
- “技术方案里把 PRD 里的流程图和改造前后示意也带上”
- “这是需求文档，群里又补了几条规则，帮我整理进技术方案并记到知识库”
- “根据这个产品需求，先写技术方案，然后直接改代码”
- “我有一份技术方案，帮我归一化成模板、拆任务并落到当前仓库”

### skill-manager

管理和推荐skills的skill，当用户询问该用什么skill时，列出可用的skills、推荐场景和推荐理由

```bash
npx skills add xiyueyezibile/xiy-skills@skill-manager -g -y
```



功能特性：

- 自动发现当前项目中可用的skills
- 根据用户需求推荐合适的skill
- 为每个skill提供推荐场景和推荐理由
- 列出所有可用的skills供用户选择
- 提供安装命令和详细信息

### reply-generator

根据聊天记录、场景描述和模板要求生成自然回复，尽量减少 AI 味，并贴近上下文中的说话习惯

```bash
npx skills add xiyueyezibile/xiy-skills@reply-generator -g -y
```

功能特性：

- 支持根据聊天记录、对话片段或场景描述生成回复
- 支持直接点名模板，或只描述想要的风格
- 默认提供 `2-3` 个候选回复，并明确给出推荐项
- 优先模仿上下文中的说话习惯，再结合模板做微调
- 当场景正式或信息不足时，会自动收敛到更稳的表达

使用示例：

- "帮我回一句，别太官方"
- "按嘉豪的语气回，轻阴阳一点"
- "下面这段聊天给我 3 个版本"
- "帮我回老板一句，礼貌但别太软"

扩展模板：

1. 在 `skills/reply-generator/references/templates/` 下复制 `TEMPLATE.md` 新建一个模板文件
2. 在 `skills/reply-generator/references/INDEX.md` 里补模板索引
3. 在 `skills/reply-generator/references/style-mapping.md` 里补风格触发词映射

这样新增模板时通常不需要修改 `SKILL.md`

![template growth](assets/readme-illustrations/03-template-growth.svg)

### team-pitfalls

团队踩坑收集器：面向非纯闲聊工程任务，在任务开始前返回仓库、领域和通用知识导航入口，由 agent 先读索引简介再按需打开具体案例，任务结束前复盘是否值得沉淀；知识写入默认交给脚本完成，正常情况下避免 agent 手写 Markdown 和索引

```bash
npx skills add xiyueyezibile/xiy-skills@team-pitfalls -g -y
```

功能特性：

- 使用时固定包含“前置检查 + 后置复盘”两段动作
- 提供 `begin_task.py` / `end_task.py` 两步生命周期门禁：前者只校验 Wiki 并返回导航入口，后者记录沉淀、采用或跳过结果
- 前置检查不是一次性免检；任务中途发现新领域、页面链路、外部工具、数据系统或文档规范，且原索引未覆盖时，保留同一 `task-id` 补跑 `begin_task.py` 并追加新的 `--domain`
- 默认通过 `upsert_pitfall.py` / `delete_pitfall.py` / `record_pitfall_usage.py` 写入、删除和累计使用次数，脚本自动刷新正文页、`index.md`、`llms.txt` 和相关 repo/domain index；若脚本被沙箱、权限或工具策略拦截，则降级为 agent 按模板自然写入
- `upsert_pitfall.py` 命中已有条目时默认只累计使用次数；需要补强正文时显式传 `--replace-existing`
- 前置检查实际采用记录时调用 `record_pitfall_usage.py` 最小更新使用次数，区分“问题再次出现”和“知识被复用”
- 分层阅读优先：仓库领域索引 `repos/<repo>/domains/<domain>/index.md` → 全局领域索引 `domains/<domain>/index.md` → 仓库索引 `repos/<repo>/index.md` → 全局通用坑位 `pitfalls/*.md`
- 同一仓库可拆多个领域；业务跨仓库时还可维护全局领域级，用来反向发现其他仓库的同领域记录
- 每个领域 `index.md` 都保留简短介绍，说明业务、页面/链路范围、典型术语或指标边界
- 适合放进领域级的知识：某类业务、某个页面、页面簇、业务链路、端内入口、领域术语、领域指标或类似稳定范围
- `--domain` 可重复传入，适配一个任务同时命中业务领域、页面领域或链路领域的场景
- 不再使用 query 召回、字段打分、命中词证据、Top-N 截断或脚本生成条目摘要作为主流程
- 先读 repo/domain 索引简介，再决定是否打开 `glossary.md`、`corrections.md` 或 `pitfalls/*.md` 正文
- 不重复输出 `SKILL.md`、`llms.txt` 或全量 `index.md`，脚本只返回稳定导航路径
- 新增/更新知识支持通过 `--json-file` 安全传入结构化 payload，兼容带空格路径与 UTF-8 BOM，并提供明确解析位置
- 自动化产物统一归一化为 `artifacts/repos/<repo-slug>/<file-slug>` 相对 POSIX 路径
- 采用外部 LLM Wiki root 管理踩坑记录，skill 包内不再保存知识库正文
- 标准结构包含 `SCHEMA.md`、`llms.txt`、`index.md`、`domains/<domain-name>/`、`pitfalls/`、`repos/<repo-name>/` 和 `repos/<repo-name>/domains/<domain-name>/`
- 只记录“新同学不看大概率会写错”的可复用问题
- 将具体案例按“案例事实 → 失效机制 → 条件式规则”提炼，通用化时保留因果结构而非简单删除专有名词
- 通用坑位必须通过跨场景迁移测试；无法举出第二场景时优先保留为领域级或仓库级知识
- 支持同一事件多层沉淀：仓库领域记录保存当前仓库业务边界，全局领域记录保存跨仓库业务共性，仓库记录保存仓库共性，全局记录保存跨项目机制
- 对同类问题做去重与累计次数
- 固定使用 `~/.team-pitfalls-wiki` 作为外部 LLM Wiki root，并在首次运行时自动初始化基础结构
- 约束不记录密钥、token、cookie 等敏感信息

生命周期门禁示例：

```bash
python3 skills/team-pitfalls/scripts/begin_task.py --task-id task-20260717 --repo fe-buyin --domain daren
python3 skills/team-pitfalls/scripts/begin_task.py --task-id task-20260717 --repo fe-buyin --domain daren --domain slardar
python3 skills/team-pitfalls/scripts/end_task.py --task-id task-20260717 --result skipped --reason "没有新的可迁移知识"

# 如果本轮采用并更新了已有知识，结束时改用：
python3 skills/team-pitfalls/scripts/end_task.py --task-id task-20260717 --result recorded --used-entry-id P-001
```

固定目录：

```text
~/.team-pitfalls-wiki
```

### superpowers

覆盖全流程的工作流系统

```bash
npx skills add https://github.com/obra/superpowers
```

### ian-xiaohei-illustrations

Ian 风格的中文正文配图 skill，适合为文章、帖子、博客、Notion 文档和方法论内容生成小黑怪诞手绘配图

```bash
npx skills add https://github.com/helloianneo/ian-xiaohei-illustrations
```

功能特性：

- 面向中文正文配图，而不是商业插画或 PPT 信息图
- 默认使用小黑 IP、纯白手绘、少量红橙蓝批注的视觉风格
- 适合流程、结构、状态、隐喻、观点类内容的正文插图
- 支持先做 shot list，再按单张结构逐张生成

### taste-skill

高审美前端设计 skill 仓库，适合做落地页、作品集、品牌页和已有项目的界面重设计，也包含图像生成类设计技能

```bash
npx skills add https://github.com/Leonxlnx/taste-skill
```

### skill-creator

帮助 skill 创建

```bash
npx skills add https://github.com/anthropics/skills
```

### last30days

最近30天的热点搜索
```
git clone https://github.com/mvanhorn/last30days-skill.git ~/.claude/skills/last30days
```
