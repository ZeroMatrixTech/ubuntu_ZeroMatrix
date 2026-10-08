# ZeroMatrix 开发工作区

从应用菜单打开 **ZeroMatrix Development**，或终端执行 `zeromatrix-code`。
初次打开请检查内容后确认 VS Code Workspace Trust，以允许构建和调试。

- `Ctrl+Shift+P` → `Tasks: Run Task`：选择 C++ / Python / Rust 编译、运行和测试任务。
- 调试面板选择 C++: GDB、Python: debug 或 Rust: LLDB，再按 F5。
- ACLt 日常开发：`ACLt: daily workflow`；查看状态：`ACLt: status`。
- 环境升级或交接：`ACLt: full acceptance` 和 `ACLt: force evidence`。
- `System: verify toolchain` 记录普通用户的工具链验收证据。

ACLt 是安装介质记录的独立 Git 副本，初始开发分支 `dev/local`。
离线提交前自行设置 Git 用户名与邮箱。团队同步可导入审核过的 Git bundle；在线更新另行配置远端。
源码目录和 `.local/state/zeromatrix` 中的失败日志必须保留；示例成功不代替 ACLt 全量验收。
系统基线和扩展版本由镜像维护，不在离线机器上自动升级。
