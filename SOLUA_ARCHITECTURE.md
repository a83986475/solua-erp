# SOLUA ERP 架构规范与迁移方案

> 状态：生效  
> 最后更新：2026-10-17  
> 适用仓库：`a83986475/solua-erp`

## 1. 当前真实状态

当前 `solua-erp` 是 **完整 ERPNext fork + SOLUA 自定义层**，不是纯独立自定义 App。

目标架构：

```text
frappe-bench/
├── apps/frappe/       # 官方
├── apps/erpnext/      # 官方，尽量不改
└── apps/solua_home/   # SOLUA 独立自定义 App
```

## 2. 核心原则

1. Frappe / ERPNext 视为上游依赖。
2. SOLUA 新业务功能进入独立 `solua_home`。
3. 优先使用 hooks、doc_events、doctype_js、extend_doctype_class、override_whitelisted_methods、fixtures。
4. 不再把新的 SOLUA 业务逻辑直接写进 ERPNext core。
5. ERPNext 更新必须人工审查 `.github/workflows`，禁止无条件同步上游 CI。
6. 现有生产定制采用渐进迁移，禁止一次性大搬家。

## 3. 迁移阶段

### Phase A — 冻结边界

- 不移动现有生产代码。
- 不改数据库 DocType 名称。
- 不改现有 API 路径。
- 新功能只进入 SOLUA 自定义层。

### Phase B — 独立 App

目标独立仓库/应用：`solua_home`。

### Phase C — 渐进迁移

建议顺序：

```text
JS/CSS
→ printing
→ API
→ WhatsApp
→ wholesale
→ retail
→ DocType/Page
→ overrides
→ install/patch
```

### Phase D — ERPNext 回归接近官方

最终让 `apps/erpnext` 尽量接近官方源码，SOLUA 功能由 `apps/solua_home` 提供。

## 4. Git / CI 规则

- `main`：稳定、可部署。
- `develop`：集成开发。
- `feature/*`：功能开发。
- `hotfix/*`：生产紧急修复。

SOLUA GitHub Actions 只服务：

1. PR 代码质量检查。
2. SOLUA 自定义功能测试。
3. 必要时手动 ERPNext 兼容测试。

不再每天替 ERPNext 官方项目运行完整 CI。

## 5. 禁止继承的 ERPNext/Frappe 官方 workflow

默认禁止：

- Lock threads
- POT regeneration
- Weekly release PR
- Backport
- Asset release
- Docker official release trigger
- Semantic release
- Release notes automation
- Hotfix translation sync
- 官方 self-hosted runner daily CI

MariaDB / PostgreSQL 测试只能保留 PR、手动或明确业务事件触发，不允许默认每日 cron。

## 6. 2026-10-17 CI 回归事件

此前 2026-10-04 已完成过 CI 清理，但随后当前 `main` 走到了与该清理历史分叉的另一条提交链。

结果：

- 被删除的 `lock.yml` 等 workflow 重新出现在 `main`。
- MariaDB / Postgres 的 daily schedule 重新恢复。
- 2026-10-14 起再次出现自动失败邮件。

这不是 GitHub 自动恢复文件，而是 **Git 历史分叉 / 旧分支 checkpoint 覆盖当前 main 状态** 导致。

## 7. 2026-10-17 已执行修复

已重新删除以下 workflow：

```text
lock.yml
generate-pot-file.yml
initiate_release.yml
backport.yml
build-and-commit-assets.yml
docker-release.yml
release.yml
release_notes.yml
run-hotfix-translation-sync.yml
sync-hotfix-translations.yml
```

并再次移除：

```text
server-tests-mariadb.yml -> schedule/cron
server-tests-postgres.yml -> schedule/cron
```

新增：

```text
.github/workflows/solua-ci-policy.yml
```

该 Policy Guard 会：

- 在 main/develop 的 workflow 文件发生变更时运行。
- 在相关 PR 中运行。
- 拒绝上述 ERPNext/Frappe 官方维护 workflow 被重新加入。
- 拒绝任何未经审核的 `schedule:` / `cron:`。

## 8. 防止第三次复发

以后生产 checkpoint / ERPNext upstream sync 必须遵守：

1. **不得用旧分支整体覆盖 main。**
2. checkpoint 前先基于当前 main rebase/merge。
3. 不允许从 upstream 无审核恢复 `.github/workflows`。
4. 如确需新增定时任务，必须先更新 Policy Guard 并记录业务理由。
5. 每次 ERPNext 更新后检查：
   - `.github/workflows`
   - `erpnext/`
   - `tests/`
   - `pyproject.toml`
   - `package.json`
   - `yarn.lock`
6. 生产自定义代码 checkpoint 不得把旧 CI 配置带回 main。

## 9. 当前结论

当前采用：

> 先保护 main 与 CI 边界 → 新功能进入独立 SOLUA App → 旧代码渐进迁移 → ERPNext 最终恢复接近官方源码。

CI Policy Guard 是当前仓库防止上游定时 workflow 再次“复活”的第一道保护。
