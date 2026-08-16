# 会话总结：ERPNext v16 开发环境搭建 + 服务器定制开发

> 生成时间: 2026-07-17 | 最后更新: 2026-08-06 | 供下个对话引用

---

## 一、已完成的工作

### 第一会话：本地 WSL2 开发环境搭建

| 任务 | 状态 |
|------|------|
| WSL2 + Ubuntu 24.04 开发环境 | ✅ |
| bench 5.31.0 安装（通过 pipx） | ✅ |
| Python 3.14（deadsnakes PPA） | ✅ |
| Node.js 24（通过 nvm） | ✅ |
| MariaDB + Redis 配置 | ✅ |
| ERPNext v16（version-16 分支）安装到站点 `dev.localhost` | ✅ |
| 创建自定义 App `solua_home` | ✅ |
| 安装 `solua_home` 到 dev.localhost | ✅ |
| 编写 `start.sh`（一键启动脚本，解决 Procfile schedule 问题） | ✅ |
| 编写 `setup-erpnext.sh`（一键安装脚本） | ✅ |
| 编写 `ERPNext 定制开发操作手册.md`（含全部踩坑记录） | ✅ |

### 第二会话：服务器翻译修复（初始尝试）

| 任务 | 状态 |
|------|------|
| 通过 `ssh qq` 连接服务器 | ✅ |
| 构建 `bench build` 并重启 supervisor | ✅ |
| 翻译未生效（旧 .mo 文件不含中文，只有 2006 字节英文） | ❌ 第三会话修复 |

### 第三会话：完整修复 + 功能完善

| 任务 | 状态 |
|------|------|
| **翻译修复（真正解决）** | ✅ |
| 删除旧 .mo 文件后重新编译 | ✅ |
| .mo 从 2KB（英文）到 1.27MB（中文 8418 条） | ✅ |
| 中文翻译在服务器上生效 | ✅ |
| **服务器 Node 24 切换** | ✅ |
| nvm + Node v24.18.0 已安装 | ✅ |
| 更新 supervisor.conf 添加 PATH 环境变量 | ✅ |
| node-socketio 进程使用 Node 24 | ✅ |
| 更新 frappe 用户 .bashrc 默认 PATH | ✅ |
| **solua_home 部署到服务器** | ✅ |
| 打包传输并解压到 apps 目录 | ✅ |
| 注册到 apps.txt + apps.json | ✅ |
| 创建 Python symlink | ✅ |
| install-app + migrate 执行成功 | ✅ |
| **完善中文翻译** | ✅ |
| zh.csv 从 48 条扩充到 150+ 条 | ✅ |
| install.py 同步更新 | ✅ |
| 添加错误处理 try/except | ✅ |
| **Git 初始化并推送到 GitHub** | ✅ |
| 创建 .gitignore | ✅ |
| 推送到 https://github.com/a83986475/solua-erp.git（原 erpnext-apps，后改名） | ✅ |

### 第四会话：部署验证

| 任务 | 状态 |
|------|------|
| **模块导入验证** | ✅ `import solua_home` 成功 |
| **hooks.py 注册检查** | ✅ doc_events 全部正确注册 |
| **类重写检查** | ✅ extend_doctype_class 配置正确 |
| **App 文件完整性** | ✅ 18 个文件齐全 |
| **数据库翻译** | ✅ 105 条中文翻译已导入 |
| **自定义字段** | ✅ Customer 有 5 个自定义字段 |
| **数据库日志** | ✅ 无错误，仅正常 DDL |
| **Supervisor 状态** | ✅ 所有进程 RUNNING |

### 第五会话：窗帘多色方案 + 自定义 POS + 功能完善（本次）

| 任务 | 状态 |
|------|------|
| **窗帘多色方案设计** | ✅ |
| Template + Variant 数据模型讨论 | ✅ |
| 条码策略方案 A（条码放模板，扫码弹窗选颜色） | ✅ |
| 颜色用葡语属性值（Branco/Preto/Azul...） | ✅ |
| **自定义 POS 扫码颜色选择器** | ✅ 已设计（未编码） |
| 后端 API 设计：`scan_barcode_for_pos()` | ✅ 伪代码已写 |
| 前端 JS 设计：`pos_custom.js`（onScan 重绑定 + 颜色弹窗） | ✅ 伪代码已写 |
| **创建客户 ValueError 修复** | ✅ |
| `after_customer_created` 中子表过滤语法修正 | ✅ `frappe.get_all("Contact", filters=[[...], [...]])` |
| Walkin 客户提前返回跳过联系人创建 | ✅ |
| **`is_billing_contact` 列修复** | ✅ |
| MySQL 报错：`Unknown column 'tabContact.is_billing_contact'` | ✅ 已创建 Custom Field |
| 修复方式：`frappe.get_doc({"doctype": "Custom Field", ...})` | ✅ |
| **测试数据删除** | ✅ |
| CR-001 模板 + 6 个颜色 Variant 全部删除 | ✅ |
| **Variant 自动价格同步** | ✅ |
| `api/stock.py` — `auto_create_item_price()` 函数 | ✅ |
| `hooks.py` — `Item.after_insert` 钩子注册 | ✅ |
| 模板设标准价 → 创建 Variant → 自动生成 Item Price（Standard Selling） | ✅ |
| 3 个 bug 修复：死赋值 + currency API + on_update→after_insert | ✅ |
| **`boot.py` 缺失导致崩溃修复** | ✅ |
| `ModuleNotFoundError: No module named 'solua_home.boot'` | ✅ 已创建 boot.py |
| 残留临时文件清理（_fix_billing.py, [29, from） | ✅ |
| **hooks.py 多次损坏修复** | ✅ |
| hooks.py 重写 3+ 次（未被 '' 多行字符串 + sed 多行替换破坏） | ✅ |
| 所有 .py 文件语法检查通过 | ✅ |
| pip editable 重新安装 + bench clear-cache | ✅ |

### 第六会话：POS 扫码选色落地 + 前后端契约审查 + 文档/代码统一（本次）

| 任务 | 状态 |
|------|------|
| **POS 扫码颜色选择器前端实现** | ✅ |
| `public/js/pos_custom.js` — onScan 原型方法重绑定 + 颜色弹窗 + 加购 | ✅ |
| 关键设计：挂在 `ItemSelector.prototype.bind_events`（POS 刷新重建组件后仍生效） | ✅ |
| `hooks.py` 注册 `page_js = {"point-of-sale": "public/js/pos_custom.js"}` | ✅ |
| 颜色弹窗（frappe.ui.Dialog + HTML 网格 + 防堆叠 + XSS 转义） | ✅ |
| 加购复用标准「搜索→点击 .item-wrapper」流程（价格/UOM 自动带出） | ✅ |
| **前后端契约审查（发现并修复 3 个 bug）** | ✅ |
| 🔴 条码查询 `get_value("Item", {"barcode":...})` 列不存在 → 改查 `Item Barcode` 子表 | ✅ |
| 🟡 `custom_swatch_image` 字段不存在报错 → `has_column()` 守卫 + getattr 兜底 | ✅ |
| 🟡 无异常处理 → try/except + log_error + 返回 `{"type":"error"}` | ✅ |
| 前端处理 `r.exc` / `type:"error"`（红色提示 + 恢复搜索框焦点） | ✅ |
| **操作手册更新** | ✅ |
| 6.5.4 伪代码 → 真实代码（含契约表 + 踩坑记录） | ✅ |
| 新增 6.5.8 部署与验证（本地/生产命令 + 验证清单 + 常见问题） | ✅ |
| **install.py 多规格初始化（此前仅文档有）** | ✅ |
| 新建 `install.py`：`add_item_attributes()` Cor 属性 | ✅ |
| `add_variant_custom_fields()` 5 个 Item 多规格字段（含色卡图） | ✅ |
| `configure_item_variant_settings()` 模板→Variant 继承字段（官方 API） | ✅ |
| `hooks.py` 指向 `solua_home.install.*`；setup.py 清理死代码改为函数库 | ✅ |
| 手册 6.5.5/6.5.6 与代码统一（标注已实现） | ✅ |
| **solua-home 双目录去重分析** | ✅ |
| 发现 `C:\Users\Yang\erpnext` 是 solua-home 子模块的孤儿拷贝（git 已损坏） | ✅ |
| 生成清理脚本 `solua-home/scripts/cleanup-erpnext-dup.bat`（移到回收站） | ✅ |
| 所有改动双份同步（erpnext 根 + solua-home）+ md5 校验 | ✅ |

### 第七会话：生产升级部署 + POS 扫码选色全流程验收（本次）

| 任务 | 状态 |
|------|------|
| **生产快速止血：客户创建 ValueError 修复部署** | ✅ |
| 根因：服务器跑 7 月中旬旧代码，`frappe.db.exists("Contact", {"links": [...]})` 子表过滤写法不被支持 | ✅ 本地第五会话已修复，本次仅部署 |
| 上传修复版 `api/sales.py`（md5 一致 + 语法检查）+ 备份 `sales.py.bak-20260806` | ✅ |
| 重启 web + 端到端验证：创建客户 TEST-FIX-VERIFY → 无报错 → 联系人自动创建 → 清理 | ✅ |
| **完整升级部署（commit `1e2236a`）** | ✅ |
| ⚠️ 发现：本地 WSL 的 `pos.py`/`pos_custom.js` 是修复前旧版（含已知坑），修复版在示例副本 → 先同步再提交 | ✅ |
| 本地 commit + push GitHub（解决 WSL 凭据为空问题：复用 Windows 侧 GCM） | ✅ |
| 服务器备份站点 + git pull（fast-forward）+ migrate + build + 重启全部服务 | ✅ |
| 5 个多规格自定义字段创建、翻译 200 条、Item Variant Settings 81 个继承字段 | ✅ |
| 三处代码一致（本地 / GitHub / 服务器 = `1e2236a`） | ✅ |
| **Sales Order / Quotation 日期类型修复（commit `5cb1ff4`）** | ✅ |
| 报错 `str < datetime` TypeError → 改用 `frappe.utils.date_diff`（整数，兼容字符串/日期） | ✅ |
| ⚠️ 踩坑：`add_days`/`today` 在 frappe 16 返回字符串，`getdate(...) < add_days(...)` 仍是 date < str | ✅ 第二版修复用 date_diff |
| 4 场景端到端验证通过（SO 正常/越界 × QUO 正常/越界） | ✅ |
| **POS 默认不加载商品（commit `adea055`）** | ✅ |
| `override_whitelisted_methods` 拦截 `point_of_sale.get_items`：无 search_term 返回空列表 | ✅ 解决全量物料卡顿 |
| 前端空态提示「请扫码或搜索商品」（替换 Items not found 横幅） | ✅ |
| 验证：HTTP handler 层解析到自定义函数，空搜索空列表、搜索 SKU001 正常 | ✅ |
| **Walkin 散客顾客** | ✅ 创建（Individual）+ 设为 `收银方式1` POS Profile 默认顾客 |
| Walkin 自动联系人钩子正确跳过（after_customer_created 精确匹配） | ✅ |
| **窗帘测试数据（生产 erp.solua.one）** | ✅ |
| `Cor` 属性 + `CR-001` 模板（条码 6901234567890）+ 6 个颜色 Variant（AZ/BG/BR/CZ/PR/VM） | ✅ |
| Standard Selling 价格 6 条（1200–1450 MZN，auto_create_item_price 自动生成） | ✅ |
| Stock Reconciliation `MAT-RECO-2026-00002` 补库存 10 件/色（Finished Goods - SHD） | ✅ |
| 测试环境：用户 `pos.test@solua.one` + Profile `收银方式1-Test`（顾客=Walkin）+ 开店单 | ✅ |
| **扫码选色全流程浏览器实测（验收 ✅）** | ✅ |
| 打开 POS → 空态提示「请扫码或搜索商品」→ 顾客默认 Walkin | ✅ |
| 输入条码 6901234567890 → 弹出「选择颜色」弹窗（6 色块全显示） | ✅ |
| 点击 Branco → 购物车加入 `CR-001-BR` × 1，MZN 1,200.00 | ✅ |
| 控制台无 JS 错误，错误日志为空 | ✅ |
| **实测发现并解决 2 个问题** | ✅ |
| 🔴 扫码报 403「Item Price 权限不足」：生产站点 Item Price 仅授权 Purchase/Sales Master Manager | ✅ 已给 Sales User 角色加 Item Price 读权限（最小权限，验证通过） |
| 🔴 点色报「仓库中无此物料」：Variant 无库存 | ✅ 盘点单补库存 |
| **POS 分组清理 + 模块隐藏（零售环境瘦身）** | ✅ |
| POS Profile 收银方式1 配置 item_groups=Products，分组树只显示成品 | ✅ 验证：get_item_groups=[Products]、搜索返回 6 色 Variant |
| 隐藏 4 个模块 Workspace（Manufacturing/Projects/Quality/Subcontracting，is_hidden=1） | ✅ 收银员视角验证全部消失；管理员仍可见（Frappe 设计） |
| Maintenance/EDI 无桌面 Workspace（本来就不显示），无需处理 | ✅ |

### 第八会话：App 命名正规化（my_custom_app → solua_home）+ 生产配置盘点（本次）

| 任务 | 状态 |
|------|------|
| **基础档案盘点** | ✅ 公司/科目/仓库/物料/价格/税/POS/用户/翻译全量核对，主干完整 |
| **demo 数据清理** | ✅ SKU001-010、test 物料、demo 客户/供应商/分组、32 张测试单据全删，验证归零（见 demo-data-cleanup-plan.md） |
| **三处代码同步** | ✅ GitHub（solua-erp `3f1e70c`）/ 服务器 / 本地示例 md5 全量一致 |
| **App 重命名：my_custom_app → solua_home** | ✅ 方案 A 完整重命名 |
| 模块名（Python 包名）| ✅ `solua_home`（小写+下划线，不能有空格） |
| 显示元数据 | ✅ app_title=Solua Home 定制 / publisher=Solua Home, Lda / email=admin@solua.one |
| GitHub 仓库改名 | ✅ `erpnext-apps` → `solua-erp`（gh CLI，旧 URL 自动重定向） |
| 服务器迁移 | ✅ 目录 apps/my_custom_app → apps/solua_home + apps.txt/apps.json/symlink/tabInstalled Application |
| 🔴 关键踩坑：installed_apps 旧名残留 | ✅ tabDefaultValue 里旧列表导致 migrate 报 No module named 'my_custom_app'，已改为 [frappe, erpnext, solua_home] |
| 验证 | ✅ import solua_home、POS 拦截 get_items→solua_home.api.pos.get_items、page_js 生效、supervisor RUNNING |
| **⚠️ 遗留：site_config.json 旧 app 名** | 🔴 sites/erp.solua.one/site_config.json 的 installed_apps 仍是旧名，需改为 solua_home（待办） |
| **SHD → SH 迁移评估** | ✅ 已出评估清单（SHD-SH 迁移评估清单.md），待确认方案后执行 |
| **POS 付款默认行为确认** | ✅ 当前 Cash 为默认并自动填全额；可选关闭默认开关实现「收银员选方式→自动填剩余金额」 |

### 第九会话：生产配置变更 + 收银员账号 + Demo 公司删除（2026-08-07，本次）

**一句话总结**：完成 POS 收款流程改造、配置快照导出、SHD→SH 迁移执行、Demo 公司整体删除、正式收银员账号 pos1/pos2 创建，并同步所有文档。系统进入「唯一公司 SH + 正式收银员」的生产前状态。

| 任务 | 状态 |
|------|------|
| **代码：隐藏评论输入框（保留活动时间线）** | ✅ 提交 `87444ed` |
| 实现方式 | ✅ `solua_home/public/css/hide_comments.css`（隐藏 `.comment-box`）+ hooks.py `app_include_css`，活动时间线保留 |
| 部署验证 | ✅ 服务器 Node 24 build + 重启，CSS 经 HTTPS 200，三处一致（GitHub/服务器/本地） |
| **POS 收款流程改造** | ✅ |
| `set_grand_total_to_default_mop` 1→0（收银方式1 / 收银方式1-Test） | ✅ 打开收款界面不再自动选 Cash/填全额，点任意付款方式自动填剩余金额（`auto_set_remaining_amount`） |
| 实测 | ✅ 点 Cash/刷卡自动填充全部通过（含混合支付） |
| 发现：Cash default 标记不可去 | ✅ ERPNext 强制至少一个默认付款方式（validate_payment_methods），但开关关闭后 default 不再生效 |
| **配置快照导出** | ✅ `config-snapshot/` 目录（v1/v2/v3） |
| v1 | ✅ 180 Property Setter + 29 Custom Field + 2 POS Profile（SHD） |
| v2 | ✅ 新增 4 隐藏模块（Workspace is_hidden）+ 3 用户设置（含 pos.test 静音） |
| v3 | ✅ 最终态：POS Profile ×3（含 SH 迁移后），用于重置重放保险 |
| **site_config.json installed_apps 修复** | ✅（第八会话遗留的最后一处旧名） |
| 修复 | ✅ `[frappe, erpnext, solua_home]`，备份 `site_config.json.bak-20260807` |
| 验证闭环 | ✅ clear-cache + 重启（7 进程 RUNNING）+ 日志零新增报错 + 重启后 build_index 正常 |
| **pos.test 静音** | ✅ `mute_sounds=1`（zh 语言用户） |
| **SHD → SH 配置迁移（执行）** | ✅ |
| 新建 `收银方式1 - SH` POS Profile | ✅ Walkin 默认、Cash(默认)+Credit Card、自动填收款关、warehouse/科目联动 SH |
| 依赖补齐 | ✅ 新建科目 `Bank Account - SH`（Credit Card 在 SH 的默认账户）+ Mode of Payment SH 账户行 |
| 物料/库存 | ✅ 未迁移（测试档案留在 SHD，后随公司删除） |
| **Demo 公司 Solua Home, Lda (SHD) 删除** | ✅（详见 SHD-company-deletion-record.md） |
| 备份 | ✅ `20260807_002435`（database+files+private-files） |
| 删除范围 | ✅ 单据/科目 97/仓库 5/成本中心/税模板/POS Profile×2/GL/SLE/Bin/付款方式账户行 |
| 验证 | ✅ 全表扫描 ~130 表 SHD 残留 0，唯一公司 SH |
| **正式收银员 pos1/pos2 创建** | ✅ |
| 账号 | ✅ pos1@solua.one（POS 收银员 1）/ pos2@solua.one（POS 收银员 2） |
| 权限 | ✅ Sales User + Accounts User（收银最小权限）+ 新增自定义角色 **POS Cashier**（仅开店/关店 submit） |
| 绑定 | ✅ 收银方式1 - SH（applicable_for_users 子表：pos1/pos2/Administrator）+ 默认公司 SH + 静音 + zh/Africa/Maputo |
| 实测 | ✅ 密码校验通过；pos1 身份 create_opening_voucher 开店成功（POS-OPE-2026-00003，已取消清理） |
| **文档归档** | ✅ |
| 新建《SHD-company-deletion-record.md》 | ✅ 删除记录/顺序/备份号/回滚/上线对照清单 |
| demo-data-cleanup-plan.md 交叉引用 | ✅ 顶部注明 SHD 已整体删除 |

### 第十会话：Print Designer 汉化 + 价格标签打印（2026-08-08，本次）

**一句话总结**：安装官方 Print Designer 设计器，用「运行时覆写」方案完成全界面汉化（不改源码、升级不冲突），部署 50×30mm 价格标签打印格式，修复条码渲染链路（模板值先渲染再生成），全流程验证通过（设计器→预览→PDF→headless Chrome 截图）。

| 任务 | 状态 |
|------|------|
| **Print Designer 生产安装** | ✅ 先备份数据库 → bench get-app + install-app → 实测发票/标签/小票打印 |
| **汉化双机制（不改 print_designer 源码）** | ✅ |
| 方案 A：translations/zh.csv 追加 40 条 `__()` 翻译 | ✅ 实测 10/10 生效（frappe 翻译机制覆盖） |
| 方案 B3：`public/js/print_designer_zh.js` MutationObserver 运行时覆写 | ✅ 67+ 硬编码 label 中文（编译时固化的英文翻译文件覆盖不了） |
| 服务端白名单接口 `get_zh_translations()` | ✅ 14,279 条 zh 字典兜底（frappe.cache 24h），字段标签不限单据类型全覆盖 |
| 修复观察器 3 个 bug（applied 置位过早/节流丢批/缺 characterData 监听） | ✅ |
| **DocType 下拉过滤（方案 A）** | ✅ 提交 `96d8f96` |
| 覆写 `LinkControl.set_custom_query` 合并白名单 33 个常用单据 | ✅ 服务端实测：过滤后 33 个含 Item，搜 Item 命中，Tag 被过滤（预期） |
| **「有内容时点击弹下拉」** | ✅ 提交 `75fad0d` → 后迁移全站 `solua_home_global.js`（app_include_js，提交 `64946b7`） |
| **设计器顶栏按钮** | ✅ 注入「新建/编辑格式」按钮（提交 `4b891a1`）+ Exit 改为回对话框（提交 `0c4940f`） |
| **条码渲染链路修复** | ✅ 提交 `30c2a61` |
| 根因：条码元素 value 是 Jinja 模板，弹窗/画布预览直接把模板发给 get_barcode → 报 Invalid barcode value | ✅ |
| 修复：拦截 `frappe.call`，get_barcode 遇 `{{` 模板值先调 `render_user_text_withdoc` 渲染成真实值再生成 | ✅ 端到端实测：渲染 6901234567890 → SVG 正常，旧路径精确复现报错 |
| ⚠️ 脚本 bug 把 print_designer_print_format 写空 | ✅ 从 Version 审计恢复 + 重新 patch（ean13 + 绑定 custom_label_barcode），打印管线恢复正常 |
| **50×30mm 价格标签格式「价格标签 50x30 PD」** | ✅ doc_type=Item |
| 页面尺寸 | ✅ @page 50mm×30mm（实测打印 HTML/CSS 确认） |
| 元素 | ✅ 中文名/葡语名/型号/价格（Dynamic Text）+ 条码（Barcode 元素，ean13，绑定 custom_label_barcode） |
| 物料条码回填 | ✅ 7 个测试物料 custom_label_barcode 全量补齐（子表条码优先/变体继承模板） |
| ⚠️ 发现：测试条码 6901234567890 校验位错误 | 正确应为 6901234567892（python-barcode 渲染时自动重算校验位 → 库值与图像不一致，待确认修复） |
| **标签效果验证** | ✅ 用 headless Chrome（服务器 /usr/bin/google-chrome）截图 50×30mm 标签 PNG，用户确认看到中文名/葡语名/型号/价格/条码，缩放拖拽正常 |
| **三处代码一致** | ✅ 服务器 / 本地示例 / GitHub md5 全同，提交 `30c2a61` 已推送 |
| **遗留待办** | ① 条码校验位修正方案 ② 物料条码自动生成器（带校验位）③ 设计器布局美化（字体/价格格式）④ 标签打印机实打测试 |

### 第十一会话：颜色池扩容 + 批量生成变体向导（2026-08-08，本次）

**一句话总结**：颜色池 Cor 从 6 色扩到 16 色并解决缩写冲突（Prata 银 PR→PT），给颜色值加色卡图字段，实现「批量生成变体」服务端 API + 物料列表向导按钮（选模板→勾颜色→建变体→自动继承价格/条码/名称），端到端实测通过。

| 任务 | 状态 |
|------|------|
| **颜色池扩容（Cor 属性 6→16 色）** | ✅ |
| 缩写冲突修复 | ✅ Prata(银) PR→**PT**（原与 Preto(黑) PR 冲突，变体编码会撞车） |
| 新增 10 色 | ✅ Verde 绿/Amarelo 黄/Laranja 橙/Rosa 粉/Roxo 紫/Dourado 金/Marrom 棕/Turquesa 青/Creme 奶油 + Prata 银 |
| 幂等函数 | ✅ `add_color_pool()`（install.py，重复执行不重复插入 + 缩写唯一校验） |
| **色卡图字段** | ✅ Item Attribute Value 新增 `swatch_image`（Attach Image）— 每色可配色卡小图，POS 颜色弹窗/设计器显示色块 |
| **批量生成变体 API** | ✅ `bulk_create_variants()` + `get_template_attribute_values()`（api/variants.py） |
| 自动建变体 | ✅ 命名 模板-缩写、继承模板价格（auto_create_item_price）、回填条码（validate_item 逻辑）、复制中文名/葡语名 |
| 中文名拼接 | ✅ 「模板名·颜色中文」（如 测试窗帘 3m·白色），POS 简称=颜色名 |
| 前端向导按钮 | ✅ `item_variant_wizard.js`（page_js 注册到 Item）：物料列表「批量生成变体」→选模板→自动列出颜色→勾选→创建 |
| 颜色翻译 | ✅ 16 色葡→中翻译入 Translation 表 |
| **CR-001 变体重建** | ✅ 引用检查（无库存/无单据）→ 删除重建，编码不变（CR-001-PR 仍是 Preto），价格统一 1200，条码/中文名回填 |
| **端到端实测** | ✅ TEST-TPL-001 → 勾 Branco+Verde → 2 变体（价格 1500/条码回填/中文名「测试窗帘 3m·白色·绿色」）全对，重复运行正确跳过，测试数据已清理 |
| **三处代码一致** | ✅ 提交 `51a2bc1` 已推送（`bdef22b..51a2bc1`），install.py / variants.py / hooks.py / wizard.js md5 全同 |
| **遗留待办** | ① 条码校验位修正（`6901234567890` → 正确 `6901234567892`）② 建档自动生成合法 EAN-13（今天测试 `6901234567891` 已被 ERPNext 拒收 → 校验位功能已生效，生成器必须带校验位） |

### 第十二会话：POS 折扣权限方案 C（收紧版：任何折扣 >0 都需管理员审批）（2026-08-08，本次）

**一句话总结**：折扣管控最终版——打开收银员折扣输入（allow_discount_change=1），但**任何折扣（幅度 >0）都触发审批门**（阈值从 15% 收紧为 0%），收银员无审批角色（pos1/pos2 仅 Sales/Accounts User + POS Cashier），只有管理员（yangyang7920 / Administrator 持有 Sales Master Manager/Accounts Manager/System Manager）能审批。行折扣保险补丁（rate 自动联动折后价）保留，修复 ERPNext 清折扣 bug。A-F 全链路测试通过。

| 任务 | 状态 |
|------|------|
| **决策（收紧版）** | ✅ 用户要求「任何折扣都需管理员授权，收银员无自由打折权」→ 阈值 15%→0%（MAX_DISCOUNT_PERCENTAGE=0） |
| **行折扣保险补丁** | ✅ api/sales.py（before_validate）：行有 discount_percentage 且 rate 仍是原价时 → 自动把 rate 改为折后价（修复 v16.28 `calculate_item_rate` 的 rate 优先清折扣 bug） |
| **超限审批机制** | ✅ 任何折扣（>0%）提交时拦截报错「折扣 X% 未经审批，需管理员在发票上勾选「折扣超限已审批」后提交」；管理员（或勾选 custom_discount_approved=1 后）直接通过 |
| **审批字段** | ✅ Sales Invoice 新增 `custom_discount_approved`（Check，install.py 创建）+ 翻译 |
| **hooks 注册** | ✅ api/sales.py 新函数注册到 doc_events（Sales Invoice before_validate） |
| **POS Profile 折扣权限** | ✅ 收银方式1 - SH `allow_discount_change` 0→1（收银员可见行折扣/整单折扣输入框） |
| **测试（收紧版全部通过）** | ✅ |
| A：pos1 行折扣 1%（任何>0）提交被拒 | ✅ 报「折扣 1% 未经审批…」 |
| B：pos1 整单折扣 2% 提交被拒 | ✅ |
| C：pos1 无折扣正常提交 | ✅ |
| D：管理员直接打 10% 通过 | ✅ discount=10% |
| E：pos1 草稿 5% → 管理员勾审批 → pos1 提交成功（审批流闭环） | ✅ |
| F：POS 场景 pos1 行折扣 3% 提交被拒（POS 也无法绕过审批门） | ✅ |
| **角色确认** | ✅ pos1/pos2 仅 Sales/Accounts User + POS Cashier（无审批角色）；审批角色仅 yangyang7920 + Administrator 持有 |
| **测试数据清理** | ✅ 6 张测试发票全部取消+删除，库存/开店单保留 |
| **三处代码一致** | ✅ 服务器 / 本地示例 md5 全同（api/sales.py / hooks.py / install.py） |
| **踩坑** | ⚠️ taxes 子表 description 是 reqd=1（Sales Taxes and Charges 标准字段），测试脚本必须填，真实 POS 界面自动生成 |

### 第十三会话：条码三件套（自动生成器 + 校验位修正 + 厂家错码容错）（2026-08-08，本次）

**一句话总结**：一次性解决条码全链路问题——① 无条码物料建档自动生成合法 EAN-13（带校验位 + 去重）；② 修正现有测试条码 6901234567890→6901234567892（模板子表 + 6 变体镜像字段）；③ 厂家条码校验位错误时自动置空 barcode_type 跳过格式校验（防重复保留）。标签渲染层同步加固：校验位错误的 13 位数字强制 code128 原样输出（python-barcode 的 EAN-13 会自动重算校验位导致图≠库，收银扫码对不上）。

| 任务 | 状态 |
|------|------|
| **① 自动生成器** | ✅ `generate_unique_ean13()` + `before_validate_item`（api/stock.py） |
| 触发条件 | ✅ 非变体物料子表无任何条码时自动生成（变体走继承模板条码，不自动生成） |
| 生成规则 | ✅ 69 开头 + 10 位随机 + EAN-13 校验位；查 Item Barcode 子表 + custom_label_barcode 去重，碰撞重试 20 次 |
| 写入 | ✅ 自动 append 到 barcodes 子表（barcode_type=EAN）+ 镜像 custom_label_barcode + 界面提示「已自动生成：XXXX」 |
| **② 现有条码修正** | ✅ 6901234567890 → 6901234567892（校验位错误） |
| 修正范围 | ✅ Item Barcode 子表（CR-001）+ 6 个变体 custom_label_barcode 镜像字段，旧码残留归零 |
| **③ 厂家错码容错** | ✅ barcode_type=EAN 且校验位错 → 自动置空 barcode_type，ERPNext 跳过格式校验（防重复检查仍在） |
| 关键点 | ✅ 必须放 `before_validate`（在 ERPNext 自带 validate_barcode 之前跑），否则错码直接被 InvalidBarcode 拒收 |
| ⚠️ 踩坑 | 🔴 修改 hooks.py 后必须 `bench clear-cache` 才生效（重启 web 不清 hooks 缓存）——get_hooks 验证加载 |
| **标签渲染加固** | ✅ label_helpers.py：13 位纯数字校验位正确→ean13；校验位错误→强制 code128 原样（不重算，图=库） |
| **测试（全部通过）** | ✅ |
| 自动生成 | ✅ TEST-BC-AUTO-001 → 自动生成 6940504403010（13 位合法） |
| 错码容错 | ✅ 6901234567891 (EAN) 成功建档，barcode_type 保存后为空 |
| 防重复保留 | ✅ 重复条码 6901234567892 仍被拦「already used in Item CR-001」 |
| 变体继承 | ✅ CR-001-BR custom_label_barcode = 6901234567892 |
| 渲染 | ✅ 对码 ean13 PNG / 错码 code128 PNG 均生成成功 |
| **测试数据清理** | ✅ TEST-BC-* 全部删除，数据库仅剩 CR-001 一条码（已修正） |
| **三处代码一致** | ✅ 服务器 / 本地示例 md5 全同（api/stock.py / printing/label_helpers.py / hooks.py） |

### 打印格式盘点（2026-08-08，上线差距评估）

| 单据 | 现有格式 | 结论 |
|------|---------|------|
| 小票（POS Invoice） | ✅ 4 个标准（POS Invoice / Standard / with Item Image / Return） | 有默认，但需按热敏纸定制（58/80mm、Logo、NUIT、支付明细、找零） |
| 交班（POS Opening/Closing Shift） | ⚠️ 无专门格式 | 用通用布局，建议 Print Designer 做 Z 报告 |
| 订货（Purchase Order） | ✅ 3 个标准 | 有默认 |
| 销售发票（Sales Invoice） | ✅ 5 个 + PD v2 | 有默认 |
| 出库（Delivery Note） | ✅ 2 个标准 | 有默认 |
| 入库（Purchase Receipt） | ⚠️ 仅 Serial/Batch 专用 | 普通收货单无格式，建议补 |
| 采购发票（Purchase Invoice） | ✅ 3 个标准 | 有默认 |
| 报价单（Quotation） | ✅ 2 个标准 | 有默认 |
| 供应商报价（Supplier Quotation） | ⚠️ 无 | 按需 |
| 库存调整（Stock Entry） | ⚠️ 无 | 按需 |
| 付款（Payment Entry） | ✅ 1 个 | 有默认 |
| PDF 生成器 | ⚠️ `wkhtmltopdf`（Print Designer 格式建议切 chromium，标签已用 chrome 验证） | 待切换 |
| 付款方式 | ⚠️ 仅 Cash/卡/支票/电汇/Bank Draft，**无 M-Pesa/E-mola**（莫桑比克主流移动支付） | 待补 |
| 信头 | ✅ Company Letterhead - Grey 默认 | 需填真实 NUIT/地址/电话 |

### 第十四会话：折扣审批升级为「密码审批」（2026-08-08，本次）

**一句话总结**：把原来的「折扣超限已审批」勾选框 + 角色白名单审批，改为**管理员在发票上输入审批密码**才能放行——收银员即使能看到/编辑发票也没有自助放行能力（密码是唯一凭证）。

| 任务 | 状态 |
|------|------|
| **审批密码字段** | ✅ Sales Invoice 新增 `custom_approval_password`（Password，标签「审批密码」） |
| **勾选框降级** | ✅ `custom_discount_approved` 保留为内部标记：Property Setter 隐藏(hidden=1) + 只读(read_only=1)，界面不可见，只由代码校验密码后置位 |
| **公司配置** | ✅ 设置→公司→Solua Home, Lda 新增：`custom_enable_discount_approval`（总开关，默认开）/ `custom_discount_approval_threshold`（阈值%，默认0=任何折扣）/ `custom_discount_approval_password`（审批密码） |
| **审批逻辑** | ✅ api/sales.py：折扣幅度 > 阈值 且未审批时 → 密码匹配则置标记+清空密码字段；密码错误直接 throw；提交无密码 throw；保存草稿仅提示不拦截 |
| **角色白名单移除** | ✅ 删除 `DISCOUNT_APPROVER_ROLES` / `is_discount_approver()`——人人平等，密码即授权 |
| **兜底** | ✅ `_try_decrypt`：密码字段值已加密则解密、明文则原样（兼容两种读取时机） |
| **初始密码** | ✅ `solua2026`（可在公司表单修改；为空=不启用审批） |
| **测试（17/17 通过）** | ✅ T1 无折扣提交 / T2 收银员10%被拦（草稿保留） / T3 草稿可存 / T4 密码错误被拒 / T5 正确密码提交+标记置位+密码清空 / T6 两段式（收银员草稿→管理员输密码保存→收银员提交） / T7 总开关关闭放行 / T8 阈值15%放行10% / T9 POS 场景被拦 |
| ⚠️ 踩坑 | 🔴 **密码字段掩码**：`frappe.get_doc()` 加载密码字段返回掩码占位符，直接赋值+save() 会把 `*********` 写进库！正确做法：`frappe.utils.password.encrypt(pwd)` 加密后 SQL/`db.set_value` 直写，读取用 `decrypt()` |
| ⚠️ 测试须知 | pos1/pos2 的用户名是 `pos1@solua.one`（不是 pos1）；脚本测试必须设 `price_list_rate`，否则 ERPNext 清折扣导致门不触发 |
| **三处代码一致** | ✅ api/sales.py / install.py 已同步（md5 同） |

**实际使用流程**：
1. 收银员 POS 打折 → 提交被拦（发票留草稿）
2. 管理员打开草稿 → 在「审批密码」输入密码 → 保存（标记自动置位，密码清空）
3. 收银员重新提交 → 成功

### 第十五会话：变体标签条码升级为「变体编码 Code 128」（2026-08-08，本次）

**一句话总结**：窗帘变体的标签条码从「共享模板 EAN」改为「打自己的变体编码（如 CR-001-BR）Code 128」——收银扫标签直接定位具体颜色，无需选色弹窗；同时修复了标签设计里烘焙旧条码（6901234567890）导致所有标签扫码查不到的隐藏 bug。

| 任务 | 状态 |
|------|------|
| **渲染逻辑**（label_helpers.py） | ✅ `_get_barcode`：变体无独立条码 → 返回 (变体编码, code128)；有独立条码优先用自己的；模板/普通商品走原逻辑 |
| **标签条码字段**（api/stock.py） | ✅ `validate_item`：变体 `custom_label_barcode` = 自己的条码或变体编码（不再继承模板 EAN）；非变体不变 |
| **PD 标签格式** | ✅ 「价格标签 50x30 PD」条码元素：barcodeFormat ean13→**code128**，value 改为动态 `{{ doc.custom_label_barcode }}`（修复设计时烘焙的旧值 6901234567890） |
| **POS 扫码兜底**（api/pos.py） | ✅ `scan_barcode_for_pos`：Item Barcode 子表找不到时，按 item_code 精确匹配——扫变体码直接返回 variant，前端直接加购 |
| **已有数据** | ✅ 6 个 CR-001 变体 `custom_label_barcode` 已改为各自变体编码 |
| **测试（11/11 通过）** | ✅ 变体→(CR-001-BR,code128) / 模板→EAN / get_barcode_img 渲染 / PD 值模板渲染（变体→CR-001-BR，模板→6901234567892）/ PD code128 SVG / 扫码 CR-001-BR→variant 直选 / 扫码 EAN→template 6 色选色 / 未知→not_found |
| ⚠️ 权衡 | 标签单条码元素只能一种格式：改 code128 后**普通商品标签也打 Code 128**（EAN 数字照样可扫，值不变，只是外观更紧凑）。如需普通商品恢复 EAN-13 超市风格，需在标签上再加一个 EAN 元素（PD 无元素级显隐条件，需用两个元素或后续处理） |
| **顺带修复** | 旧标签设计 value 烘焙了校验位修正前的 6901234567890，所有标签打出来扫码都查不到——已改为动态取值 |
| **三处代码一致** | ✅ label_helpers.py / api/stock.py / api/pos.py 已同步（md5 同） |

**变体标签新行为**：CR-001-BR 标签印 Code 128「CR-001-BR」→ 扫码直接加入白色变体；CR-001 模板 EAN 6901234567892 不变 → 扫码仍弹选色窗。

### 第十六会话：放弃 EAN-13，条码统一 Code 128（2026-08-08，本次）

**一句话总结**：按「只要条码不重复就行，没必要校验位验证」的思路，正式放弃 EAN-13：自动生成器不再计算校验位，标签渲染一律 Code 128（数字/字母原样输出，图=库永不错位）。扫码枪两种码制都读，条码值才是关键。

| 任务 | 状态 |
|------|------|
| **自动生成器**（api/stock.py） | ✅ `generate_unique_ean13` → `generate_unique_barcode`：69 + 11 位随机数字，共 13 位，**无校验位计算**；去重检查 Item Barcode 子表 + custom_label_barcode，碰撞重试 20 次 |
| **自动建档** | ✅ 无条码非变体物料：自动生成 + 写子表（barcode_type 留空）+ 回填 custom_label_barcode + 提示 |
| **barcode_type 留空的原因** | ✅ ERPNext 的 Item Barcode barcode_type 选项表里**没有 Code128**（只有 EAN/UPC-A/CODE-39/GTIN 等），填了也会被清空；空类型 = 跳过一切格式校验，只剩无条件防重复——正是想要的策略 |
| **标签渲染**（label_helpers.py） | ✅ 删除 EAN-13 校验位分支，`get_barcode_img` 一律 code128 原样渲染（删掉 `_calc_ean13_checksum`/`_is_valid_ean13`） |
| **厂家 EAN 容错保留** | ✅ before_validate_item 的容错仍生效：EAN 类型校验位错误自动清空类型（ERPNext 数据库级校验绕不过），能保存、标签 code128 渲染 |
| **测试（7/7 通过）** | ✅ 生成器 13 位唯一 / 自动建档保存+生成 / custom_label_barcode 回填 / code128 PNG 渲染 / 重复条码拦截（already used）/ 错校验位 EAN 可保存（类型清空）/ 错码也渲染 code128 |
| **三处代码一致** | ✅ api/stock.py / printing/label_helpers.py 已同步（md5 同） |

**现在的条码体系（全链路统一 Code 128）**：
- 新物料无条码 → 自动生成 69 开头 13 位唯一码，标签打 Code 128
- 变体 → 标签打变体编码（CR-001-BR）Code 128，扫码直选颜色
- 厂家条码 → 值不变，标签按 Code 128 打印（校验位错的也能用，类型留空即可）
- 唯一硬规则：条码值不重复（ERPNext 无条件检查）

### 第十七会话：变体颜色码注册进标准条码子表（2026-08-08，本次）

**一句话总结**：把 6 个窗帘变体的颜色码（CR-001-BR 等）注册进各自的标准条码子表（barcode_type 留空），让**采购收货/库存单据**的标准扫码（`erpnext.stock.utils.scan_barcode`）也能识别颜色码——之前只有 POS 能扫（靠 item_code 兜底），入库环节扫颜色码会找不到。

| 任务 | 状态 |
|------|------|
| **注册** | ✅ 6 个变体各加 `[barcode: 变体码, barcode_type: 空]` 到 Item Barcode 子表（幂等：已存在跳过） |
| **标准扫码验证** | ✅ `scan_barcode('CR-001-BR')` → item_code=CR-001-BR（采购收货/库存单据用的就是它）；扫 `6901234567892` → 模板 CR-001；未知码 → {} |
| **POS 扫码无回归** | ✅ `scan_barcode_for_pos`：CR-001-BR→variant 直选；6901234567892→template 6 色选色；未知→not_found |
| **逻辑说明** | 子表命中优先于 item_code 兜底，POS 行为不变；变体码唯一、类型留空跳过格式校验（防重复保留） |

**背景**：用户确认双轨设计——方案 A 为基础（厂家包装条码 = 模板共享码 → 扫码选色），附加打印颜色码让入库更简单（扫颜色码直接定位变体）。注册后全站扫码口（POS / 采购收货 / 库存单据 / 发货单）都能扫颜色码识别变体。

**后续小修**：CR-001 模板 `custom_label_barcode` 里的 SVG 残留（疑似测试时把渲染图写进字段）已清掉，恢复为纯数字 `6901234567892`；全量复查确认所有物料该字段均为纯条码值，无其他残留。

**新增 CR-002 测试产品族**（共享条码测试用）：模板 CR-002（Cortina Roman 2.0m，共享条码 `6901234567893`）+ 4 色变体（Branco/Preto/Azul/Cinza，Standard Selling 1500 MZN）——扫共享条码弹 4 色选色框，扫变体码直选。踩坑：① 模板不能设 standard_rate（ERPNext after_insert 会给模板自动建价并报错，只给变体显式建价）；② 变体名不能含 `/`（被自定义 validate_item 拦截，CR-001 同款用连字符格式）。

**校验规则放开**（api/stock.py）：物料名称规则从拦 `<>"'/` 收窄为只拦危险字符 `<>"'`——`/`、`&`、`()` 等常见字符放行（用户要求：真实物料名常含 `/`，如「140×200 / Algodão」，不应拦建档）。保留编码长度 ≥3 校验。实测：斜杠/&/括号通过 ✅，尖括号/双引号/编码过短仍拦截 ✅。

**POS 模板直加修复**（用户实测 CR-002 发现）：扫共享条码只出模板、选不了、报「未设置物料价格」。根因：v16 POS 原生扫码/搜索路径 `search_by_term` 命中模板条码直接返回模板，`auto_add_item` 自动加购（模板无价→报错），自定义 onScan 选色框没拦截这条路径。修复：① `api/pos.py get_items` 给商品附加 `has_variants` 标记；② `pos_custom.js` 换用 solua_home 包装器 + capture 阶段拦截模板卡片的点击/自动加购，改为弹颜色选择框。覆盖手工输码回车、原生扫码、点模板卡片三条路径。后端验证：模板 has_variants=1、变体=0 且带价。

**二次修复**（用户仍报「只出现模板」）：查配置发现 `收银方式1 - SH` 的 **auto_add_item_to_cart=0**——原生搜索命中模板后只**展示**模板卡片，不会自动点击也不会弹框（硬件扫码才走自定义 onScan）。补 `filter_items` 覆写：搜索命中**唯一模板**时自动调后端弹颜色选择框；防误弹守卫（搜索框内容已变则跳过）。page_js 是服务端内联进页面 HTML、每请求从磁盘读，改完刷新页面即可生效（无需重启）。

### POS 库存开关参考（上线配置，2026-08-15）

用户问「库存不准时能否临时关闭无库存不可售」——答案是两级开关 + 一个显示开关，机制如下（供上线后参照）：

| 开关 | 位置 | 当前值 | 作用 | 影响范围 |
|------|------|:---:|------|------|
| **允许负库存**（allow_negative_stock） | 设置 → 库存设置（Stock Settings） | 关（0） | POS 不检查库存，**没库存也能卖**，库存变负 | **全系统**（POS/采购/交货/库存单据） |
| **允许负库存**（物料级） | 物料档案 → 允许负库存 | 全关（0） | 只放开**这一个物料**，其他仍保护 | 单物料 |
| **隐藏无库存商品**（hide_unavailable_items） | POS Profile | 关（0） | 只控制 0 库存商品**在 POS 列表显不显示**，不影响能否卖 | POS 显示 |

**代码机制**：POS `check_stock_availability`（pos_controller.js）开头 `if (is_negative_stock_allowed) return;` 直接跳过库存校验；`is_negative_stock_allowed`（erpnext/stock/stock_ledger.py:2357）优先读全局 Stock Settings，其次读单物料 Item.allow_negative_stock。POS 前端通过 `pos_invoice.get_stock_availability` 拿 `(available_qty, is_stock_item, is_negative_stock_allowed)`。

**配合用法（上线后库存不准时）**：
- 个别物料不准 → 只开**单物料开关**，对完库存/盘点后关掉
- 整体不准 → **全局开关临时开**，对完账立刻关；不建议长期开（库存变负后报表/毛利/盘点失真）
- 「隐藏无库存商品」与能否卖无关，纯显示控制：想看到 0 库存商品保持关，不想看到就开
- 开负库存卖出的缺口，事后必须用入库/盘点把账调平

**POS 折扣审批改为弹窗输密码**（2026-08-15，用户要求：审批流程要快，直接在 POS 页面弹窗，不去后台翻草稿）：
- 原流程：POS 提交被拦 → 去 销售→销售发票 打开草稿 → 填「审批密码」→ 保存 → 再提交（太慢）
- 新流程：POS 提交时 `Form.prototype.savesubmit` 被 pos_custom.js 拦截（仅 `doc.is_pos=1` 的 POS 发票）→ 弹「折扣审批」对话框 → 输密码 → 后端 `verify_discount_approval_password` 校验 → 通过则写入 `custom_approval_password` 继续提交（后端门再次把关，绕不过）
- 后端配套：`api/sales.py` 新增 whitelisted `verify_discount_approval_password(password, company)`；草稿保存提示只在**非 POS**（`is_pos` 为空）时弹，POS 草稿保存静默（避免频繁提示）
- 桌面发票/订单保持原流程（字段填密码）不变——用户明确「那是另一回事」
- 验证：verify 正确/错误密码 ✅｜POS 发票(is_pos=1,10%)草稿静默保存 ✅｜提交被拦「未经审批」✅｜带密码提交成功 approved=1 ✅
- 踩坑：脚本测试 POS 发票提交需带 payments 全额付款（Partial Payment 检查在折扣门前），真实 POS 付款对话框已自动满足
- **Bug 修复**：用户实测报 `frappe.utils.flt is not a function`（has_unapproved_discount 卡死、弹窗不出现）——Frappe v16 的 `flt` 是**全局函数**（`window.flt`，定义在 `frappe/public/js/frappe/form/controls/float.js`），`frappe.utils.flt` 不存在；改为全局 `flt(...)`（与 erpnext 自带 POS 代码一致），提交 `e523d29` 已推送 GitHub，三处 md5 一致
- **「加密密钥无效」弹窗的真正根因（重要，写进备忘录）**：折扣收银时反复弹「加密密钥无效！请检查 site_config.json」但提交其实成功。用临时日志补丁抓到调用者栈（savedocs → submit → validate → `_try_decrypt('solua2026')` → `decrypt('solua2026')` InvalidToken）——**根因是 Frappe `decrypt()` 的副作用**：`decrypt` 的 `except InvalidToken` 分支执行 `frappe.throw(...)`，而 `frappe.throw` 内部 `msgprint` 会把「加密密钥无效」写进 `frappe.local.message_log` **然后才抛异常**；我们的 `_try_decrypt` 虽 try/except 接住了异常（提交照常成功），但 message_log 里的消息已随 API 响应返回，前端 `frappe.call` 把 `_server_messages` 当服务端消息弹出 → 用户看到「加密密钥无效」。**修复**：`_try_decrypt` 只对 Fernet 密文（固定以 `gAAAA` 开头）调用 decrypt，明文密码（如对话框输入 `solua2026`）直接原样返回，不再误触发解密 → 消息零污染。验证：明文返回且 message_log 空 ✅、加密值正常解密 ✅、完整折扣提交成功且无警告 ✅。临时日志补丁已从 frappe/utils/password.py 移除（原文件恢复），提交 `3914027` 已推送 GitHub，本地/服务器 md5 一致
- **反复「改了没生效」的真正根因（重要，写进备忘录）**：服务器代码已是新版，但用户浏览器仍跑旧 pos_custom.js——Frappe `pageview.js`（`frappe/views/pageview.js`）在**生产模式**（`developer_mode != 1`）下把整个 Page 文档（**含 page_js 自定义脚本**）缓存进 `localStorage["_page:<page名>"]`，之后每次打开页面**直接用缓存、不再请求服务器**，硬刷新 Ctrl+Shift+R 也清不掉 localStorage。point-of-sale 页无 HTML 模板（无 jinja）→ `_dynamic_page` 从未置位 → 必被缓存。**根治**：`override_whitelisted_methods` 包装 `frappe.desk.desk_page.getpage` → `solua_home.override.desk_page.getpage`，返回文档置 `_dynamic_page=1`，pageview.js 见标记即跳过 localStorage 缓存（每页多一次小请求，本项目可接受）。已端到端验证：handler.py:67 请求时 `override_whitelisted_method` 解析 ✅；直接调用返回 `_dynamic_page: 1` + 最新脚本（无 `frappe.utils.flt`）✅。**踩坑**：override 函数必须带 `@frappe.whitelist()` 装饰器——handler 的 `is_whitelisted` 校验的是**替换后**的函数（whitelisted 集合在模块 import 时由装饰器登记），第一版漏了装饰器导致页面 403「方法未申明 @frappe.whitelist()」；补上装饰器（`allow_guest=True` 与原方法一致）+ 重启后恢复正常，按 handler 三步（override 解析 → get_attr → is_whitelisted）验证全部通过。提交 `350dc53`（override）+ `219b3ed`（whitelist 补丁）已推送 GitHub

**收银完成静默打印 + 自动开新单（2026-08-16，用户要求超市收银体验）**：
- 问题：POS Profile `print_receipt_on_order_complete=1` 时，收银完成后默认走 `frappe.utils.print` 在**新标签页**打开带正式信头（Company Letterhead - Grey）的 printview——太正式、流程慢
- 修复（pos_custom.js）：① `pos_silent_print`——隐藏 iframe 加载 printview（`no_letterhead=1`，小票无正式信头），`iframe.contentWindow.print()` 阻塞到打印对话框关闭；② 包装 `PastOrderSummary.load_summary_of`——after_submission 时临时关掉默认 new-tab 打印、正常渲染收据摘要，静默打印完成（对话框关闭）后自动调 `events.new_order()` 开新单（超市收银模式）；③ 手动打印按钮也改走静默打印（不再弹新标签页）
- 开关：仍用 POS Profile「打印收据」(print_receipt_on_order_complete)——开=自动打印+自动开新单，关=手动流程；手动打印始终是静默方式（注：此开关后续已拆分为独立控制，见下条「自动开新单独立开关」）
- 提交 `d74a1fc` 已推送 GitHub；printview 本身不响应 trigger_print（`frappe.utils.print` 的 trigger_print=1 只存在于 utils.js），打印由 iframe 自己调 window.print()

**自动开新单独立开关（2026-08-16，与自动打印分开控制）**：
- 需求：自动开新单与自动打印解耦——原实现绑在 `print_receipt_on_order_complete` 上（打印开=自动打印+自动开新单）
- 新增 POS Profile 自定义字段 `custom_auto_new_order`（Check，默认 1，标签「收银后自动开新单」，insert_after `print_receipt_on_order_complete`），install.py 的 `add_pos_profile_settings()` 创建并给存量 Profile 补默认 1；`after_install` 已挂接，bench migrate 即生效
- pos_custom.js：① 透明包装 `PastOrderSummary` 构造函数（`Reflect.construct` + 原型链保留），从 settings（`get_pos_profile_data` 返回完整 Profile 文档，自定义字段自动包含）读出 `inst.auto_new_order_on_complete`；② `load_summary_of` 改双开关逻辑——打印开+开新单开=静默打印完自动开新单；打印开+开新单关=只打印停留摘要页；打印关+开新单开=不打印、短暂显示 1.2s 后自动开新单；打印关+开新单关=原生手动流程
- 验证：bench migrate 建字段 ✅、`get_pos_profile_data` 返回 `custom_auto_new_order: 1` ✅、服务器 JS node --check ✅；收银方式1 - SH 已置 1（保持原行为）

**小票功能与设计进展（2026-08-16，用户询问小票是什么/在哪设计）**：
- 当前小票 = POS Profile（收银方式1 - SH）→「打印格式」选的内置 `POS Invoice` 格式；已实际渲染成 PDF 预览给用户看过
- ⚠️ 发现的问题：内置格式是**标准单据宽度**，不是窄条热敏纸——预览里**金额列被截断**（"1,5" 只显示一半），打到 58/80mm 热敏纸上会很难看 → 上线前需做一张专用小票格式
- 设计入口：① **Print Designer**（推荐，可视化拖拽，同价格标签工具）——画布设 80mm 宽，拖入店名/单号/日期/收银员/商品行/合计/折扣/总额/付款/找零；② **内置打印格式编辑器**（设置→打印→打印格式，改 HTML/Jinja + CSS，精确控制宽度字号，纯代码）
- 建议版式：店名 → 单号/日期时间/收银员 → 分隔线 → 商品（名称/数量/单价/金额）→ 合计/折扣/总额 → 现金/刷卡/找零 → 感谢语
- **免确认静默打印方案**（用户问“什么插件”）：① 方案 A：Chrome `--kiosk-printing` 启动参数——`window.print()` 直接打到默认打印机、完全不弹对话框（零安装，热敏机设为系统默认打印机即可，免费）；② 方案 B：**QZ Tray**（行业标准）——收银台装桌面程序+浏览器扩展，网页 JS 发原始 ESC/POS 指令，更快更稳、支持钱箱自动弹开/直接打条码，商业使用需授权（个人免费）
- **待确认**：用户热敏小票机纸宽（58mm/80mm），确认后在 Print Designer 搭「小票 80mm/58mm」版式，两个方案通用

**清理测试日志与控制台监控（2026-08-16）**：
- pos_custom.js 移除全部调试 console.log：脚本版本标记（"script v3 loaded"）、filter_items 检查、搜索框内容已变跳过、scan 返回日志；保留 `console.error`（小票打印失败真实错误处理）
- 服务器 /tmp 清理：历次诊断脚本（*.py/*.b64）、测试 PDF（before_label/before_SI/label_CR-001-BR）、config-snapshot 临时副本、decrypt_fail.log（已无）、headless Chrome 临时目录
- 本地 .freebuff/ 清理：34 个诊断脚本 + 根目录 check_mo.py/.tmp_setup_cr001.py（.html/.png/.pdf 预览产物保留）
- 确认：`frappe/utils/password.py` 已恢复原版（无补丁残留）、`/tmp/decrypt_fail.log` 已不存在

**POS 三条主流程回归实测（2026-08-16，删调试日志后确认功能不受影响）**：
- 后端全链路实测 **20/20 通过**：① 选色——共享条码 `6901234567893`→模板 CR-002+4 色（AZ/BR/CZ/PR）、变体码 `CR-001-BR`→直接定位、不存在条码→not_found、get_items 搜索命中变体+带 has_variants 字段；② 折扣审批——正确/错误密码、POS 草稿静默保存、无密码提交被拦、带密码提交成功+approved=1、message_log 无「加密密钥无效」警告；③ 打印——两个开关=1、POS Invoice 格式渲染成功（7522 字符）、POS 页面文档含新版 JS 且无调试日志残留
- **关键测试细节（踩坑）**：模拟带折扣的 Sales Invoice 时 `rate` 必须为**折后价**（1500×0.9=1350）——ERPNext `taxes_and_totals.py` 的 `calculate_item_rate` 在 rate 与折扣矛盾时**以 rate 为准清掉折扣**（`item.rate > price_list_rate` → margin；否则 `discount_percentage=0`）。真实 POS 前端会把 rate 联动重算为折后价再提交，所以用户实测没问题、纯脚本模拟会踩坑。模拟提交需设 `doc._action="submit"` 走提交拦截分支（frappe 内部 submit() 也会自设，但显式设置更稳）
- 测试发票已清理（临时单删除，用户历史单 00022-00025 保留），测试脚本无残留

**POS 开店对话框自动预填唯一 POS Profile（2026-08-16，用户问“pos 设置还得选，不能默认吗”）**：
- 现象：POS 打开 → 无未交班 Opening Entry → 弹「开店」对话框，POS Profile 字段必填且无默认 → 每次都要手动选
- 根因：`pos_controller.js` 的 `create_opening_voucher()` 对话框里 POS Profile 是 `reqd: 1` 且没有 default（后端 `pos_profile_query` 按 用户绑定 applicable_for_users + 公司 + disabled 过滤）
- 修复（pos_custom.js）：包装 `Controller.prototype.create_opening_voucher`，弹窗显示后（`frappe.ui.open_dialogs` 全局注册表）找「含 pos_profile + balance_details 字段」的对话框；若当前用户可用 POS Profile **恰好 1 个**则 `set_value` 自动填入（触发 onchange 自动带出付款方式表 Cash/Credit Card），多个时保持手动选择不打扰
- 验证：pos1/pos2/Administrator 三账号数据层查询均只返回「收银方式1 - SH」→ 都会自动预填；本地/服务器 md5 一致（`3e132b4b`）、页面文档含新代码、JS 语法 OK
- 提交 `6bca96c` 已推送 GitHub
- **BUG 修复（2026-08-16 用户实测发现未预填）**：收银员角色对子表 `POS Profile User` **无读权限**，预填里的 `frappe.db.get_list("POS Profile User")` 抛 `Insufficient Permission`，promise 链静默断裂 → 什么都不填。修复：改为直接调用 POS Profile Link 下拉**同源**的 whitelisted 方法 `pos_profile_query`（`erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query`，返回 `[[name], ...]`），不再碰子表；pos1/Administrator 身份验证均返回唯一「收银方式1 - SH」→ 预填生效。教训：**收银员最小权限下，前端不要用 `frappe.db.get_list` 查无读权限的 Doctype，优先复用 whitelisted 查询方法**

**POS 增值税配置（模式 A：标签价含税，2026-08-16）**：
- 现象：POS 发票净额=总额（如 960=960），不含 VAT；而手动建销售发票选「IVA - SH」会加 16% → 顾客多付、价签与实际收款不一致
- 根因：POS Profile（收银方式1 - SH）`taxes_and_charges` 为空；物料/公司也无默认税模板；模板 `IVA - SH` 与 `Mozambique Tax - SH` 重复（都是 16%、科目 VAT - SH）
- 模式 A（用户选定）：物料 standard_rate = 标签价 = 顾客实付价（含 IVA），税模板 `IVA - SH` 税额行置 `included_in_print_rate=1`（价内税）→ 系统自动拆分：1500 → 净 1293.10 + IVA 206.90，账上照记税、顾客不多付
- 实施：① 取消测试发票 `ACC-SINV-2026-00028`（今天用户测的、未收款、taxes 16% 非价内，取消后留档标 Cancelled）；② 修模板异常 docstatus（master 模板 is_submittable=0 但导入时 docstatus=1，锁死后续修改报 UpdateAfterSubmitError，归 0）；③ IVA - SH 行 `included_in_print_rate=1`；④ 停用重复的 `Mozambique Tax - SH`；⑤ POS Profile 挂 `IVA - SH`；⑥ install.py 新增 `configure_pos_tax()`（幂等，随 migrate 重放）+ v4 快照 pos_profiles 补 `taxes_and_charges: "IVA - SH"`
- 验证：销售发票实测 1500→净 1293.10+税 206.90+总额 1500 ✅；configure_pos_tax 幂等重跑不改变状态 ✅；三处 md5 一致 ✅
- 说明：快照无税模板段（历史缺口，重放靠 install.py 兜底）；付款单「业务编号」= Cheque/Reference No 所在节（Transaction ID 的翻译），仅银行类科目收付款时强制必填，现金类（Cash/E-MOLA）不用填

**本地 WSL 升级：my_custom_app → solua_home（2026-08-16，用户选方案 A 第 2 步）**：
- 源：从 Windows 工作区 `my_custom_app_example/solua_home` 复制到 `~/frappe-bench/apps/solua_home`（内容与生产/GitHub md5 一致）
- 踩坑①（import 失败）：扁平布局的 app 用 PEP 660 editable 装不上（finder 只映射 api/override/printing 子包、不映射顶层）——照抄 my_custom_app 的旧式机制：site-packages 里建**符号链接** `solua_home -> apps/solua_home`（+ egg-link 路径），`import solua_home` 即通
- 注册：sites/apps.txt + apps.json 手动加 solua_home（install-app 前置检查要求）
- 安装：`bench --site dev.localhost install-app solua_home`（redis 警告是噪音，安装本身成功）→ `bench migrate`（after_migrate 钩子全跑）→ `uninstall-app my_custom_app --yes`
- 踩坑②（服务起不来）：honcho 在任何进程退出时停掉全部——redis 端口被手动实例占用→bench 自带 redis bind 失败→全停；watch(yarn) 用系统 Node 18.19.1 不满足 frappe 的 Node≥24→报错退出→全停。解决：释放端口 + `export PATH=$HOME/.nvm/versions/node/v24.18.0/bin:$PATH` 再 `bench start`
- 踩坑③（pkill 自杀）：`pkill -f 'pattern'` 会匹配到执行命令的 bash 自身（命令行含同样字符串）→ 进程被杀、命令无输出；用字符类 `[0]` 规避
- 补 developer_mode=1（dev 站点应有）+ assets 软链 `sites/assets/solua_home -> apps/solua_home/public`（否则 /assets/solua_home/... 404）
- 验证：ping 200、端口 11000/13000/8000 全开、installed_apps 含 solua_home、Custom Field/189 条翻译/override 导入全 OK、资产 200
- 已知差异：本地 dev 站点是默认 demo 公司（`solua home`），**没有生产那套 IVA - SH 税模板/科目**（configure_pos_tax 只配置已存在的模板，不负责创建）——本地测 POS 含税需自行按生产建公司配置，或直接用生产做功能实测
- 旧 apps/my_custom_app 目录未删（已注销），如需彻底清理可删除

---

## 二、服务器环境信息

> 🚨🚨 **版本基准（2026-08-16 实测确认，最高优先级，勿再混淆）**
>
> | 环境 | Frappe | ERPNext | 分支 | 说明 |
> |------|--------|---------|------|------|
> | **生产** erp.solua.one | **16.27.0** | **16.28.0** | version-16 | **所有上线功能/定制/踩坑记录以此为准** |
> | **本地 WSL** `~/frappe-bench` | **16.27.0** | **16.28.0** | version-16 | 与生产**完全一致**，可作测试环境（注意：仍装着旧 `my_custom_app`，未升级 solua_home） |
> | **Windows 侧工作区** `C:\Users\Yang\solua-home\sites\erpnext` | — | **17.0.0-dev** | develop | **只是 git 子模块副本，不是运行环境**，勿据此判断版本 |
>
> 验证命令：服务器/本地 `pip show frappe`、`grep __version__ apps/erpnext/erpnext/__init__.py`；本地 `wsl -e bash -lc "cd ~/frappe-bench && bench --site all list-apps"`。
> ⚠️ 历史教训：本档案早期把「服务器 ERPNext 版本」误写成 17.0.0-dev（实为 Windows 副本版本），已更正为 16.28.0。

| 项目 | 值 |
|------|-----|
| **SSH 连接** | `ssh qq`（用户 `ubuntu`） |
| **Bench 目录** | `/home/frappe/frappe-bench/` |
| **Bench 用户** | `frappe`（通过 `sudo -u frappe -i` 切换） |
| **Bench 路径** | `/usr/local/bin/bench` |
| **操作系统** | Ubuntu 24.04.4 LTS |
| **Bench 版本** | 5.31.0 |
| **Frappe 版本** | 16.27.0 |
| **ERPNext 版本** | 16.28.0（`version-16` 分支） |
| **站点** | `erp.solua.one`（生产）、`erpnext.localhost`（测试） |
| **当前语言** | `zh`（中文） |
| **Node.js** | v24.18.0（nvm 管理，system node 仍为 v20） |
| **数据库** | MariaDB，db_name: `_62af7cb1044ac230` |
| **Supervisor** | 已配置 `/etc/supervisor/conf.d/frappe-bench.conf`，所有进程 RUNNING |
| **solua_home** | 0.0.1，已安装到 erp.solua.one 站点 |
| **GitHub 仓库** | https://github.com/a83986475/solua-erp.git |

### SSH 免密执行命令模式

```bash
# 执行 bench 命令（注意需要 source env/bin/activate）
ssh qq 'sudo -u frappe -i bash -l -c "cd /home/frappe/frappe-bench && source env/bin/activate && bench --site erp.solua.one <命令>"'

# 执行 supervisorctl 命令（ubuntu 用户有免密 sudo）
ssh qq 'sudo supervisorctl status'
ssh qq 'sudo supervisorctl restart all'

# 数据库查询
ssh qq 'mysql -h 127.0.0.1 -u _62af7cb1044ac230 -pUwwJaHWYXIL21g5O _62af7cb1044ac230 -e "SELECT ..."'
```

---

## 三、本地 WSL2 环境信息

| 项目 | 值 |
|------|-----|
| **操作系统** | Windows 11 + WSL2 Ubuntu 24.04 |
| **WSL 用户** | `yang` |
| **Bench 目录** | `~/frappe-bench/` |
| **Python** | 3.14.x |
| **Node.js** | 24.x（nvm 管理） |
| **Bench** | 5.31.0（pipx 安装） |
| **Frappe** | 16.27.0（`version-16` 分支） |
| **ERPNext** | 16.28.0（`version-16` 分支） |
| **Git 用户名** | yangyang7920 |
| **Git 邮箱** | a83986475@gmail.com |
| **开发站点** | `dev.localhost:8000` |
| **自定义 App** | `solua_home 0.0.1`（2026-08-16 已从 my_custom_app 升级，见会话记录） |
| **启动脚本** | `bash ~/frappe-bench/start.sh`（或 `bench start`，需 nvm Node 24 的 PATH） |

### 自定义 App `solua_home` 结构（最新）

```
~/frappe-bench/apps/solua_home/
├── __init__.py              # 模块入口
├── hooks.py                 # 事件注册（doc_events, extend_doctype_class 等）
├── boot.py                  # ★ 新增：extend_bootinfo（注入颜色列表等到 boot 信息）
├── api/
│   ├── __init__.py
│   ├── sales.py             # ★ 重组：销售相关 API（含 after_customer_created）
│   ├── stock.py             # ★ 新增：库存相关 API（含 auto_create_item_price）
│   └── pos.py               # ★ 新增：POS 自定义 API（含 scan_barcode_for_pos, create_test_data）
├── install.py               # ★ 安装/迁移入口（after_install, after_migrate）
│                            #   → 复用 setup.py（翻译 + 基础字段）
│                            #   → add_item_attributes() Cor 属性
│                            #   → add_variant_custom_fields() 5 个多规格字段
│                            #   → configure_item_variant_settings() 继承字段
├── setup.py                 # ★ 初始化函数库（add_translations/add_custom_fields，供 install.py 复用）
├── tasks.py                 # 定时任务
├── config/
│   └── docs.py              # 文档配置
├── override/
│   └── sales_invoice.py     # SalesInvoice 类重写
├── public/
│   └── js/
│       ├── solua_home.js # 通用前端 JS
│       └── pos_custom.js    # ★ 新增：POS 扫码选颜色自定义 JS（page_js 注册）
├── translations/
│   └── zh.csv               # 中文翻译 CSV（150+ 条）
├── locale/
│   └── *.po                 # 多语言 PO 文件
├── .gitignore               # Git 忽略规则
├── setup.cfg
├── requirements.txt
├── MANIFEST.in
└── README.md
```

---

## 四、翻译修复详情（完整版）

### 问题
服务器上（生产模式，supervisor/nginx）切换语言到 `zh` 后页面仍显示英文。

### 初步尝试（未生效）
- 运行 `compile-po-to-mo --locale zh --force` → `.mo` 文件重新生成了
- 但旧 `.mo` 文件内容不正确（只有 2006 字节英文国家名翻译）
- 导致 `get_all_translations('zh')` 返回空数据

### 真正修复
```bash
# 1. 删除旧的错误 .mo 文件
rm -f sites/assets/locale/zh/LC_MESSAGES/erpnext.mo
rm -f sites/assets/locale/zh/LC_MESSAGES/frappe.mo

# 2. 重新编译（强制从 .po 源文件生成）
bench --site erp.solua.one compile-po-to-mo --locale zh --force

# 3. 清理缓存
bench --site erp.solua.one clear-cache

# 4. 重启服务
sudo supervisorctl restart all
```

### 修复前后对比
| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| `get_all_translations('zh')` | 2,006 字节（英文） | **1,270,616 字节（中文）** |
| `.mo` 翻译条目数 | 只有国家名 | **8,418 条完整翻译** |
| 包含 "客户" 翻译 | ❌ | ✅ |

### 注意事项
- 命令是 `compile-po-to-mo`，不是 `compile-translations`（后者不存在）
- 参数是 `--locale zh`，不是 `--language zh`
- 需要 `--force` 强制重新编译
- `.po` 源文件在 `apps/erpnext/erpnext/locale/zh.po`（非 LC_MESSAGES 目录）
- `bench restart` 可能因 supervisor 权限失败，改用 `sudo supervisorctl restart all`
- 旧 `.mo` 文件可能损坏或不含中文，**删除后重新编译**是关键

---

## 五、服务器 Node 24 切换详情

### 背景
服务器系统 Node 为 `v20.20.2`（`/usr/bin/node`），但 ERPNext v16 要求 Node 24+ 才能 `bench build`。

### 操作
1. **nvm 已安装**：`/home/frappe/.nvm/`（之前已装 Node v24.18.0）
2. **更新 supervisor.conf**：添加 `environment=PATH=` 指向 nvm 的 Node 24（备份为 `supervisor.conf.bak`）
3. **更新 .bashrc**：`export PATH=/home/frappe/.nvm/versions/node/v24.18.0/bin:$PATH`
4. **重启验证**：socketio 进程确认使用 `/home/frappe/.nvm/versions/node/v24.18.0/bin/node`

### 验证
```bash
ps aux | grep socketio
# /home/frappe/.nvm/versions/node/v24.18.0/bin/node ...
```

---

## 六、solua_home 部署详情

### 部署步骤
1. 本地打包：`tar czf solua_home.tar.gz solua_home`（23K）
2. 传输：通过 SSH 管道 `cat | ssh qq "sudo -u frappe bash -c 'cat > ..."'`
3. 解压注册：`tar xzf` + 添加到 `apps.txt` / `apps.json`
4. Symlink：`ln -sf ... env/lib/python3.14/site-packages/solua_home`
5. 安装：`bench --site erp.solua.one install-app solua_home`
6. 迁移：`bench --site erp.solua.one migrate`（触发 after_migrate → add_translations）
7. 重启：`sudo supervisorctl restart all`

### 翻译完善
| 文件 | 扩充内容 |
|------|---------|
| `translations/zh.csv` | 从 48 条扩充到 150+ 条 |
| `install.py`（add_translations） | 约 100 条，覆盖销售/采购/库存/财务/制造/CRM/项目/人事/支持/通用UI/系统提示 |
| 代码质量 | 添加 try/except 错误处理，删除无用 import，修正 f-string 语法 |

### Git 初始化
| 操作 | 详情 |
|------|------|
| 仓库 | `https://github.com/a83986475/solua-erp.git`（原 erpnext-apps，2026-08-06 改名） |
| 分支 | `main` |
| 首次提交 | `8c9b266` → 初始提交：ERPNext 中文定制功能 |
| 20 个文件 | 1064 行插入 |
| `.gitignore` | Python / IDE / OS / Frappe 排除规则 |

---

## 七、待办 & 改进方向

| 优先级 | 事项 | 说明 |
|--------|------|------|
| 🔴 高 | ~~实现 POS 扫码颜色选择器~~ | ✅ **已完成（第六会话）**：前后端 + hooks + 手册全部落地 |
| 🔴 高 | ~~创建窗帘测试数据并实测~~ | ✅ **已完成（第七会话）**：生产实测扫码选色全流程通过（空态→扫码→弹窗→加购） |
| 🔴 高 | ~~真实收银员权限决策~~ | ✅ **已完成（第七会话）**：已给 `Sales User` 角色添加 Item Price **读权限**（仅 read，最小权限），并验证纯 Sales User 身份扫码正常 |
| 🟡 中 | ~~实现 install.py 的 `add_item_attributes()`~~ | ✅ **已完成**：Cor 属性自动初始化 |
| 🟡 中 | ~~实现 install.py 的 `add_variant_custom_fields()`~~ | ✅ **已完成**：5 个多规格字段 |
| 🟡 中 | ~~实现 install.py 的 `configure_item_variant_settings()`~~ | ✅ **已完成**：官方 API + 未配置才写入守卫 |
| 🟢 低 | ~~部署到生产服务器验证~~ | ✅ **已完成（第七会话）**：migrate + build 后扫码选色实测通过，三处代码一致 |
| 🟢 低 | ~~清理测试数据~~ | ✅ **已完成（2026-08-07）**：SHD 公司整体删除（含收银方式1-Test、CR-001 测试物料与库存） |
| 🟢 低 | **停用/删除 pos.test 用户** | pos1/pos2 已创建，pos.test 无可用 Profile（收银方式1-Test 已随 SHD 删除）；待确认后禁用或删除 |
| 🟢 低 | 同步 CSV/install.py 翻译 | 少量条目不一致（如 Ticket vs Ticketing），建议后续统一 |
| 🟢 低 | 清理 api/pos.py 中的 create_test_data() | 测试完成后删除，不属于生产代码 |
| 🟢 低 | 执行 `cleanup-erpnext-dup.bat` | 删除 `C:\Users\Yang\erpnext` 孤儿拷贝（需先关闭 IDE） |
| 🔴 高 | **SH 真实物料 + 库存** | 当前 SH 空库，正式营业前需建真实物料档案 + 盘点入库（新增待办，pos1/pos2 上线前提） |
| 🟡 中 | **配置快照推送到 GitHub** | config-snapshot/ 三份 JSON 建议推送到 solua-erp 仓库异地备份（新增待办） |
| 🟡 中 | **config-snapshot 补录收银员配置** | 快照 v3 之后新增的 POS Cashier 角色权限、pos1/pos2 账号、applicable_for_users 绑定未含，建议导出 v4 |
| 🔴 高 | ~~条码校验位修正 + 自动生成器~~ | ✅ **已完成（第十三会话）**：自动生成器（非变体无条码→自动生成合法 EAN-13）+ 现有条码 6901234567890→…892 修正 + 厂家错码自动容错（barcode_type 置空跳格式校验）+ 标签渲染错码强制 code128 原样 |
| 🔴 高 | ~~颜色池扩容 + 批量生成变体向导~~ | ✅ **已完成（第十一会话）**：Cor 6→16 色、缩写去冲突、色卡图字段、bulk_create_variants API + 物料列表向导按钮 |
| 🔴 高 | ~~折扣权限方案 C（收紧版）~~ | ✅ **已完成（第十二会话）**：allow_discount_change=1 + 行折扣保险补丁 + 审批门收紧（任何折扣 >0 都需管理员勾审批，阈值 15→0）+ A-F 测试通过 |
| 🟢 低 | **「折扣超限已审批」字段权限** | 若需限制只有管理员能勾选该字段，可加 Role 权限（当前任何能编辑发票的用户都能勾） |
| 🔴 高 | **POS 小票定制** | 58/80mm 热敏、Logo、NUIT/税务、支付明细、找零、退货小票（Print Designer） |
| 🔴 高 | **交班 Z 报告** | POS Closing Shift 打印格式（销售额/单数/支付方式合计/退货） |
| 🔴 高 | **付款方式补 M-Pesa/E-mola** | 莫桑比克主流移动支付，目前只有 Cash/卡/支票/电汇 |
| 🟡 中 | **PDF 生成器切 chromium** | Print Settings pdf_generator wkhtmltopdf → chromium（Print Designer 格式渲染） |
| 🟡 中 | **入库单 Purchase Receipt 格式** | 目前仅 Serial/Batch 专用，普通收货单补 Print Designer 格式 |
| 🟡 中 | **信头/公司信息** | Company Letterhead 填真实 NUIT/地址/电话，发票抬头 |
| 🟡 中 | **税模板确认** | IVA 税率与含税/不含税、小票税务信息显示 |
| 🟡 中 | **退货流程实测** | Return 单据 + Return POS Invoice 打印 |
| 🟢 低 | **Supplier Quotation / Stock Entry / Material Request 格式** | 按需用 Print Designer 补 |
| 🟢 低 | **价格标签布局美化** | 「价格标签 50x30 PD」当前为测试布局，需按实际标签打印机调整字体大小/位置/价格显示格式（第十会话遗留） |
| 🟢 低 | **标签打印机实打测试** | 设计器预览与 PDF 已验证，待接实体打印机打样确认（第十会话遗留） |

---

## 八、常用命令速查

### 本地开发
```bash
cd ~/frappe-bench && bash start.sh           # 启动开发服务器
bench --site dev.localhost migrate           # 数据库迁移
bench --site dev.localhost clear-cache       # 清理缓存
bench build                                  # 构建前端
```

### 服务器运维
```bash
ssh qq                                       # SSH 连接
sudo supervisorctl status                    # 查看进程状态
sudo supervisorctl restart all               # 重启所有服务
bench --site erp.solua.one backup            # 备份站点
bench --site erp.solua.one clear-cache       # 清理缓存
```

### 翻译相关
```bash
# 编译指定语言翻译（先删旧 .mo 再编译）
rm -f sites/assets/locale/zh/LC_MESSAGES/*.mo
bench --site erp.solua.one compile-po-to-mo --locale zh --force
bench --site erp.solua.one clear-cache
sudo supervisorctl restart all

# 构建完整前端（含翻译）
bench build

# 检查翻译是否加载
bench --site erp.solua.one execute frappe.translate.get_all_translations --args "('zh',)" | wc -c
```

### 更新 solua_home（Git 工作流）
```bash
# 本地
cd ~/frappe-bench/apps/solua_home
git add -A && git commit -m "更新说明"
git push

# 服务器
ssh qq 'sudo -u frappe -i bash -l -c "cd /home/frappe/frappe-bench/apps/solua_home && git pull && cd /home/frappe/frappe-bench && source env/bin/activate && bench --site erp.solua.one migrate && sudo supervisorctl restart all"'
```

---

## 九、关键踩坑记录（备忘录）

### 服务器翻译修复（关键！）
- `compile-po-to-mo` 生成的 `.mo` 文件可能不含中文翻译
- **必须删除旧 `.mo` 文件后重新编译**，才能得到正确文件
- 验证方法：`get_all_translations('zh')` 应返回 1.27MB+ 的数据
- `.po` 源文件路径：`apps/erpnext/erpnext/locale/zh.po`

### supervisor Node 路径
- supervisor 不加载 `.bashrc`，需用 `environment=PATH=` 指定 Node 路径
- 备份 supervisor.conf：`cp config/supervisor.conf config/supervisor.conf.bak`
- 重启用 `sudo supervisorctl restart all`（ubuntu 用户有免密 sudo）

### Python 3.14 f-string 注意事项
- f-string 内不能使用 `\"` 嵌套双引号（Python 3.14 语法错误）
- 改用单引号 `field.get('fieldname')` 或提取变量

### 传输文件到服务器（WSL → SSH）
```bash
cat /tmp/file.tar.gz | ssh qq 'sudo -u frappe bash -c "cat > /home/frappe/frappe-bench/apps/file.tar.gz"'
```

### 其他
- SSH 的 `qq` host 仅在 Windows 的 `~/.ssh/config` 中配置，WSL 内无法直接使用
- 复杂 Python 命令通过 SSH 执行时，建议先写成脚本文件上传再执行，避免转义问题

### hooks.py 操作守则
- `hooks.py` 使用**多行字符串**而非 `'\n'.join()` 避免转义地狱
- `hooks.py` 的 `doc_events` 字典闭括号要一一对应，多一个或少一个 `}` 都会导致 SyntaxError
- 修改 hooks.py 后必须做语法检查：`python3 -c "compile(open('hooks.py').read(), 'hooks.py', 'exec')"`
- 避免用 `sed` 直接修改 hooks.py 的 JSON-like 结构（多行替换容易出错）
- 推荐用 Python 脚本写文件替换 hooks.py 内容

### after_insert vs on_update
- **`after_insert`**：仅在**首次创建**时触发，适合：Variant 创建时自动生成价格、创建默认配置
- **`on_update`**：**每次保存都触发**，适合：数据验证、同步更新
- Variant 自动价格同步必须用 `after_insert`，否则每次编辑 Variant 都会重复运行

### frappe.db.exists 子表过滤
- **错误写法**：`frappe.db.exists("Contact", {"links": [{"link_doctype": "Customer", "link_name": name}]})`
- **正确写法**：
  ```python
  frappe.get_all("Contact", filters=[
      ["Dynamic Link", "link_doctype", "=", "Customer"],
      ["Dynamic Link", "link_name", "=", doc.name],
  ], limit=1)
  ```

### Item 价格相关
- **Template Item（has_variants=1）** 不能设置 Item Price
- 价格必须设在具体 **Variant** 上
- 批量设置方法：Selling → Item Price → ⋮ → Add Multiple Items
- 自动方案：`after_insert` 钩子从模板 standard_rate 自动创建 Variant 的 Item Price

### 创建 Custom Field 的正确 API
```python
cf = frappe.get_doc({
    "doctype": "Custom Field",
    "dt": "Contact",
    "fieldname": "is_billing_contact",
    "label": "Is Billing Contact",
    "fieldtype": "Check",
    "insert_after": "is_primary_contact",
})
cf.insert(ignore_permissions=True)
frappe.db.commit()
```
- Custom Field 创建后会自动添加数据库列，无需手动 ALTER TABLE
- 若 ALTER TABLE 失败，可能是数据库用户权限不足

### frappe.defaults.get_user_default("currency")
- 获取当前用户的默认货币的正确 API
- 不要用 `frappe.db.get_single_value("Currency", "default_currency")`（Currency 不是 singleton doctype）

### Item 条码查询：`Item` 主表没有 barcode 列（重要！）
- **错误**：`frappe.db.get_value("Item", {"barcode": barcode}, "name")` → 抛 `Unknown column 'tabItem.barcode'`
- **正确**：条码存在 `tabItem Barcode` 子表，查子表的 `parent`（= Item name = item_code）：
  ```python
  item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
  ```
- 与官方一致：`erpnext.stock.utils.scan_barcode()`（erpnext/stock/utils.py）

### 前端 page_js 钩子
- 注册：`page_js = {"point-of-sale": "public/js/pos_custom.js"}`（路径相对 app 根目录，含 public/）
- **开发模式**：直接生效，刷新页面即可
- **生产模式（supervisor/nginx）**：必须 `bench build` 后重启才生效（后端 Python 不需要）
- `frappe.require("point-of-sale.bundle.js")` 是异步加载，自定义 JS 需轮询等待 `erpnext.PointOfSale.ItemSelector` 就绪（最多 ~30s）

### 自定义字段存在性检查
- `frappe.db.has_column("Item", "custom_swatch_image")` 检查物理列是否存在（自定义字段会建列）
- 配合 `getattr(v, "custom_swatch_image", "")` 兜底，避免 `get_all` 指定不存在的字段报错
- 更语义化的替代：`frappe.db.field_exists("Item", "custom_swatch_image")`

### Item Variant Settings 配置 API
- 正确用法（与官方测试 `set_item_variant_settings` 一致）：
  ```python
  doc = frappe.get_doc("Item Variant Settings")
  doc.set("fields", [{"field_name": "item_group"}, ...])
  doc.save()
  ```
- 建议加守卫 `if doc.get("fields"): return`，避免每次 migrate 覆盖管理员手动配置

### onScan 重绑定（POS 自定义扫码）
- POS 每次刷新都会重建 ItemSelector 并重新执行 `bind_events`，不能只 detach 一次
- 正确做法：包装 `erpnext.PointOfSale.ItemSelector.prototype.bind_events`（先调用原方法，再 detachFrom + attachTo 自定义）
- `onScan.detachFrom(document)` 会移除 document 上**所有** onScan 监听器（含默认的），再 attach 自己的

### solua-home 子模块双目录问题
- `C:\Users\Yang\erpnext` 是从 `solua-home/sites/erpnext`（git 子模块）复制出的孤儿拷贝
- 复制子模块目录时 `.git` 文件（`gitdir: ../../.git/modules/sites/erpnext`）也会被复制，相对路径失效 → `fatal: not a git repository`
- 该目录被 IDE 占用时无法重命名/删除（`Device or resource busy`），需先关闭 IDE 再用回收站脚本清理
- 结论：**保留 solua-home 里的正式子模块，删除根目录孤儿拷贝**（内容已 md5 验证一致）

### Frappe `decrypt()` 的 `frappe.throw` 副作用（重要！2026-08-16 折扣收银反复弹「加密密钥无效」）
- **症状**：用 try/except 接住了 `decrypt()` 异常，但前端仍弹「加密密钥无效！请检查 site_config.json」，且功能其实正常（提交成功）
- **根因**：`decrypt()` 的 `except InvalidToken` 分支执行 `frappe.throw(...)`；`frappe.throw` 内部会先 `msgprint` 把消息写进 `frappe.local.message_log` **然后才抛异常**。调用方 try/except 接住异常后，message_log 里的消息已随 API 响应返回，前端 `frappe.call` 把 `_server_messages` 当服务端提示弹出
- **诊断方法**：临时给 `decrypt()` 打日志补丁（记录输入值 + `traceback.format_exc()` + 调用者栈）抓复现；定位到 `savedocs → submit → validate → _try_decrypt('solua2026')`
- **修复**：调用 `decrypt()` 前先判断值是否为 Fernet 密文（**固定以 `gAAAA` 开头**），非密文直接原样返回，绝不误触发 decrypt → message_log 零污染
- **推广**：任何封装 decrypt/encrypt 的工具函数都应先判密文格式，避免把明文/脏值喂给 decrypt 触发 throw 副作用

### 前端 pageview localStorage 缓存（重要！2026-08-16 反复“改了没生效”）
- **症状**：服务器代码已是新版，用户浏览器仍跑旧 page_js（pos_custom.js），Ctrl+Shift+R 也清不掉
- **根因**：`frappe/views/pageview.js` 在**生产模式**（`developer_mode != 1`）把整个 Page 文档（**含 page_js 自定义脚本**）缓存进 `localStorage["_page:<页面名>"]`，之后每次打开**直接用缓存不再请求服务器**；页面无 HTML 模板（无 jinja）时 `_dynamic_page` 从未置位 → 必被缓存
- **根治**：`override_whitelisted_methods` 包装 `frappe.desk.desk_page.getpage`（`solua_home/override/desk_page.py`），返回文档置 `_dynamic_page=1` → pageview.js 见标记跳过 localStorage 缓存（每页多一次小请求）
- **踩坑（403）**：override 函数必须带 `@frappe.whitelist()` 装饰器——handler 的 `is_whitelisted` 校验的是**替换后**的函数（whitelisted 集合在模块 import 时由装饰器登记）；漏装饰器会报 403「方法未申明 @frappe.whitelist()」，页面都打不开

### 前端 `flt` 是全局函数，不是 `frappe.utils.flt`（2026-08-16）
- **症状**：`frappe.utils.flt is not a function` TypeError，自定义 JS 卡死
- **原因**：Frappe v16 的 `flt` 是**全局函数**（`window.flt`，定义在 `frappe/public/js/frappe/form/controls/float.js`），`frappe.utils.flt` 不存在
- 修复：直接写 `flt(...)`（与 erpnext 自带 POS 代码一致）；同理 `cint` 也建议用全局函数或自行转换，避免踩同类坑
