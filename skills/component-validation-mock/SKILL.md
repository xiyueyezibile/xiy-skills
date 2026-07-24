---
name: component-validation-mock
description: 为前端组件创建可复现的页面首屏 Mock 验证环境，持久记录用户提供或确认的页面 URL，生成浏览器操作 JSON，自动打开正确页面并完成桌面端或移动端截图及简单交互验证。当用户要求“组件 mock”“把组件放到首屏看效果”“打开页面截图验证”“移动端调试截图”“点击/输入后截图”“为组件做视觉验收”时，务必使用此 skill。
compatibility: 需要可编辑的前端仓库、可运行的本地开发服务，以及 Browser 或 Chrome 浏览器控制能力。
---

# Component Validation Mock

把待验证组件以最小、可撤销、仅开发环境生效的方式展示在目标页面首屏，并用结构化浏览器动作完成截图和简单交互验证。

## 目标产物

业务仓库只保留组件首屏 Mock 所必需的 dev-only 代码。验证状态和产物统一保存在用户目录：

```text
~/.component-validation/
├── page-urls.json
└── cases/<case-name>/<run-id>/
    ├── browser-actions.json
    ├── report.md
    └── screenshots/
```

每次执行至少交付组件首屏 Mock 代码、操作 JSON、截图和报告。不要把操作 JSON、截图、报告或 URL 映射写入业务仓库。

## 开始前收集

优先从用户描述和仓库中推断，只有无法安全推断时才追问：

- 待展示组件的文件路径、导出名
- 目标页面路由和所属应用/package
- 组件必需 props、上下文 Provider、接口数据
- 桌面端或移动端；移动端未给设备时默认 `390x844`
- 要执行的简单交互和每个截图时机
- 本地服务启动命令、端口、鉴权前置条件

先检查当前 git 根目录、工作区改动、项目约束文件、运行脚本和目标页面挂载关系。保留用户已有改动，不改 `.gitignore` 和 `.vscode`。

### 页面 URL 记忆

页面 URL 的优先级是：

1. 用户本轮直接给出的完整 URL
2. 用户通过文字、截图、浏览器当前页、配置文件或文档明确指出并由本轮验证确认的 URL
3. `~/.component-validation/page-urls.json` 中当前仓库、当前页面的最近记录
4. 从路由和开发服务推导出的候选 URL；候选必须实际打开并确认后才能记录

用户只给路由片段时，结合已经确认的开发服务 origin 生成完整 URL。不要凭常见端口、页面名或构建工具猜最终 URL。

每次得到用户提供或实际验证通过的完整 URL 后立即记录：

```bash
python3 <skill-dir>/scripts/component_validation_state.py record-url \
  --repo <git-root-name> \
  --page <稳定页面标识> \
  --url <完整-http(s)-url> \
  --source <user|browser|config|docs|inferred-verified>
```

读取历史 URL：

```bash
python3 <skill-dir>/scripts/component_validation_state.py resolve-url \
  --repo <git-root-name> \
  --page <稳定页面标识>
```

URL 记录不得包含 token、cookie、密码、签名或鉴权码。脚本会拒绝常见敏感 query 参数；发现敏感值时先生成安全的可复现 URL 再记录。

## 工作流

### 1. 定位真实页面

从路由、页面入口、共享页面挂载关系反查真实渲染文件。不要仅凭文件名猜测路由。

确认：

- 目标路由可由当前 package 启动
- 组件依赖的主题、国际化、状态管理和路由上下文
- 页面是否需要登录、接口数据或端内环境

### 2. 选择最小 Mock 方式

按优先级选择：

1. 使用仓库已有 story、demo、playground 或 mock 机制
2. 使用仅开发环境生效的 query 参数，例如 `?componentMock=<case-name>`
3. 在目标路由旁新增 dev-only 验证路由
4. 最后才临时替换页面主体；必须保留原实现并易于恢复

Mock 容器应：

- 让组件进入首屏可视区域，避免被导航栏或浮层遮挡
- 保留组件实际依赖的 Provider
- 使用确定性数据，禁止真实写操作
- 覆盖 loading、empty、error 等状态时，一种状态对应一个 case
- 对异步内容提供稳定的就绪标记，例如 `data-component-validation-ready`
- 不在生产构建中暴露验证入口

### 3. 生成浏览器操作 JSON

读取 [浏览器操作协议](references/browser-actions-schema.md)，基于
[示例](assets/browser-actions.example.json)。先创建本次运行目录：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prepare-case \
  --case <case-name>
```

脚本返回 JSON，其中 `runDir` 是本次唯一目录。把操作文件写到 `<runDir>/browser-actions.json`，截图写到 `<runDir>/screenshots/`，报告写到 `<runDir>/report.md`。

动作只允许：

- `open`
- `waitFor`
- `click`
- `fill`
- `press`
- `select`
- `scroll`
- `screenshot`

移动端 case 必须设置 `device.kind` 为 `mobile`，并提供 viewport。打开页面后先应用设备模拟，再刷新或重新打开目标 URL，确保响应式逻辑按移动端初始化。

运行前执行：

```bash
python3 skills/component-validation-mock/scripts/validate_browser_actions.py \
  <runDir>/browser-actions.json
```

如果 Skill 安装在其他位置，使用该 Skill 目录下脚本的实际路径。

### 4. 启动并预检页面

使用仓库已有命令启动正确 package 的开发服务。确认：

- URL 返回页面而不是 404、错误页或错误 package
- 最终 URL 来自用户信息、已持久化映射或实际打开确认，不能只由路由名称猜测
- 控制台没有由本次 Mock 引入的错误
- 目标组件处于首屏且就绪标记可见
- 截图目录已创建

若端口被占用，先确认占用进程是否就是目标服务，不要直接终止未知进程。

### 5. 执行浏览器动作

用户明确指定 Browser 或 Chrome 时遵从指定；否则根据目标 URL 选择可用浏览器。

将 JSON 动作映射到浏览器的实际 API：

- `open`：导航到 URL
- `waitFor`：等待选择器可见或文本出现
- `click`：点击唯一匹配元素
- `fill`：清空并输入内容
- `press`：发送按键
- `select`：选择下拉项
- `scroll`：滚动窗口或容器
- `screenshot`：保存当前视口或指定元素截图

每次交互前重新观察页面，优先使用稳定的 `data-testid`、role、label 或文本定位。不要依赖容易变化的深层 CSS 层级。定位不唯一时停止并修正 Mock 或动作 JSON，不要随意点击第一个元素。

简单交互只覆盖点击、输入、按键、选择和滚动。拖拽、多指手势、文件上传、复杂画布操作不属于默认范围，需单独说明。

### 6. 截图验证

桌面端按 JSON viewport 截图。移动端必须确认：

- viewport 已切换为目标移动端尺寸
- 页面重新初始化后再操作
- 没有仅改变窗口宽度却遗漏移动端 user agent/touch 的问题；若浏览器不支持完整设备模拟，在报告中明确能力差异

至少截图：

1. 组件初始首屏状态
2. 每个用户指定的关键交互后状态

截图前等待动画和异步状态稳定；优先等待可观察条件，不使用随意的长时间 sleep。

每生成一张截图后执行一次全局保留策略：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prune-screenshots --limit 500
```

按文件修改时间仅保留 `~/.component-validation/cases/` 中最近 500 张 PNG 截图，旧截图由脚本删除。JSON、报告和 URL 映射不计入 500 张限制，也不会随截图一起删除。

### 7. 交付报告

`<runDir>/report.md` 使用以下结构，禁止保存到业务仓库：

```markdown
# <case-name> 组件验证

- 页面：<URL>
- 设备：<desktop/mobile + viewport>
- 组件：<path + export>
- Mock 入口：<route/query>

## 验证结果

- [通过/失败] 初始首屏展示：<证据>
- [通过/失败] <交互名称>：<证据>

## 产物

- 操作 JSON：<用户目录下的绝对路径>
- 截图：<用户目录下的绝对路径>

## 已知限制

- <无则写“无”>
```

报告只能声明实际观察到的结果。页面未打开、截图未生成或交互未执行时，不得写“通过”。

## 失败处理

- 缺组件 props：先从类型、调用点和 story 推断；仍不确定再询问
- 页面需鉴权：使用现有已登录浏览器会话；不得读取 cookie、密码或会话存储
- 接口不稳定：使用仓库已有 mock 层或确定性本地数据
- 浏览器能力不可用：仍可生成并校验 JSON，但明确标记截图验证未执行
- 历史 URL 已失效：实际探测路由或向用户确认，验证新 URL 后覆盖当前页面记录
- 移动端模拟不完整：记录实际 viewport、user agent 和 touch 能力
- 页面错误：保留错误证据，定位为 Mock、页面或环境问题，不用修改业务逻辑掩盖

## 完成门槛

只有同时满足以下条件才算完成：

- 组件在目标页面首屏可见
- 实际打开的 URL 与用户提供或已确认的页面 URL 一致，并已更新 URL 映射
- JSON 通过校验
- 浏览器实际打开了正确 URL
- 设备模式与 case 一致
- 要求的交互已执行
- 截图文件存在且内容可辨认
- 报告中的每项结论都有截图或页面观察证据
- 报告、操作 JSON 和截图均不在业务仓库内
- 截图保留策略已执行，用户目录下截图总数不超过 500
