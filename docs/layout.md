# 目录与权限

| 路径 | 用途 | 所有者 |
|---|---|---|
| `/opt/zeromatrix/offline` | ISO 自带的软件包、索引与构建清单 | root，只供配置与修复 |
| `/opt/zeromatrix/toolchains` | 未来单独管理的工具链；当前优先系统工具链 | root |
| `/etc/zeromatrix` | 环境基线与系统配置 | root |
| `/var/lib/zeromatrix` | 系统配置状态 | root |
| `/var/log/zeromatrix` | 系统配置日志 | root |
| `~/workspace/ZeroMatrixTech/ACLt` | 每位开发者独立源码副本 | 开发者 |
| `~/.local/state/zeromatrix` | 用户验收记录 | 开发者 |

系统工具链使用 `/usr/bin`，不全局覆写 PATH、PYTHONPATH、Rust flags。
用户工作区从 `/etc/skel/workspace/ZeroMatrixTech` 创建；已有用户执行
`mkdir -p "$HOME/workspace/ZeroMatrixTech"`。不迁移或改写现有 ACLt 工作区。
ACLt 的 build、target、artifacts 和运行任务遵循上游规范，不把任务放在网络盘或共享目录。
项目源码的离线交付应另行导出审核过的 commit / Git bundle，记录 SHA；本版不打包维护者的工作目录。

用户编辑器配置位于 `~/.local/share/zeromatrix/vscode`，用户初始化日志位于
`~/.local/state/zeromatrix`。首次登录为已有安装账户创建个人工作区，
不依赖 `/etc/skel` 对已创建账户生效。详见 [编辑器工作流](editor-workflow.md)。
