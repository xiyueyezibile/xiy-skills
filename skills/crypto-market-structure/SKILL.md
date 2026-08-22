---
name: crypto-market-structure
description: 消息面选币的行情结构子 Skill。用户要求分析 Binance U 本位加密永续或股票代币/TradFi perpetual 的 1d/4h/1h/15m 技术结构、趋势、突破回踩、ATR 止损、止盈目标、成交量、流动性、是否适合市价/近价限价入场时使用。只做公共行情与交易结构确认，不读取账户、不算个人仓位、不下单；应与 crypto-news-intel、crypto-news-analysis-report、crypto-risk-ledger、crypto-trade-executor 或 crypto-news-selector-pack 协作。
---

# Crypto Market Structure

负责判断消息候选是否真正具备可交易结构。它不负责新闻取证、账户风险、真实下单或交易记录；这些分别交给 `crypto-news-intel`、`crypto-risk-ledger`、`crypto-trade-executor`。

## 数据来源与脚本

优先复用 `crypto-news-selector` 随包脚本：

```bash
python3 scripts/binance_market_snapshot.py scan --limit 30
python3 scripts/binance_market_snapshot.py analyze --symbols BTCUSDT,ETHUSDT
python3 scripts/binance_market_snapshot.py scan --tradfi-only --limit 30
python3 scripts/binance_market_snapshot.py analyze --include-tradfi --allow-partial --symbols UNITREEUSDT,KUAISHOUUSDT
```

上述命令从本 Skill 安装目录执行；单独安装本 Skill 时，`scripts/binance_market_snapshot.py` 已随包携带。

脚本只调用 Binance 公共只读接口。普通加密永续默认只包含 `PERPETUAL`；股票代币 / TradFi perpetual 必须显式加 `--include-tradfi` 或 `--tradfi-only`。新上市股票代币历史 K 线可能不足，使用 `--allow-partial` 返回部分指标，并在结论中降低置信度。若当前 Skill 是单独安装且没有脚本，可用等价 Binance 公共 API 或说明缺少自动脚本，只输出人工结构分析。

每次输出都要标明：

- `generated_at`
- K 线最后一根时间
- 交易对是否为 U 本位永续且 `TRADING`
- `contract_type`、`underlying_type` 和 `underlying_sub_type`；股票代币必须标注 `TRADIFI_PERPETUAL`
- 最新价、24h 成交额/成交笔数
- 1d/4h/1h/15m 的结构摘要

## 周期规则

- 短周期：4h 定方向，1h 确认结构，15m 找入场触发。
- 中长线：1d 定市场状态和主趋势，4h 构建结构，1h 择时；15m 只减少成交偏差，不能用噪声推翻日线逻辑。
- 股票代币 / TradFi perpetual：额外检查底层股票交易时段、休市期间 Binance 合约 24/7 定价偏差、汇率/指数/流动性差异；K 线历史不足时不要强行计算完整 EMA/RSI/ATR 结论。
- 不用单根针或瞬时拉盘作为入场依据。
- 止损必须放在结构失效位之外，并通过 ATR 校验，不按固定金额或随意百分比。

## 入场类型

### 市价

只在所需收盘、突破、回踩或反转确认已经发生时允许。给出参考价和最大可接受成交偏差，但执行时是否下单由 `crypto-trade-executor` 和用户精确确认决定。

### 近价限价

只有方向和消息逻辑已成立、仅等待价格回到已验证的 15m 支撑/阻力或突破回踩位时才允许。

- 挂单价距离最新价不得超过 `min(0.5%, 0.25 × 15m ATR / 最新价)`。
- 默认 30 分钟有效。
- 超时、15m 收盘破坏结构、BTC 反向剧烈波动、核心消息被证伪时必须重算。

## 结构淘汰规则

直接标为 `淘汰` 或 `只观察`：

- 非 U 本位永续、非 `TRADING`、稳定币相关或流动性明显不足；但用户明确要求股票代币时，允许 `contractType=TRADIFI_PERPETUAL`，并必须标注它不是普通加密永续。
- 消息后冲高回落、放量滞涨、量价背离，且无法重新站回关键位。
- 做多止损必须放得很远但保守目标空间不足；做空同理。
- RSI/资金费率/OI 显示过度拥挤，却没有可承受的结构止损。
- 15m 看起来触发，但 1h/4h 主结构反向。
- 中长线计划只能靠 15m 局部低点做止损。

## 输出格式

```markdown
## 行情数据状态
- 数据时间：
- 交易对范围：
- 新鲜度判断：

## 结构表
| 币种 | 周期模式 | 方向 | 1d | 4h | 1h | 15m | ATR/波动 | 流动性 | 状态 |
|---|---|---|---|---|---|---|---|---|---|

## 交易结构（仅结构通过时）
- symbol：
- side：
- entry_type：market / near_limit / wait
- reference_price：
- near_limit_price：
- structure_stop：
- conservative_target：
- extended_targets：
- invalidation：
- structure_rr：
- 技术置信度：

## 给协作 Skill 的交接
- 给 `crypto-news-intel`：需要补证的消息时间点或反向事件。
- 给 `crypto-risk-ledger`：允许/不允许进入仓位测算的币种及原因。
- 给 `crypto-trade-executor`：只有 `entry_type=market` 且仍满足门禁时，才可能生成自动执行草案。
```

## 计算提醒

- 盈亏比先按结构目标计算，再由 `crypto-risk-ledger` 扣除手续费、滑点、资金费率得到保守净盈亏比。
- 不通过调高杠杆修复盈亏比；杠杆只影响保证金占用和强平距离，不改变价格结构。
- 同一风险簇的多个山寨币不可被当作真正分散，必须提示给 `crypto-risk-ledger` 做组合相关性折减。
