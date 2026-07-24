---
name: component-validation-mock
description: 为前端组件创建目标页面首屏 Mock 验证环境。用户要求组件 mock、首屏看效果、高清/移动端截图、点击输入后截图或视觉验收时使用。
compatibility: 需要可编辑前端仓库、可运行本地服务、Browser 或外部 Chrome；高清模式需要 macOS screencapture 与屏幕录制权限，移动端高清需用户预先准备 Chrome DevTools 设备页面。
---

# Component Validation Mock

把待验证组件以最小、可撤销的临时代码展示在目标页面首屏，并用结构化浏览器动作完成截图和简单交互验证。

核心语义：

- 用户给出的 URL 是目标页面，不代表组件已经在该页面出现。
- 必须先定位该 URL 对应的真实页面入口并完成 Mock，再打开用户给定或实际确认的同一个 URL 验证。
- 禁止为触发 Mock 追加 `componentMock`、`mockCase`、`debug` 等 query/hash；新增参数可能改变真实路由、缓存、埋点或接口参数。
- 除非用户明确同意，不得切换到 story、demo、playground 或新路由截图。
- 默认使用用户外部 Chrome 验证；默认交付系统高清截图；用户明确说“不需要高清”“普通截图即可”时才降级。

## 产物

业务仓库只保留组件首屏 Mock 所需的临时代码。验证状态和产物统一写入用户目录：

```text
~/.component-validation/
├── page-urls.json
└── cases/<case-name>/<run-id>/
    ├── browser-actions.json
    ├── mock-changes.json
    ├── report.md
    └── screenshots/
```

每次至少交付：

- 目标页面首屏 Mock 代码
- `<runDir>/mock-changes.json`
- `<runDir>/browser-actions.json`
- 初始首屏截图和用户指定交互后的截图
- `<runDir>/report.md`

不要把改动清单、操作 JSON、截图、报告或 URL 映射写入业务仓库。保留用户已有改动，不改 `.gitignore` 和 `.vscode`。

## 开始前

优先从用户描述和仓库推断，无法安全推断时再追问：

- 组件文件、导出名、必需 props、Provider、接口数据
- 目标页面 URL、路由、package 和本地服务命令
- 桌面端或移动端；移动端未给设备时默认 `390x844`
- 是否明确不需要高清；未说明即按高清模式
- 需要执行的简单交互和截图时机
- 鉴权、端内环境、接口稳定性等前置条件

先检查 git 根目录、工作区状态、项目约束、运行脚本、路由配置和目标页面挂载关系。

## URL 规则

明确区分：

- **目标页面 URL**：用户提供或历史记录中的页面地址，用于锁定路由、package 和页面入口。
- **实际验证 URL**：默认与目标页面 URL 完全一致；只有本地服务 origin 经确认不同时，才允许替换 origin，pathname、query、hash 必须保持不变。

URL 优先级：

1. 用户本轮给出的完整 URL
2. 用户通过文字、截图、浏览器当前页、配置或文档明确指出并由本轮验证确认的 URL
3. `~/.component-validation/page-urls.json` 中当前仓库、当前页面的最近记录
4. 从路由和开发服务推导出的候选 URL；候选必须实际打开并确认后才能记录

用户只给路由片段时，结合已确认的开发服务 origin 生成完整 URL。不要凭常见端口或页面名猜测。

每次得到完整目标页面 URL 后立即记录，记录值就是后续浏览器要打开的 URL，不能保存带临时 Mock 参数的地址：

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

URL 记录不得包含 token、cookie、密码、签名或鉴权码；发现敏感值时先生成安全可复现 URL。

## 工作流

### 1. 定位页面

从目标 URL 的 pathname、query、hash、路由配置、页面入口和共享挂载关系反查真实渲染文件。确认：

- 目标路由可由当前 package 启动
- 组件依赖的主题、国际化、状态管理和路由上下文
- 页面是否需要登录、接口数据或端内环境
- 哪些已有 query/hash 决定真实页面状态；必须原样保留，不能新增 Mock 参数

### 2. 建立首屏 Mock

按优先级选择：

1. 在目标 URL 对应页面入口增加临时首屏 Mock 分支，打开原 URL 即渲染组件。
2. 复用目标页面或仓库已有 mock 数据、Provider、fixture、story 封装，但仍挂载回目标页面入口。
3. 页面入口无法直接修改时，在最近共享挂载层增加只对目标 pathname 或页面标识生效的临时分支，不通过 URL 参数触发。
4. 最后才临时替换目标页面主体，并保留原实现，确保易恢复。

Mock 容器必须：

- 让组件首屏可见，避免导航栏或浮层遮挡
- 保留真实依赖的 Provider
- 使用确定性数据，禁止真实写操作
- loading、empty、error 等状态一态一 case
- 提供稳定就绪标记，例如 `data-component-validation-ready`
- 不设计可由新增 URL 参数触发的入口

Mock 数据必须满足视觉验收质量。读取并遵循 [Mock 数据质量规则](references/mock-data-quality.md)：从真实调用点、类型、fixture/story、页面文案取材；标题、图片、金额、状态、列表、时间等可见内容要合理且一致；不得用 `test`、`foo`、重复数字、Lorem、破图或大量空值敷衍，除非 case 明确验证空态或异常态。

完成每个 Mock 改动后，立即按 [Mock 改动清单协议](references/mock-changes-schema.md) 写入 `<runDir>/mock-changes.json`。行号只辅助导航，稳定锚点、前后片段和文件 SHA-256 用于抵抗代码漂移；清单不是可信回滚脚本。

### 3. 生成操作 JSON

读取 [浏览器操作协议](references/browser-actions-schema.md)，基于 [示例](assets/browser-actions.example.json) 创建动作文件。

先准备运行目录：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prepare-case \
  --case <case-name>
```

`browser-actions.json` 必须写入 `targetUrl`，值为目标页面完整 URL。所有 `open.path` 必须与 `targetUrl` 的 pathname、query、hash 一致；仅允许在本地服务 origin 已确认不同的情况下替换 origin。

写完后校验：

```bash
python3 <skill-dir>/scripts/validate_mock_changes.py <runDir>/mock-changes.json
python3 <skill-dir>/scripts/validate_browser_actions.py <runDir>/browser-actions.json
```

动作只允许 `open`、`waitFor`、`click`、`fill`、`press`、`select`、`scroll`、`screenshot`。移动端 case 必须设置 `device.kind=mobile` 和 viewport。高清 case 设置 `requireNativeScale: true`，桌面默认 DPR 2，移动端默认 DPR 3；用户明确不需要高清时才可 `requireNativeScale: false`。

### 4. 启动和预检

使用仓库已有命令启动正确 package 的开发服务。确认：

- URL 不是 404、错误页或错误 package
- 实际验证 URL 与目标页面 URL 一致；若仅替换 origin，pathname/query/hash 必须一致
- 没有跳到未获同意的 demo/story 路由
- 控制台没有由本次 Mock 引入的错误
- 组件在首屏且就绪标记可见
- 截图目录已创建

端口被占用时，先确认占用进程是否就是目标服务，不要直接终止未知进程。

### 5. 浏览器执行

默认先使用用户外部 Chrome：检查外部浏览器插件连接，连接成功后再导航、观察 DOM、执行交互。用户明确指定 Browser 时遵从指定；外部 Chrome 不可用时先引导连接或说明阻塞，只有用户同意降级或环境确实不可用时才改用内置 Browser，并在报告中说明。

每次交互前重新观察页面，优先用稳定的 `data-testid`、role、label 或文本定位。定位不唯一时停止并修正 Mock 或动作 JSON，不要随意点击第一个元素。

默认只覆盖点击、输入、按键、选择和滚动。拖拽、多指手势、文件上传、复杂画布操作需单独说明。

### 6. 截图

先读取并遵循 [系统高清截图流程](references/system-screenshot.md)。

默认高清路径：

- 用 macOS `screencapture` 截取外部 Chrome 所在显示器，再从原始 PNG 无缩放裁切组件或页面区域。
- Chrome 在副屏时直接用 `-D <display-id>` 捕获该屏，不要先拉回主屏。
- 禁止截图后插值放大。
- 权限缺失时说明需要开启屏幕录制、辅助功能或自动化权限，等待用户确认后重试；不能静默降级。

移动端高清路径：

- 复用用户预先准备的 Chrome DevTools 设备页面。
- 开始前确认设备工具栏、viewport、user agent/touch 和页面重新初始化都正确。
- 缺少页面时提醒用户准备一个可长期复用的设备页面；不要由 Agent 反复临时打开或关闭 DevTools。

普通截图兜底：

- 仅用户明确不需要高清时启用。
- 报告必须标记“普通浏览器截图，非系统高清截图”。
- 若按 DPR 生成，仍用 `validate_screenshot_resolution.py` 校验像素。

至少截图初始首屏和每个用户指定关键交互后的状态。截图前等待动画和异步状态稳定，优先等待可观察条件，不随意长 sleep。每生成一张截图后执行：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prune-screenshots --limit 500
```

### 7. 报告

`<runDir>/report.md` 必须保存在用户目录，包含：

- 用户目标页面与实际验证地址；若仅替换 origin，明确说明
- 设备、viewport、组件路径和 Mock 入口
- 初始首屏、Mock 数据完整度、每个交互的通过/失败结论和证据
- Mock 改动清单、操作 JSON、截图路径
- 清晰度信息：请求 DPR、实际 DPR、CSS viewport、PNG 像素、高清校验结果
- 已知限制；没有则写“无”

报告只能声明实际观察到的结果。页面未打开、截图未生成或交互未执行时，不得写“通过”。

## 取消 Mock

用户要求取消、清理或恢复 Mock 时，先读取对应 case 的 `mock-changes.json` 辅助定位，但不能照单整文件回滚：

1. 确认当前 git 根目录与清单 `repoRoot` 是同一仓库。
2. 读取当前源码和 staged/unstaged diff；行号只作导航。
3. 核对 symbol/锚点、`afterSnippet`、SHA-256 和相邻上下文，判断当前代码是否仍属于该次 Mock。
4. 证据一致时只生成最小反向补丁；不得使用 `git checkout -- <file>`、`git restore <file>` 或整文件覆盖。
5. 本次创建的文件仅在内容仍匹配、无新增引用或用户修改时删除。
6. 无法确认归属时跳过该项并报告冲突，请用户决定。

撤销后重新读取文件和 diff，报告逐文件标记 `removed`、`skipped-conflict` 或 `already-absent`。

## 失败处理

- 缺 props：先从类型、调用点、story 推断；仍不确定再问。
- 缺可信业务数据：从类型、真实调用点、fixture/story 和相邻文案构造脱敏代表性数据；无法确认关键语义时标限制。
- 页面需鉴权：使用现有已登录浏览器会话；不得读取 cookie、密码或会话存储。
- 接口不稳定：使用仓库已有 mock 层或确定性本地数据。
- 浏览器能力不可用：仍可生成并校验 JSON，但标记截图验证未执行。
- 系统截图权限未开：提醒到“系统设置 -> 隐私与安全性”开启屏幕录制；需要控制 Chrome 时同时提醒辅助功能/自动化。
- 移动端 Chrome 页面未准备：提醒用户创建并保留 DevTools 设备页面，默认 `390x844`。
- 历史 URL 失效：探测路由或向用户确认，验证新 URL 后覆盖记录。
- 目标页面入口无法安全 Mock：报告原因并请求方向，不用独立 demo/story 截图代替。
- 页面错误：保留证据，定位为 Mock、页面或环境问题，不修改业务逻辑掩盖。

## 完成门槛

只有同时满足以下条件才算完成：

- 组件在目标页面首屏可见。
- URL 映射和浏览器验证都使用用户目标页面 URL；若仅替换 origin，pathname/query/hash 保持一致。
- Mock 挂载在目标 URL 对应入口，打开目标 URL 后无需额外导航即可看到组件。
- Mock 数据覆盖主要可见字段，语义、字段关系、文本长度、图片和列表密度可信。
- 无随意占位导致的空白、破图、塌陷、异常截断或状态/操作矛盾。
- JSON、Mock 改动清单均通过校验并覆盖本次改动。
- 浏览器打开正确 URL，设备模式与 case 一致，要求交互已执行。
- 截图存在且可辨认；高清模式记录正确显示器、原始 PNG、裁切尺寸且无插值放大。
- 移动端高清复用用户准备的 DevTools 设备页面并记录 viewport/设备模式。
- 普通截图兜底只在用户明确不需要高清时启用，并清楚标注非高清。
- 报告中每项结论都有截图或页面观察证据。
- 报告、改动清单、操作 JSON、截图均不在业务仓库内。
- 截图保留策略已执行，用户目录截图总数不超过 500。
