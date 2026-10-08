# VS Code 与离线工作流

## 安装后的体验

使用候选 ISO 默认的 **Install ZeroMatrix Development (offline setup)** 启动项。
安装器仍询问账户、时区和磁盘选择；结束前自动运行离线配置，不预设擦盘或通用密码。
首次登录 GNOME 时，ZeroMatrix 初始化程序建立个人工作区、Python venv、独立 VS Code 配置，
从本地 VSIX 安装精确版本扩展，然后打开工作区。应用菜单提供 **ZeroMatrix Development**。
后续从终端运行 `zeromatrix-code` 可再次打开。

工作区包含 C++、Python、Rust 示例和介质锁定提交的 ACLt 独立 Git 副本。
`Ctrl+Shift+P` → `Tasks: Run Task` 可运行编译、测试和 ACLt 流程；F5 的调试配置包含
C++ GDB、Python debugpy、Rust CodeLLDB。首次打开工作区需要检查并确认 Workspace Trust。
示例无第三方 Python / Cargo 依赖；ACLt 全量验收以实际退出码和日志为准。

## 构建输入

1. 当前已导入 VS Code `1.140.0-1790759618` amd64，锁定信息见 `config/code-package.json`。
   更新时从 [VS Code 官方网站](https://code.visualstudio.com/download) 下载 amd64 `.deb`。
2. 在联网采集 VM 中，按扩展列表取得固定版本 VSIX：
   `ms-vscode.cpptools`、`ms-python.python`、`ms-python.debugpy`、
   `ms-python.vscode-pylance`、`rust-lang.rust-analyzer`、`vadimcn.vscode-lldb`。
3. 从 VS Code 扩展界面使用 **Download VSIX**（或指定版本下载），选 linux-x64 版本，
   依赖扩展也一起取得。不能只保存依赖联网下载后端的通用安装器。
4. 保存下载来源、版本和许可证信息，导入脚本记录实际包版本及 SHA256。

参考 [官方离线 VSIX 安装方式](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)。
原生扩展包检查至少包括 cpptools、OpenDebugAD7、rust-analyzer、codelldb；
扩展依赖缺失、架构不对或包被改动时拒绝构建。扩展与 code 的版本兼容性仍需实际安装验收。
部分 Python 扩展版本依赖 Python Environments 等扩展，导入错误会给出缺失 ID，补齐相应固定版本即可。
`rust-src` 作为系统包提供 Rust 标准库分析所需源码；版本与 rustc 必须配套。

在仓库根运行 `make code-info` 可核对本地安装包。`config/code-package.json` 记录本地
文件的摘要，用于固定构建输入，不替代对下载来源的核实。采集脚本默认自动选择锁定的
仓库根安装包，也支持显式 `CODE_DEB` 路径（内容必须与锁定清单相同）。
升级时使用 `make code-lock CODE_DEB=/path/to/new-code.deb` 更新清单，再重新采集依赖及验证扩展。

在联网、由相同 Ubuntu ISO 安装的干净采集 VM 中，将同一个安装包与仓库复制过去后：

```bash
sudo bash scripts/collect-packages.sh /absolute/path/to/debs
```

当前已锁定输入可直接执行 `make acquire`。若准备新输入或手动导入，回到构建机：

```bash
make bundle DEBS_DIR=/absolute/path/to/debs
make editor VSIX_DIR=/absolute/path/to/vsix
make workspace ACLT_DIR=/absolute/path/to/ACLt
make iso BASE_SHA256=OFFICIALLY_VERIFIED_SHA256
```

ACLt 导出要求干净工作区，保存 HEAD 的 Git bundle（包含其可达历史）与完整提交 SHA，
不打包维护者未提交文件、凭据、工具链或本地配置。导入前要审查源码历史是否适合交付。
每套输入目录拒绝覆盖；升级时用新构建 checkout 准备新输入，修改 VERSION。

## 配置与日志

- `~/.local/share/zeromatrix/vscode/data`：独立编辑器配置和状态。
- `~/.local/share/zeromatrix/vscode/extensions`：固定版本扩展。
- `~/workspace/ZeroMatrixTech`：个人源码、示例、工作区说明。
- `~/.local/state/zeromatrix/first-login.log`：首次登录日志。
- `~/.local/state/zeromatrix/extensions.txt`：安装后的扩展版本。
- `/var/log/zeromatrix/provision.log`：系统离线配置日志。

关闭编辑器、扩展自动更新与 Git 自动 fetch；Rust Cargo 任务明确使用 `--offline`。
不关闭工作区信任。初始化只添加缺失的工作区文件，保留已有 ACLt 与设置；不修改全局 Git 身份。
失败时不写成功标记，修复后执行 `zeromatrix-code` 重试。首次登录日志保留失败输出，配置与验收日志保留退出码。
当前自动初始化只处理全新安装的一次配置；不支持在已有 profile 上无审查地热升级。

## 发布边界

[VS Code 产品许可](https://code.visualstudio.com/license)覆盖公司内部部署，
官方产品和扩展不统一采用源码仓库的 MIT 许可。本候选构建按公司内部介质使用。
公开发行前另行解决官方产品和各扩展的分发许可；必要时采用 Code - OSS 及可分发的扩展方案。
项目自身许可证仍未确定。

当前 7 个扩展已用所提供 VS Code 1.140 在断网命名空间实际安装并核对版本；完整安装器流程仍必须在真实断网安装的桌面会话中验证自动配置、
语言补全、三个 F5 调试入口和 ACLt 全量流程后，才能称为完整工作流已验收。
