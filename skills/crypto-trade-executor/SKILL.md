---
name: crypto-trade-executor
description: 消息面选币的半自动交易执行子 Skill。仅当用户已完成研究计划、账户审计、风险测算，并明确要求为单个 Binance U 本位永续市价计划生成订单草案，或回复精确“确认执行 TOKEN”时使用。负责 prepare/execute 两阶段确认、设置杠杆/保证金、开市价主单、挂 reduce-only 止盈和 closePosition 止损；没有未过期精确令牌绝不调用写接口。
---

# Crypto Trade Executor

负责真实资金动作的最后一公里。它只执行已经通过 `crypto-news-intel`、`crypto-market-structure`、`crypto-risk-ledger` 审核的一笔 U 本位永续市价计划；不负责临场重写消息理由、放宽风险，也不替用户确认。

## 前置条件

同时满足才可生成草案：

- 用户明确要求自动执行或生成确认单。
- 计划是单个 U 本位永续市价单，不是近价限价、加仓、反手、移动止损或批量篮子一键下单。
- `crypto-risk-ledger` 已完成本轮账户/流水审计，且没有未处理差异。
- 计划包含 `plan-id`、symbol、方向、数量、杠杆、保证金模式、结构止损、1–3 级固定数量止盈。
- Binance 密钥已由用户在本地配置，且只需要 U 本位合约交易权限；仍不得请求提现、转账或现货交易权限。

若任一条件不满足，只输出“不能执行”的原因和需要补齐的最小信息。

## 两阶段流程

### 1. prepare：生成草案，不写交易接口

```bash
python3 scripts/binance_confirmed_trade.py prepare \
  --plan-id PLAN_ID --symbol BTCUSDT --side LONG --quantity 0.01 \
  --leverage 5 --margin-type CROSS --stop-loss 62000 \
  --take-profit-level 66000:0.006 --take-profit-level 68000:0.003
```

脚本会从当前工作目录向上寻找 `.git` 或 `AGENTS.md` 来定位项目根目录，并读取/写入该根目录的 `.crypto`；找不到项目标记时退回当前工作目录。实际执行时推荐把命令的 `workdir` 设为要保存凭证的项目根目录；如需指定其他根目录，可设置 `CRYPTO_ROOT=/path/to/.crypto`。

`prepare` 只能校验交易规则、数量、最小名义金额、价格方向和草案完整性，并写入 `<项目根目录>/.crypto/confirmations/`。默认有效期 10 分钟。

向用户展示：

- 交易对、方向、数量
- 杠杆、逐仓/全仓
- 最新参考价与执行说明
- 止损价
- 每一级止盈价和固定数量
- 草案过期时间
- 精确确认短语：`确认执行 TOKEN`

不要把模糊回复当确认。草案过期、计划参数变化、行情条件变化或用户重新选币时，废弃旧草案并重新 `prepare`。

### 2. execute：只有精确令牌才能写接口

只有用户在当前对话中逐字回复未过期的 `确认执行 TOKEN` 时，才执行：

```bash
python3 scripts/binance_confirmed_trade.py execute --token TOKEN --confirm TOKEN
```

执行脚本会再次检查：

- 令牌和到期时间
- 单/双向持仓模式
- 交易规则、最小数量、最小名义
- 同币种已有仓位
- 残留算法保护单
- 执行前最新标记价

随后按顺序处理：设置杠杆/保证金模式 → 提交唯一 client order ID 的市价主单 → 挂 `MARK_PRICE` 触发的固定数量 reduce-only 止盈 → 挂 `closePosition=true` 整仓止损。

## 失败与保护

- 检测到同币已有仓位或残留保护单：拒绝执行，不自动合并仓位。
- 主单状态超时或未知：停止自动重试，要求人工检查账户。
- 止损保护失败：取消已挂止盈，并尝试紧急 reduce-only 市价平仓；若仍失败，输出最高级别“存在未保护真实仓位”告警。
- 部分止盈失败但止损成功：保留已成功保护，明确报告“部分保护”，不能冒充完整成功。
- 止损触发后，后续审计要识别并清理未触发 reduce-only 止盈残单；清理前阻止同币再次开仓。

## 执行后记录

执行成功后立即读取私有快照核对真实成交、仓位和保护单，然后调用 `crypto_memory.py open` 记录实际成交。记录用的 rationale 必须来自确认前已保存的计划，不能用成交后的走势补写。

输出必须包含：

```markdown
## 执行结果
- 主单状态：
- 实际成交均价/数量：
- 杠杆/保证金模式：
- 止盈保护：
- 止损保护：
- ledger 记录：
- 后续必须检查：
```

## 明确禁止

- 禁止无 `确认执行 TOKEN` 调用写接口。
- 禁止批量自动开篮子；篮子最多逐单生成草案并逐单确认。
- 禁止执行近价限价、加仓、反手、移动止损；这些只给手动清单。
- 禁止扩大用户已确认数量、移动止损或新增未确认止盈。
- 禁止打印 API Key/Secret、签名串、账户敏感标识。
