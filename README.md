# ZeroMatrix Ubuntu Development

Ubuntu 26.04.1 LTS amd64 开发系统，同一仓库维护两条可安装基线。

| PROFILE | 用途 | 差异 |
|---|---|---|
| `vm`（默认） | VirtualBox / VMware / KVM | 默认安全图形启动；包含对应 guest agent |
| `physical` | x86_64 实体机 | 正常图形启动、保留 Ubuntu firmware、允许安装器驱动检测 |

共用 Ubuntu 官方 Desktop 安装器、完整 GNOME 桌面、C++/Python/Rust 工具链、标准目录和 VS Code 工作区。启动菜单两条基线均提供正常/安全图形入口，也保留带相同配置的 Ubuntu 兼容入口。虚拟机 ISO 的 `nomodeset` 仅用于安装启动，不作为已安装系统的永久配置。VM guest agent 不保证与未来 VirtualBox/内核组合兼容，仍需验收。

## 构建 ISO（Linux）

构建机需要网络（首次 clone/LFS 获取），至少约 60 GB 可用空间。ISO 重打包不需要 root，不会修改宿主机软件源。

```bash
sudo apt update
sudo apt install make python3 git git-lfs xorriso dpkg-dev squashfs-tools uidmap util-linux
git lfs install
git clone https://github.com/ZeroMatrixTech/ubuntu_ZeroMatrix.git
cd ubuntu_ZeroMatrix
git lfs pull
make iso-vm       # 等价于 make 或 make iso PROFILE=vm
make iso-physical # 实体机
# 或 make isos
```

原始 ISO 已展开为 `base/media/`（光盘文件树）和 `base/boot/`（BIOS/UEFI 引导记录）。原来嵌套在主系统层中的 Snap 以原始应用文件名存放在 `base/snaps/`，`base/system-layer.json` 保存还原路径、权限、时间和校验值。没有人工分块文件。大型系统层、Snap、原始 deb 仍通过 Git LFS 保存；目前最大自然源文件为 2,141,511,680 字节，低于 2 GiB，请确认远端 LFS 的对象大小及存储配额。

`base/tree-manifest.json` 锁定源目录全部文件和符号链接。构建读取这些文件，**不需要仓库根目录的原始 ISO**。维护者导入新基底前应验证 Ubuntu 官方校验签名，再更新 `config/base-iso.json`，在新 checkout 中执行 `make base-import`。原始 ISO 仅是首次导入输入，不提交完整 ISO。

`make` 自动完成源目录校验、私有用户命名空间解包、APT 按包裁剪、重新压缩、生成安装源清单和 BIOS/UEFI ISO。首次重压缩需要较长时间，后续两条基线共用缓存。Linux/WSL2 需要允许 user namespace，并为当前用户配置 `/etc/subuid`、`/etc/subgid` 范围；`newuidmap` / `newgidmap` 由 `uidmap` 提供。可先用 `unshare --user --map-auto --map-root-user true` 检查。构建不需要真实 root，不会修改宿主机的软件包或软件源。

文件布局和裁剪规则详见 [docs/build-layout.md](docs/build-layout.md)。
产物：`dist/zeromatrix-<VERSION>-<PROFILE>-amd64.iso`，及 SHA256 和构建清单。已有产物/partial 不覆盖，可使用 `make iso PROFILE=vm VERSION=0.2.0-rc2`。版本默认读 `VERSION`。本仓库不承诺在线软件版本或 ISO 字节可重现；实际软件版本记录在目标系统日志。

## Windows 构建

管理员 PowerShell 安装 WSL2：

```powershell
wsl --install -d Ubuntu
```

重启并在 WSL Ubuntu 终端执行上述 Linux 依赖安装、clone、`git lfs pull`、`make`。仓库放在 WSL 的 `~/src/` 等 Linux 文件系统中，避免 `/mnt/c` 权限及性能问题。生成后在 `dist` 目录执行 `explorer.exe .`，复制 ISO 到 Windows，用 VirtualBox 加载。WSL 构建路径需要独立验证。

## 安装与首次登录

1. 校验 `dist/*.iso.sha256`；写入 USB 或挂到虚拟机光驱。
2. VirtualBox 选择 Ubuntu 64-bit，**跳过 VirtualBox 无人值守安装**，建议 8 GB RAM、2 CPU、80 GB 动态 SATA 磁盘、VMSVGA/128 MB、先关闭 3D；网卡 NAT，网线已连接。BIOS/UEFI 安装模式安装后保持一致。
3. 选择 **Install ZeroMatrix vm/physical** 入口。所有 Ubuntu 启动入口均加载相同 ZeroMatrix 配置，介质根目录也提供 `autoinstall.yaml` 自动发现。按安装器提示选择语言、磁盘和用户；安装器格式化操作只针对你选中的目标磁盘。
4. **安装阶段必须联网**。晚期配置从 Ubuntu 仓库安装开发工具，从 Microsoft 官方签名 APT 仓库获取 Code。失败会使安装报告失败，日志位于目标 `/var/log/zeromatrix/provision.log`，解决网络后可在目标系统运行 `sudo bash /opt/zeromatrix/offline/scripts/provision-online.sh /opt/zeromatrix/offline` 重试。
5. 安装完成弹出 ISO，重启登录。首次登录联网获取锁定版本扩展及指定提交的 ACLt，创建 `~/workspace/ZeroMatrixTech` 和 Python `.venv`，自动打开工作区。初始化失败不会标记完成；联网后执行 `zeromatrix-code` 重试，查看 `~/.local/state/zeromatrix/first-login.log`。
6. 先运行 `cat /var/log/zeromatrix/provision-complete`，确认系统配置成功；该文件不存在时不能视为开发环境安装完成。再在工作区选择 C++ GDB、Python debugpy、Rust LLDB 执行 F5。`bash /opt/zeromatrix/offline/verify.sh` 验证编译工具链，ACLt 全量验收另外运行。

`/opt/zeromatrix/offline` 是兼容历史脚本的配置路径名称，新基线不具备完全离线安装保证。VS Code 使用独立 profile `~/.local/share/zeromatrix/vscode`，保留工作区信任机制。

## 维护与许可

- `config/profiles/*.json`：两条基线差异；`config/packages.txt`：共用开发包；`config/remove-packages.txt`：裁剪包清单。
- `config/editor-acquisition.json`：在线扩展版本；`config/project-online.json`：项目 URL 和固定提交。
- `make test`：构建逻辑/工作流测试；生成清单的安装验收状态为 pending，实际安装和 F5 验收后才能发布。
- 历史离线脚本与输入仍保留，但默认构建不读取 `offline/repo`、`.deb`、VSIX 或公司 Git bundle。旧离线产物仍可能包含这些文件，不应公开发布。

自有构建代码采用 Apache-2.0；英文 [LICENSE](LICENSE) 为准，中文说明见 [LICENSE.zh-CN.md](LICENSE.zh-CN.md)。Ubuntu 基底、固件和下载软件保留各自许可证。Code/扩展由最终用户机器从官方源下载，减少镜像二次分发范围，**不代表全部 ISO 自动获得公开分发许可**；Ubuntu 商标、第三方组件和 GPL 对应源码义务仍需审核。展开的 Ubuntu 基底及应用源文件同样属于再分发，不能把它声明为 Apache-2.0。

历史离线部署说明保存在 `docs/legacy-offline-readme.md`，仅适用于 0.1.x。

### 已安装系统缺少 Rust 或 Code

先检查 `ls /opt/zeromatrix` 和 `sudo tail -n 80 /var/log/zeromatrix/provision.log`。
如果已有 `/opt/zeromatrix/offline`，联网后重试：

```bash
sudo bash /opt/zeromatrix/offline/scripts/provision-online.sh /opt/zeromatrix/offline
```

如果该目录不存在，说明 ZeroMatrix 配置尚未落入目标系统。把 ZeroMatrix ISO 重新插入虚拟光驱，在文件管理器打开光盘，进入光盘目录打开终端，运行：

```bash
sudo bash ./zeromatrix/scripts/provision-online.sh ./zeromatrix
```

完成后注销再登录，运行 `rustc --version`、`cargo --version` 和 `code --version`。完整验收使用 `/opt/zeromatrix/offline/verify.sh`。在线安装需要能访问 Ubuntu、Microsoft 和 Marketplace；仅能打开普通网页并不足以证明这些地址可达。
