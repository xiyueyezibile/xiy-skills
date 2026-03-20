---
name: commit-message-generator
description: 自动分析git代码改动并生成符合Conventional Commits规范的commit信息。当用户需要提交代码、生成commit信息、分析git diff、遵循commit规范时，务必使用这个skill！
---

# Commit Message Generator

自动分析git工作区的代码改动，智能识别变更类型和范围，生成符合Conventional Commits规范的高质量commit信息。

## When to use

当用户：
- 说"帮我生成commit信息"、"提交代码"、"看看改了什么"
- 需要分析当前git工作区的代码改动
- 想要自动生成符合规范的commit信息
- 询问代码变更的范围和类型
- 需要遵循Conventional Commits规范提交代码
- 已经完成代码修改，准备提交
- 看到git status或git diff的输出，想要生成commit信息

## Instructions

1. 首先检查当前目录是否是git仓库，使用 `git status` 命令
2. 获取代码改动信息，优先使用 `git diff --staged` (如果有暂存的改动)，否则使用 `git diff`
3. 如果没有暂存的改动，询问用户是否需要先 `git add` 某些文件
4. 详细分析代码改动的内容，识别：
   - 改动类型（feat, fix, docs, style, refactor, test, chore等）
   - 改动的范围（哪个模块、文件、功能、组件）
   - 改动的详细描述（具体做了什么）
5. 当有多种类型的改动时，按优先级规则确定主type
6. 根据Conventional Commits规范生成一条综合的commit信息
7. 向用户展示：
   - 分析到的代码改动列表
   - 生成的commit信息
   - 建议使用的commit命令
8. 询问用户是否需要修改commit信息或直接使用
9. 如果用户同意，可以执行 `git commit -m "..."` 来提交

## Conventional Commits 规范

### 基本格式

```
<type>(<scope>): <subject>
```

### Type类型说明

| Type | 说明 | 使用场景 |
|------|------|----------|
| feat | 新功能 | 添加新特性、新功能、新组件 |
| fix | 修复bug | 修复问题、解决bug、修复错误 |
| docs | 文档更新 | 修改README、文档、注释 |
| style | 代码格式 | 调整格式、空格、缩进、分号等（不影响代码运行） |
| refactor | 重构 | 代码重构、优化结构、不改变功能 |
| perf | 性能优化 | 提升性能、优化速度、减少资源消耗 |
| test | 测试相关 | 添加测试、修改测试、测试用例 |
| chore | 构建/工具 | 构建脚本、依赖更新、工具配置 |

### Scope（可选）

scope用于指定改动的范围，例如：
- `components` - 组件相关
- `utils` - 工具函数
- `api` - API接口
- `docs` - 文档
- `tests` - 测试
- 或具体的模块名、文件名

### Subject（主题）

- 使用祈使句，现在时态
- 首字母小写
- 结尾不加句号
- 中文或英文都可以，保持一致

## 优先级规则

当有多种类型的改动时，按以下优先级确定主type（优先级从高到低）：

1. **feat**（新功能）- 最重要，有新功能就用feat
2. **fix**（修复bug）- 其次重要，修复问题
3. **refactor**（重构）- 重构代码
4. **perf**（性能优化）- 性能提升
5. **docs**（文档）- 文档更新
6. **style**（格式）- 代码格式
7. **test**（测试）- 测试相关
8. **chore**（构建/工具）- 最后，构建工具

## 示例输出

### 示例1：多种类型改动

```
📊 分析到以下代码改动：

✅ 新功能 - 修改了 src/components/Button.tsx，添加了loading状态和禁用状态
✅ Bug修复 - 更新了 src/utils/api.ts，修复了请求超时问题和错误处理
✅ 文档 - 添加了 README.md 的使用说明和API文档
✅ 格式 - 调整了 src/styles/main.css 的缩进和空格

🎯 生成的commit信息：
feat: 添加Button组件loading状态、修复API请求超时、更新文档

💡 建议使用的commit命令：
git commit -m "feat: 添加Button组件loading状态、修复API请求超时、更新文档"

需要修改commit信息吗？或者直接使用这个提交？
```

### 示例2：只有Bug修复

```
📊 分析到以下代码改动：

✅ Bug修复 - 修复了 src/components/LoginForm.tsx 中的表单验证问题
✅ Bug修复 - 修正了 src/utils/validator.ts 中的邮箱验证逻辑

🎯 生成的commit信息：
fix: 修复LoginForm表单验证和邮箱验证逻辑

💡 建议使用的commit命令：
git commit -m "fix: 修复LoginForm表单验证和邮箱验证逻辑"
```

### 示例3：只有文档更新

```
📊 分析到以下代码改动：

✅ 文档 - 更新了 README.md，添加了安装说明
✅ 文档 - 修改了 docs/API.md 中的接口文档

🎯 生成的commit信息：
docs: 更新README安装说明和API文档

💡 建议使用的commit命令：
git commit -m "docs: 更新README安装说明和API文档"
```

### 示例4：带scope的commit

```
📊 分析到以下代码改动：

✅ 新功能 - 在 src/components/ 目录下添加了 Card 组件
✅ 新功能 - 为 Card 组件添加了测试用例

🎯 生成的commit信息：
feat(components): 添加Card组件及测试用例

💡 建议使用的commit命令：
git commit -m "feat(components): 添加Card组件及测试用例"
```

## 分析技巧

### 如何识别改动类型

- **feat**: 新增函数、组件、功能、API端点
- **fix**: 修改条件判断、错误处理、修复逻辑错误
- **docs**: 只修改.md文件、注释、文档字符串
- **style**: 只修改空格、缩进、换行、分号、引号
- **refactor**: 重命名变量/函数、提取公共代码、改变结构但不改变功能
- **perf**: 优化算法、减少循环、缓存结果
- **test**: 新增或修改.test.js/.spec.js文件
- **chore**: 修改package.json、构建脚本、配置文件

### 如何确定scope

- 看改动主要集中在哪个目录
- 看改动的文件属于哪个模块
- 如果改动分散，scope可以省略
- 常用scope: components, utils, api, docs, tests, styles, config

## 常见问题

**Q: 如果有feat和fix混合，用什么type？**
A: 用feat，因为feat优先级更高

**Q: 只有style改动，应该用什么？**
A: 用style，标明是代码格式调整

**Q: 改动很多文件，怎么描述？**
A: 概括主要改动，不要列每个文件，突出重点

**Q: 中英文commit信息都可以吗？**
A: 都可以，保持项目一致性即可
