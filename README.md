
## Skills List

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

### team-pitfalls

团队踩坑收集器：对话中出现易错点时，按标准沉淀到skill里

```bash
npx skills add xiyueyezibile/xiy-skills@team-pitfalls -g -y
```

功能特性：

- 只记录“新同学不看大概率会写错”的可复用问题
- 先做通用模式判断，再决定是否写入
- 对同类问题做去重与累计次数
- 约束不记录密钥、token、cookie 等敏感信息

### superpowers

覆盖全流程的工作流系统

```bash
npx skills add https://github.com/obra/superpowers
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

### btc-trading-analyst

BTC 合约交易分析专家，10 年加密货币合约交易经验

```bash
npx skills add xiyueyezibile/xiy-skills@btc-trading-analyst -g -y
```

功能特性：

- 10年加密货币合约交易经验，专注于 BTC 市场分析
- 结合技术面、消息面和市场情绪进行综合分析
- 中短线交易策略，博弈支撑位和阻力位
- 严格的风险控制规则，以损定杠杆
- 标准化的开仓分析报告输出
- 支持 50倍、25倍等多种杠杆选择
- **内置完整的 K 线形态库**（看涨/看跌形态识别）
- **追涨追空场景库**，包含假突破识别
- 高胜率 K 线形态筛选标准（位置优先、量能配合、趋势确认）
- 形态胜率周期差异分析（日线、周线/月线、分钟线）
