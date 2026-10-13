# 当前候选发行验收（0.2.x）

使用[构建与安装规范](build-and-install.md)。当前版本读根目录 `VERSION`；vm 与 physical 必须分别留存验收记录。2026-10-09 的 VirtualBox 安装反馈仅覆盖已记录的安装路径，未列出的项目保持 pending。

## 构建与来源

- 记录源码提交、工作区状态、VERSION、PROFILE、基底摘要和实际构建命令。
- 执行 `make test`、`make base-check`，构建后执行 `make verify-iso`；保存 ISO、摘要与 manifest。
- 记录缓存输入与 `ROOTFS_BUILD`，保留失败日志。测试或封装成功不代表安装成功。

## 安装与首次登录

- 新建目标 VM，全程联网安装；使用对应 profile，记录启动入口、固件模式及手动参数调整。
- 安装完成并移除光盘后启动系统；确认 `/var/log/zeromatrix/provision-complete`，保存 `provision.log`。
- 首次登录联网完成扩展与指定 ACLt 提交下载；保存首次登录日志及 `extensions.txt`。
- 核对个人 ACLt 副本的提交与 `config/project-online.json`，记录实际工具版本及其与 ACLt 环境规范的偏差。
- 普通用户执行 `bash /opt/zeromatrix/offline/verify.sh`，保存输出与退出码。
- 分别验证 C++ / Python / Rust 补全和 F5；验证初始化失败提示、联网重试及保留已有用户文件的行为。

## ACLt 验收

从目标系统的个人 ACLt checkout 根目录，以普通用户执行：

```bash
bash scripts/run-singlehost.sh
python3 scripts/aclt-flow.py run --force
```

保存输出、退出码、commit SHA、工作区状态及资源信息。保留失败证据，不关闭 LeakSanitizer 后报告完整通过。原项目环境规范由 ACLt 仓库维护。

## 平台与发布

BIOS、UEFI、启用 Secure Boot 的 VM、physical 实体机和 WSL2 构建分别验收。实体机另检查显示、磁盘、网卡及计划支持的电源管理功能。未测试项目标记 pending；VM 成功不推定实体机兼容。

按[许可说明](licensing.md)完成分发审查后才能正式发行。记录不支持项、已知问题与剩余风险。0.1.x 离线输入证据见[历史候选输入记录](candidate-inputs.md)，不作为当前在线安装的验收结论。
