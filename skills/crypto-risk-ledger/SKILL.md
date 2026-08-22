---
name: crypto-risk-ledger
description: 消息面选币的账户风控与交易流水子 Skill。用户要求按 Binance 账户余额/权益计算 U 本位永续开仓数量、杠杆、逐仓/全仓、组合风险、回撤闸门、记录开仓/平仓/加减仓、复盘、读取学习资料，或每次触发交易型选币流程前做持仓与本地 ledger 对账时使用。只做只读账户审计、风险测算和本地项目根目录 `.crypto` 生命周期记录；不生成真实下单确认令牌、不调用交易写接口。
---

# Crypto Risk Ledger

负责把研究计划落到“账户能不能承受、该用多大数量、当前流水是否一致”。它是交易型消息面选币流程的前置门禁，但不负责新闻取证、行情结构判断或真实下单。

## 固定本地状态

固定使用项目根目录下的 `.crypto`。首次使用先初始化：

```bash
python3 scripts/crypto_memory.py init
```

脚本会从当前工作目录向上寻找 `.git` 或 `AGENTS.md` 来定位项目根目录，并把密钥、流水和 Wiki 写入该根目录的 `.crypto`；找不到项目标记时退回当前工作目录。实际执行时推荐把命令的 `workdir` 设为要保存凭证的项目根目录；如需指定其他根目录，可设置 `CRYPTO_ROOT=/path/to/.crypto`。

涉及建议、开仓、平仓、加减仓、复盘或学习资料时，先读取：

```bash
python3 scripts/crypto_memory.py context
```

需要账户风险判断时，再让用户通过隐藏输入配置 Binance 密钥：

```bash
python3 scripts/crypto_memory.py configure-binance
```

密钥只允许保存到 `<项目根目录>/.crypto/config.json`，目录权限 `0700`、文件权限 `0600`。不得在对话、命令参数、日志、Wiki 或交易流水中输出密钥。默认只读；本 Skill 不请求也不使用交易写权限。

## 每次触发必须审计

只要进入消息面选币、持仓、数量、复盘、学习资料或交易生命周期相关任务，都先执行上下文读取，再执行私有只读快照：

```bash
python3 scripts/binance_private_snapshot.py
```

按以下顺序处理差异，完成前不继续生成新仓位建议：

1. `UNTRACKED_ACTIVE_POSITION`：账户有真实仓位但本地流水未记录。检查近期成交和最近计划；能唯一匹配时补记 `OPEN`，不能唯一匹配时只追问缺失事实。
2. `QUANTITY_CHANGED`：真实数量与流水不一致。用近期成交识别加仓或部分平仓，追加 `ADJUST`；不能把当前持仓均价当成每笔原始成交价。
3. `LOGGED_POSITION_NOT_ACTIVE`：流水显示未平但账户无仓位。检查近期成交，能重建时追加 `CLOSE` 并复盘；数据不足时标为“疑似已平仓待确认”，不要继续计入当前风险。
4. `ALIGNED`：明确写出已对齐，不让用户手动提醒。

如果未配置密钥或读取失败：允许继续做公开消息和行情观察，但不得输出精确数量、杠杆、保证金占用或“可执行建议”。

## 仓位与组合风险

先由消息和结构给出入场参考价、结构止损、保守目标，再反推数量；不得先选杠杆再倒推风险。

核心公式：

- `账户风险额 = 账户权益 × 风险比例`
- `止损距离比例 = abs(入场参考价 - 止损价) / 入场参考价`
- `风险约束名义仓位 = 账户风险额 / 止损距离比例`
- `保证金占用 = 名义仓位 / 建议杠杆`
- `交易数量 = 名义仓位 / 入场参考价`

风险上限：

- 单币精选：净盈亏比 `>1 且 <1.5` 通常不超过权益 `0.5%`；`1.5–3` 通常 `0.75%`；A+ 且 `≥3` 最高 `1.25%`。
- 篮子：核心仓单腿 `0.4%–0.6%`，侦察仓 `0.15%–0.3%`，任何单腿不超过 `0.6%`；计划止损风险合计默认不超过权益 `4%`，同方向高 Beta 不超过 `2.75%`。
- 中长线：单腿 `0.2%–0.5%`，中长线桶连同已有同方向敞口不超过权益 `1.25%`。
- 保留至少 `20%` 可用余额，不把全部余额用于保证金。
- 组合单日亏损、滚动 7 日回撤、月度高点回撤等闸门触发时，降低风险或禁止新仓。

逐仓优先。只有私有快照可用、全部持仓风险可核算、强平压力测试通过、无对冲关系不明仓位时，才可建议全仓；全仓不等于满仓。

## 交易记录

用户确认实际手动开仓时，缺少币种、方向、成交价、数量中任何一项就只追问缺项。记录前把推荐当时的理由写入 JSON，不能只保存 `plan-id`：

```bash
python3 scripts/crypto_memory.py open --symbol BTCUSDT --side LONG --entry 64000 --quantity 0.01 --plan-id PLAN_ID --rationale-file /tmp/crypto-plan-rationale.json
```

理由 JSON 必须包含：`strategyMode`、`batchId`、`portfolioContext`、`summary`、`catalyst`、`technicalSetup`、`derivativesConfirmation`、`tradePlan`、`positionSizingReason`、`invalidation`、`confidence`、`dataCutoff`、非空 `sources`。

### 用户声明已开但成交事实缺失

如果用户说“我开了 X/Y/Z”，但私有快照没有对应真实持仓，或缺少方向、实际入场价、数量中任一项：

- 不得为了方便复盘而伪造 `OPEN` 流水。
- 如果用户说明是在跟单、子账户、其他交易所或机器人里开的，不能用当前 Binance 主账户私有快照的“无持仓”判断已经平仓或不存在；在用户明确说平仓前，按用户声明保持 active tracking。
- 只追问正式 ledger 必需的最少信息：每个币种的方向、实际入场价、数量；若用户也能提供止损/计划则一并记录。
- 在用户暂时不补成交细节但要求持续跟进时，可在 `<项目根目录>/.crypto/position-watch/` 建立 `user_declared_open_positions_pending_trade_details` 跟踪清单，记录：
  - 用户声明已开仓的 symbol。
  - 仓位来源，例如 `copy_trading` / 子账户 / 其他交易所；若是跟单仓，标注 `active_until_user_says_closed=true`。
  - 已知未来催化节点、事件时间、当前阶段、需要跟进的公告/落地/失效条件。
  - 明确标注 `direction/entry/quantity = unknown/null`，并写明“不能用于盈亏、R 倍数或仓位风险计算”。
- 每次后续触发消息面选币、复盘或持仓跟进时，先读取该 watchlist；若用户补齐成交事实，再转写正式 `OPEN`，并在 rationale 中引用原始未落地催化与跟踪清单。

平仓：

```bash
python3 scripts/crypto_memory.py close --trade-id TRADE_ID --exit 66000 --fees 0
```

加仓或部分平仓：

```bash
python3 scripts/crypto_memory.py adjust --trade-id TRADE_ID --quantity-delta -0.005 --price 65000 --fees 0.2
```

完整平仓后必须基于原建议、开仓记录、持仓期间消息与量价、实际结果做归因分析；只把跨交易可复用、有证据的结论写入 Wiki。

平仓复盘不能只记录最终盈亏。若用户反馈“盈利但中途浮亏很多”或类似过程风险，必须记录 MAE/最大不利浮动的定性或定量信息、浮亏发生阶段、是否由短挤/流动性/资金费率/OI 拥挤造成，以及下次同类题材应降低仓位、等待触发或提高风险标签。缺少入场价、数量或精确浮亏数值时，只记录用户声明的定性复盘，不伪造 R 倍数或正式盈亏。

若用户反馈“有浮盈但被一根阴线打到保本损”，必须把结果记为 `breakeven_stop_after_unrealized_profit` 或等价语义，并复盘浮盈保护缺口：是否未分批止盈、是否未上移止损、是否在事件前 12-24 小时仍无保护持仓、15m/1h 大阴线是否触发退出。缺少具体浮盈金额时只记录定性结论。

## 输出格式

```markdown
## 生命周期审计
- context：已读取 / 未读取（原因）
- private_snapshot：已读取 / 不可用（原因）
- ledger_vs_account：ALIGNED / UNTRACKED_ACTIVE_POSITION / QUANTITY_CHANGED / LOGGED_POSITION_NOT_ACTIVE
- 处理动作：

## 风险闸门
- 账户权益/可用余额：可展示必要摘要，不暴露敏感细节
- 当前持仓风险： 
- 组合回撤闸门：
- 是否允许新增计划：

## 仓位测算
| plan-id | symbol | side | entry | stop | risk% | notional | quantity | leverage | margin | portfolio_risk |
|---|---|---|---|---|---|---|---|---|---|---|

## 记录/复盘动作
- 新增 OPEN/ADJUST/CLOSE：
- 需要用户补充的最少信息：
```
