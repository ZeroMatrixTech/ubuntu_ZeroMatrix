# ZeroMatrix 开发工作区

从应用菜单打开 **ZeroMatrix Development**，或终端执行 `zeromatrix-code`。
初次打开请检查内容后确认 VS Code Workspace Trust，以允许构建和调试。

- `Ctrl+Shift+P` → `Tasks: Run Task`：选择 C++ / Python / Rust 编译、运行和测试任务。
- 调试面板选择 C++: GDB、Python: debug 或 Rust: LLDB，再按 F5。
- ACLt 日常开发：`ACLt: daily workflow`；查看状态：`ACLt: status`。
- 环境升级或交接：`ACLt: full acceptance` 和 `ACLt: force evidence`。
- `System: verify toolchain` 记录普通用户的工具链验收证据。

ACLt 是安装介质记录的独立 Git 副本，初始开发分支 `dev/local`。
提交前自行设置 Git 用户名与邮箱。当前在线安装从配置 URL 获取固定提交并设置 `origin`；后续 fetch、合并和升级由开发者明确执行。历史离线安装可导入审核过的 Git bundle。
源码目录和 `.local/state/zeromatrix` 中的失败日志必须保留；示例成功不代替 ACLt 全量验收。
系统工具在安装阶段联网获取，扩展在首次登录按介质配置的版本下载；初始化完成后不会自动迁移工作区或刷新安装基线。
