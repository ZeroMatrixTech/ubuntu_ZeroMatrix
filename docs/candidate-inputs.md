# 0.1.0-rc2 候选输入验收

日期：2026-10-08。用途：公司内部开发安装介质。

## 已完成

- 原始 Ubuntu ISO SHA256：`601e30fbf5d97759367c632e2c33630665039b7e2158fd068403da3ccf1bda1f`。
  与官方下载清单一致；`gpgv` 用系统 Ubuntu 归档公钥验证了清单签名。
  签名 key fingerprint：`843938DF228D22F7B3742BC0D94AA3F0EFE21092`。
- VS Code `.deb`：`1.140.0-1790759618` amd64，与已记录本地 SHA256 一致。
- 333 个 Debian 包：经 Ubuntu 官方签名索引解析并下载，保存完整版本、来源和 SHA256。
- 从原始 ISO 的 `minimal.standard.squashfs` 提取实际 dpkg 状态，在只含 file: 软件源、
  独立 APT 状态目录的环境执行固定包集合模拟安装。禁止移除包，退出码 0。
  初次发现的反向依赖冲突已补齐，并保留失败日志。
- 7 个 VSIX：在无网络接口的用户命名空间，使用原始 `.deb` 解包的 VS Code 1.140
  实际安装成功；安装后的版本列表与清单一致。
- CodeLLDB 使用作者发布的完整 linux-x64 VSIX，与作者 GitHub Release asset SHA256 一致。
- 19 项构建与输入测试、Bash 语法检查通过。
- 原始 Code 包安装的 rust-analyzer 与 CodeLLDB 后端 CLI 启动检查通过；
  debugpy 1.8.20 在 Python 3.14.4 下可导入。
- 普通用户断网命名空间内，从离线种子创建的 ACLt 副本执行
  `bash scripts/run-singlehost.sh` 和 `python3 scripts/aclt-flow.py run --force`，均退出 0。
  完整流程包含 20 次 sanitizer 运行。这里使用宿主机工具链，不能替代安装后验收。

| 扩展 | 固定版本 |
|---|---|
| ms-vscode.cpptools | 1.34.4 |
| ms-python.python | 2026.8.0 |
| ms-python.debugpy | 2026.6.0 |
| ms-python.vscode-pylance | 2026.4.1 |
| ms-python.vscode-python-envs | 1.38.0 |
| rust-lang.rust-analyzer | 0.3.3073 |
| vadimcn.vscode-lldb | 1.12.3 |

Python 扩展包含 extensionPack，debugpy 则依赖 Python。打包时要求两类成员完整，
安装顺序只遵循真正的 extensionDependencies，并关闭 CLI 的在线 extensionPack 拉取。
VSIX 平台属性同时支持 Identity.TargetPlatform 和旧式 Property 字段。

## 验收边界

以上是输入完整性、离线依赖解析和编辑器扩展安装证据；模拟安装不会执行包的 maintainer scripts。
命名空间测试未执行完整 Ubuntu 安装器、GNOME 首次登录、语言服务交互或 F5 调试。
测试扩展 CLI 在隔离命名空间中临时使用 `--no-sandbox`；发行配置对普通用户保留默认沙箱。
完整断网装机、BIOS / UEFI / Secure Boot、实体机兼容及 ACLt 全量验收仍须按验收清单执行。
当前候选不是正式发布或生产就绪结论；自身许可证及公开分发方案仍待决定。

原始日志保存在本地 `artifacts/input-validation`，原始信任材料位于 `offline/trust`，
镜像附带各输入的 SHA256。正式发行应在已提交、干净的工作区重建并保存装机证据。
