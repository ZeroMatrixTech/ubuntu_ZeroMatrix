# 构建与发布

## 边界

用户机器安装及日常开发不需要网络。软件包采集在独立、可联网的构建 VM 上完成；
完全隔离环境可通过受控介质导入同一包集合。不要直接在维护者宿主机 sudo 运行采集脚本。
采集 VM 必须由同一原始 Desktop ISO 安装、amd64、Ubuntu 26.04.1；
采集脚本只下载，不安装或升级工具链；会先解析完整依赖，再对干净 Desktop 的已安装状态补齐反向依赖。依赖闭包必须在新的离线 VM 上验证。
新增 Python / Cargo 依赖时，应另行建立锁定的 wheelhouse / cargo vendor，并补充验收；当前 ACLt 不需要它们。

## 已锁定输入的自动采集（推荐）

当前已建立 `config/packages-acquisition.json`（333 个包）与
`config/editor-acquisition.json`（7 个扩展）：来源 URL、精确版本与 SHA256 都已锁定。
仓库根保留原始 Ubuntu ISO 和已锁定的 code `.deb`，在联网构建机执行：

```bash
make acquire
make iso
```

`make acquire` 校验官方 ISO 签名，下载固定输入并校验摘要，生成离线软件源和 VSIX 集合。
不需要 sudo，不修改宿主机 APT 状态、软件源或编辑器配置。默认下载缓存位于
`build/acquire`，可用 `ACQUIRE_DIR=/path/to/cache` 覆盖。已有正确缓存直接复用。
`make iso` 本身仍保持离线；包集合已存在且与锁定清单不同则拒绝覆盖。

固定 URL 如果将来从上游移除，应使用团队保存的离线包集合或另行审查更新输入，
不自动替换为“最新版”。原始 ISO 与 code `.deb` 不从此入口自动下载。
当前完整输入与校验报告见 [候选输入验收](candidate-inputs.md)。

## 软件包采集

在采集 VM 安装构建工具 `dpkg-dev`，复制本仓库，然后运行：

```bash
sudo bash scripts/collect-packages.sh /absolute/path/to/debs
```

采集使用空的 APT 包状态记录解析依赖，以包含 VM 上已经安装的依赖包。
VS Code 安装包自动从仓库根读取，按 `config/code-package.json` 校验；
先用 `make code-info` 检查。把仓库和同一 `.deb` 一起复制到采集 VM。
输出包含 APT 下载的包及采集环境记录。把目录复制回构建机。
在构建机（需要 Python 3、GNU Make、dpkg-deb、dpkg-scanpackages、xorriso）执行：

```bash
python3 scripts/media.py bundle /absolute/path/to/debs
```

`offline/repo/` 必须为空或不存在；工具拒绝覆盖已有包集合。配置时固定安装整个包集合的精确版本，不仅锁定顶层包。清单包含每个包的
包名、版本、架构、大小、SHA256，以及配置脚本和包清单。它锁定实际采集结果，
不会推定与 ENV-1 一致。发生版本偏差时记录、测试、审查后才更新协作基线。

## ISO 构建

软件包之外，必须先执行 `make editor VSIX_DIR=/path/to/vsix` 与
`make workspace ACLT_DIR=/path/to/ACLt`；准备方法见 [工作流](editor-workflow.md)。


从 Ubuntu 官方渠道获取并验证原始 ISO 的 SHA256；不能仅把本地计算值当成官方认证。

```bash
python3 scripts/media.py build   --base /absolute/path/to/ubuntu-26.04.1-desktop-amd64.iso   --sha256 OFFICIALLY_VERIFIED_SHA256   --version 0.1.0-rc2
```

### Make 入口（推荐）

在仓库根目录执行；构建机还需要 GNU Make。`VERSION` 当前为 `0.1.0-rc2`，
维护发行时修改这个文件。Make 不会联网下载依赖或使用 sudo。

```bash
# 软件包采集完成后只需导入一次
make bundle DEBS_DIR=/absolute/path/to/debs

# 官方核实摘要后执行；把示例值替换为真实 64 位摘要
make iso BASE_SHA256=OFFICIALLY_VERIFIED_SHA256

# 后续候选版也可以临时覆盖版本及原始 ISO 路径
make iso VERSION=0.1.0-rc3 BASE_ISO=/path/to/base.iso BASE_SHA256=OFFICIALLY_VERIFIED_SHA256
```

把已核实的 SHA256 单独保存到 `config/base-iso.sha256`（只包含 64 位摘要），
以后执行 `make` 或 `make iso` 即可。该本地文件不提交 Git。不能用未经官方验证的
本地计算结果代替可信摘要。缺少离线包或可信摘要时，构建立即停止并指出准备步骤。

`make check` 检查工具、配置及包清单；完整 ISO 摘要在构建时验证。
`make test` 执行单元测试和 Bash 语法检查；`make iso` 先完成上述检查。
`make help` 显示所有入口。同版本 ISO 已存在时拒绝覆盖，应使用新候选版本号。
这些入口不执行装机或 ACLt 全量验收，产物仍是候选发行。

输出 `dist/zeromatrix-0.1.0-rc2-amd64.iso` 及摘要。保留原 ISO 的 BIOS/UEFI 启动信息、
原始启动入口及原内容，把 payload 加入 `/zeromatrix` 并增加默认 ZeroMatrix 安装入口。
该入口通过交互 Autoinstall 的 late-commands 完成离线系统配置，首次登录完成用户配置。构建工具重新生成 md5sum.txt，
同时保留原文件中排除启动文件的策略，并更新修改过的 GRUB 配置摘要。
镜像构建本身不执行装机；安装器仍询问磁盘与账户等所有常规问题。

## 离线安装

断开 VM 网卡或实体机网络，按 Ubuntu 安装界面选择离线安装，不下载更新或第三方驱动。
选择默认 ZeroMatrix 启动项，安装结束前自动配置环境，首次登录自动打开工作区。
如果使用原始 Ubuntu 备用入口安装，需要安装后手动挂载介质（示例 `/mnt/zeromatrix`）并执行：

```bash
sudo bash /mnt/zeromatrix/zeromatrix/provision.sh /mnt/zeromatrix/zeromatrix
mkdir -p "$HOME/workspace/ZeroMatrixTech"
bash /mnt/zeromatrix/zeromatrix/verify.sh
```

配置工具验证介质摘要，仅使用专用 file: APT 源；失败即退出。不会删除系统软件源，
也不会联网补缺失依赖。离线包集合不完整时，应回采集 VM 补包并重新发布候选版。
配置程序需 root，编译与 sanitizer 验收必须普通用户运行。

## 后续版本

提交配置与脚本，记录源码 SHA、工作区状态、基底摘要、包清单摘要及验收证据。
正式发布前保持工作区干净，把已验收镜像与清单保存到受控存储。
本工具不保证镜像逐字节可复现：时间戳等仍会变化；当前保证输入有摘要、过程可追溯。
后续可独立增加完全无人值守的部署配置、签名内部 APT 源、硬件驱动配置与自动 VM 测试。

构建器先写 `.iso.partial`，镜像写入和摘要计算完成后才改为 `.iso`。
失败时保留 partial 和日志，下一次构建拒绝覆盖该文件。构建大镜像时
需让临时目录与产物目录有足够空间；可设置 `TMPDIR=/path/to/build-tmp`。
