# xPos 客户端诊断与修复记录

> 历史记录按时间排列；这里的版本号、安装包和状态仅代表对应日期，不代表当前运行版本。当前安装基线见 [`baseline-manifest.md`](baseline-manifest.md)。不记录密码、API Secret 或可用于认证的凭据。

## 2026-09-17：只读诊断

### 运行版本与身份

- 当时运行 `C:\xpos\X POS.exe`，版本 1.0.9，加载 `C:\xpos\resources\app.asar`；SHA-256：`4CB3A05B5BA8F1BCD2034EF93D880EF3BDD534DFF9131860489B5DBB8C7063F5`。与 2026-09-17 核对包一致；删除检查分页/父子表修复是否包含在包中未确认。
- 截图中的 POS Profile、Company 和 Opening Cash Balance 不能证明收银员身份。源码从 `last_logged_user` 读用户并查询本地 `pos_users`；当时真实账号未确认。本地数据库服务账号、ERP 同步账号、收银员账号及 Hub/Till 角色是不同身份。
- Open Shift 页面表示本地已认证用户没有打开班次，不是登录页；当时未点击开班，未创建业务记录。

### 当时的问题与未确认项

- Setup、Login、Open Shift、Settings 源码没有可见语言选择器；翻译未命中时回退英文。是否属于版本设计或回归未确认。
- 截图没有展示商品卡，不能据此确认图片失败。图片来自本地商品记录的 `image`；未完成字段→URL→只读 HTTP 状态检查，故图片为空、404、403 或网络问题均未确认。
- 日志显示子表删除检查多次 403、POS Users 404、Companies 525。403 的实际端点/响应和权限原因未确认；404 不能单凭名称判断 DocType 缺失；525 不能单凭状态判断证书过期。
- 当时旧状态曾有 `pendingPushCount=0`，但没有本轮新鲜的待上传交易数量；不得把旧值当作当前状态。源码显示队列 `pending_invoices`、`pending_purchases` 可含 `pending`、`syncing`、`failed`、`dead_letter`。
- 最小诊断应读取真实请求路径、DocType、响应体和权限；确认 `last_logged_user`；选定失败商品检查图片链路；分别检查源站 TLS。不得仅凭截图或错误码猜根因。

## 2026-09-18：本地 xPos 客户端修复

### 范围和改动

- 只操作 Windows 本地客户端和隔离测试副本；未操作 WSL，也未更改 qq 上的 ERP 代码、权限或业务数据。源码基线为 `kodlyft/xpos` 的 develop `67457ca89e6d61077abad0df532cab473d61e356`，保留 v1.0.9 构建线。
- 删除检查复用各资源的授权 `pullMethod` 并分页：子表使用 `xpos.api.sync.get_child_table_data`，POS Users 使用 `xpos.api.auth.get_pos_users`；保留安全阈值和删除日志。
- Companies GET 最多重试两次；最终失败日志增加资源、端点、URL、状态码和截短响应，不关闭 TLS 校验。
- 商品图同步兼容 `custom_swatch_image`，主进程认证下载并缓存，渲染层优先读取缓存。
- 增加本地语言保存/翻译加载和用户菜单、开班页语言选择器；Open Shift 显示已认证账号并提供显式切换，不因没有 open shift 自动强制回登录页。

### 验证与人工验收

- 类型检查、357 项测试、Electron 构建和打包通过；隔离 Windows MariaDB/mock 环境覆盖语言持久化、账号切换、离线图片缓存、删除安全、端点选择与 525 重试。
- 隔离测试队列为 0，失败同步未误删记录；测试服务和进程停止，隔离证据目录保留。
- 当时仍待：使用真实测试 API 凭据做一次完整增量/删除同步；用真实商品检查图片；在干净测试机安装 Hub/Till 包。
- 原始包及变更后包、安装包、隔离测试路径和 SHA-256 记录于 2026-09-18 的历史提交中。敏感配置值未读取或记录。

### 2026-09-18 同步契约 follow-up

- 定价规则改用 qq 已有的 `xpos.x_pos.api.pricing_rules.get_active_pricing_rules`，归一化返回值供离线定价引擎使用。
- Exchange Rates 配置值误含 `date desc`，而请求构造又追加排序，导致 `date desc asc`；修为字段名 `date`。
- Modes of Payment 列表移除生产不存在的 `pos_tender_currency` 字段，继续使用已有发票币种回退。
- 类型检查、358 项测试、Electron 构建和打包通过；该 follow-up 未修改 qq。详细包版本和备份路径可从原始 Git 提交还原。

### 2026-09-18 备份与构建证据

- 基线留档目录：`C:\xpos\backups\xpos-20260918-baseline\`。原始 v1.0.9 ASAR 为 10,267,328 bytes，SHA-256 `4CB3A05B5BA8F1BCD2034EF93D880EF3BDD534DFF9131860489B5DBB8C7063F5`；`schema.sql` SHA-256 `FF036ED8F610BA3CD10BC80C0CB7A4F199F238035E4F7162896D3C2E7EE387DD`。DB 配置只留非敏感校验值，未记录密码。
- 首轮修复包 `C:\xpos\resources\app.asar`：10,585,579 bytes，SHA-256 `BDA52E10F0F394F24AABCEE420B4C11567934861153E5CE45F5AD6B8BCC6E957`；对应 EXE SHA-256 `538F2184A510EEF9FFA271C6F5FEFCC5184059BF212540E18565D7B0D324E69A`。Hub/Till 包目录为 `C:\xpos\builds\xpos-repair-20260918\`，ZIP SHA-256 分别为 `702EF515AD9E1C18D5424A101385566D42377406C7E56AE1D2E23E8ED2F07D30`、`DF5CD54F1B824A36BCD640D9B98E0896D29E6BEDE54DF0315A51C150B736C7A2`。
- follow-up 回滚副本在 `C:\xpos\backups\xpos-20260918-followup-sync\app.asar.pre-followup-20260918`；安装包 SHA-256 `2B362E93E15C7BF6E29473464C404BA8AD0DB9F10D16F2D62D509BAB86A8D548`，Hub/Till ZIP SHA-256 分别为 `D81F7D064430399F4F7D53459E63C4E4F7BDF1280E7DFB9C1AA93FABD75BD34B`、`0F1F0B9F70CEE3F2466A319E19C7526695645F2075DC9F51E6C036C230F751D2`。替换时客户端进程曾被明确关闭；数据库配置密码未解密或输出。

## 2026-09-19：Web xPos 与本地库存修复

### Web xPos Report 417

- Sales Invoice 列表曾查询生产元数据不存在的 `custom_fbr_invoice_no` 与 `fbr_invoice_number`，触发 `frappe.client.get_list` 417。
- 仅从列表查询移除不兼容字段，不改 Frappe 核心、权限或业务数据；保留发票详情中仍使用的兼容字段。xPos 专用前端构建成功并清缓存/重启 Web；当时入口返回 HTTP 200，生成的 OrdersView 资源不再请求 `fbr_invoice_number`。
- `bench build --app xpos` 曾因服务器 Node 20.20.2 不满足要求的 Node >=24 而失败；没有升级服务器运行时，因为专用构建已成功。

### 本地库存同步与商品列表

- Bin 同步游标增加版本标记，版本变化时重置增量游标；upsert 同步更新 `stock_cache`，删除 Bin 时清理对应缓存。
- 库存展示优先使用 ERP Bin 的 `actual_qty`、缓存仅回退；商品目录用 `has_variants = 0` 排除模板，不硬编码 SKU。
- 当时报告 `yarn test:run` 360 项、类型检查、Electron 构建通过，生成包与本机安装 `app.asar` SHA-256 一致；qq `/xpos/` 返回 200。
- 人工验收仍待：用已登录账号打开 Reports 确认 417 消失；重启本地 xPos 同步后核实代表窗帘库存及模板过滤。没有把 HTTP 200 等同于完整 UI 验收。
- 本地备份在 `C:\xpos\backups\xpos-20260919-xpos-fix`；该次安装包 SHA-256 `BAA1FE20B6001BF15922CD9F4A68B657AF119288E46F57F8052FF4439B01110A`。qq Web xPos 资产旧版另存于 `sites/erp.solua.one/private/backups/xpos-web-pre-report-417-20260919.tar.gz`；报告当时确认 bench 站点备份包含 site config、数据库和公开/私有文件。
