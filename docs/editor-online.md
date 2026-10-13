# 当前编辑器工作流（0.2.x）

系统构建与安装以[构建与安装规范](build-and-install.md)为准。当前安装阶段联网安装工具链和 Code；首次登录联网下载固定版本扩展与指定提交的 ACLt。`/opt/zeromatrix/offline` 是兼容路径名称，不表示支持离线初始化。

## 初始化与日常使用

首次 GNOME 登录自动初始化；也可执行 `zeromatrix-code` 重试或打开工作区。初始化必须以普通开发者账户运行。

- 工作区：`~/workspace/ZeroMatrixTech`，含 C++、Python、Rust 示例及 ACLt Git 副本，初始分支 `dev/local`。
- 编辑器数据：`~/.local/share/zeromatrix/vscode/data`；扩展：同级 `extensions`。
- 日志：`~/.local/state/zeromatrix/first-login.log`；已安装扩展版本：同目录 `extensions.txt`。
- 成功标记：同目录 `setup-complete` 与 `first-login-complete`，不代表 F5 或 ACLt 全量验收通过。

初始化添加缺失的模板文件，保留已有文件和 Git 工作区；已有 ACLt 目录必须是 Git checkout。成功后不自动重新安装新版本配置。不要通过删除成功标记来无审查升级已有环境。

首次打开检查 Workspace Trust。通过 `Tasks: Run Task` 选择编译、测试或 ACLt 流程；调试面板分别选择 C++ GDB、Python debugpy、Rust LLDB 并按 F5。编译示例成功不能替代项目全量验收。

## 维护输入

| 配置 | 用途 |
|---|---|
| `config/editor-acquisition.json` | 首次登录获取的扩展 ID 和固定版本 |
| `config/project-online.json` | ACLt 来源 URL 与固定提交 |
| `config/vscode/settings.json` | 独立 profile 的初始设置 |
| `templates/workspace/` | 工作区模板与调试任务 |

默认在线构建不要求先执行 `make acquire`、`make editor` 或 `make workspace`。旧离线导入方法保存在[历史编辑器流程](editor-workflow.md)。修改以上输入后，重建新候选版本，并在新的安装与账户中验收；已有安装不会自动迁移。

## 故障与验收

先确认 `/var/log/zeromatrix/provision-complete` 存在，再检查首次登录日志。保持网络可访问项目来源与扩展下载服务，执行 `zeromatrix-code` 重试。缺少系统工具时按构建与安装规范重跑系统配置。

分别验收语言补全、三个 F5 入口、扩展实际版本和 ACLt 全量测试，记录失败与退出码。当前 VirtualBox 安装反馈不覆盖这些检查。日常断网可用性取决于工具、扩展后端和项目依赖是否已准备齐全，不能由首次安装成功推定。

许可范围见[许可说明](licensing.md)，历史扩展安装证据见[0.1.x 候选输入记录](candidate-inputs.md)；历史记录不代替当前版本验收。
