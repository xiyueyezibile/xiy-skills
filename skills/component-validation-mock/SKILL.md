---
name: component-validation-mock
description: 为前端组件创建可复现的页面首屏 Mock 验证环境，把用户提供的 URL 视为目标页面而非组件现成展示页，先在该页面对应入口注入 dev-only Mock，确保同一页面 URL 的首屏直接显示组件，再优先使用用户外部 Chrome 浏览器完成桌面端或移动端截图及简单交互验证。默认交付高清版：高清截图使用 macOS 系统原生截图；移动端复用用户预先准备的 Chrome DevTools 设备页面，缺少页面或权限时明确提醒；用户明确不需要高清时才回退浏览器截图。当用户要求“组件 mock”“把组件放到首屏看效果”“打开页面截图验证”“高清截图”“移动端调试截图”“点击/输入后截图”“为组件做视觉验收”时，务必使用此 skill。
compatibility: 需要可编辑的前端仓库、可运行的本地开发服务、Browser 或 Chrome 浏览器控制能力；高清模式需要 macOS screencapture 与屏幕录制权限，移动端高清模式还需要用户预先准备 Chrome DevTools 设备页面。
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
    ├── mock-changes.json
    ├── report.md
    └── screenshots/
```

每次执行至少交付组件首屏 Mock 代码、Mock 改动清单、操作 JSON、截图和报告。不要把改动清单、操作 JSON、截图、报告或 URL 映射写入业务仓库。

默认交付要求：

- 优先使用用户外部 Chrome 浏览器验证页面；先检查外部浏览器插件连接，连接成功后使用外部浏览器导航、观察和交互。
- 除非用户明确说“不需要高清”“普通截图即可”，否则默认交付高清版，使用 macOS `screencapture` 截取外部 Chrome 所在显示器，再从原始 PNG 无缩放裁切组件或页面区域。
- 外部 Chrome 不可用时，先引导完成外部浏览器连接；只有用户同意降级或环境确实无法使用外部 Chrome 时，才改用内置 Browser，并在报告中说明。

## 开始前收集

优先从用户描述和仓库中推断，只有无法安全推断时才追问：

- 待展示组件的文件路径、导出名
- 目标页面路由和所属应用/package
- 组件必需 props、上下文 Provider、接口数据
- 桌面端或移动端；移动端未给设备时默认 `390x844`
- 是否明确不需要高清；未说明时默认按高清模式处理
- 要执行的简单交互和每个截图时机
- 本地服务启动命令、端口、鉴权前置条件

先检查当前 git 根目录、工作区改动、项目约束文件、运行脚本和目标页面挂载关系。保留用户已有改动，不改 `.gitignore` 和 `.vscode`。

### 页面 URL 记忆

> 关键语义：用户提供的 URL 只说明“组件应该在哪个页面验证”，不表示当前打开该 URL 已经能看到组件。收到 URL 后，必须先定位它对应的页面入口并完成 Mock，再打开验证地址。禁止跳过 Mock 直接截图用户原始页面。

明确区分：

- **目标页面 URL**：用户提供或历史记录中的页面地址，用于锁定路由、package 和页面入口；持久化保存此地址
- **验证 URL**：在目标页面 URL 上保留原有 path/query/hash，并追加或更新 `componentMock=<case-name>` 后得到的地址；浏览器最终打开此地址

除非用户给出的 URL 本身就是 story/demo，或用户明确同意改用独立演示页，否则不要把验证切换到另一个 story、demo、playground 或新路由。最终截图必须来自用户目标页面对应的入口。

页面 URL 的优先级是：

1. 用户本轮直接给出的完整 URL
2. 用户通过文字、截图、浏览器当前页、配置文件或文档明确指出并由本轮验证确认的 URL
3. `~/.component-validation/page-urls.json` 中当前仓库、当前页面的最近记录
4. 从路由和开发服务推导出的候选 URL；候选必须实际打开并确认后才能记录

用户只给路由片段时，结合已经确认的开发服务 origin 生成完整 URL。不要凭常见端口、页面名或构建工具猜最终 URL。

每次得到用户提供或实际确认的完整**目标页面 URL**后立即记录。不要用追加了 `componentMock` 的验证 URL 覆盖用户目标页面 URL：

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

### 1. 从目标 URL 定位真实页面

从用户目标页面 URL 的 pathname、query、hash、路由配置、页面入口和共享页面挂载关系反查真实渲染文件。不要仅凭组件文件名猜测路由，也不要因为目标组件当前不在页面上就改去其他演示页。

确认：

- 目标路由可由当前 package 启动
- 组件依赖的主题、国际化、状态管理和路由上下文
- 页面是否需要登录、接口数据或端内环境
- 目标 URL 中哪些 query/hash 决定真实页面状态，生成验证 URL 时必须保留

### 2. 在目标页面入口建立首屏 Mock

按优先级选择：

1. 在目标 URL 对应页面入口识别 `componentMock=<case-name>`，命中时渲染首屏 Mock
2. 复用该页面或仓库已有的 mock 数据、Provider、fixture、demo 组件封装，但仍挂载在目标页面入口
3. 如果页面入口无法直接修改，在其最近的共享挂载层增加只对该 pathname 和 case 生效的 dev-only 分支
4. 最后才临时替换目标页面主体；必须保留原实现并易于恢复

不要新增另一个验证路由来替代用户目标页面。确实无法在该页面入口 Mock 时，停止并说明阻碍，不能用其他页面截图冒充成功。

Mock 容器应：

- 让组件进入首屏可视区域，避免被导航栏或浮层遮挡
- 保留组件实际依赖的 Provider
- 使用确定性数据，禁止真实写操作
- 覆盖 loading、empty、error 等状态时，一种状态对应一个 case
- 对异步内容提供稳定的就绪标记，例如 `data-component-validation-ready`
- 不在生产构建中暴露验证入口

Mock 数据必须让组件内部内容达到可用于视觉验收的完整度，而不只是满足类型并成功渲染。读取并遵循 [Mock 数据质量规则](references/mock-data-quality.md)：优先从真实调用点、类型定义、仓库 fixture/story 和页面文案中还原字段语义；标题、图片、金额、状态、标签、列表、时间等可见内容都要合理填充，字段之间保持业务一致。不要使用 `test`、`foo`、重复数字、无意义 Lorem、失效图片或大量空值敷衍内容，除非本 case 明确验证的就是空态或异常态。

截图前同时检查数据和布局：可见字段是否齐全、文本长度是否具有代表性、图片是否成功加载、列表密度是否合理、金额与单位是否匹配、状态与可用操作是否一致，以及是否因劣质 Mock 出现非预期空白、塌陷、截断或占位符。组件能显示但内部观感失真时，继续完善 Mock，不能判定视觉验证通过。

完成每个 Mock 代码改动后，立即按 [Mock 改动清单协议](references/mock-changes-schema.md) 记录到 `<runDir>/mock-changes.json`。每项至少包含仓库相对文件路径、创建或修改类型、记录时行号、稳定 symbol/锚点、改动摘要、改动前后片段和文件 SHA-256。行号只用于帮助导航，锚点和片段用于抵抗后续代码漂移；不得把清单当成可信回滚脚本。

完成代码改动后生成验证 URL：

1. 以目标页面 URL 为基准
2. 保留已有 pathname、非敏感 query 和 hash
3. 追加或更新 `componentMock=<case-name>`
4. 若本地服务 origin 与用户 URL 不同，只替换经过确认的 origin，path/query/hash 保持一致

例如用户给出：

```text
http://127.0.0.1:3000/coupon/list?tab=unused#content
```

本次验证地址应为：

```text
http://127.0.0.1:3000/coupon/list?tab=unused&componentMock=coupon-card#content
```

### 3. 生成浏览器操作 JSON

读取 [浏览器操作协议](references/browser-actions-schema.md)，基于
[示例](assets/browser-actions.example.json)。先创建本次运行目录：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prepare-case \
  --case <case-name>
```

脚本返回 JSON，其中 `runDir` 是本次唯一目录。把改动清单写到 `<runDir>/mock-changes.json`，操作文件写到 `<runDir>/browser-actions.json`，截图写到 `<runDir>/screenshots/`，报告写到 `<runDir>/report.md`。

在开始浏览器验证前校验改动清单：

```bash
python3 <skill-dir>/scripts/validate_mock_changes.py \
  <runDir>/mock-changes.json
```

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

高清 case 设置 `deviceScaleFactor` 和 `requireNativeScale: true`，作为期望设备规格与报告字段；最终高清证据以系统截图的真实 PNG 像素和显示器缩放为准。桌面端默认 DPR `2`，移动端默认 DPR `3`。用户明确不需要高清时可设置 `requireNativeScale: false` 并使用浏览器截图兜底，不得把兜底产物标成高清。

运行前执行：

```bash
python3 skills/component-validation-mock/scripts/validate_browser_actions.py \
  <runDir>/browser-actions.json
```

如果 Skill 安装在其他位置，使用该 Skill 目录下脚本的实际路径。

### 4. 启动并预检页面

使用仓库已有命令启动正确 package 的开发服务。确认：

- URL 返回页面而不是 404、错误页或错误 package
- 验证 URL 与目标页面 URL 的 pathname 一致，且保留原有有效 query/hash
- 验证 URL 只增加 Mock 开关，不得跳转到未获用户同意的其他 demo/story 路由
- 控制台没有由本次 Mock 引入的错误
- 目标组件处于首屏且就绪标记可见
- 截图目录已创建

若端口被占用，先确认占用进程是否就是目标服务，不要直接终止未知进程。

### 5. 执行浏览器动作

默认先使用用户外部 Chrome 浏览器：先按外部浏览器能力检查插件连接，连接成功后使用外部浏览器打开验证 URL、观察 DOM、执行交互。用户明确指定 Browser 时遵从指定；外部 Chrome 不可用时先引导连接或说明阻塞，只有用户同意降级时才改用内置 Browser。最终导航必须发生在 Mock 代码完成并且开发服务重新编译之后。

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

先读取并遵循 [系统高清截图流程](references/system-screenshot.md)。除非用户明确表示“不需要高清”“普通截图即可”，默认选择高清模式并交付高清版：使用 macOS `screencapture` 截取外部 Chrome 所在显示器，再从原始 PNG 无缩放裁出目标页面或组件区域。Chrome 位于副屏时直接用 `-D <display-id>` 捕获该屏，不要先把窗口拉回主屏。禁止截图后插值放大，因为这不会增加文字和边缘细节。

移动端高清截图不要由 Agent 临时打开、关闭或反复切换 DevTools。优先复用用户已经准备好的 Chrome DevTools 设备页面；开始前确认页面处于设备模式、目标 viewport 正确且组件已重新初始化。若没有准备，提醒用户准备一个可长期复用的移动端 Chrome 页面并打开 DevTools 设备工具栏，然后等待用户确认。后续任务继续复用这个页面，避免每次重复打扰用户。

高清模式所需的屏幕录制、辅助功能或自动化权限未开启时，说明具体权限名称和开启位置，等待用户开启后重试；不能静默改走低清路径。只有用户明确不需要高清时，才使用原来的浏览器 `screenshot` 动作兜底，并在报告中标记“普通浏览器截图，非系统高清截图”。

移动端必须确认：

- Chrome DevTools 设备工具栏已由用户预先准备并保持可复用
- viewport 已切换为目标移动端尺寸，未给出时默认 `390x844`
- 页面在设备模式下重新初始化后再操作
- 没有仅改变窗口宽度却遗漏移动端 user agent/touch 的问题
- 系统截图来自 Chrome 实际所在显示器，双显示器场景先定位正确 display

至少截图：

1. 组件初始首屏状态
2. 每个用户指定的关键交互后状态

截图前等待动画和异步状态稳定；优先等待可观察条件，不使用随意的长时间 sleep。

浏览器截图兜底仍按原规则校验：普通视口截图的像素宽高应严格等于 `CSS viewport × DPR`；全页截图宽度应相等，高度不得小于该乘积。例如 `390×844 @3x` 应输出 `1170×2532`：

```bash
python3 <skill-dir>/scripts/validate_screenshot_resolution.py \
  <runDir>/screenshots/initial.png \
  --css-width 390 --css-height 844 --dpr 3
```

系统高清截图使用 `file`、`sips` 或等效只读工具记录原始显示器截图和裁切后 PNG 的真实像素尺寸，并确认裁切过程没有缩放。浏览器截图兜底若输出像素不符，或实际导出为 CSS 像素尺寸的 JPEG，即使页面 `devicePixelRatio` 正确，也不能声明高清截图验证通过。元素内图片还应检查资源分辨率是否覆盖其实际渲染尺寸；资源本身分辨率不足时，在报告中单独提示。

每生成一张截图后执行一次全局保留策略：

```bash
python3 <skill-dir>/scripts/component_validation_state.py prune-screenshots --limit 500
```

按文件修改时间仅保留 `~/.component-validation/cases/` 中最近 500 张 PNG 截图，旧截图由脚本删除。JSON、报告和 URL 映射不计入 500 张限制，也不会随截图一起删除。

### 7. 交付报告

`<runDir>/report.md` 使用以下结构，禁止保存到业务仓库：

```markdown
# <case-name> 组件验证

- 用户目标页面：<用户提供或持久化的 URL>
- 实际验证地址：<追加 Mock 开关后的 URL>
- 设备：<desktop/mobile + viewport>
- 组件：<path + export>
- Mock 入口：<route/query>

## 验证结果

- [通过/失败] 初始首屏展示：<证据>
- [通过/失败] Mock 数据与视觉完整度：<数据来源、字段合理性、图片加载、列表密度和布局观察>
- [通过/失败] <交互名称>：<证据>

## 产物

- Mock 改动清单：<用户目录下的绝对路径>
- 操作 JSON：<用户目录下的绝对路径>
- 截图：<用户目录下的绝对路径>
- 清晰度：请求 DPR / 实际 DPR / CSS viewport / PNG 像素尺寸 / 高清校验结果

## 已知限制

- <无则写“无”>
```

报告只能声明实际观察到的结果。页面未打开、截图未生成或交互未执行时，不得写“通过”。

### 取消 Mock

用户要求取消、清理或恢复 Mock 时，先读取对应 case 的 `mock-changes.json` 辅助定位，但不能直接照单撤销：

1. 确认当前 git 根目录与清单 `repoRoot` 指向同一仓库。
2. 对每个文件读取当前源码，并查看该文件实际的 staged/unstaged diff；清单中的行号仅作导航。
3. 逐项核对 symbol/锚点、`afterSnippet`、文件 SHA-256 和相邻上下文，判断当前代码是否仍是该次 Mock。文件哈希变化不等于 Mock 已失效，可能只是用户在别处继续编辑；应缩小到对应 hunk 比较。
4. 只有证据一致时才生成最小反向补丁。不要使用 `git checkout -- <file>`、`git restore <file>` 或整文件覆盖，因为文件可能混有用户后续改动。
5. 对本次创建的文件，仅在内容仍匹配且没有新增引用或用户修改时删除；否则保留并报告冲突。
6. 无法确认归属时停止该项撤销，列出清单记录与当前源码的差异，请用户决定；不能猜测删除。

撤销后重新读取文件和 diff，确认只移除了已核实的 Mock 代码，再在报告中逐文件标记 `removed`、`skipped-conflict` 或 `already-absent`。

## 失败处理

- 缺组件 props：先从类型、调用点和 story 推断；仍不确定再询问
- 缺少可信业务数据：从类型、真实调用点、fixture/story 和相邻页面文案构造脱敏的代表性数据；无法确认关键字段语义时明确说明，不用随意占位内容冒充通过
- 页面需鉴权：使用现有已登录浏览器会话；不得读取 cookie、密码或会话存储
- 接口不稳定：使用仓库已有 mock 层或确定性本地数据
- 浏览器能力不可用：仍可生成并校验 JSON，但明确标记截图验证未执行
- 系统截图权限未开启：提醒用户在“系统设置 → 隐私与安全性”中开启屏幕录制；需要自动置前或操作 Chrome 时同时提醒开启辅助功能/自动化，用户确认后重试
- 移动端 Chrome 页面未准备：提醒用户创建并保留一个 Chrome DevTools 设备页面，选择目标设备或默认 `390x844`，完成后再继续；不要擅自反复打开调试工具
- 用户明确不需要高清：使用浏览器截图兜底，保留正常视觉验证，但报告不得声称系统级高清或 Retina 原生截图
- 历史 URL 已失效：实际探测路由或向用户确认，验证新 URL 后覆盖当前页面记录
- 用户 URL 页面里原本没有组件：这是正常前提；先在对应页面入口建立 Mock，不能直接截图原页面或换到其他路由
- 目标页面入口无法安全 Mock：报告失败原因并请求方向，不得用独立 demo/story 的截图代替
- 移动端模拟不完整：记录实际 viewport、user agent 和 touch 能力
- 页面错误：保留错误证据，定位为 Mock、页面或环境问题，不用修改业务逻辑掩盖

## 完成门槛

只有同时满足以下条件才算完成：

- 组件在目标页面首屏可见
- URL 映射保存的是用户目标页面 URL，不是追加 Mock 参数后的验证 URL
- 实际验证地址与目标页面 URL 使用同一 pathname，并保留原有有效 query/hash
- Mock 已挂载在目标 URL 对应的页面入口，打开验证 URL 后无需额外交互、滚动或导航即可在首屏看到组件
- Mock 数据覆盖组件主要可见字段，内容语义、字段关系、文本长度、图片和列表密度足以代表真实使用场景
- 不存在由随意占位数据导致的非预期空白、破图、布局塌陷、异常截断或状态/操作矛盾
- JSON 通过校验
- Mock 改动清单通过校验，并覆盖本次所有 Mock 代码改动
- 浏览器实际打开了正确 URL
- 设备模式与 case 一致
- 要求的交互已执行
- 截图文件存在且内容可辨认
- 高清模式使用系统原生截图，记录正确显示器、原始 PNG 尺寸、裁切尺寸且没有插值放大
- 移动端高清模式复用了用户准备的 Chrome DevTools 设备页面，并记录 viewport/设备模式
- 普通截图兜底仅在用户明确不需要高清时启用，并清楚标注非高清；若按 DPR 生成则通过 `validate_screenshot_resolution.py` 校验
- 报告中的每项结论都有截图或页面观察证据
- 报告、改动清单、操作 JSON 和截图均不在业务仓库内
- 截图保留策略已执行，用户目录下截图总数不超过 500
