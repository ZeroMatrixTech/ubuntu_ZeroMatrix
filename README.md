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
