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
{"type": "open", "path": "/demo?componentMock=button-loading"}
```

`path` 可使用站内绝对路径或完整 `http(s)` URL。

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
- 任一动作失败即停止，保留已生成截图并写入报告
- 实际打开成功后，将完整页面 URL 更新到 `~/.component-validation/page-urls.json`
- 每生成一张截图后执行全局裁剪，只保留最近 500 张截图
- 每个交互动作后重新观察页面
- 不允许通过 JSON 执行任意 JavaScript、shell、网络请求或文件读写
- 不允许在 JSON 中存放 token、cookie、密码等敏感信息
