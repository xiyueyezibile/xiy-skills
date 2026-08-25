---
name: "xiy-llm-wiki"
description: "维护独立 Git 仓库形式的个人 LLM Wiki，编译和沉淀可复用知识并标识当前工作。当前 Git 仓库在 ~/.xiy/config.json 启用 session_watch 时，自动读取 Wiki；action=extract 会在会话结束时提炼有依据的可复用信息，写入 Wiki 并自动提交 push。"
---

# Xiy LLM Wiki

管理一个独立的个人 LLM Wiki Git 仓库。Wiki 仓库根目录就是 Wiki 本身，不再在业务仓库中创建 `llm-wiki/` 子目录。`~/.xiy/` 只保存配置、仓库映射和本地路径，不保存 Wiki 内容。

LLM Wiki 的核心不是原文归档，而是把用户提供的资料、对话结论和工作经验编译成结构化、可交叉链接、可持续更新的 Markdown 知识。它采用“原始资料 -> Wiki 页面 -> 索引与日志”的累积式模型：知识在写入时被整理，后续查询直接复用已有页面。

参考定义：

- [Karpathy LLM Wiki pattern](https://github.com/MinhMPA/llm-wiki/blob/master/llm-wiki.md)
- [LLM Wiki implementation](https://github.com/nashsu/llm_wiki)

## 触发边界

普通编码、分析、聊天和其他 Skill 执行期间，不得自动写入或同步；唯一例外是 `~/.xiy/config.json` 中已启用 `session_watch.action=extract` 的当前 Git 仓库。它会在每次会话开始时自动进行只读加载，并在会话结束时由 Codex 回看本轮对话，只记录有依据、可复用的新知识，然后自动提交 push。

- 用户明确要求记录、沉淀、学习或更新知识时，调用 `record`。
- 用户明确要求识别当前工作时，调用 `status`；此命令不写 Wiki 内容，但会先拉取远端最新改动。
- 用户明确要求配置或关联 Wiki 仓库时，调用 `init` 或 `link`。
- 用户明确要求同步时，调用 `sync`；`record` 成功后也会自动执行同样的同步。
- 用户明确要求监听指定仓库的会话时，先配置 `watch --action extract`，再安装 Codex hooks。

`extract` 只会记录新出现的、可验证的结论、决策、规则、踩坑或资料摘要；不得记录普通进度、一次性实现细节、未经确认的推测或敏感信息。没有新内容时不写入。

## 配置与仓库关联

配置文件固定为 `~/.xiy/config.json`。它至少包含：

```json
{
  "llm_wiki": {
    "repo": "/path/to/llm-wiki",
    "remote": "origin"
  },
  "repositories": {
    "/path/to/work-repo": {
      "name": "work-repo"
    }
  }
}
```

1. `llm_wiki.repo` 指向独立 Wiki Git 仓库；仓库根目录就是完整 Wiki。
2. `repositories` 保存业务仓库到 Wiki 的关联，路径必须是 Git 根目录。
3. 如果 Wiki 目录不存在，`init --wiki-repo <path-or-url>` 初始化或克隆它。
4. 如果当前目录不是 Git 仓库，`status` 仍可识别 Wiki 仓库；`record` 不能生成当前工作关联，必须说明原因。
5. 自动 push 使用 Git 已配置的 remote、凭据和 SSH/credential helper；Skill 不读取或保存 token、cookie、密码或私钥。

### 使用前同步门禁

除首次创建空 Wiki 外，所有命令在读取或修改 Wiki 前都必须执行：

```bash
git pull --ff-only <remote> <current-branch>
```

先检查 Wiki 工作树是否干净。存在本地未提交改动、无当前分支、远端拉取失败或无法快进时，立即停止，不覆盖本地内容，也不继续记录或提交。`record` 拉取一次后再写入，并复用本次同步结果完成 commit/push。

## 当前工作识别

每次手动调用 `status`、`record` 或 `sync` 时，都读取当前业务仓库的 Git 事实：

- 当前分支或提交；
- 工作区是否有未提交改动；
- 改动文件列表；
- 最近一次提交标题。

把这些事实整理为简短的“当前工作”描述，并写入 Wiki 的 `wiki/current-work.md`。不能把推测当成事实；没有足够证据时使用“正在处理未命名改动”。

## 命令

从本 Skill 目录执行脚本：

```bash
python3 scripts/llm_wiki.py init --wiki-repo /path/to/llm-wiki
python3 scripts/llm_wiki.py link
python3 scripts/llm_wiki.py status
python3 scripts/llm_wiki.py record --category decision --note "这里写要沉淀的内容"
python3 scripts/llm_wiki.py sync
python3 scripts/llm_wiki.py watch --action extract
python3 scripts/llm_wiki.py hooks install
```

### `init`

创建 `~/.xiy/config.json`，并初始化 Wiki 仓库以下结构：

```text
<wiki-repo>/
├── WIKI_SCHEMA.md
├── raw/
├── wiki/
│   ├── index.md
│   └── current-work.md
└── log.md
```

已有 Wiki 文件不覆盖。初始化建立结构和配置后会自动提交并在有远端时 push 骨架；后续 `record` 或 `sync` 的每次 Wiki 更新都会自动提交 push。

### `link`

把当前业务 Git 仓库登记到 `~/.xiy/config.json`，用于识别“我现在在做什么”。不写入 Wiki，不触发 push。

### `status`

先拉取 Wiki 远端最新提交，再输出当前业务仓库、Wiki 仓库和当前工作摘要；不会写入 Wiki 内容。

### `record`

只有用户明确要求记录时才能执行。要求提供非空 `--note`，可选 `--category`：

- `context`：仓库或业务上下文
- `decision`：已确认决策
- `rule`：可复用规则
- `pitfall`：踩坑或纠错
- `source`：外部资料摘要

记录时更新 `wiki/<category>/YYYY-MM-DD.md`、`wiki/index.md`、`wiki/current-work.md` 和 `log.md`。必要时把原始资料保存到 `raw/`，但不保存 token、cookie、密钥、隐私或大段受版权保护的原文。

写入完成后自动执行：

```text
git add -A
git commit -m "wiki: ..."
git push <remote> HEAD:<current-branch>
```

没有文件变化时不创建空提交；commit 或 push 任一步失败都必须报告失败原因，不能宣称同步完成。

### `sync`

先拉取 Wiki 远端最新提交，再刷新当前工作标识，提交 Wiki 仓库已有变化并 push。它是显式同步入口；`record` 成功后会复用已完成的拉取并自动调用它。

## Wiki 维护原则

- Wiki 页面是编译后的知识，不是聊天记录转储。
- 每条知识尽量包含结论、依据、适用条件、反例或不确定性。
- 页面之间使用相对 Markdown 链接交叉引用。
- `wiki/index.md` 是全局目录，`log.md` 是 ingest、query、maintenance 和 sync 的时间日志。
- `WIKI_SCHEMA.md` 是本 Wiki 的维护协议，随 Wiki 一起演进。
- 原始资料只读，Wiki 页面可由 LLM 更新；不要删除已有结论来掩盖冲突，应记录冲突与来源。

## 会话监听与 Codex hooks

会话监听是显式配置能力，不会因安装 Skill 自动开启。它通过 Codex 或 Trae 的 `UserPromptSubmit`、`Stop` 等命令型 hooks 调用 `scripts/xiy_llm_wiki_hook.py`；hook 根据事件中的 `cwd` 找到 Git 根目录，只处理该仓库在 `~/.xiy/config.json` 中启用的 `session_watch` 配置。对于 Codex 的 `UserPromptSubmit`，hook 按其 JSON 协议在 `additionalContext` 注入当前工作和只读加载指令，因此本轮模型能实际获得 Wiki 上下文，而不是仅在终端打印状态。

先在目标仓库执行：

```bash
python3 /path/to/xiy-llm-wiki/scripts/llm_wiki.py watch \
  --action extract \
  --events UserPromptSubmit Stop
python3 /path/to/xiy-llm-wiki/scripts/llm_wiki.py hooks install
python3 /path/to/xiy-llm-wiki/scripts/llm_wiki.py hooks install --path ~/.trae/hooks.json
python3 /path/to/xiy-llm-wiki/scripts/llm_wiki.py hooks install --path ~/.trae-cn/hooks.json
```

安装 `~/.codex/hooks.json` 后必须重启 Codex，或先启动一次普通交互式 `codex`，让 Codex 重新加载配置并登记新增 hook 的信任哈希；已打开的桌面任务不会热加载新 hook。然后在目标仓库中新建任务进行验证。若 Codex 显示 hook 未受信任，只审核并授权指向 `xiy_llm_wiki_hook.py` 的 `UserPromptSubmit` 与 `Stop` 项，不要使用永久绕过 hook 信任的启动参数。

验证成功时，任务界面会显示 `Xiy LLM Wiki 监听已命中当前仓库`；会话开始阶段能看到读取 `SKILL.md`、`WIKI_SCHEMA.md`、`wiki/current-work.md` 和 `wiki/index.md`，结束阶段能看到 `Xiy LLM Wiki 会话收尾`。

配置会写成：

```json
{
  "repositories": {
    "/path/to/work-repo": {
      "name": "work-repo",
      "session_watch": {
        "enabled": true,
        "action": "extract",
        "events": ["UserPromptSubmit", "Stop"]
      }
    }
  }
}
```

`action=extract` 是默认值：Codex 的 `Stop` hook 通过 `decision=block` 和 `reason` 请求一次有明确提示的续跑，回看本轮对话并只记录有依据、可复用的新知识；续跑时 `stop_hook_active=true`，hook 不会再次阻止结束。`record` 会自动 pull、commit、push。`action=status` 只拉取 Wiki 并输出状态，不写入；`action=sync` 会在匹配事件发生时执行 Wiki 同步并可能 commit/push。停用监听：

```bash
python3 /path/to/xiy-llm-wiki/scripts/llm_wiki.py watch --disable
```

hook 是按仓库路径匹配的，不会监听未配置的仓库；事件缺少有效 Git 工作目录、配置不存在或 Wiki 不可用时会静默退出，不阻塞会话。

## 外部机器人读取协议

给外部机器人读取时，提供 [references/external-agent-guide.md](references/external-agent-guide.md)。该文档规定了读取顺序、当前工作识别、证据引用、冲突处理、时间有效性和只读边界。外部机器人默认只能拉取和读取 Wiki，不能自动写入、提交或推送。

## 交付要求

执行后说明：

- 识别到的业务仓库、Wiki 仓库和当前工作；
- 是否实际写入 Wiki；
- 自动 commit 的提交标题；
- push 是否成功；失败时给出具体命令和原因。
