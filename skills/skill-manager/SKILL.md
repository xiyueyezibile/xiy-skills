---
name: skill-manager
description: 管理和推荐skills的skill，当用户询问该用什么skill时，列出可用的skills、推荐场景和推荐理由。使用这个skill来帮助用户找到最适合他们任务的skill。
---

# Skill Manager

帮助用户发现、了解和选择合适的skill来完成任务。

## When to use

当用户：
- 询问"该用什么skill"、"有什么skill"、"推荐skill"等类似问题
- 描述一个任务并想知道用什么skill来完成
- 想要了解当前可用的skills列表
- 需要选择最合适的skill来解决问题

## Instructions

1. 首先查看当前项目中可用的skills，遍历 `skills/` 目录
2. 读取每个skill的 `SKILL.md` 文件，获取：
   - skill名称（name）
   - skill描述（description）
   - 功能说明
   - 使用场景
3. 根据用户的问题或任务描述，分析并推荐合适的skill
4. 为每个推荐的skill提供：
   - skill名称
   - 简短描述
   - 推荐理由（为什么这个skill适合当前任务）
   - 使用场景
   - 安装命令（如果需要）
5. 如果没有明确的任务描述，列出所有可用的skills供用户选择
6. 询问用户是否需要更多关于某个skill的详细信息

## 输出格式

```
## 📋 可用的Skills

### 1. [Skill名称]
- **描述**: [skill的简短描述]
- **推荐场景**: [适合使用的场景]
- **推荐理由**: [为什么推荐这个skill]
- **安装命令**: `npx skills add [path] -g -y`

### 2. [Skill名称]
...

## 💡 推荐

根据你的需求，我推荐使用：
- **[Skill名称]**: [推荐理由]

需要了解更多关于某个skill的详细信息吗？
```

## 示例输出

```
## 📋 可用的Skills

### 1. commit-message-generator
- **描述**: 自动分析代码改动并生成符合规范的commit信息
- **推荐场景**: 需要提交代码、生成commit信息、遵循Conventional Commits规范
- **推荐理由**: 可以自动分析git diff，智能识别改动类型，生成一条简洁的commit信息
- **安装命令**: `npx skills add /Users/bytedance/Desktop/my/xiy-skills/skills/commit-message-generator -g -y`

### 2. find-skills
- **描述**: 帮助用户发现和安装agent skills
- **推荐场景**: 搜索新的skill、发现社区技能、一键安装skill
- **推荐理由**: 可以通过一句话描述需求，AI自动搜索最匹配的技能，一键安装立即可用
- **安装命令**: `npx skills add vercel-labs/skills@find-skills -g -y`

## 💡 推荐

根据你的需求，我推荐使用：
- **commit-message-generator**: 因为你提到需要提交代码，这个skill可以帮你自动生成规范的commit信息

需要了解更多关于某个skill的详细信息吗？
```
