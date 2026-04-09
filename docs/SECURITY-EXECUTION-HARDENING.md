# 执行链与文件系统安全设计说明

## 1. 问题定义

OpenHarness / Velaris 的风险不只来自 `bash` 工具本身，还来自所有“最终会触发本地执行、本地写入或本地删除”的辅助链路，例如：

- `bridge spawn`
- 后台 `task`
- `remote_trigger`
- command hook
- worktree 创建 / 清理
- plugin 安装 / 卸载

如果这些链路各自维护一套校验逻辑，就会出现“主链安全、侧链绕过”的问题。

## 2. 本轮设计目标

### 2.1 执行安全统一化

把下面三件事沉到公共层，避免每个调用点重复实现：

- 危险命令识别与审批
- 工作目录 `cwd` 白名单校验
- 子进程输出脱敏与截断

对应实现位于：

- `src/openharness/security/command_guard.py`
- `src/openharness/security/execution.py`
- `src/openharness/security/redaction.py`

### 2.2 文件系统删除边界显式化

对于 `rmtree`、`unlink`、覆盖写入这类操作，不再只看“当前功能看起来是内部使用”，而是增加两个问题：

1. 路径是否来自用户输入、配置或可伪造的持久化状态？
2. 失败兜底分支是否会把删除范围扩大？

## 3. 覆盖矩阵

| 链路 | 风险 | 现状 |
|---|---|---|
| `bash_tool` | 任意命令执行 | 已接入统一审批 / `cwd` 校验 / 输出脱敏 |
| `bridge/session_runner` | 侧链执行绕过 | 已接入统一安全辅助 |
| `tasks/manager` | 后台 shell / agent 执行 | 已接入统一安全辅助；API Key 改走环境变量 |
| `remote_trigger_tool` | cron job 旁路 | 已接入统一安全辅助 |
| `hooks/executor` | hook 成为旁路入口 | 已接入统一安全辅助 |
| `enter/exit_worktree` | worktree 落到敏感目录 | 已拦截受保护路径，并统一输出脱敏 |
| `team_lifecycle` worktree cleanup | 失败兜底递归删除 | 已限制为仅允许清理托管 `worktrees/` 根目录下路径 |
| `plugins/installer.uninstall_plugin` | 路径逃逸删除 | 已限制为单段插件目录名，拒绝 `..` / 绝对路径 / 分隔符 |

## 4. 非 subprocess 文件系统专项扫描结果

这轮重点排查了以下操作：

- `shutil.rmtree`
- `Path.unlink` / `os.unlink`
- `write_text` / 覆盖写入
- `os.rename` / `replace`

### 4.1 已确认需要修复的点

#### `src/openharness/plugins/installer.py`

- 原问题：`uninstall_plugin(name)` 直接执行 `get_user_plugins_dir() / name`
- 风险：如果 `name` 带有 `../`，理论上可能越出插件根目录并删除外部路径
- 处理：现在只接受单段目录名，并在 `resolve()` 后再次校验仍位于用户插件根目录下

### 4.2 已确认边界可接受的点

#### `src/openharness/commands/registry.py`

- `/session clear` 删除的是 `get_project_session_dir(cwd)` 生成的托管目录
- `/issue clear`、`/pr_comments clear` 删除的是项目内固定上下文文件
- 这些入口虽然有删除动作，但路径不是任意用户输入路径，而是框架派生的托管路径

#### `src/openharness/swarm/mailbox.py`

- 写入文件名来自系统生成的消息 ID / 时间戳
- 落盘目录来自 team/agent 托管 mailbox 路径
- 使用临时文件 + `rename` 做原子写入，不存在跨目录任意写

#### `src/openharness/tools/skill_manage_tool.py`

- 支持文件路径只允许写入 `references/templates/scripts/assets`
- 且会在 `resolve()` 后再次校验不能逃逸技能目录
- 删除技能时也只允许删除用户技能目录下的内容

## 5. 当前残余风险

本轮加固后，剩余风险主要不在“明显可绕过的侧链”，而在“未来新增功能可能重复造轮子”：

1. 仍有少量托管目录清理逻辑是各模块自行维护，尚未全部抽成统一文件系统守卫。
2. `commands/registry.py` 这类命令层写删操作虽然当前落在托管路径，但边界约束更多依赖路径工厂函数，而不是统一 guard。
3. 后续若新增“按路径删除目录/文件”的工具，如果不复用公共边界校验，容易重新引入路径逃逸问题。

## 6. 建议的下一步

### 6.1 短期

- 把“删除/覆盖写入目标必须位于托管根目录或显式白名单目录”抽成公共辅助
- 给删除型入口补一个统一测试模式：
  - 受保护路径
  - `..` 路径逃逸
  - 绝对路径
  - 托管目录内正常路径

### 6.2 中期

- 建立 `filesystem_guard.py`，与 `execution.py` 对称：
  - `validate_delete_target`
  - `validate_write_target`
  - `validate_managed_dir_target`

### 6.3 长期

- 把安全设计从“执行链守卫”扩展到“执行链 + 文件系统链 + 凭据链”三层矩阵
- 对新增工具建立安全接入 checklist，避免 review 时靠人工记忆兜底
