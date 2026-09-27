# ERPNext 定制开发操作手册

> **当前规范**：本手册仅记录当前开发、生产安全和已确认业务规则。xPos 客户端事件另见 [xPos 操作历史](xpos-client/OPERATIONS_HISTORY.md)；长期有效的安全经验见 [精简历史记录](docs/ERPNext-手册历史记录.md)。历史细节不代表当前生产状态。
>
> 版本基线：生产 ERPNext v16。最后整理：2026-09-23。此日期是文档整理日期，不是生产回读日期。

## 目录

1. [环境与职责](#1-环境与职责)
2. [安全边界](#2-安全边界)
3. [本地开发与 Git](#3-本地开发与-git)
4. [生产发布与回滚](#4-生产发布与回滚)
5. [定制开发约定](#5-定制开发约定)
6. [商品、仓库、价格与单据规则](#6-商品仓库价格与单据规则)
7. [xPos 运行规则](#7-xpos-运行规则)
8. [备份、恢复与日常验证](#8-备份恢复与日常验证)
9. [记录维护](#9-记录维护)

## 1. 环境与职责

### 1.1 当前架构

- Windows 工作区保存源码；Solua Home 的定制只放在仓库中的 `my_custom_app_example/solua_home`（Frappe 模块名 `solua_home`）。
- 生产 ERPNext 运行在主机别名 `qq`，站点为 `erp.solua.one`；生产 Bench 路径是 `/home/frappe/frappe-bench`。凡出现这个路径，均指 `qq` 生产环境。
- `frappe` 是生产 Bench、Python、pip、Node/yarn 及应用文件写入的执行用户。`ubuntu` 只用于只读检查和系统服务管理；Supervisor 重启等系统级操作按主机权限执行。
- 生产版本基线为 ERPNext v16。部署前须在生产回读实际版本；本地检查通过不等于生产行为通过。

### 1.2 工作证据

按证据强度分别报告：代码/差异检查、最小本地验证、生产文件与配置回读、已登录页面或 API 行为验证。某一层通过不能替代下一层，也不能把“发出命令”描述为“完成部署”。

## 2. 安全边界

- **禁止修改 Frappe / ERPNext 核心源码**；定制只写入 `solua_home` 或独立 xPos 项目。
- 生产改动必须有明确授权和精确范围。先确认目标站点、DocType、物料/仓库、文件和 commit；不因相似名称扩展范围。
- 不直接 SQL 写入业务 DocType、库存账、Item Price 或附件关联；优先用 Frappe DocType/API 与原生单据，并在独立进程回读。
- 不删除已有库存/交易引用的 Item 或 Variant；需要下架时先禁用并保留历史。修正颜色或编码不能直接改动已有库存流水所依赖的记录。
- 不在通用手册中给出递归删除 App、批量更新整套 Bench、删除站点、重装站点、强制覆盖新站点、杀端口进程或移除 scheduler 的快捷命令。确需维护时，先核实精确对象、依赖、备份和恢复方法；没有可验证回滚点就停止。
- 密码、API Key/Secret、Hub 密钥文件内容、个人账号、客户资料、完整备份、生产交易编号和未公开生产数据不得写入文档、截图或提交。
- 错误处理不能通过忽略权限、丢弃队列、删除失败数据或关闭无关校验来掩盖。

## 3. 本地开发与 Git

1. 先读调用链、hooks 与相邻实现，再选最小改动；扩展 Frappe 行为前先确认版本和当前钩子。
2. 在 `my_custom_app_example/solua_home` 修改；不在 `erpnext/` 或 `frappe/` 改业务逻辑。
3. 变更前后分别查看 `git status`、`git diff --check` 和精确文件差异。保留工作区中已有改动；提交时只暂存本任务文件。
4. 运行受影响功能的最小已有检查。涉及解析、权限、金额、库存或导入的分支，至少覆盖正常路径和关键失败路径。
5. 先提交经过检查的精确 commit。部署记录必须注明完整 commit，不使用含义不清的“最新版本”。

## 4. 生产发布与回滚

所有以下 `bench` 命令都在 `qq` 上由 `frappe` 用户执行；绝不在文档命令中连接其他主机。

### 4.1 发布前

1. 确认用户授权、站点 `erp.solua.one`、变更文件和目标完整 commit SHA。
2. 在 `qq` 检查应用仓库状态、当前 HEAD 和差异；有未提交改动、未知文件或目标不符时停止，不覆盖现场。
3. 用目标站点创建数据库及文件备份，确认备份文件存在且大小非零；记录路径、时间和校验信息，不复制备份内容到文档。
4. 对本地目标 commit 查看变更文件和差异；确认不含凭据、测试数据、无关文件及意外删除。先运行针对改动的最小检查。
5. 逐项判断是否需要 DocType/schema/patch 迁移、前端构建、缓存刷新和服务重启。不要把 `migrate`、全量安装钩子或全量构建当作固定步骤。
6. 若需要前端构建，必须在同一登录 shell 中加载生产 Node 24，并在构建前验证 `command -v node` 与 `node --version`。不要直接使用可能落到 `/usr/bin/node` 的 Node 20；无法证明当前 shell 使用 Node 24 时停止，不继续构建。

生产前端构建的最低检查：

```bash
sudo -u frappe -i bash -lc '
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm use 24
  command -v node
  node --version
  bench build --app solua_home
'
```

输出必须显示 Node `v24.x`；`sudo -u frappe -H` 或普通非登录 shell 不保证加载 nvm，不能替代上述检查。服务器已安装 Node 24 时优先复用现有安装，不重复安装或修改 supervisor；只有确认服务进程也错误使用 Node 20 时，才另行评估 PATH 配置。

### 4.2 发布与回读

1. 在 `qq` 只部署已审查的完整 commit；部署后读取 HEAD、工作树和目标文件，确认与批准版本一致。
2. 只执行判断为必需的迁移/构建；有失败或输出超出预期即停，不继续重启掩盖错误。
3. 按实际改动重启必要服务并清理相关缓存；确认服务健康、错误日志无新增相关异常。

`bench restart` 失败不能直接判定应用或 Supervisor 异常。它可能以 `frappe` 用户执行内部 `sudo` 检查而返回非零；重启前先用有系统服务权限的账号独立检查：

```bash
sudo supervisorctl status
sudo systemctl is-active supervisor
```

若 Supervisor 为 active，且 Web、SocketIO、Worker 等目标仍为 `RUNNING`，不要重复盲目执行 `bench restart`。从 `supervisorctl status` 读取生产实际程序组名，只定向重启本次变更需要的 Web/Worker 组；例如当前 Bench 常见形式为：

```bash
sudo supervisorctl restart frappe-bench-web:* frappe-bench-workers:*
sudo supervisorctl status
```

如果实际组名不同，以状态输出为准，不照抄示例；不要使用 `restart all`，也不要为解决 `bench restart` 的权限返回值去杀进程、重启数据库或 Redis。重启后必须再次回读所有目标进程状态及相关页面/API。

4. 对目标功能做生产回读：读取相关配置/记录，再用获准的页面或 API 流程验证关键行为。读取和行为验证分开记载。
5. 汇报完整 commit、备份位置、差异、测试、迁移判断、重启结果、回读结果及未完成项。

### 4.3 回滚

- 发布前记录精确的原 commit 与变更前文件备份；回滚只恢复本次变更范围，不覆盖同时存在的他人改动。
- 代码回退后重新执行必要的构建、缓存、重启和生产回读。
- 若迁移可能改变或丢失数据，只有经评估可恢复且获授权时才从对应站点备份恢复；恢复前核对站点、时间和文件，不用代码回滚冒充数据回滚。
- 无法确认回滚目标、备份完整性或数据影响时停止并升级处理。

## 5. 定制开发约定

- 优先使用 Frappe 标准 DocType、权限、事件钩子和 API。事件逻辑集中在 `solua_home`；需要扩展核心类时优先采用项目现有的 `extend_doctype_class` 模式，并保留父类行为。
- `hooks.py` 是注册入口；修改 hooks 或已导入的 Python 模块后，判断当前进程是否缓存代码，并在生产执行受控重启。
- 前端脚本按 DocType / Page 的实际加载入口注册；同一钩子若有多个 app 使用，追加合并，不覆盖其他 app 配置。
- 安装与迁移钩子必须幂等、范围明确；不得在普通部署中重建颜色池、批量覆写业务资料或创建测试交易。
- 新 API 明确权限、字段白名单、输入验证和错误返回；访客可访问的功能不得读取或暴露库存成本、内部价格及其他非公开数据。
- 动态界面文字使用翻译键；收银界面不得留下新增的硬编码英文。当前业务不使用 `APPLY TAX WITHHOLDING`。
- 自定义字段、角色和基础配置应由可重复执行的安装/迁移逻辑管理；执行前检查幂等性，避免重复建字段、角色或权限。
- 新 DocType、字段或权限变更要检查导出定义、模块归属、迁移结果和受影响角色；不要依赖生产手工改表单而不回存代码。
- 不用忽略权限或直接 SQL 写业务单据来绕过校验。需批处理时使用 DocType/API，先输出目标和差异，写后逐项回读。

## 6. 商品、仓库、价格与单据规则

### 6.1 商品与颜色

- 窗帘按条、窗帘杆按根、地板革按卷；数量使用整数。库存、销售和价格归具体普通 Item 或颜色 Variant，模板本身不作为库存商品。
- 窗帘颜色根据实物/供应商色卡确认。固定色号是独立字段，保留前导零；不能从葡语颜色名、货号或照片猜色。`Cor` 是 ERP 属性值，不能代替固定色号。
- 同色变体使用模板的唯一包装条码识别；原生 Item Barcode 留在模板，变体标签条码字段继承该值。不得把 SKU/货号冒充条码。
- 有库存或交易历史的 Item/Variant 不直接改名、删除或重建库存账。需纠正时先保留旧记录和历史，再用 ERPNext 原生单据迁转并逐项回读。
- `SH151060` 的生产色卡替换已由用户于 2026-09-23 确认完成：10 个颜色变体已关联新色卡，旧色卡已删除。该状态来自用户现场核查；本次未另行连接生产 API 回读。
- 新建多色款：先建立模板 Item 并启用变体，在模板属性表中一次列全确认的颜色，再生成 Variant；逐个核对 Variant 编码、属性、条码、价格和默认仓库。
- 新增全店共用颜色前先查 `Item Attribute` 的 `Cor` 字典；字典值含名称和缩写。建色后还须把它加到目标模板并明确生成的变体范围。
- 下架颜色用禁用保留交易历史；只有确认无库存、无交易引用时才考虑删除。修改颜色缩写会影响 SKU，先核对历史单据和条码引用。
- 窗帘 Variant 的包装条码和变体 SKU 是不同用途：遵循当前条码规则，不给颜色 Variant 擅自复制或生成独立条码；扫码映射须先在实际 POS 流程验证。
- 装箱换算用 UOM `箱/Caixa`（符号 Cx）。换算行只写在杆模板的 UOM 换算表并随模板保存自动同步到变体：`SH151138-2MS`、`SH151152-3MS` 为 1 箱 = 12 根，`SH151145-2MD`、`SH151169-3MD` 为 1 箱 = 6 根（2026-09-24 生产回读，20 个颜色变体全部继承一致）。变体自身的换算行优先于模板；后续改装箱数只改模板，不要单独改变体。
- 单据上直接选箱：销售订单/销售单/交货单行的单位可选 `箱/Caixa`，数量按箱录入，金额与库存按换算式折算（2026-09-26 生产回读：4 个杆变体 `get_conversion_factor` 返回 12/6）。拣货单明细行的单位同样可改（`Pick List Item.uom` 可编辑，保存时按该行单位重算换算式），但**数量必须一起按新单位填**：12 根改成箱要填 1，否则会变成 12 箱 = 144 根。
- Stock Settings 的 `allow_uom_with_conversion_rate_defined_in_item` 自 2026-09-26 起为 1（由 `install.py` 的 `configure_pick_list_printing` 幂等维护）：单据行的单位下拉只列出该物料 UOM 换算表里的单位。ERPNext 保证每个物料都有一行本位单位（本次回读 93 个物料、0 个缺行），所以不会出现空下拉；选到没有换算关系的单位被挡住，避免按 1:1 算错数量。

### 6.2 仓库与库存

仓库内最近一次生产回读（2026-09-18）记录的树为：

```text
Warehouse - SH
├─ Receiving - SH
├─ Dispatch - SH
├─ Zone A - SH
│  ├─ A-R01-S01 - SH
│  ├─ A-R01-S02 - SH
│  └─ A-R02-S01 - SH
├─ Zone B - SH
└─ Zone C - SH
```

同次回读记录 `Finished Goods - SH` 已停用，默认收货仓为 `Receiving - SH`；组仓库不能直接存库存，仓库间调整使用 Material Transfer。该记录不是本次实时回读。仓库和默认值必须在 `qq` 核对后才能用于新入库或交货；当前本地零售设置仍含旧的 `Finished Goods - SH` 默认值，不能据此推定生产配置。

POS 的允许负库存与禁止超卖是联动且含义相反的设置。修改或验收库存销售策略时，必须同时回读 Stock Settings 的 `allow_negative_stock` 和对应 POS Profile 的 `block_sale_beyond_available_qty`；不能只看一个开关，也不能照搬历史生产值。

窗帘期初库存曾在仓库记录中标记为已完成；不再列为待导入事项。再次操作前按物料、仓库回读实际数量，不按旧清单重复入库。

### 6.3 价格与成本

窗帘价格表映射：

| 业务含义 | Price List |
|---|---|
| 成本/采购 | `Standard Buying` |
| Home Store 价 | `Wholesale Selling 3` |
| 批发价 | `Wholesale Selling` |
| 建议零售价 | `Standard Selling` |

- 改价前精确枚举启用且可销售的 Item，排除模板、停用项和 LEGACY 项；备份后用 DocType API 只写差异，再逐物料回读价格表、金额、币种和 UOM。
- 不直接 SQL 写 Item Price。`Standard Selling` 是零售标签价/顾客含税实付价；税设置要以生产现状回读，不能把 Home Store 价写到 `Standard Selling`。
- 库存成本以 Bin/valuation 回读为准；采购价表不等于已入库成本。库存成本由业务提供的最终单位成本，不擅自分摊运费或清关费。

### 6.4 销售订单与交货

- 缺货时与业务确认后调整订购数量；不默认保留欠货待补送。
- 支持分批交货；区分订购、本次交货、此前已交付和剩余数量。以 ERPNext 原生 Sales Order、Delivery Note、Sales Invoice、Payment Entry 与库存账建立关联。
- 门店/地址/联系人等业务字段应从实际收货安排取得；回填只补空、不覆盖已有订单值。提交前检查关联单据、数量、仓库、权限与签收信息。
- 已关闭的交货单不因缺少开票安排而要求补填或重新打开；不要把开票计划写成所有历史/关闭交货单的必填项。对新交货单是否需要具体开票计划，按当前业务要求及生产表单验证确认。
- 对于开票、定金和尾款，沿用 ERPNext 原生发票、预收款、Payment Entry 与核销关系；不得把订金重复记作收入。

### 6.5 打印与导出

- 批发订单、交货单、销售单与拣货单应准确显示真实条码、SKU、固定色号和葡语优先描述；商品名称、SKU、固定色号、图片/二维码等显示项按各自独立开关控制。关闭的列应移除并重排，不留空白列。
- 订单与交货打印显示订购、此前已交付、本次和剩余数量时，来源应是单据关联与历史已提交交货单；关联缺失时显示未知，不伪造 0。
- 拣货单明细来自 `Pick List.locations`；导出数量/金额应为数值，并保护权限、DocType 白名单及 CSV 编码。
- 拣货单有两份自定义格式：「拣货单（颜色版）」供仓库/客户核对（图片、色号、条码、仓库、已拣数量），「拣货单（简版）」供现场拣货（只留 SPU、SKU、数量，底部两列确认框：拣货人 / 司机装车）。拣货单默认打印格式自 2026-09-26 起为「拣货单（简版）」。两份格式的修订都要在生产上用真实单据完整渲染一次，不能只做模板解析。
- 标准 DocType 的默认打印格式必须用 Customize Form / `frappe.make_property_setter` 设置（`Sales Order`、`Delivery Note` 都是这样）；不要直接写 `DocType.default_print_format` 字段，Frappe 校验明确禁止标准 DocType 这样做，历史遗留的直接写入值要清掉并改用 Property Setter。
- 拣货单数量列**以「箱」为主位**（2026-09-27 起）：简版里货号维护了整箱换算的行显示 `<b>1 箱/Caixa</b>`，下一行小字给本位数量 `(= 12 根)`；没有换算关系的行照旧显示 `12 根`；已按箱录入的行不重复提示；没有换算关系的行不显示折箱数，不能凭空除以猜测的装箱数。颜色版有独立的 `Un.` 列，所以保持本位数量为主，只在下面补一行 `(= 1 箱/Caixa)`。
- 拣货单合计（`Total Qty / 总数量`）始终是**本位单位**的和，不是箱数（箱数跨行/跨货号相加没有意义）：所有行单位一致时在合计后补上单位（如 `180 根`），单位混杂时留空。行改成箱主位后裸数字会被误读成箱，所以合计必须带单位。
- 折箱显示只属于拣货单：销售订单、销售单、交货单的数量保持业务单位（条/根/卷）不变，不套用折箱显示。
- A4 设计器的格式会隐藏共享 logo，改用公司抬头区里的 `.company-logo`，所以取数必须在打印快照之上补齐 `company.logo`：已提交单据的快照存于 logo 功能之前，公司抬头只有 name/nuit/address/phone；漏补就打出没有公司标识的单（草稿不走快照反而正常，最容易漏测）。2026-09-26 已修：`printing/a4_designer.py` 的 `get_a4_print_data` 统一走 `get_company_print_info(doc)`；生产回读：已提交订单渲染出 `.company-logo`，PDF 带 logo 124 KB / 去掉 logo 64 KB。
- A4 设计器另存的格式在保存那一刻就把模板固化进 Print Format，设计器代码后来新增的区块（公司抬头、边框开关等）不会进入旧格式；要拿到新效果只能重新加载设计设置并另存为新格式（只允许 create-only，不覆盖旧格式，历史格式保留）。
- 打印模板里的 `creation` 等字段是 datetime 对象，必须先转字符串再截取日期；直接下标切片会抛 `PrintFormatError`（模板第 4 行）让整张单据打不出来。本地测试若用字符串伪造字段会漏掉这个错，要补一个传入 datetime 的用例。
- 关于“信纸”的一个易错点：Frappe 剔除信纸的办法是 `frappe/utils/pdf.py` 里的 `soup.find_all(attrs={"class":"hidden-pdf"})`（**只在生成 PDF 的那条路上剥掉**）。打印 CSS（print.bundle.css）里**没有任何** `.hidden-pdf{display:none}` 规则，所以如果把信纸内联到页面里，它在屏幕和 Chrome 打印中都会显示。不过实测 `/printview` 返回的 body **根本不含信纸元素**（`get_html_and_style` / `get_context` 两种取法都不含），所以当前屏幕预览与纸面都没有重复公司抬头；不要为了“去掉信纸”去关 `Print Settings.with_letterhead`——需要时先确认信纸到底有没有渲染进 body。
- 打印里的公司 logo 目前指向私有文件 `/private/files/SOLUA LOGO.png`（`Company.company_logo`）。PDF 生成时 Frappe 会把当前用户可读的私有图片转成 base64 再交给 wkhtmltopdf，所以纸面/PDF 正常（2026-09-26 实测：带 logo 97 KB / 去掉 logo 37 KB）；但 on-screen 预览里它可能显示破图（跨站/无会话取私有文件 403、页面 https 而图片是 http 的混内容）。排查 logo 时先看 PDF 里图片是否存在，再判断是不是真问题。注意内联查找是按 File 记录的 `file_url` 原样匹配：文件名带空格时必须保持原样的 `/private/files/SOLUA LOGO.png`，一旦被 URL 编码成 `%20` 就匹配不上，wkhtmltopdf 会以匿名请求取图并得到 403，logo 会真的丢掉。
- 打印格式所属 Module 必须是真实存在的 Module Def；改格式先渲染/预览，再在生产读回。
- 用 JSON 文件部署自定义打印格式时，必须同时带上 `"custom_format": 1`、`"print_format_type": "Jinja"`、`"standard": "No"`。缺了这几项 Frappe 会把它当成「Print Format Builder」格式：`html` 照样存进数据库，但渲染时**被静默忽略**，页面回退成原生默认版式（逐字段排布 + 自动 `Print Heading`），从外观看不出是同一个格式，极易误判成「格式没生效」。判断依据：渲染结果里出现 `data-fieldname=` 或 `print-heading` 就是走了默认版式。2026-09-27 实证：新格式 `客户订单确认单（公司抬头-新）` 第一次部署就是这个原因。
- 站点 PDF 管线（`frappe.utils.pdf.get_pdf` / wkhtmltopdf 0.12.6 + 15mm 页边距 + `--print-media-type`）会把整页 HTML 统一缩放到 CSS 尺寸的约 **0.77 倍**（实测：100mm 宽的方块出图 76.9mm；`.solua-global-logo` 的 15.4mm 出图 11.8mm），而浏览器打印（Chrome）是 1:1。因此**不能用浏览器打印出来的样张去核对下载 PDF 里的毫米尺寸**；CSS 里的毫米值要按实际打印路径来定，两者相差约 23%，不要为此反复改 CSS。
- 公司共享 logo 的基准尺寸是 `.solua-global-logo` 的 **15.4mm × 12.3mm**；标题（`h2`）**金色 `#99732c` 居中**，与 logo 同行（行高 12.3mm）。这个版式照客户确认的销售单样张（Chrome 打印，logo 落在纸面 11.9mm 处、标题中点 = 页中点）定的。
- **logo 不能直接绝对定位在 `.print-format` 上**。`.print-format` 在屏幕预览里带 padding（实测 0.2in ≈ 19.2px，正文因此从 19px 处开始），而 `position:absolute;left:0;top:0` 锚的是**边框盒**——logo 会落在内容区之外、贴着容器左上角、并压住下面第一行标题（2026-09-27 实际症状：黑 logo 捅进金色标题）。正确写法是垫一个零高度定位盒承载 logo，标题占 12.3mm 行高并垂直居中，两者自然对齐（实测 logo/标题 top 均为 83px、垂直偏移 0px、标题居中跨满 555px 内容宽）：
  ```css
  .print-format{position:relative}
  .print-format .solua-brand{position:relative;height:0;margin:0}
  .print-format .solua-brand .solua-global-logo{position:absolute;left:0;top:0;width:15.4mm;height:12.3mm;object-fit:contain}
  .print-format > h2:first-of-type,.print-format .company-header h2{min-height:12.3mm;margin:0 0 2mm;
      display:flex;align-items:center;justify-content:center;text-align:center;color:#99732c}
  ```
  这套规则写在 `get_solua_print_css()` 里（共享 CSS 在 body 中、晚于格式自带 css，等特异度时胜出），所以**一次修改就统一了所有手写批发格式**；A4 设计器的格式会把 `.solua-global-logo` 置 `display:none!important`，且标题在 `.brand-title` 里（选择器不匹配），版式不受影响。
- **小纸格式要自己关掉公司 logo**。共享 CSS 会在 body 里输出 `.solua-brand` + `.solua-global-logo`（15.4×12.3mm、绝对定位），A4 格式正好用它做公司抬头，但 `价格标签 50x30` 纸面只有 50×30mm，logo 会直接盖住商品名（2026-09-27 实测：logo 与 `.name-zh` 同为 top 23.21mm）。因为格式自己的 `<style>` 排在共享 CSS 之后，在该格式的 `<style>` 里加一行 `!important` 即可盖掉，**只改格式、不需要改代码或重启**：
  ```css
  .print-format .solua-brand, .print-format .solua-global-logo { display: none !important; }
  ```
  这份记录 2026-09-27 还做了规范化：`standard` 由 `Yes` 改为 `No`。原先 `standard=Yes` 时任何 `doc.save()` 都会被 `Standard Print Format cannot be updated` 拦下，只能绕过校验写库；改成 `No` 后（仓库 JSON 与生产记录一致）就能正常保存，也和仓库里其它格式文件保持一致。
  另一种写法是 `{{ get_solua_print_css(with_logo=False) }}`（`printing/wholesale.py` 已支持该关键字参数，默认 True），但它依赖代码已部署+重载；改 DB 里的 `raw_commands` 不会触发代码重载，所以**在运行中的 worker 还没加载新函数时改用它会直接 TypeError 让整张标签打不出来**。稳妥顺序：先部署并确认 worker 已重载，再改调用方式。
- 共享 CSS **不包含 `@page`**，所以每份手写批发格式必须自带 `@page{size:A4;margin:12mm}`；缺了页边距会走 Frappe 默认 15mm，位置和样张对不上。`批发销售单（颜色版）新版` 与 `批发销售单（颜色版）` 已于 2026-09-27 补齐；后者原先是**只有数据库、没有磁盘源文件**的手建记录，2026-09-27 已从生产导出为 `print_format/sales_invoice_wholesale_color/sales_invoice_wholesale_color.json`（字段与 key 顺序、1 空格缩进、CRLF 行尾、结尾不加换行都对齐仓库里其它格式文件），以后从文件重导不会再丢 `@page`。
- `format_print_money(value, currency=None, precision=0)` 必须接受 `precision` 关键字参数。打印模板会写 `format_print_money(item.rate, precision=0)`，不接受时整张格式在第 6 行抛 TypeError，单据**完全打不出来**（2026-09-27 修，涉及 `客户订单确认单（A4新版）`、`-紧凑版`、`-紧凑无边框版` 三份；默认 0 位小数不变）。
- Print Designer 的格式（`print_designer = 1`）如果 `print_designer_print_format` 为 `None`，渲染时会抛 `the JSON object must be str, bytes or bytearray, not NoneType`——这是**空壳格式**（建了记录但从未在设计师里保存过内容）。识别办法：看 `print_designer_print_format` / `print_designer_settings` 是否为 None。处理方式是停用它，或把一份可用格式的 `print_designer_*` 负载拷过去（2026-09-27 把 `Sales Order DIY` 的负载拷给了空壳 `PRINT DESIGN 销售订单`）。
- 销售订单新格式 `客户订单确认单（公司抬头-新）`（module `Solua Wholesale`，Jinja，非默认、不影响旧格式）：共享 logo 左上 + 金色居中标题 + 两栏「公司 / 客户」表头，明细为 Artigo / SKU / EAN / Descrição / 数量 / Un. / 单价 / 金额。它的 CSS 自带 `@page{size:A4;margin:12mm}`（共享 CSS 不含 `@page`，缺了会多出约 3mm 偏移）。模板里 SKU 列必须写 `item.order_code or item.item_code`——`item.sku` 这个键在批发打印数据里不存在，渲染出来是 `no such element` 而不是报错。

### 6.6 员工标签打印操作

1. 打开 ERPNext/xPos 中当前门店已启用的 Barcode Printer（标签打印）入口，搜索或扫描目标物料；先确认显示的是正确 Item/Variant。
2. 选择已核实的条码、纸张/标签尺寸和打印机。打印前检查预览中的商品名、SKU/色号、条码及价格；价格以当前 Item Price 为准。
3. 先打印一张并用实际扫描设备验证条码能识别正确物料，再批量打印。更换标签纸或打印机后重新做单张校验。
4. 找不到物料、条码空缺/重复、价格不符或预览字段错位时停止打印，交由有权限的管理员修正主数据或打印格式；不要在标签端猜填。

员工只使用被授权的打印入口和价格/条码选项。不同物料类型的条码规则可能不同；不要把窗帘模板包装码规则套用到有独立条码的普通商品。

## 7. xPos 运行规则

- Hub 连接云端并持有受保护的同步凭据；Till 只连接 Hub 局域网地址，不保存 ERPNext API Key/Secret。任何安装包、日志、截图和文档均不得包含密钥内容。
- ERPNext 收银员身份用于业务归属与权限审计；同步服务身份只负责传输并应有最小权限。不要用 Administrator 或收银员个人 API 密钥同步。
- 退货最终确认需经理审批；任何大于 0 的行/整单折扣需经理审批，且折后价不得低于成本。离线时没有可用经理账号就禁止折扣。
- 同步失败保留队列和业务数据，按本地 ID 到服务器单据的映射排查。扫码先精确查询本地条码数据；不得用临时联网回退掩盖本地同步缺字段。
- 角色、Profile、同步权限和生产安装包状态可能变化；发布前按门店和当前构建回读，不复用旧 ZIP、旧密钥文件或历史 SHA。

### 7.1 用户与角色维护

- 由管理员在 User 表单创建员工账号，使用员工本人可管理的登录名；只分配岗位所需角色。不要把 Administrator 用作日常收银账号。
- 收银岗位通常需要销售/收款权限；是否需要 POS 开班/关班权限、采购或财务入口，应按当前门店流程单独核实。角色名相似不代表权限相同。
- 员工需使用 POS Profile 时，把用户加入该 Profile 的适用用户列表，并同时确认管理员仍可访问；列表非空时可能限制 Profile 对其他用户可见。
- 给员工改角色后，以该员工身份重新登录，验证菜单、开班、收银、退货审批和不能访问的操作。不能只凭角色配置页判断权限已生效。
- 密码通过受支持的用户邀请/重置流程交付；不把初始密码、邮箱清单或 API 密钥写入脚本、文档或日志。

### 7.2 翻译维护

- 少量界面词条可通过 ERPNext Translation 界面维护；批量或长期维护的词条放入所属 App 的翻译资源并纳入版本控制。
- ERPNext v16 通过脚本/API 维护翻译前，先回读当前 Translation DocType 的字段和语言代码；生产环境使用 `source_text`、`translated_text` 或 `zh` 等值时，以实际 schema 为准，不照搬旧版本字段名或 `zh-CN` 假设。
- 源文案必须与界面实际翻译键完全一致；保留 `{0}` 等占位符、HTML 标记和快捷键。不要为填满表格而翻译不面向用户的内部标识。
- 合并翻译前检查 CSV 列数、引号/逗号、重复源文本及目标语言；避免把空翻译覆盖成空字符串。对中文、葡语分别检查。
- 翻译资源更新后只执行所需的导入/构建步骤；切换到对应语言，在实际页面验证菜单、弹窗、错误消息和动态文本。未验证的语言覆盖率不能报告为完成。

### 7.3 xPos 日常使用与故障处理

- 收银前确认员工身份、门店 POS Profile、开班状态、当前商品同步时间和打印机状态；用已知条码做一次查找校验。
- 退货由收银员发起，按门店现行规则由经理完成最终确认。行折扣和整单折扣只在经理批准且折后价不低于成本时使用；离线状态没有可用审批人时不打折。
- 发现同步排队/失败时记录本地单据 ID、时间和错误信息，保留队列并通知管理员；不要清空本地数据、反复提交或改用个人 API 密钥。
- 断网时只按已验证的离线能力操作；恢复网络后观察队列同步完成并由管理员核对服务器单据。安装包、日志和截图不得包含同步密钥。

## 8. 备份、恢复与日常验证

- 每个生产发布批次开始时，对准确站点执行一次完整 Bench 备份，并核验 config、database、public files、private files 四个文件均存在且非空；同批次代码同步、migrate/build/cache/restart 与验收共用该恢复点，不按文件或测试重复完整备份。备份路径位于 `private/backups/`，不得将备份内容复制到文档或工作区。
- `private/backups/` 是 Frappe/Bench 专用保留区，只能含 Bench 生成的普通备份文件；任何智能体、脚本或人工操作都不得在那里创建子目录或写手动快照。手动回滚副本、Print Format 快照和部署文件只放在 `private/deployment_snapshots/<YYYYMMDD-task>/`。每次生产写入前先核对目标不在 `backups/`；若顶层发现目录，立即停止创建快照及 Bench 备份，确认归属、句柄、时间和哈希后再原样原子迁移，不删除、不合并。
- 每个发布批次开始时仅做一次完整 Bench 备份并核验 config、database、public files、private files 四文件存在且非空；同批代码同步、migrate/build/cache/restart 与验收共用此恢复点，不按文件/测试重复备份，也不能用手动目录模拟备份。A4 设计器只允许 create-only，校验/渲染失败须数据库事务 rollback，不为每次新建格式做完整备份；后续格式变化克隆另存新版本，不能原地覆盖。仅新发布批次、数据库迁移或重大生产变化使恢复点失效时才重新完整备份。
- 恢复前再次确认目标站点和备份日期；先在可恢复副本验证。恢复会覆盖数据，须有明确授权，并记录恢复后的站点健康和抽样业务回读。
- 库存、价格、物料、附件、单据等批量操作先预览拟变更清单并检查重复；写入后读取每一目标记录或可审计全量结果。
- 验收至少覆盖受影响角色、正常路径、权限边界和失败路径；部署报告明确是本地检查、服务端回读还是页面/API 实测。

## 9. 记录维护

- 本节“当前规范”优先于历史记录；历史回读必须带日期，过期或冲突的生产事实标记“待生产回读”。
- 主手册只保留可复用的操作规则，不追加逐次聊天、完整 SHA、交易编号、事故流水或临时待办。
- xPos 客户端事件归入 [xPos 操作历史](xpos-client/OPERATIONS_HISTORY.md)；通用安全经验归入 [精简历史记录](docs/ERPNext-手册历史记录.md)。涉及仓库外个人笔记时，只作为原始需求来源，不自动当作当前配置。
