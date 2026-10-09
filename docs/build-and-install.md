# 0.2.0-rc3 构建与安装规范

## 当前验收范围

2026-10-09，用户反馈 rc3 在 VirtualBox 中安装流程跑通。成功启动路径为普通图形入口，手动删除 `quiet splash`。这份记录不代表 C++/Python/Rust 编译测试、Code 扩展、F5、实体机、UEFI/Secure Boot 或 WSL2 已全部通过。原有 rc3 ISO 及其校验文件保留，不覆盖。

## 标准构建

使用 Linux，或 WSL2 的 Linux 文件系统。安装依赖：

```bash
sudo apt update
sudo apt install make python3 git git-lfs xorriso dpkg-dev squashfs-tools uidmap util-linux
git lfs install
git clone https://github.com/ZeroMatrixTech/ubuntu_ZeroMatrix.git
cd ubuntu_ZeroMatrix
git lfs pull
unshare --user --map-auto --map-root-user true
make                 # 默认 vm，版本读 VERSION（当前 0.2.0-rc3）
# 或 make iso-physical
# 或 make isos
make verify-iso
```

需要约 60 GB 可用空间及当前用户的 subuid/subgid 映射。除安装依赖外，不使用 `sudo make`。构建依次完成工具检查、测试、源目录校验、解包/裁剪/压缩缓存和 ISO 封装。源文件来自 `base/media`、`base/boot`、`base/snaps`，正常构建无需原始完整 ISO，也不打入 Code deb、VSIX 或公司源码 bundle。

输出为 `dist/zeromatrix-<VERSION>-<PROFILE>-amd64.iso`、`.iso.sha256` 和 `.manifest.json`。`make verify-iso` 校验 dist 中全部 ISO 校验文件，缺失镜像或校验不符会报错。

两条基线共用 `build/rootfs-<VERSION>`。只调整安装载荷或启动参数时，可以通过 `ROOTFS_BUILD` 显式复用已完成缓存；脚本校验输入指纹与系统层 SHA256，不能复用不同裁剪规则的缓存。本机 rc3 曾复用 rc2 的相同系统层，首次 clone 直接 `make` 会自行生成当前版本缓存。

已有 ISO/partial 时拒绝覆盖。修改后使用新版本；裁剪输入变化时同时选择新缓存目录：

```bash
make isos VERSION=0.2.0-rc4 ROOTFS_BUILD=build/rootfs-0.2.0-rc4
```

Windows 在管理员 PowerShell 执行 `wsl --install -d Ubuntu`，随后在 WSL 终端执行上述流程。仓库放在 `~/src` 等 Linux 路径，生成后通过 `explorer.exe .` 取出 dist 产物。该构建平台仍待独立验收。

## VirtualBox 安装

1. 跳过 VirtualBox 无人值守安装。建议 8 GB RAM、2 CPU、80 GB 动态 SATA 磁盘、VMSVGA、128 MB 显存，关闭 3D；NAT 网卡，网线已连接。安装前后保持相同固件模式。
2. 挂载 rc3 vm ISO。选择 `Install ZeroMatrix vm (normal graphics, online)`，按 E，在 linux 行删除 `quiet splash`，保留其他参数，Ctrl+X 启动。此修改只影响本次启动，rc3 ISO 原启动菜单保持不变。
3. 进入 Live 桌面后打开安装器。选择 Default selection；额外专有硬件驱动和媒体格式不勾选。只有目标虚拟磁盘数据可清除时才选择 Erase disk。创建普通用户，不启用 Active Directory。
4. 全程联网。安装末尾从 Ubuntu 源安装开发工具，从 Microsoft 签名 APT 源安装 Code。Live 中的载荷为 `/cdrom/zeromatrix`；安装末尾才复制到 `/target/opt/zeromatrix/offline`。重启后对应 `/opt/zeromatrix/offline`，不应要求 Live 本身存在这个目录。
5. 安装明确显示完成后重启，弹出光盘并按 Enter。如果此时提示无法卸载 `/cdrom`，通过设备→光驱移除虚拟盘，再按 Enter；只有确认安装完成后才考虑关机再启动。
6. 首次登录保持联网，下载扩展和指定提交的 ACLt，初始化工作区。失败可运行 `zeromatrix-code` 重试。

## 安装后验收

```bash
cat /var/log/zeromatrix/provision-complete
rustc --version
cargo --version
g++ --version
python3 --version
code --version
bash /opt/zeromatrix/offline/verify.sh
```

普通用户执行 verify.sh，另行验证工作区各语言 F5 和项目全量测试。安装完成标记只表示系统配置脚本成功，不能替代用户工作流验收。

失败时检查 `/var/log/zeromatrix/provision.log`、`/var/log/installer/` 以及 `~/.local/state/zeromatrix/first-login.log`。已有载荷可联网重试：

```bash
sudo bash /opt/zeromatrix/offline/scripts/provision-online.sh /opt/zeromatrix/offline
```

若目标系统完全没有载荷，挂载 ZeroMatrix ISO，在光盘目录打开终端运行 `sudo bash ./zeromatrix/scripts/provision-online.sh ./zeromatrix`，成功后注销再登录。
