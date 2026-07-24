# 用户目录状态协议

固定根目录为 `~/.component-validation`，不允许改成业务仓库内的同名目录。

## URL 映射

`page-urls.json` 由状态脚本维护：

```json
{
  "version": 1,
  "entries": {
    "alliance-mobile-mono::add-product": {
      "repo": "alliance-mobile-mono",
      "page": "add-product",
      "url": "http://127.0.0.1:5568/add-product?mode=video",
      "source": "user",
      "updatedAt": "2026-07-24T10:00:00+00:00"
    }
  }
}
```

- `repo` 使用 git 根目录名或用户明确给出的稳定仓库标识
- `page` 使用路由名、页面名或稳定业务页面标识
- 同一仓库和页面只保留最近一次确认 URL
- `url` 保存用户目标页面 URL；浏览器实际验证也应打开该 URL
- 除非本地服务 origin 已经被确认不同，否则浏览器实际验证 URL 必须与该地址完全一致；允许替换 origin 时，pathname、query 和 hash 仍必须保持不变，不得追加 Mock 参数
- `source` 记录 URL 来源，不保存用户原文
- 不保存凭证或敏感 query 参数

## 运行目录

`prepare-case` 创建：

```text
cases/<case-name>/<UTC timestamp>/
```

同一秒重复运行时，脚本追加数字后缀，避免覆盖历史截图。

每个运行目录还必须包含 `mock-changes.json`。它记录本次 Mock 修改过或创建的仓库文件、记录时位置、锚点、前后片段与文件哈希，供后续取消 Mock 时辅助定位。该文件是审计线索而不是回滚事实源；撤销前必须与当前源码和 Git diff 复核。

## 截图保留

`prune-screenshots` 递归扫描 `cases/` 下的 `.png` 文件，按修改时间从新到旧排序，只保留最近 `500` 张。数量恰好为 500 时不删除。
