# SOLUA ERP 架构规范与迁移方案

> 状态：生效
> 最后更新：2026-10-04
> 适用仓库：a83986475/solua-erp

## 1. 当前真实状态

当前 solua-erp 不是一个纯自定义 App 仓库，而是一个包含完整 ERPNext 源码的 fork，并在同一仓库中叠加了 SOLUA 自定义功能。

当前仓库同时包含：

- ERPNext 官方源码：erpnext/accounts、erpnext/selling、erpnext/stock、erpnext/buying、erpnext/manufacturing 等。
- SOLUA 自定义模块：solua_wholesale、whatsapp_inbox、retail_settings、override、print_format、product_bundle_definition 等。
- SOLUA 自定义 hooks / setup / 前端资源。
- 部分 ERPNext 上游 CI、测试和维护文件。

因此当前仓库应定义为：

    solua-erp = ERPNext fork + SOLUA compatibility/customization layer

而不是：

    solua-erp = standalone SOLUA custom app

## 2. 目标架构

长期目标是将 ERPNext 官方代码与 SOLUA 自定义代码彻底分离：

    frappe-bench/
    ├── apps/
    │   ├── frappe/          # 官方 Frappe，尽量不修改
    │   ├── erpnext/         # 官方 ERPNext，尽量不修改
    │   └── solua_home/      # SOLUA 独立自定义 App
    │       ├── solua_home/
    │       │   ├── api/
    │       │   ├── overrides/
    │       │   ├── wholesale/
    │       │   ├── whatsapp/
    │       │   ├── retail/
    │       │   ├── printing/
    │       │   └── public/
    │       ├── hooks.py
    │       ├── modules.txt
    │       ├── pyproject.toml
    │       └── setup.py
    └── sites/

原则：

1. frappe 和 erpnext 视为上游依赖，不承载 SOLUA 新业务代码。
2. 所有 SOLUA 新功能必须进入 solua_home。
3. 优先使用 Frappe 官方扩展机制：doctype_js、doctype_list_js、override_whitelisted_methods、doc_events、extend_doctype_class、fixtures / Custom Field / Property Setter、自定义 Page / DocType / API。
4. 只有扩展机制确实无法解决时，才允许维护 ERPNext fork patch，并必须单独记录原因与上游差异。
5. ERPNext 更新不得再无条件覆盖 .github/workflows、测试文件或 SOLUA 自定义目录。

## 3. 当前目录分类

### 3.1 ERPNext 上游代码

erpnext/ 整体视为上游源码。正常情况下禁止直接加入 SOLUA 专属业务逻辑。

### 3.2 已识别的 SOLUA 自定义代码

当前至少包括：

    api/
    banking/                  # 需逐项确认是否为上游或 SOLUA 修改
    boot.py
    hooks.py
    install.py
    item_metrics.py
    override/
    print_format/
    printing/
    product_bundle_definition/
    retail_settings/
    solua_wholesale/
    tasks.py
    whatsapp_inbox/
    public/                   # 需按资源来源逐项分类
    www/                      # 需按页面来源逐项分类

这些目录在迁移完成前继续工作，但从本规范生效后：

> 禁止再新增新的顶层 SOLUA 业务目录。新代码必须进入未来独立的 solua_home App。

## 4. 迁移策略

采用渐进迁移，禁止一次性重构生产系统。

### Phase A — 冻结边界（立即生效）

- 不移动现有生产代码。
- 不改变数据库 DocType 名称。
- 不改变现有 API 路径。
- 不修改生产 numbering、权限和业务逻辑。
- 新需求只允许进入 SOLUA 自定义层。
- ERPNext 上游更新前先审查差异。

目的：先停止继续增加技术债。

### Phase B — 建立独立 solua_home App

新建独立仓库，建议：a83986475/solua-home

建议模块：

    solua_home/
    ├── api/
    ├── overrides/
    ├── wholesale/
    ├── whatsapp/
    ├── retail/
    ├── printing/
    ├── integrations/
    ├── public/
    └── patches/

### Phase C — 低风险代码先迁移

优先顺序：前端 JS/CSS → 打印功能 → API → WhatsApp → 批发模块 → Retail Settings → 自定义 Page/DocType → ERPNext override → 数据迁移和历史 patch。

每迁移一个模块必须完成开发环境安装、行为回归、版本兼容验证，再从 fork 删除对应旧代码。

### Phase D — ERPNext fork 回归纯上游

最终目标是让 apps/erpnext 尽量与官方 ERPNext 对齐，所有 SOLUA 代码由 apps/solua_home 提供。

届时升级流程应变成：

    更新 frappe
    → 更新 erpnext
    → migrate
    → 安装/更新 solua_home
    → SOLUA 回归测试

## 5. ERPNext 更新标准流程

以后更新 ERPNext 禁止直接“全部同步”。更新前必须重点检查：erpnext/、.github/、pyproject.toml、package.json、yarn.lock、requirements.txt、patches、tests。

### .github/workflows 规则

ERPNext 官方 workflow 默认不继承。release、backport、translation sync、lock threads、weekly release、Docker official build、官方 self-hosted runner CI、官方 hotfix branch automation 默认拒绝进入 SOLUA 仓库。

### ERPNext tests 规则

上游测试用于参考，但不要因为 develop 分支测试变化直接修改生产业务逻辑。顺序必须是：先判断是否由 SOLUA 改动导致，再对照 upstream 当前版本，再判断是否仅为测试预期变化，最后才考虑业务代码。

## 6. Git 分支规范

当前已有 main、develop、backup/develop-20260929。

- main：可部署、稳定。
- develop：SOLUA 集成开发。
- feature/*：单功能开发。
- hotfix/*：生产紧急修复。
- backup/*：仅临时历史备份。

不复制 ERPNext 官方 version-xx / version-xx-hotfix 分支体系，除非未来确有维护 ERPNext fork 的需求。

## 7. CI 策略

SOLUA GitHub Actions 只服务三个目的：PR 代码质量检查、SOLUA 自定义功能测试、必要时手动执行 ERPNext 兼容性测试。

不再每天替 ERPNext 官方项目跑完整 CI。

当前已完成：

- 删除 Lock Threads 定时任务。
- 删除 Weekly Release PR。
- 删除 POT regeneration。
- 删除官方 backport / release / Docker / translation workflow。
- 停止 PostgreSQL 每日测试。
- 停止 MariaDB 每日测试。

MariaDB / PostgreSQL 仅保留 PR、workflow_dispatch 或明确需要的事件触发。

## 8. 新开发强制规则

允许：在 SOLUA 自定义 App 添加功能；使用 hooks 扩展 ERPNext；新建 SOLUA API、DocType、Page、Report；用 fixtures 管理 Custom Field；用 JS/CSS 扩展标准界面。

禁止：

- 为 SOLUA 功能直接修改 erpnext/ 核心文件。
- 把新的 SOLUA Python package 随意放到仓库根目录。
- 无审核同步 ERPNext 的 .github/workflows。
- 为消除 CI 红灯修改生产业务规则。
- 把 ERPNext 官方 Secret / release bot 配置复制到 SOLUA。
- 同一个功能同时在 ERPNext core 和 SOLUA App 各维护一份实现。

## 9. 升级风险等级

| 类型 | 风险 | 建议 |
|---|---|---|
| SOLUA 独立 JS/CSS | 低 | 优先迁移 |
| API / Print | 低~中 | 第二批迁移 |
| 自定义 DocType | 中 | 保持名称不变迁移 |
| hooks / method override | 中 | 做回归测试 |
| extend_doctype_class | 中 | 核对 ERPNext 版本接口 |
| 直接 ERPNext core patch | 高 | 尽量消除 |
| DB schema 手工修改 | 很高 | 改成 migration/patch |
| ERPNext + SOLUA 混合仓库长期升级 | 很高 | 逐步退出 |

## 10. 当前决策

当前不执行大规模目录搬迁，因为现有生产系统已有较多定制，直接移动 Python module 会改变 import path，DocType module、hooks、API 路由可能同时受影响。

当前统一采用：

> 先冻结边界 → 新功能进入独立 App → 旧模块逐批迁移 → 最后让 ERPNext 恢复接近官方源码。

这是 SOLUA ERP 后续所有开发、升级和 CI 清理的统一架构原则。
