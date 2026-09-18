# 本地定制收尾审计（2026-09-18）

## 1. 审计范围与基线

- 仓库：`C:\Users\Yang\solua-home\sites\erpnext`
- 远端：`https://github.com/a83986475/solua-erp.git`
- 分支：`develop`
- 审计起始 HEAD/远端：`456e1c3057`
- 已知正式定制提交：`6067bc989`（窗帘色卡和销售流程）
- 已阅读：`ERPNext 定制开发操作手册.md` 第 17–19 章、`xpos-readonly-diagnosis-20260917.md`、`.gitignore`、`git status`、`git diff`
- 本审计不操作 WSL、生产业务数据或服务器；不修改 `erpnext/`、`frappe` 核心源码。

审计时根仓库没有待提交的已跟踪业务改动。审计过程中并行 xPos 任务产生了以下已跟踪改动，全部排除，不读取其内容、不暂存、不修改、不回滚：

- `xpos-client/frontend/electron/database/dbService.ts`
- `xpos-client/frontend/electron/database/schema.sql`
- `xpos-client/frontend/electron/sync/syncConfig.ts`

另有并行任务临时目录 `.tmp_delivery_audit/inspect.mjs`、`.tmp_delivery_audit/prod_readonly.py`，同样只记录、不暂存、不移动。

## 2. 分类结论

### 保留并提交

1. `my_custom_app_example/solua_home/`：正式 `solua_home` 应用的唯一权威源码位置；包括 hooks、API、override、打印格式、报表、零售设置、静态业务图片、前端 JS、翻译和最小测试脚本。
2. `my_custom_app_example/solua_home/tests/` 中的 5 个测试脚本和 `release_whitelist.txt` 已在审计起始 HEAD 中跟踪；它们可读、可重建，用于最小静态/行为检查，本次不重复新增。仅 `tests/artifacts/` 归档。
3. `xpos-readonly-diagnosis-20260917.md`：只读诊断证据和未确认项，不含凭据。
4. 本审计报告：记录分类、归档、哈希、测试和剩余风险。

### 仅本地保留，不提交

- `release/` 当前 Hub/Till 安装包：安装包和其中的 `app.asar` 不进入 Git；当前包哈希只记录在本报告的最终证据中。`release/_role-templates/` 是无凭据值的安装源模板，本次作为独立的 xPos 角色模板提交，不与 `xpos-client` 混合。
- `XPOS-HUB-KEY.json`：外置 Hub 凭据文件，禁止提交、复制到 ZIP、截图或写入文档；保留在原路径供安装流程使用。
- 生产配置快照、生产清理记录、历史上下文和本地输出：保留或归档，不作为本次源码备份。

### 归档（可恢复，不直接删除）

- `my_custom_app_example/solua_home/tests/artifacts/`：Chrome/Crashpad/缓存/本地数据库/会话运行时产物；其中可能含 Cookie 或会话信息，不能提交。
- 根目录 `.codex-*`、`.xpos_*`、`_tmp*`、临时 `.remote.vue`/`main.js` 构建输出和独立 ASAR：调试脚本、补丁、构建副本或临时导出，不是正式源码。
- `output/`、`outputs/`、`.freebuff/`、`config-snapshot/`、`dump.rdb`：本地输出、缓存、生产快照或数据库文件；不进入 Git。
- `release/` 的历史 `.bak-*` 安装包及重复构建物：与当前包重复，归档；当前包本身仅本地保留。
- 根目录旧的、已由本报告替代的未跟踪审计/迁移/安装记录：归档，不覆盖原文件内容。
- 已跟踪的 `curtain-swatch-single-bronze-antigo-v2.png` 保持原样，不删除、不改名；归档中的未跟踪 `curtain-swatch-azul-v2.png` 与它 SHA-256 同为 `48F1B05EBBD6FA4579FC6A01A1A42F1201ECD54AA414B487D900E39A493A95A5`，实际图中文字为“青古”，来源/命名不可靠，因此不作为新增权威色卡提交。

### 敏感或来源不明，禁止提交

- `XPOS-HUB-KEY.json`
- `config-snapshot/`
- `my_custom_app_example/solua_home/tests/artifacts/`
- 含本机路径、待完善导入数据或未确认业务映射的 `outputs/` 文件

## 3. 权威源码边界

正式 ERPNext 自定义应用只认：

`my_custom_app_example/solua_home/`

它与 `xpos-client/` 是两套应用。xPos 的并行改动不纳入本次提交；`xpos-client/frontend/src/stores/itemStore.ts` 审计时未见改动，当前不属于本次收尾范围。

## 4. 删除/归档安全规则

- 先生成归档清单和 SHA-256，再使用同仓库内明确的本地归档目录移动文件；不使用 `git reset --hard`、`git checkout`、`git add .` 或不可恢复递归删除。
- 归档目录加入精确 `.gitignore` 规则，避免把回收内容再次纳入提交。
- 不归档、不移动、不修改并行 xPos 路径和 `XPOS-HUB-KEY.json`。

## 5. 最终证据

- 归档目录：`.local-archive-20260918/`
- 归档清单/哈希：`1005` 个文件，`2,398,804,246` bytes；历史 Hub/Till 备份包、xPos 临时目录、生产快照、浏览器运行时产物均保留在该目录。当前 Hub 包 SHA-256：`A0027AB899E04969CBC54DADD9E05012F71AF1402FBC56BF7F3F7481CFDB9CF7`；当前 Till 包 SHA-256：`5129D231EFAAB1EBE1366EEB09A98C7BE8064DA274A74491B275786BCF93826C`。
- 正式 app 语法/最小测试：44 个 Python 文件 AST 通过、8 个 JSON 通过；`wholesale_forms_check.cjs`、`wholesale_page_check.cjs`、`wholesale_print_check.py` 全部 PASS；`git diff --cached --check` 通过。
- staged 文件清单与敏感模式扫描：48 个明确文件；不含 `XPOS-HUB-KEY.json`、`config-snapshot/`、`tests/artifacts/`、ASAR、安装包或并行路径；模板中只保留凭据边界和读取逻辑，没有凭据值。
- fetch/分叉检查：已执行 `git fetch origin develop`；无分叉，本地先保留并行提交 `895ddaa2eb`，随后新增本次提交。
- commit SHA：并行 xPos `895ddaa2eb`；正式 app `8477ac2e24`；审计/诊断/角色模板 `0b11e92bfb`。
- push 与 `git ls-remote` 回读：已成功执行 `git push origin HEAD:develop`，远端从 `0b11e92bfb` 更新到 `8c4d301f1f`；随后 `git ls-remote origin refs/heads/develop` 回读为 `8c4d301f1fe59a5ea6aedf18c6dbd038c9359565`。本行随后的报告更新提交会再次推送并回读。
- 剩余未处理项：并行 xPos 改动、`.tmp_delivery_audit/`、当前安装包和 Hub 外置凭据不纳入本次提交；其余以最终 `git status` 为准。
