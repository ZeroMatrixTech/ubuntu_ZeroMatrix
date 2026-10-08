# 候选发行验收

- 原始 ISO 的官方 SHA256 已核实；包清单、源码 SHA、工作区状态已留存。
- 包集目标是 Ubuntu 26.04.1 / amd64；Cargo 精确版本已记录。
- 新建 VM 网卡断开，Ubuntu 安装和离线配置成功；日志有完整退出码。
- 普通用户运行 `verify.sh`：C++17、Rust、Python、ASan/UBSan/LeakSanitizer 均成功。
- 实际工具版本与 ENV-1 逐项比较；偏差有记录和审查，不能用更高版本替代验证。
- 从审核过的 ACLt 离线源码副本根目录执行：

```bash
bash scripts/run-singlehost.sh
python3 scripts/aclt-flow.py run --force
```

保存完整输出、退出码、commit SHA、工作区状态及资源信息。保留失败证据，
不关闭 LeakSanitizer 后报告完整通过。原项目环境规范保持原位，不由系统项目修改。

分别验证 UEFI / BIOS VM；实体机另验证显示、磁盘、网卡、休眠等需要支持的功能。
Secure Boot 必须在启用状态另行测试；保留启动信息不等于通过 Secure Boot 验证。
没有测量证据前不声明最低硬件需求；VM 验收不自动等于实体机支持。
许可证与第三方分发义务完成后才能正式发行。未完成项目明确列为 pending。

## 编辑器与安装集成

- 默认 ZeroMatrix 安装入口自动执行 late-commands，失败会阻止完成安装。
- 首次登录断网，扩展全部来自 VSIX，安装版本与清单一致，无后端联网下载。
- 新账户获得个人 ACLt 副本，SHA 与介质一致；再次初始化不会覆盖用户修改。
- C++ / Python / Rust 补全及 F5 调试分别成功，Rust 标准库分析可用。
- 示例构建和测试成功，ACLt 任务入口执行全量流程并保留真实输出及退出码。
- 桌面入口、首次登录失败提示和重试行为验证通过。
