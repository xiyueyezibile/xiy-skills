# 浏览器操作 JSON 协议

## 顶层结构

```json
{
  "version": 1,
  "caseName": "button-loading-mobile",
  "baseUrl": "http://127.0.0.1:3000",
  "device": {
    "kind": "mobile",
    "viewport": {
      "width": 390,
      "height": 844
    },
    "deviceScaleFactor": 3,
    "requireNativeScale": true,
    "isTouch": true,
    "userAgent": "optional"
  },
  "actions": []
}
```

规则：

- `version` 当前固定为 `1`
- `caseName` 仅使用字母、数字、点、下划线和短横线
- `baseUrl` 仅允许 `http://` 或 `https://`
- `device.kind` 为 `desktop` 或 `mobile`
- viewport 宽高为正整数
- `deviceScaleFactor` 必填且范围为 `2` 到 `4`；桌面端默认 `2`，移动端默认 `3`
- `requireNativeScale` 必须为 `true`，表示执行器必须验证浏览器真实 DPR，而不是只接受配置值
- `actions` 至少包含一个 `open` 和一个 `screenshot`
- 文件中的截图路径必须是相对路径，不得包含 `..`
- 操作 JSON 位于 `~/.component-validation/cases/<case-name>/<run-id>/`
- 截图路径相对于本次 `runDir` 解析，不得写入业务仓库

## 定位器

需要定位元素的动作使用一个 `locator`：

```json
{"by": "testId", "value": "submit-button"}
```

`by` 允许：

- `testId`
- `role`
- `label`
- `text`
- `css`

优先顺序为 `testId`、`role`/`label`、`text`、`css`。`role` 可额外提供 `name`。

```json
{"by": "role", "value": "button", "name": "提交"}
```

## 动作定义

### open

```json
{"type": "open", "path": "/coupon/list?tab=unused&componentMock=coupon-card#content"}
```

`path` 可使用站内绝对路径或完整 `http(s)` URL。

`open.path` 必须来自用户目标页面 URL，并只追加或更新本次 `componentMock` 参数。原目标 URL 的 pathname、有效 query 和 hash 必须保留；不得擅自换成独立 demo/story 路由。

### waitFor

```json
{
  "type": "waitFor",
  "locator": {"by": "testId", "value": "component-ready"},
  "state": "visible",
  "timeoutMs": 10000
}
```

`state` 为 `visible`、`hidden`、`attached` 之一，`timeoutMs` 最大 30000。

### click

```json
{
  "type": "click",
  "locator": {"by": "role", "value": "button", "name": "提交"}
}
```

### fill

```json
{
  "type": "fill",
  "locator": {"by": "label", "value": "手机号"},
  "value": "13800000000"
}
```

### press

```json
{
  "type": "press",
  "locator": {"by": "label", "value": "搜索"},
  "key": "Enter"
}
```

### select

```json
{
  "type": "select",
  "locator": {"by": "label", "value": "城市"},
  "value": "shanghai"
}
```

### scroll

窗口滚动：

```json
{"type": "scroll", "x": 0, "y": 500}
```

容器滚动：

```json
{
  "type": "scroll",
  "locator": {"by": "testId", "value": "list"},
  "x": 0,
  "y": 500
}
```

### screenshot

视口截图：

```json
{
  "type": "screenshot",
  "path": "screenshots/initial.png",
  "fullPage": false
}
```

元素截图：

```json
{
  "type": "screenshot",
  "path": "screenshots/result.png",
  "locator": {"by": "testId", "value": "result-card"}
}
```

## 执行语义

- 动作严格按数组顺序执行
- 截图前读取 `window.devicePixelRatio`，必须与 `deviceScaleFactor` 一致；不一致时重新建立支持 DPR 模拟的浏览器上下文并重新打开页面
- 每个 case 的初始视口截图必须执行 PNG 像素尺寸校验：非全页截图应等于 `viewport × deviceScaleFactor`，全页截图宽度应相等且高度不得小于该值
- 禁止通过截图后插值放大冒充高清截图；若环境无法提供原生高 DPR，必须标记降级且不能声明高清验证通过
- 任一动作失败即停止，保留已生成截图并写入报告
- 实际打开成功后，将未包含本次 `componentMock` 参数的用户目标页面 URL 更新到 `~/.component-validation/page-urls.json`
- 每生成一张截图后执行全局裁剪，只保留最近 500 张截图
- 每个交互动作后重新观察页面
- 不允许通过 JSON 执行任意 JavaScript、shell、网络请求或文件读写
- 不允许在 JSON 中存放 token、cookie、密码等敏感信息
