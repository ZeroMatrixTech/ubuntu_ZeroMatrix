# Current online baseline / 当前在线基线

0.2.x defaults to target-side downloads of VS Code, Marketplace extensions and the configured company project. These binaries and project history are excluded from new ISO payloads. Downloaded components retain their original licenses. Original Ubuntu ISO chunks remain Ubuntu/third-party material and are not Apache-2.0. Public redistribution still requires Ubuntu branding and component/source compliance review. Historical offline policy below applies to 0.1.x artifacts only.

0.2.x 默认由目标电脑在线获取 Code、扩展和项目，新 ISO 不包含这些二进制或项目历史。下载组件保留原许可；Ubuntu 原始镜像分块仍须遵守原有许可、商标及源码提供义务。历史离线政策仅适用于旧产物。

---

# 许可与发行政策 / Licensing and distribution policy

## 项目许可 / Project license

本项目有权授权的原创构建代码、Makefile、脚本、配置、工作流模板、测试及项目文档采用 **Apache License 2.0**，SPDX 标识为 `Apache-2.0`，另有明确许可声明的文件除外。未经修改的官方英文全文见 [LICENSE](../LICENSE)，中文阅读说明见 [LICENSE.zh-CN.md](../LICENSE.zh-CN.md)。英文全文为适用许可条款；中文说明不修改该许可。

Original build code, Makefile, scripts, configuration, workflow templates, tests and project documentation that this project is entitled to license are licensed under **Apache License 2.0**, SPDX `Apache-2.0`, unless explicitly marked otherwise. See [LICENSE](../LICENSE) for the unmodified official English terms and [LICENSE.zh-CN.md](../LICENSE.zh-CN.md) for a Chinese reading guide. The English license governs; the guide does not modify it.

## 授权边界 / Scope boundaries

本许可不重新授权 Ubuntu、Debian 软件包、官方 VS Code、VSIX 扩展、第三方代码、外部参考材料或随附公司项目。它们保留各自版权、许可证和通知。将其下载、缓存、安装或封装到 ISO，不产生额外分发权利。名称、标志及商标也不因本项目许可而获得授权。

This license does not relicense Ubuntu, Debian packages, official VS Code, VSIX extensions, third-party code, external reference materials or bundled company projects. Their copyrights, licenses and notices remain applicable. Downloading, caching, installing or packaging them in an ISO does not grant additional redistribution rights. Names, logos and trademarks are not licensed by this project license.

## 当前镜像 / Current image

当前包含官方 VS Code、C/C++ 扩展和 Pylance 的候选镜像按公司内部部署设计，不宣称可以公开再分发。对外发布须逐项取得适用授权，或替换、移除不允许公开分发的组件；各组件内部使用也须遵守其条款。将镜像交付给外部组织时，不能自动沿用内部部署结论。参见 [编辑器工作流](editor-workflow.md)。

The current candidate image containing official VS Code, the C/C++ extension and Pylance is prepared for internal company deployment; public redistribution is not claimed to be authorized. External releases require applicable authorization for each component or replacement/removal of components that cannot be publicly redistributed. Internal use remains subject to each component's terms. Delivery to an external organization must not automatically be treated as internal deployment. See [editor workflow](editor-workflow.md).

这是一项镜像发行政策，不是对 Apache-2.0 原创代码添加“仅限内部使用”限制。公众仍可以依照 Apache-2.0 使用、修改和分发被授权的构建源码。

This is an image distribution policy, not an internal-use-only restriction added to the original Apache-2.0 code. The licensed build source remains available for use, modification and distribution under Apache-2.0.

## ACLt 及内部软件 / ACLt and internal software

当前镜像含有 ACLt Git bundle。其代码及参考实现已采用 Apache-2.0，但其声明明确不自动覆盖协议规范、项目文档、研究论文、名称、商标或兼容性声明。本项目不扩大该授权。公开发行前须确认 bundle 中实际版本、历史内容和每类工件的授权，或排除未获授权公开分发的材料。

The current image includes an ACLt Git bundle. Its code and reference implementations use Apache-2.0, but its declaration explicitly does not automatically cover protocol specifications, project documentation, research papers, names, trademarks or compatibility statements. This project does not expand that grant. Before public release, verify the actual bundled version, history and authorization for each artifact category, or exclude materials lacking public redistribution authorization.

其他内部软件保留其原有许可和访问政策。不得通过本仓库的根许可证，推定它们已经获得开源授权。

Other internal software retains its existing licenses and access policies. This repository's root license must not be interpreted as granting open-source permission for that software.

## 发行维护要求 / Release maintenance requirements

发行时保存完整组件清单、版本、来源、摘要、适用许可证及版权通知，覆盖基础系统和新增内容。保留包内版权文件及第三方通知；按各许可证要求提供对应源码、修改记录、构建材料或合规的源码提供方式。离线包采集和哈希清单不能替代这些义务。对 Ubuntu 衍生镜像，还须单独核查名称、标志及 Canonical 相关政策，同时尊重各组件自身许可证授予的权利。

For each release, retain a complete component inventory, versions, provenance, hashes, applicable licenses and copyright notices covering both the base system and additions. Preserve packaged copyright files and third-party notices; supply corresponding source, change notices, build materials or compliant source offers as required by each license. Offline acquisition and hash manifests do not replace these obligations. Ubuntu-derived images also require separate review of branding and Canonical policies while respecting rights granted by individual component licenses.

## 贡献与归属 / Contributions and attribution

贡献者须有权提交并授权所贡献内容，保留已有第三方声明，不得提交未经授权的公司内部材料。除明确另行声明或独立协议外，有意提交供本项目收录的贡献按 Apache-2.0 第 5 条处理。具体版权声明应使用真实权利人；本政策不将所有贡献的版权转移给公司。

Contributors must be entitled to submit and license their contributions, preserve existing third-party notices and avoid submitting unauthorized internal company materials. Unless explicitly stated otherwise or governed by a separate agreement, contributions intentionally submitted for inclusion are handled under section 5 of Apache-2.0. Copyright notices must identify the actual rights holders; this policy does not assign all contributor copyrights to the company.

## 官方参考 / Official references

- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [VS Code product license](https://code.visualstudio.com/license)
- [VS Code FAQ: extensions and Marketplace](https://code.visualstudio.com/docs/supporting/faq)
- [Canonical intellectual property policy](https://canonical.com/legal/intellectual-property-policy)
- [GNU license FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)

本文记录许可范围与发行政策，不是所有镜像组件已完成合规审查的证明。

This document records licensing scope and distribution policy; it is not certification that every image component has completed compliance review.
