# xPos 客户端修复报告（2026-09-18）

## 范围与基线

- 本次只操作 Windows 本地客户端与隔离测试副本，未操作 WSL。
- qq 上的 ERP 代码只做了只读确认，未改权限、业务数据或服务器代码。
- 受控源码目录：`xpos-client/frontend`。
- 源码来源：`https://github.com/kodlyft/xpos.git` 的 `develop`，基线提交 `67457ca89e6d61077abad0df532cab473d61e356`；源码目录在此基础上保留为可构建的 v1.0.9 客户端基线。
- 仓库中已有的 `.codex-xpos-*`、ASAR 和其他未知文件未删除、未移动；本次构建只使用 `xpos-client/frontend`。
- 生成目录、安装包、ASAR、数据库、配置、日志和凭据均由 `xpos-client/.gitignore` 排除，未纳入 Git。

## 根因与最小修复

1. 删除检查在统一同步层硬编码 `frappe.client.get_list`，忽略了资源自身的授权拉取端点。子表因此发出无权限列表请求（403），POS Users 则请求了不存在的标准端点（404）。删除检查现在复用每个资源的 `pullMethod` 并分页；子表使用 `xpos.api.sync.get_child_table_data`，POS Users 使用 `xpos.api.auth.get_pos_users`，保留删除比对、安全比例阈值和删除日志，不吞掉错误。
2. Companies 的 525 以前没有统一的有界重试和足够上下文。GET 请求现在最多重试两次；最终失败日志包含资源、端点、完整 URL、HTTP 状态和截短响应，不关闭 TLS 校验。
3. 商品同步只依赖 `image`，没有把当前服务端兼容字段 `custom_swatch_image` 归一化到本地图片链路，也没有认证下载后的离线缓存。客户端现在在同步和详情读取时做字段归一化，主进程使用已保存认证信息下载并缓存图片，渲染层优先使用缓存。
4. 语言状态和入口未恢复；新增本地语言持久化、翻译加载和用户菜单/开班页选择器。
5. 未开班时界面缺少明确的已认证收银账号和切换入口；OpeningDialog 现在显示当前账号并提供显式 `Switch account`，未开班不会自动强制回登录页。

## 主要修改文件

- 同步：`frontend/electron/sync/syncEngine.ts`、`frontend/electron/sync/syncConfig.ts`
- 图片 IPC/缓存：`frontend/electron/imageCache.ts`、`frontend/electron/main.ts`、`frontend/electron/preload.ts`、`frontend/src/services/electronBridge.ts`
- 图片字段与 UI：`frontend/src/stores/itemStore.ts`、`frontend/src/types/pos.types.ts`、`frontend/src/views/PosView.vue`、`frontend/src/components/items/ItemImage.vue`、`ItemCard.vue`、`ItemListRow.vue`
- 语言和账号 UI：`frontend/src/lib/locale.ts`、`frontend/src/components/LanguageSelector.vue`、`frontend/src/components/Navbar.vue`、`frontend/src/components/dialogs/OpeningDialog.vue`、`frontend/src/main.ts`
- 基线与排除规则：`README.md`、`baseline-manifest.md`、`.gitignore`、`frontend/package.json`（版本对齐到 1.0.9）

## 验证证据

在 `xpos-client/frontend` 执行：

- `corepack yarn typecheck`：通过。
- `corepack yarn test:run`：357 个测试全部通过。
- `corepack yarn build:electron`：通过。
- `corepack yarn run pack`：通过，Electron ASAR 完整性 fuse 保留。

在 `C:\xpos\test-repair-20260918` 的独立 Windows MariaDB 3308、独立 user-data 和隔离 mock 服务中验证：

- 语言：选择中文后 `document.documentElement.lang=zh`，数据库设置 `ui_language=zh`，重载后仍为 `zh`。
- 账号/开班：未开班页显示已认证的测试收银账号和 `Switch account`；点击后回到登录页；隔离测试账号能重新登录并开班。
- 图片：测试商品的本地 `image` 可渲染为 1x1 图片；认证下载写入 `image-cache`，停止 mock 服务后同一图片仍能从离线缓存读取。
- 删除安全：失败同步后测试商品和测试收银账号仍存在；待同步发票和采购队列均为 0；没有发生误删。
- 端点选择：隔离日志中子表使用 `xpos.api.sync.get_child_table_data`，POS Users 使用 `xpos.api.auth.get_pos_users`；该轮日志没有 403/404。
- 525：Companies 产生 `retry 1/2`、`retry 2/2` 后才记录最终失败；mock 日志显示每轮 3 次请求，最终日志包含 `status=525`、端点、完整 URL 和截短响应。
- 测试 MariaDB、mock HTTP 服务和测试客户端进程已停止；隔离测试目录保留作为证据，未删除。

## 备份与产物

原始 v1.0.9 基线备份：`C:\xpos\backups\xpos-20260918-baseline\`

- `app.asar.v1.0.9`：10,267,328 bytes，SHA256 `4CB3A05B5BA8F1BCD2034EF93D880EF3BDD534DFF9131860489B5DBB8C7063F5`
- `schema.sql`：32,222 bytes，SHA256 `FF036ED8F610BA3CD10BC80C0CB7A4F199F238035E4F7162896D3C2E7EE387DD`
- 两份本地 DB 配置副本：未输出配置值；两份 SHA256 均为 `90BB0B75CF9E2F14FD4880F5A92466A32FFF8C08B89F612DA6EA66A02A00F184`
- `app_extracted-v1.0.9`：当前安装解包应用的完整留档。
- 回滚副本：`app.asar.pre-repair-20260918`，SHA256 同原始 `app.asar.v1.0.9`。

由于本地连接配置中的数据库密码是应用加密值，本次没有猜测或解密密码，也没有导出业务数据；结构备份以现有幂等 `schema.sql` 留档，当前数据库服务和数据未被修改。

新的客户端：

- `C:\xpos\resources\app.asar`：10,585,579 bytes，SHA256 `BDA52E10F0F394F24AABCEE420B4C11567934861153E5CE45F5AD6B8BCC6E957`
- 同一构建源文件：`xpos-client/frontend/release/win-unpacked/resources/app.asar`
- `X POS.exe`：`xpos-client/frontend/release/win-unpacked/X POS.exe`，SHA256 `538F2184A510EEF9FFA271C6F5FEFCC5184059BF212540E18565D7B0D324E69A`

Hub/Till 角色包使用全新外部目录生成，没有运行会删除固定目录或生成密钥的旧脚本，也没有覆盖原有 `release`：

- `C:\xpos\builds\xpos-repair-20260918\XPos-Hub-Setup.zip`，SHA256 `702EF515AD9E1C18D5424A101385566D42377406C7E56AE1D2E23E8ED2F07D30`
- `C:\xpos\builds\xpos-repair-20260918\XPos-Till-Setup.zip`，SHA256 `DF5CD54F1B824A36BCD640D9B98E0896D29E6BEDE54DF0315A51C150B736C7A2`
- 两个角色目录各自的 78 项 `SHA256SUMS.txt` 均已校验通过。

## 仍需人工验证

- 在不影响生产的窗口，用真实测试 API key 连接 qq，确认一次完整增量同步和删除同步；重点观察上述子表、POS Users 和 Companies 525 日志。
- 用真实已有商品确认 `custom_swatch_image` 和 `image` 两种字段下的图片下载、缓存和离线显示。
- 在干净 Windows 测试机安装 Hub/Till 包后做一次安装器、MariaDB 初始化、登录、开班和打印回归。

## 2026-09-18 同步错误 follow-up

18:14 UTC 的新日志不是之前的删除检查问题，而是三个客户端/服务端接口契约不一致：

- `xpos.api.pricing_rules.get_active_pricing_rules` 旧接口硬编码查询不存在的 `apply_recursion` 列；客户端已切换到 qq 上已有的 `xpos.x_pos.api.pricing_rules.get_active_pricing_rules`，并把新版返回值归一化到现有离线定价引擎格式。
- `Exchange Rates` 的配置值误带 `date desc`，统一请求构造又追加 `asc`，形成 `date desc asc`；配置已改为字段名 `date`。
- `Modes of Payment` 把当前服务端不存在的父表字段 `pos_tender_currency` 放进列表字段；已移除该字段，收银端仍按现有发票币种回退逻辑工作。

Follow-up 验证：类型检查通过；完整测试 358/358 通过；Electron 构建和打包通过。qq 仍未修改。

- follow-up 回滚副本：`C:\xpos\backups\xpos-20260918-followup-sync\app.asar.pre-followup-20260918`，SHA256 `BDA52E10F0F394F24AABCEE420B4C11567934861153E5CE45F5AD6B8BCC6E957`
- 当前安装 `C:\xpos\resources\app.asar`：10,591,107 bytes，SHA256 `2B362E93E15C7BF6E29473464C404BA8AD0DB9F10D16F2D62D509BAB86A8D548`
- follow-up Hub 包：`C:\xpos\builds\xpos-repair-20260918-followup-sync\XPos-Hub-Setup.zip`，SHA256 `D81F7D064430399F4F7D53459E63C4E4F7BDF1280E7DFB9C1AA93FABD75BD34B`
- follow-up Till 包：`C:\xpos\builds\xpos-repair-20260918-followup-sync\XPos-Till-Setup.zip`，SHA256 `0F1F0B9F70CEE3F2466A319E19C7526695645F2075DC9F51E6C036C230F751D2`

更新本机时发现用户已启动 `C:\xpos\X POS.exe`，已关闭该明确的客户端进程后完成替换。两个当前 DB 配置的非密码字段仍与基线一致、端口仍为 3307，未残留隔离测试端口或测试库；客户端运行期间重新序列化了加密密码字段（仍为 `enc:v1:`），明文未读取、未输出、未入库。
