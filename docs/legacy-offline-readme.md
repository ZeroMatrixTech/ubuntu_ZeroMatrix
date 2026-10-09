# ZeroMatrix Ubuntu 开发系统

基于 Ubuntu 26.04.1 LTS Desktop / amd64，供 x86_64 实体机及虚拟机使用。
目标是一次离线安装后具有 C++、Python、Rust、VS Code 与 ACLt 开发工作流，
并通过可维护的构建项目持续发行候选 ISO。

当前候选版本见 `VERSION`。333 个离线 Debian 包、7 个 VSIX 与原始 ISO 的官方签名校验已准备完成。
离线扩展安装、针对原 ISO 的依赖检查及宿主机断网 ACLt 全量流程通过；尚未完成真实断网装机、
编辑器调试和 ACLt 全量验收，不能称为正式发行版。

## 安装体验

ISO 默认 ZeroMatrix 启动项保留账户与磁盘等安装界面，安装结束前配置离线软件环境。
首次登录创建个人工作区，从本地安装扩展并打开 **ZeroMatrix Development**。
工作区预置 C++ GDB、Python venv / debugpy、Rust 离线 Cargo / LLDB，以及
ACLt 日常检查、强制取证与全量验收任务。Live 桌面不保证预装开发工具。

## 使用 ISO 安装系统

1. 从公司受控存储获取同版本的 `.iso`、`.iso.sha256` 和 `.manifest.json`。当前候选文件名为 `zeromatrix-0.1.0-rc2-amd64.iso`；后续版本以实际发行文件名为准。
2. 核对镜像 SHA256。在 Linux 中进入三个文件所在目录运行 `sha256sum -c zeromatrix-0.1.0-rc2-amd64.iso.sha256`；在 Windows PowerShell 中运行：

   ```powershell
   Get-FileHash .\zeromatrix-0.1.0-rc2-amd64.iso -Algorithm SHA256
   Get-Content .\zeromatrix-0.1.0-rc2-amd64.iso.sha256
   ```

   两个摘要须一致，并核对公司可信渠道提供的摘要；文件之间相符不等于来源已经认证。
3. **虚拟机**：创建 x86_64 Linux 虚拟机，将 ISO 挂载为虚拟光驱，断开虚拟网卡，再从光驱启动。建议初次验收配置 4 个 CPU、8 GiB 内存、80 GiB 磁盘；这是项目验收建议，不是 Ubuntu 官方最低要求。**实体机**：先备份数据，把 ISO 写入容量至少 16 GB 的空 U 盘，再通过固件启动菜单启动 U 盘。写盘会清空所选 U 盘；安装界面中的磁盘操作也可能删除数据。
4. 选择默认 **ZeroMatrix** 启动项，按界面选择语言、账户和目标磁盘。保持断网，跳过下载更新和第三方驱动。安装结束前自动配置离线开发环境；原始 Ubuntu 备用启动项不会自动执行这套配置。
5. 安装完成后移除安装介质，重启并登录桌面。首次登录自动准备 `~/workspace/ZeroMatrixTech`、Python 虚拟环境、ACLt 副本及编辑器扩展，并打开 **ZeroMatrix Development**。等待初始化完成后再使用工作区。
6. 在普通用户终端中运行以下检查，随后在工作区分别验证 C++、Python、Rust 的 F5 调试及 ACLt 全量任务：

   ```bash
   bash /opt/zeromatrix/offline/verify.sh
   ```

   检查证据默认保存到 `~/.local/state/zeromatrix/`。工具检查成功不等于实际装机、GUI 调试和 ACLt 全量验收全部完成。当前仍是候选镜像，先在断网虚拟机验收，再部署开发电脑。详见 [验收清单](docs/acceptance.md)。

## 构建当前版本

当前输入已按版本与摘要锁定。已有原始 ISO 和 VS Code `.deb` 时，可用 `make acquire`
在联网构建机取得同一套离线输入；该命令不安装或升级宿主机软件。详细步骤见
[VS Code 与工作流](docs/editor-workflow.md)及[构建与发布](docs/build-release.md)。

```bash
make acquire
# 新 checkout 首次准备项目源码时执行，当前仓库已准备：
make workspace ACLT_DIR=/absolute/path/to/ACLt
make iso
```

摘要也可单独保存至本地 `config/base-iso.sha256`，之后运行 `make`。
构建命令不会联网下载缺项；输入必须事先完整准备。采集入口用 Ubuntu 公钥核验官方校验清单签名，并核对原 ISO。
更新工具链输入时仍需独立采集与全量验收，不能只修改版本号。
`make test` 执行单元测试和 Bash 语法检查；`make check` 检查构建输入；`make help` 显示所有入口。
这些检查不替代真实安装验收。

## Windows 下构建 ISO（WSL 2）

本项目使用 Bash、dpkg 和 xorriso，在 Windows 中通过 **WSL 2 的 Ubuntu 环境**运行 `make iso`。WSL 用于构建，不用于验证此 Desktop ISO 的安装过程。Windows 11 或 Windows 10 2004 / Build 19041 及以上可使用以下安装入口，参见 [Microsoft WSL 安装文档](https://learn.microsoft.com/en-us/windows/wsl/install)。本项目尚未在 Windows / WSL 上实机验证这些步骤。

### 1. 安装并进入 WSL

在管理员 PowerShell 中运行：

```powershell
wsl --install -d Ubuntu
```

按提示重启，首次启动 Ubuntu 时创建 Linux 用户和密码。已有 WSL 时，使用 `wsl --list --verbose` 确认 Ubuntu 的 VERSION 为 `2`；如为 `1`，运行 `wsl --set-version Ubuntu 2`（发行版名称以列表为准）。后续构建命令均在 Ubuntu 的 Bash 终端执行。

### 2. 安装构建工具并准备仓库

```bash
sudo apt-get update
sudo apt-get install -y make python3 git dpkg-dev xorriso curl gpgv ubuntu-keyring ca-certificates
mkdir -p ~/src
```

这一步安装的是 WSL 构建工具，不会把目标镜像的 C++ / Python / Rust 环境安装到 Windows。优先使用 WSL 的 Linux 文件系统（例如 `~/src/ubuntu_ZeroMatrix`），避免在 `/mnt/c` 下直接构建。建议至少预留 40 GiB 可用空间，并为下载缓存、临时文件及多版本产物增加余量。

若 Windows 已有完整仓库，假设路径为 `C:\ZeroMatrixTech\ubuntu_ZeroMatrix`，复制到 WSL：

```bash
cp -a /mnt/c/ZeroMatrixTech/ubuntu_ZeroMatrix ~/src/
cd ~/src/ubuntu_ZeroMatrix
```

也可用 `git clone` 从公司的真实仓库地址取得源码，然后进入仓库目录。Git 不包含被忽略的 ISO、deb、VSIX 和离线包集合，单独 clone 后须准备下一步输入。确保脚本保持 LF 换行。

### 3. 准备当前版本输入

联网构建路径：把以下两个已锁定文件放入仓库根目录，再执行采集命令。

- `ubuntu-26.04.1-desktop-amd64.iso`：从 Ubuntu 官方或公司可信存储获取。
- `code_1.140.0-1790759618_amd64.deb`：公司保存的固定版本，须符合 `config/code-package.json`，不能随意换为最新版。

```bash
make code-info
make acquire
```

`make acquire` 联网下载锁定的 Debian 包和 VSIX，核验原始 ISO 的官方签名及摘要，并准备 `config/base-iso.sha256`。它不会自动下载上述原始 ISO 或 Code 安装包。

如 `offline/workspace/ACLt.bundle` 尚未准备，导入公司授权的、工作区干净的 ACLt 仓库（这里的路径须替换成实际 WSL 路径）：

```bash
make workspace ACLT_DIR=/absolute/path/to/ACLt
```

若已复制完整离线输入，跳过 `make acquire` 和已有 bundle 的导入，直接进行下一步。完全离线的构建机需预先具备构建工具、原始 ISO、Code 安装包、`offline/repo/`、`offline/editor/`、`offline/workspace/` 及经过官方核实的 `config/base-iso.sha256`；不能只复制 Git 源码。首次安装 WSL 和构建工具也需要联网准备，或由公司提供预配置环境。

### 4. 执行 make 并取出产物

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp"
make iso
```

`make iso` 自动执行输入检查和测试，再构建镜像；ISO 构建阶段不需要网络。不要使用 `sudo make iso`。成功后，在 `dist/` 获得对应版本的 ISO、SHA256 和构建清单。以当前版本为例：

```bash
cd dist
sha256sum -c zeromatrix-0.1.0-rc2-amd64.iso.sha256
explorer.exe .
```

通过打开的资源管理器把三份产物复制到 Windows 存储目录，随后按上面的安装步骤使用。同版本产物已存在时构建会拒绝覆盖；制作新候选版可在仓库根执行 `make iso VERSION=0.1.0-rc3`。失败留下 `.iso.partial` 时，先查看错误并保存日志，再明确处理该临时文件后重试。磁盘空间不足时同时检查 Windows 所在磁盘与 WSL 内部空间。

当前含官方 VS Code 的完整 ISO 按公司内部部署管理；构建成功不代表获得公开再分发授权，参见 [许可政策](docs/licensing.md)。

```text
config/          包清单、版本基线、编辑器及安装器配置
templates/       工作区、任务、调试配置与桌面入口
scripts/         包采集、ISO 构建、系统配置与用户初始化
offline/         软件包、VSIX、ACLt Git bundle（不提交 Git）
docs/            构建、工作流、目录、验收与许可说明
tests/           构建与离线输入测试
dist/            候选 ISO、摘要与构建清单（不提交 Git）
```

[目录约定](docs/layout.md) · [验收清单](docs/acceptance.md) · [中英双语许可说明](docs/licensing.md)

不提交密钥、个人配置、大体积镜像或包缓存。

## 许可 / License

本项目原创构建代码、配置、模板、测试和文档采用 [Apache-2.0](LICENSE)，
另有声明及第三方内容除外。[中文说明](LICENSE.zh-CN.md)和[中英双语许可政策](docs/licensing.md)明确适用范围。
随附软件及内部项目保留各自许可；包含官方 VS Code 的候选 ISO 当前按公司内部部署设计，不宣称可公开分发。

Original project build code, configuration, templates, tests and documentation are licensed under
[Apache-2.0](LICENSE), except separately licensed and third-party content. See the
[bilingual licensing policy](docs/licensing.md) for scope. Bundled software and internal projects retain
their own licenses. The current candidate ISO containing official VS Code is prepared for internal
company deployment; public redistribution is not claimed to be authorized.
