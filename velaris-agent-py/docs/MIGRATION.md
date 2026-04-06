# Velaris Python Runtime Migration

## 当前状态

当前目录 `velaris-agent-py/` 已将本地 OpenHarness 基线迁入当前仓库，并完成第一轮可运行迁移：

- 包名改为 `velaris-agent-py`
- 新增 CLI 入口：`velaris` / `vl`
- 保留兼容入口：`openharness` / `oh`
- 新增 Python 模块入口：`python -m velaris_agent`
- 配置目录默认迁移到 `~/.velaris-agent`
- 保留 `~/.openharness` 和 `OPENHARNESS_*` 兼容读取

## 本轮迁移范围

1. 元数据与入口
- `pyproject.toml`
- `src/velaris_agent/`

2. 配置与路径兼容
- `src/openharness/config/paths.py`
- `src/openharness/config/settings.py`

3. 子进程与前端启动命令
- `src/openharness/tasks/manager.py`
- `src/openharness/ui/react_launcher.py`
- `frontend/terminal/src/index.tsx`
- `src/openharness/swarm/spawn_utils.py`

4. 本地状态目录
- teams/worktrees/plugins 改为走 Velaris 路径解析

5. 业务能力与运行时治理
- 新增 `src/openharness/biz/`：统一商旅、TokenCost、OpenClaw 三类场景能力。
- 新增 `src/openharness/velaris/`：落地 Python 版路由、签权、任务账本与 Outcome 存储。
- 新增 `biz_execute` 工具：把规划、路由、授权、执行、回写串成一条闭环。
- 新增 `travel_recommend`、`tokencost_analyze`、`openclaw_dispatch`：提供可直接调用的场景化工具入口。
- 新增 `src/velaris_agent/` 下的原生命名空间实现，`openharness.*` 保留兼容导出。
- 三类领域工具新增 `file/http` 数据源 adapter，支持从外部结构化数据直接装配业务负载。

## 下一步建议

1. 第二轮做深度场景化
- 在 `src/openharness/tools/` 和 `src/openharness/skills/` 下继续细化 travel、tokencost、openclaw 的真实工具链。

2. 第三轮做深度改名
- 逐步把内部 import 从 `openharness.*` 迁到 `velaris_agent.*`。
- 这一步需要配套测试一起改，不能只做机械替换。

3. 第四轮做外部 runtime 打通
- 把当前已落地的 Python 路由治理闭环继续接到真实外部 runtime 和观测指标。
