# 报表导出跳回主页修复

2026-10-18，站点 `erp.solua.one`，配置补丁 commit：`b4ea9f2d5283aa92dc59a66df11724152a00ab19`。

原生 Query Report 的同步 Excel/CSV 导出通过 `open_url_post(frappe.request.url, args)` 向 `/` 提交 POST。生产 `/etc/nginx/conf.d/erp-ssl.conf` 的精确根路径规则按 ERP 域名无条件返回 `302 /app`，使导出请求在到达 Frappe 前跳回主页。已登录页面复现了该行为。

仅将该跳转限定为 ERP 域名的 GET/HEAD；POST 继续使用既有 `try_files ... @webserver`。精确补丁见 `my_custom_app_example/solua_home/deployment/nginx_erp_root_post.patch`。未同步应用文件，保留生产和本地已有的其他工作区变更。

恢复点：

- Bench 四部分备份位于 `/home/frappe/frappe-bench/sites/erp.solua.one/private/backups/`，共同前缀 `20261018_213149-erp_solua_one-`。
- config、database、public files、private files 均已核验非空并计算 SHA256；大小分别为 1031、5801748、324141263、268056 字节。
- 配置原件与发布 manifest 位于 `/home/frappe/frappe-bench/sites/erp.solua.one/private/deployment_snapshots/20261018-report-export-root-post/`。
- 配置 SHA256：修改前 `de5b8daecaddca789372410027ddbb4a7d1b52a8927d146001a608839b92b1c0`，修改后 `4ec84ceabff7bc873addeeb2aab22ef06c4050010141ca3f0fe849526aef3560`。

验证：

- 发布前确认备份目录没有子目录；手动快照未写入备份目录。
- ERP、官网、www 三个域名与 GET/HEAD/POST/OPTIONS 的跳转条件矩阵自检通过。
- `nginx -t` 通过，仅 reload Nginx；服务为 active。没有 migrate、前端构建或应用服务重启。
- HTTPS：ERP GET/HEAD `/` 仍返回 `302 /app`；未登录 POST `/` 由修复前 302 变为 Frappe 403，证明请求已交给应用并保留鉴权；官网 200，www 301 到官网。
- 原筛选条件下，已登录浏览器点击 Excel 下载后仍停留原报表；导出 POST 返回 200、6611 字节。用户明确确认“下载成功”。
- CSV 导出 POST 返回 200、1844 字节；浏览器自动化显示 `ERR_BLOCKED_BY_CLIENT`，未确认 CSV 文件落地。已恢复原报表页面。
- 浏览器下载事件等待超时，未取得本地文件路径；未打开 Excel 检查文件内容。没有修改报表计算逻辑或业务数据。

回滚时只恢复上述快照中的 `erp-ssl.conf.before` 到准确配置路径，通过 `nginx -t` 后 reload。回滚会恢复旧的根路径 POST 重定向问题。

## 后续全量入口审计

- 扫描了 Frappe、ERPNext 和 `solua_home` 的前端/后端导出、打印、下载调用。标准 Query Report、Report View、Data Import、文件打包、联系人 vCard、ERPNext 银行/生产计划等少数旧式 `open_url_post` 调用中，向 `/` 提交的 POST 均被本次 Nginx 修复覆盖；自定义单据表格、PDF、订单资料包均使用 `/api/method/...`，没有第二个根路径调用。
- 扫描了生产 `Client Script` 和 `Report` 数据库记录；没有发现自定义脚本包含 `open_url_post`、`frappe.request.url` 或 `/` 根路径导出调用。当前启用报表统计为 Script Report 191、Custom Report 1、Report Builder 7、Query Report 13；Solua 相关 Query Report 为 `Solua Business Totals`、`Template Stock Tree`、`Solua Delivery Summary`。
- 线上只读路由矩阵：ERP `/` 的 GET/HEAD 仍为 302 到 `/app`，POST/OPTIONS 已进入 Frappe；`/api/method/frappe.ping` 的 GET/POST 均为 200；自定义下载 API 未登录时返回权限/参数错误而不是主页跳转；`printview` 和 `/mobile` 均正常返回 200。
- 发现一个未被当前代码触发的潜在边界：Nginx 通用 `rewrite ^(.+)/$ $1 permanent` 会把任意带尾斜杠的 POST API 变成 301。现有前端扫描未发现带尾斜杠的 API URL，因此本次不扩大修改；如未来新增此类 URL，应直接去掉尾斜杠或把该 rewrite 限制为 GET/HEAD。
- `www.solua.one` 到 `home.solua.one` 的 301 是公开站点的规范域名跳转，不是 ERP 导出入口；ERP 前端使用 `erp.solua.one` 和相对 `/api/method/...` 地址。
