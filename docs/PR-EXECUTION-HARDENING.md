# PR 描述：执行链与文件系统边界安全加固

## 背景

这一轮安全加固的目标，是把 OpenHarness / Velaris 中“模型可触发、又会落到本地执行或本地写删”的关键链路，从零散防御收敛成统一的框架级防线，减少以下两类风险：

1. 危险命令在不同执行链上出现“有的校验、有的绕过”的不一致。
2. 文件系统写入/删除入口对路径边界约束不足，导致敏感目录或托管目录外内容被误操作。

## 本次改动

### 1) 统一执行安全辅助落到剩余关键链路

- 新增并复用 `src/openharness/security/execution.py`
- `bridge spawn`、后台 `task`、`remote_trigger`、command hook 统一接入：
  - 危险命令审批
  - `cwd` 白名单校验
  - 子进程输出脱敏
- React 前端拉起 backend、本地 agent 背景任务不再把 API Key 放进 argv

### 2) 补齐剩余执行入口的安全一致性

- `src/openharness/tools/bash_tool.py`
  - 改为直接复用统一执行安全辅助
  - 避免继续维护一套分叉的审批/脱敏逻辑
- `src/openharness/tools/enter_worktree_tool.py`
- `src/openharness/tools/exit_worktree_tool.py`
  - 新增受保护路径拦截
  - 输出统一走脱敏渲染

### 3) 收紧非 subprocess 文件系统删除边界

- `src/openharness/swarm/team_lifecycle.py`
  - `git worktree remove --force` 失败后的 `rmtree` 兜底，改为只允许清理框架托管的 `worktrees/` 目录
  - 避免被伪造 `worktree_path` 扩大为任意路径递归删除
- `src/openharness/plugins/installer.py`
  - `uninstall_plugin(name)` 现在只接受单段插件目录名
  - 拒绝绝对路径、`..` 和路径分隔符，防止 `/plugin uninstall ../../foo` 类路径逃逸删除

## 设计原则

- 安全策略尽量放在框架层，而不是散落在每个调用点
- 用户可控路径默认做“目录边界校验”，不是依赖调用方自觉
- 输出先脱敏再回到模型 / UI，减少密钥二次扩散
- 对“失败兜底”分支单独做边界约束，因为这类路径最容易被忽视

## 兼容性与风险

- 兼容性：正常命令执行、正常 worktree 流程、正常插件安装/卸载不受影响
- 行为变化：
  - 危险命令在更多执行链路上会被审批/阻断
  - worktree 不允许落到受保护路径
  - 非法插件名卸载会直接返回失败，而不是尝试删除路径

## 验证

- 回归测试：
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -m pytest tests/test_tools/test_core_tools.py tests/test_swarm/test_team_lifecycle.py tests/test_plugins/test_lifecycle_flow.py tests/test_commands/test_command_flows.py -q`
- 类型检查：
  - `UV_CACHE_DIR=/tmp/uv-cache MYPYPATH=src uv run mypy -m openharness.tools.bash_tool -m openharness.tools.enter_worktree_tool -m openharness.tools.exit_worktree_tool -m openharness.swarm.team_lifecycle -m openharness.plugins.installer`

## 后续建议

- 把“路径边界守卫”进一步抽成文件系统级公共辅助，覆盖更多写删入口
- 对 `commands/registry.py` 中的托管目录清理动作补充更显式的“托管目录断言”
- 为未来新增的删除型工具建立统一 checklist：受保护路径、托管根目录、路径归一化、失败兜底边界
