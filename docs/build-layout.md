# 文件树与 ISO 构建

## 目录

- `base/media/`：可浏览的 Ubuntu 光盘文件树（EFI、boot、casper、pool、dists、说明和软件清单）。
- `base/boot/`：从原镜像提取的 MBR、EFI 等引导记录。
- `base/snaps/`：原先内嵌的应用文件，例如 Firefox、Snap Store、固件更新器；保持原文件名。
- `base/system-layer.json`：核心系统层及 Snap 的还原元数据；Snap 的多路径硬链接在解包时恢复。
- `base/tree-manifest.json`：所有源文件/符号链接校验及原始 ISO 来源。
- `config/remove-packages.txt`：按包名维护裁剪规则。
- `build/rootfs-<VERSION>/rootfs/`：解包、裁剪后的正常系统目录，可以直接查看 `etc/`、`usr/`、`var/` 等。
- `build/rootfs-<VERSION>/rootfs-files.txt`：重打包后的完整文件列表、权限和 UID/GID。
- `build/rootfs-<VERSION>/packages.tsv`、`removal-report.json`、`purge-plan.txt`：实际保留包、卸载包及依赖计划。

`base/media/casper/minimal.core.squashfs` 保存核心系统文件，嵌套 Snap 已独立列出。SquashFS 是启动/安装所需的文件系统格式，不是任意切分的 ISO 数据块。构建时把它展开到正常系统目录，恢复应用文件，再按清单裁剪。根目录拥有文件权限、用户/组、扩展属性及设备节点，不能靠普通解压后直接删文件来维护包数据库。

## 保留与裁剪

保留 GNOME、显示管理器、设置、终端、文件管理器、归档工具、网络、浏览器、邮件、音频、蓝牙、打印、字体、固件和驱动支持。C++/Python/Rust、VS Code 和调试扩展继续由联网安装/首次登录流程配置。

默认移除 LibreOffice、Rhythmbox、Shotwell 及指定游戏包。当前 Ubuntu 基底没有清单中的游戏，跳过不存在的包。实际卸载 49 个包（含 LibreOffice 相关语言包及 Python UNO 桥接），不移除 Python。APT 模拟计划必须通过保护包检查；不运行 autoremove。浏览器和邮件 Snap 保持原样。

## 构建和维护

```bash
make rootfs             # 生成/验证解包和压缩缓存
make iso-vm
make iso-physical
make isos
```

修改裁剪清单、源目录或裁剪实现后旧缓存会拒绝复用。保留旧目录用于排查，通过新路径重新构建：

```bash
make isos VERSION=0.2.0-rc4 ROOTFS_BUILD=build/rootfs-0.2.0-rc4
```

产物或 partial 已存在时同样使用新版本，避免覆盖。中断的软件包修改不会自动继续；应使用新的缓存目录。根目录部分文件属于映射 UID，清理构建缓存时需要在同样的用户命名空间中操作。

新的 ISO 使用合并裁剪后的安装系统层，以及保留 Ubuntu Live 安装器的独立叠加层。叠加层的删除标记、包数据库和软件清单一并处理。重复的可选语言/安装变体不打入新介质，安装语言包可在线获取。常规 BIOS/UEFI 启动保留，增强 TPM/Snap 型安装变体不作为这版基线的一部分。0.2.0-rc3 的 VirtualBox 安装流程已由用户反馈跑通；Secure Boot、实体机、工具链和 F5 调试仍需分别实际验收。完整构建和安装操作见 `docs/build-and-install.md`。
