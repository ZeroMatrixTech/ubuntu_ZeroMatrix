# 当前目录与权限（0.2.x）

| 路径 | 用途 | 所有者 |
|---|---|---|
| `/opt/zeromatrix/offline` | 安装载荷、配置、模板和修复脚本；名称兼容历史版本 | root |
| `/etc/zeromatrix` | 系统环境基线 | root |
| `/var/log/zeromatrix` | `provision.log` 与系统配置成功标记 `provision-complete` | root |
| `~/workspace/ZeroMatrixTech` | 个人示例、工作区和 Python `.venv` | 开发者 |
| `~/workspace/ZeroMatrixTech/ACLt` | 从固定提交建立的独立 Git 副本 | 开发者 |
| `~/.local/share/zeromatrix/vscode` | 独立 VS Code 数据与扩展 | 开发者 |
| `~/.local/state/zeromatrix` | 初始化锁、成功标记、扩展版本及用户日志 | 开发者 |

当前默认在线安装不携带离线 Debian 软件源、VSIX 集合或公司 Git bundle。安装阶段及首次登录需要联网；载荷目录名称不构成离线保证。

系统工具链使用系统路径，不全局覆写 PATH、PYTHONPATH 或 Rust flags。首次登录直接为当前普通账户合并缺失模板文件，并建立个人项目副本，不依赖 `/etc/skel` 对已有账户生效。已有文件和 ACLt checkout 保留，不修改全局 Git 身份。

详见[构建目录](build-layout.md)、[构建与安装](build-and-install.md)及[编辑器工作流](editor-online.md)。
