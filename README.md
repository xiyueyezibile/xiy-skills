
## Skills List

![skills cabinet](assets/readme-illustrations/01-skills-cabinet.svg)

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

### component-validation-mock

为前端组件创建可复现的页面首屏 Mock，并自动生成浏览器操作 JSON、打开页面、执行简单交互和截图验证

```bash
npx skills add xiyueyezibile/xiy-skills@component-validation-mock -g -y
```

功能特性：

- 从用户 URL 反查真实页面入口，可复用已有 mock 数据和组件封装，但必须挂载回该页面
- 高清模式默认使用 macOS 系统原生截图；Chrome 在副屏时直接按显示器编号捕获该屏，再从原始 PNG 无缩放裁切，无需把窗口拉回主屏
- Chrome/Browser 若只导出 CSS 像素尺寸 JPEG，即使页面 DPR 正确也判为普通截图，不会转 PNG 或放大后冒充高清
- 移动端高清截图复用用户预先准备的 Chrome DevTools 设备页面；页面或权限未准备时给出一次性准备提醒
- 用户明确不需要高清时回退普通浏览器截图，并清楚标记为非系统高清截图
- 用户给出的 URL 仅用于锁定目标页面，不假设该地址原本就能看到组件
- 在目标 URL 对应的真实页面入口增加 dev-only Mock，保留原 path/query/hash，并追加 `componentMock` 后打开验证
- Mock 数据优先复用真实调用点、类型、fixture/story 和业务文案，合理填充组件内的文本、图片、金额、状态与列表，避免只求渲染成功而影响观感
- 在用户目录记录 Mock 改动文件、位置、锚点、前后片段和哈希；取消 Mock 时先与当前源码及 Git diff 对比，再做最小撤销
- 将用户目标页面 URL 持久记录到 `~/.component-validation/page-urls.json`，不会用临时 Mock URL 覆盖
- 禁止擅自切换到独立 story/demo，用同一目标页面首屏截图
- 生成可机器校验的 `browser-actions.json`
- 支持桌面端以及移动端 viewport、触摸和 user agent 模拟
- 默认使用桌面端 DPR 2、移动端 DPR 3，并校验浏览器真实 DPR 与 PNG 输出像素，避免配置了高清但产物仍是 1x
- 支持点击、输入、按键、下拉选择、滚动等简单交互
- 自动打开目标页面，并在初始状态和关键交互后截图
- Mock 改动清单、操作 JSON、截图和验证报告统一保存到 `~/.component-validation/cases/`，不写入业务仓库
- 按修改时间全局只保留最近 `500` 张截图
- 内置 JSON 校验脚本，禁止任意脚本执行、危险截图路径和敏感会话数据

使用示例：

- “把 CouponCard 放到优惠券列表页首屏并截图”
- “用 390x844 移动端验证 SkuPanel，点开规格后再截图”
- “给空态组件做个 mock，输入关键词并按 Enter 后验证”

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

团队踩坑收集器：面向非纯闲聊工程任务，在任务开始前按仓库领域级、全局领域级、仓库级、全局级加载已有知识，任务结束前复盘是否值得沉淀

```bash
npx skills add xiyueyezibile/xiy-skills@team-pitfalls -g -y
```

功能特性：

- 使用时固定包含“前置检查 + 后置复盘”两段动作
- 提供 `begin_task.py` / `end_task.py` 两步生命周期门禁：前者按分层顺序返回知识摘要，后者只要求明确记录或跳过沉淀
- 前置检查实际采用记录时自动累计使用次数，区分“问题再次出现”和“知识被复用”
- 分层上下文优先：仓库领域级 `repos/<repo>/domains/<domain>/` → 全局领域级 `domains/<domain>/` → 仓库级 `repos/<repo>/` → 全局级 `pitfalls/`
- 同一仓库可拆多个领域；业务跨仓库时还可维护全局领域级，用来反向发现其他仓库的同领域记录
- 每个领域 `index.md` 都保留简短介绍，说明业务、页面/链路范围、典型术语或指标边界
- 适合放进领域级的知识：某类业务、某个页面、页面簇、业务链路、端内入口、领域术语、领域指标或类似稳定范围
- 不再使用 query 召回、字段打分、命中词证据或 Top-N 截断作为主流程
- 每条记录返回 `ID + Kind + Title + Tags + File + 结论` 摘要，按层级顺序审阅和采用
- 不重复输出 `SKILL.md`、`llms.txt` 或全量 `index.md`，分层读取发生在本地脚本内
- 复杂 JSON 支持通过 `--json-file` 安全传入，兼容带空格路径与 UTF-8 BOM，并提供明确解析位置
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
python3 skills/team-pitfalls/scripts/end_task.py --task-id task-20260717 --result skipped --reason "没有新的可迁移知识"
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
