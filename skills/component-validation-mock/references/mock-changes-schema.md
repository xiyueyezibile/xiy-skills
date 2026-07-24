# Mock 改动清单协议

`mock-changes.json` 保存在本次 `runDir`，用于帮助后续定位和取消 Mock，不保存到业务仓库。

```json
{
  "version": 1,
  "caseName": "coupon-card-mobile",
  "repoRoot": "/workspace/alliance-mobile-mono",
  "entries": [
    {
      "path": "packages/app/src/pages/coupon/index.tsx",
      "operation": "modified",
      "location": {
        "startLine": 42,
        "endLine": 58,
        "symbol": "CouponListPage",
        "anchor": "componentMock === 'coupon-card-mobile'"
      },
      "summary": "在优惠券列表页入口增加 dev-only CouponCard 首屏分支",
      "beforeSnippet": "return <CouponList />;",
      "afterSnippet": "if (componentMock === 'coupon-card-mobile') { ... }",
      "beforeFileSha256": "64位小写十六进制 SHA-256",
      "afterFileSha256": "64位小写十六进制 SHA-256"
    }
  ]
}
```

规则：

- `path` 必须是相对 `repoRoot` 的 POSIX 路径，不得为绝对路径、包含 `..` 或指向 `.git`、`.vscode`
- `operation` 只能是 `modified` 或 `created`
- 行号记录写入清单时的位置，必须为正整数且 `endLine >= startLine`，但后续撤销不能只依赖行号
- `anchor` 应选择只出现在对应 Mock hunk 附近的稳定文本；`symbol` 可为空字符串
- `beforeSnippet`、`afterSnippet` 保存足以辨认 hunk 的最小片段，避免记录无关代码或敏感信息
- `modified` 必须同时提供改动前后文件哈希；`created` 的 `beforeFileSha256` 为 `null`
- 清单必须覆盖本次为 Mock 修改和创建的全部业务仓库文件，一项可描述一个文件内的一个连续 hunk

## 安全撤销语义

清单只是历史快照，可能因用户继续编辑、格式化或重构而过期。取消 Mock 时必须同时核对当前源码、staged/unstaged Git diff、锚点、后置片段、文件哈希和相邻上下文。哈希不一致时缩小到 hunk 比较，不能直接判定整个文件可恢复。

只有对应 hunk 的归属能够确认时才应用最小反向补丁。禁止把清单转换成 `git restore`、`git checkout`、整文件覆盖或无条件删除命令。
