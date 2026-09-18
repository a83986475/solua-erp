# xPOS 只读诊断摘要（2026-09-17）

## 实际运行 exe / 版本

- 实际运行进程：`C:\xpos\X POS.exe`
- 文件版本 / 产品版本：`1.0.9`
- 实际加载包：`C:\xpos\resources\app.asar`
- 当前 `app.asar` SHA-256：`4CB3A05B5BA8F1BCD2034EF93D880EF3BDD534DFF9131860489B5DBB8C7063F5`
- 结论：当前运行包与已核对的 2026-09-17 包一致，不是旧 `app.asar`。具体“删除检查分页/父子表”修复是否包含在该包内，未确认。

## 登录 / 会话账号证据

- 当前截图只显示 `POS Profile=收银方式1 - SH`、Company 和 Opening Cash Balance，没有用户名；POS Profile 不是收银员账号。
- 源码显示 Electron 会话从本地 `last_logged_user` 读取用户，再查询本地 `pos_users`；本轮未取得 `last_logged_user` 的实际值，因此真实收银员账号未确认。
- `xpos@127.0.0.1:3307/xpos_local` 是本地数据库服务账号，不是收银员账号。
- ERP 同步账号、收银员账号、Hub/Till 节点角色是三类不同身份；本轮未输出任何凭据。

## Open Shift 原因

- 已确认当前页面是“已通过本地认证、但当前用户没有已打开班次”的 `OpeningDialog`，不是登录页。
- 路由先检查认证；POS 状态随后按当前用户检查本地 open shift，查不到时显示 Open Shift 页面。
- 未点击 Open Shift，因此没有创建班次或业务记录。

## 语言选项原因

- 当前桌面包的 Setup、Login、Open Shift、Settings 页面源码均没有语言选择器。
- 翻译函数只从 `window.xpos._messages` 取值；未取得翻译时回退到英文。截图中界面英文、业务数据中文与此一致。
- 结论：当前运行包缺少可见语言入口已确认；是版本设计还是回归，未确认。

## 图片失败链路

- 当前截图停留在 Open Shift 页面，没有商品卡，因此不能从截图确认商品图片失败。
- 源码显示商品图片来自本地商品记录的 `image` 字段；本轮没有完成某个失败商品的“数据库字段 → 拼接 URL/代理 → 只读 GET 状态”核对。
- 因此图片字段为空、404、403 或网络问题均未确认，不能归因。

## 403 / 404 / 525 根因

- 日志 `C:\Users\Yang\.codex\attachments\f167a052-50d2-4118-93d7-9f797829566a\pasted-text.txt` 显示：多个子表删除检查在 19:19–19:38 反复 HTTP 403；`POS Users` HTTP 404；`Companies` 在 19:31:28 HTTP 525。
- 403 已确认是删除检查请求被服务器拒绝；日志没有实际请求路径、响应体或父 DocType 权限信息，因此父权限、子表权限、路由或角色范围尚未区分。
- 404 已确认对应路由/DocType 未找到；不能仅凭 `POS Users` 名称断言服务器缺少某个具体 DocType。
- 525 已确认是代理到源站的 TLS/连接握手失败；不能仅凭 525 断言证书已过期。
- 重复出现符合同步周期重试；具体删除检查修复是否实际运行，未确认。

## 未同步交易数量 / 风险

- 上一次只读状态曾确认 `pendingPushCount=0`。
- 本轮未取得新的待上传交易数量；当前截图只显示 `Syncing: Brands`，日志也未显示具体待上传销售交易数量。
- 因此目前没有证据证明存在未同步交易，但也不能保证当前数量仍为 0。最小后续动作应是只读查询待上传销售/采购队列及状态，不触发同步、不清缓存、不删除数据。

## 最小修复建议

- 先确认当前版本是否应提供语言选择器，再决定补入口或补翻译数据。
- 只读确认 `last_logged_user` 与对应 `pos_users`，不要把 POS Profile 当作用户名。
- 选一个失败商品完成图片字段、URL 和 HTTP 状态的只读链路检查。
- 对 403/404 记录真实请求路径、DocType、响应体和服务器权限后，再判断删除检查的最小修复。
- 对 525 单独核对源站 TLS/代理链路，不能直接按证书过期处理。

## 增量只读证据（收尾）

- 本地 `last_logged_user` 及其 `pos_users` 显示身份/角色：未确认。阻碍是当前客户端没有可用的只读调试通道，本地数据库凭据受系统加密；本轮未进行权限提升、服务操作或修复，也未输出任何凭据。
- 最新待上传交易队列：未确认。当前包源码确认队列表为 `pending_invoices` 与 `pending_purchases`，状态包含 `pending`、`syncing`、`failed`、`dead_letter`；本轮未取得数据库只读连接，因此没有数量或按状态汇总。既有记录中的 `pendingPushCount=0` 不是本轮新鲜读数。
- 商品图片候选及 URL 状态：未确认。当前截图停留在 Open Shift，没有可证明“本地显示失败”的商品；因此没有选定商品、没有读取图片 URL，也没有执行 HEAD/GET，避免猜测或下载图片。
- deletion check 路径证据：当前 `app.asar` 的同步代码确认先以 Frappe list 查询方式传入 `filters` 和 `limit_page_length: 0` 获取服务器列表，再按本地存储键比较并执行删除检查；异常统一记录为 `Deletion check failed for <label>: <error>`。已取得源码未包含完整实际 HTTP URL、父 DocType 参数或服务器响应体，因此 403 是否为父子 DocType 路径错误仍未确认；POS Users 的 404 也不能仅凭当前证据区分路由不存在、DocType 不匹配或权限层处理。
