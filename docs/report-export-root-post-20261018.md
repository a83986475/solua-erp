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
