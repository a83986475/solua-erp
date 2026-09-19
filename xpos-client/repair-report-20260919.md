# xPos 修复执行报告（2026-09-19）

## 范围

- 工作区：`xpos-client/frontend`
- 生产站点：`erp.solua.one`（qq）
- 未操作 WSL；未修改生产库存、价格或权限。

## 已完成

### Web xPos Report 417

生产 `frontend/src/views/OrdersView.vue` 的 Sales Invoice 列表曾请求
`custom_fbr_invoice_no` 和 `fbr_invoice_number`。当前生产元数据不允许这两个字段，导致
`frappe.client.get_list` 返回 417。

已在生产文件修改前创建备份，并定点移除这两个列表字段；未修改 Frappe 核心、权限或业务数据。
qq 上的 xPos 专用前端构建成功，资产通过 `sites/assets/xpos` 提供，站点缓存已清理，Frappe Web
进程已重启。公开入口返回 HTTP 200，生成的 OrdersView 资源中不再请求 `fbr_invoice_number`；保留的
`custom_fbr_invoice_no` 仅用于已有发票详情赋值，不属于列表查询字段。

`bench build --app xpos` 另行尝试时被服务器 Node `20.20.2` 与 Frappe 要求 `>=24` 拒绝；没有升级运行时，
因为 xPos 专用构建已经成功。

### 本地库存同步与商品列表

- Bin 同步游标增加版本标记；版本变化时安全重置增量游标，避免旧游标跳过生产库存。
- Bin upsert 同步写入 `stock_cache`，删除旧 Bin 时同步清理对应缓存。
- 库存查询优先使用 ERP Bin 的 `actual_qty`，缓存仅作回退。
- 商品目录使用 `has_variants = 0` 过滤模板物料，不硬编码 SKU；因此按销售价格/可售变体规则继续由现有查询决定。
- 本地安装包已更新为新的 `app.asar`。

## 备份

本机新备份目录：
`C:\xpos\backups\xpos-20260919-xpos-fix`

- 旧 `app.asar`：`app.asar.pre-xpos-fix-20260919`
- 本地配置：`db-config.json.pre-xpos-fix-20260919`、`xpos-frontend-db-config.json.pre-xpos-fix-20260919`
- 源码 schema：`schema.sql.source.pre-xpos-fix-20260919`
- 新安装包 SHA-256：`BAA1FE20B6001BF15922CD9F4A68B657AF119288E46F57F8052FF4439B01110A`

qq 站点备份已由 bench 完成，包含 site_config、数据库、files 和 private-files；另有 Web xPos 资产备份：
`/home/frappe/frappe-bench/sites/erp.solua.one/private/backups/xpos-web-pre-report-417-20260919.tar.gz`

## 验证

- `yarn test:run`：14 个测试文件，360 个测试通过。
- `yarn typecheck`：通过。
- `yarn build:electron`：通过。
- Electron 目录构建：通过。
- 新构建产物与 `C:\xpos\resources\app.asar` SHA-256 一致。
- qq `https://erp.solua.one/xpos/`：HTTP 200。

## 待人工验收

用已登录的 ERP 账号打开 qq 的 xPos：进入 Reports，打开 Sales Invoice 相关报表，确认不再出现 417；
重启本地 xPos 后执行一次同步，确认代表窗帘 SKU 库存不再显示缺货，并确认模板物料不出现在商品列表。
