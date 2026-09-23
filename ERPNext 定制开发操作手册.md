# ERPNext 定制开发操作手册

> **文档入口与权威顺序**：本手册是 ERPNext / Solua Home 的当前权威开发与业务记录；xPos 客户端故障、修复和验证时间线集中在 [`xpos-client/OPERATIONS_HISTORY.md`](xpos-client/OPERATIONS_HISTORY.md)。历史实施计划和会话摘要已并入/由本手册取代，旧版本可从 Git 历史恢复。Obsidian ERP 文件夹仍是未整理的原始个人笔记，不自动视为当前配置；凭据类文件不进入仓库。

> 版本: v16 | 最后更新: 2026-09-15 | 基于真实安装经验编写

> 🔄 **2026-08-06 变更记录：App 重命名 my_custom_app → solua_home**
> - **模块名**：`my_custom_app` → `solua_home`（Python 包名规范：小写+下划线，无空格）
> - **GitHub 仓库**：`a83986475/erpnext-apps` → **`a83986475/solua-erp`**（旧 URL 自动重定向）
> - **正式元数据**：app_title=`Solua Home 定制`、publisher=`Solua Home, Lda`、email=`admin@solua.one`
> - **影响面**：代码内 42 处引用、服务器 `apps/solua_home` 目录、`apps.txt`/`apps.json`/symlink、`tabInstalled Application`、`tabDefaultValue.installed_apps`（踩坑点：漏改会导致 `No module named 'my_custom_app'`）
> - **状态**：本地示例副本 / GitHub `721e541` / 服务器三处一致，POS 扫码选色与 get_items 拦截已验证生效
> - ⚠️ 本文档后续命令/路径中的 `solua_home` 即为当前模块名（历史操作如 `bench new-app solua_home` 按新名执行即可）

> 🔄 **2026-09-01 变更记录：补充 xPos 最终架构、同步排错、权限/翻译规则与商品建档记录**
> - 明确服务器 ERPNext 账号、xPos 本地账号、同步服务账号三者职责，避免把 `Administrator`、本地 `admin` 和收银员混用
> - 固化 POS Profile 可多人共用、收银员按登录身份核验；同步 API Key/Secret 只属于服务账号，不使用 cashier 的 API
> - 记录 POS Opening Shift 本地编号与服务器单据名称不一致、HTTP 417/500/403/404 的根因与安全恢复原则
> - 固化收银员最小权限、退货密码确认、任何折扣密码审批、直接采购收货的可见范围和离线审批规则
> - 补充全界面翻译验收、`APPLY TAX WITHHOLDING` 不启用，以及 2026-08-31 窗帘商品主数据导入结果

> 🔄 **2026-09-04 变更记录：补充 09-02 生产 UAT 轮次与 POS 退货修复、09-04 Hub/Till 角色安装包**
> - 记录 09-02 生产环境全链路 UAT（R1–R4）：开班→现金/折扣/退货→班次汇总→关班的真实数字与服务器证据（Error Log 提交记录、前缀残留核查）
> - 固化 POS 退货支付行被 ERPNext 重建导致的提交失败与 `CustomSalesInvoice` `-abs()` 修复（`extend_doctype_class` 注册，服务器 md5 已核对）
> - 补充 09-04 构建的 XPos Hub / Till 双角色安装包：角色划分、端口、U 盘密钥文件、Hub/Till 种子配对与 SHA256 校验
> - 遗留：R2 轮次的 3 张已取消发票与开班/关班单据仍在库，可运行幂等清理脚本删除（详见 18.8）

> 🔄 **2026-09-13 变更记录：归档 09-08—09-09 Hub/Till 产物与本地扫码修复**
> - 更新当前 Hub/Till 安装包的实际构建产物与 SHA256，明确 Hub 持有同步凭据、Till 只配置 Hub 地址
> - 记录本地 xPos 条码搜索的根因与修复：改用本地精确条码查询，离线扫码不再依赖在线回退
> - 补充部署路径、旧 `app.asar` 备份、验证结果和后续待办，避免把旧安装包或明文密钥当成最新版本

> 🔄 **2026-09-21 变更记录：首页交货单入口、销售单打印格式可编辑化、打印格式停用、单据类型列表瘦身**
> - 首页新增顶部「销售与交货」组：新建交货单（空白新建）+ 按销售订单开交货单（对话框选已确认且未全交的销售订单，调 `make_delivery_note` 后直接打开交货单）；原「订单与客户」组不再重复放置新建交货单
> - 「批发销售单（颜色版）」由 `raw_commands` + `raw_printing=1` 转为 `html` 模板 + `raw_printing=0`：此前打印下拉不显示该格式、预览/PDF 按钮被隐藏、编辑界面 HTML 为空，用户无法自行编辑
> - 停用 4 个多余销售单打印格式（Tax Invoice / Simplified Tax Invoice / Detailed Tax Invoice / Sales Auditing Voucher），保留 Standard、with Item Image、Return、PD Format v2（详见 19.10）
> - `/desk/doctype` 列表默认只显示在用模块：隐藏 19 个用不上的模块（Manufacturing/Projects/Assets/CRM/Website/Workflow 等，共 257 个 DocType），提供「显示全部单据类型」按钮；删表风险高（核心单据大量 Link 引用、升级会被重建），故不做任何 DocType 删除（详见 19.11）

> 🔄 **2026-09-15 变更记录：补充生产物料基础数据与颜色属性操作**
> - 定向创建缺失的 Item Group：`窗帘`、`窗帘杆`、`地板革`
> - 定向创建缺失的 UOM：`根`、`卷`；并将既有 UOM `条` 修正为只允许整数
> - 在生产 `Item Attribute: Cor` 中，为除 `Branco`、`Preto` 外的 14 个基础颜色增加 `Escuro`（深）与 `Claro`（浅）值，共新增 28 个，缩写保持唯一
> - 仅运行 `bench --site erp.solua.one console` 定向脚本并回读验证；未运行 `migrate`/`after_install`，未创建 Item 变体、库存或业务交易

---

## 📖 目录

1. [环境架构总览](#1-环境架构总览)
2. [版本要求速查（重要！）](#2-版本要求速查重要)
3. [WSL2 开发环境搭建](#3-wsl2-开发环境搭建)
   - [3.12 本地 v17 vs 生产 v16 差异注意点](#312-本地-v17-vs-生产-v16-差异注意点2026-08-16-已确认)
   - [3.13 Docker 版 ERP 已移除，自启已禁用](#313-docker-版-erp-已移除自启已禁用2026-08-16)
4. [日常开发工作流](#4-日常开发工作流)
5. [创建自定义 App](#5-创建自定义-app)
6. [定制开发模式](#6-定制开发模式)
   - [6.5 多规格（Item Variant）方案](#65-多规格item-variant方案)
7. [全面汉化方案](#7-全面汉化方案)
8. [部署到服务器](#8-部署到服务器)
9. [上线前核对清单（上线 SOP）](#9-上线前核对清单上线-sop)
   - [9.4 标签打印功能使用说明（员工培训）](#94-标签打印功能使用说明员工培训)
10. [常用命令速查](#10-常用命令速查)
11. [安装问题排查](#11-安装问题排查)
12. [服务器运维问题排查](#12-服务器运维问题排查)
13. [WSL2 开发环境问题排查](#13-wsl2开发环境问题排查)
14. [自定义 App 开发问题排查](#14-自定义-app-开发问题排查)
15. [开发问题排查](#15-开发问题排查)
16. [零售参数设置](#16-零售参数设置)
17. [xPos 桌面 POS 系统](#17-xpos-桌面-pos-收银系统electron)
18. [xPos 最终架构、同步排错与商品建档记录](#18-xpos-最终架构同步排错与商品建档记录)
19. [xPos 角色包归档与本地扫码修复（2026-09-08—09-09）](#19-xpos-角色包归档与本地扫码修复2026-09-0809-09)

---

## 1. 环境架构总览

### 分层架构

```
┌─────────────────────────────────────────────┐
│              浏览器 (Browser)                │
│        http://dev.localhost:8000             │
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│         Frappe Framework (WSGI)              │
│   Python + JavaScript + MariaDB + Redis      │
├───────────────────┬─────────────────────────┤
│   erpnext (核心ERP)  │  solua_home (你的)  │
│   ─── 不要修改 ───   │  ─── 所有修改在这里 ─── │
└───────────────────┴─────────────────────────┘
```

### 开发环境 vs 生产环境

| 环境 | 位置 | 用途 | 启动方式 |
|------|------|------|---------|
| **本地开发** | WSL2: `~/frappe-bench/` | 编码、调试、测试 | `bench start` (开发服务器) |
| **生产服务器** | 服务器: `/home/xxx/frappe-bench/` | 正式运行 | `supervisor` + `nginx` |

**核心原则：永远不要修改 `apps/erpnext/` 和 `apps/frappe/` 中的源码！**
所有定制都在自定义 App 中完成。

---

## 2. 版本要求速查（重要！）

> ⚠️ **实测经验**：ERPNext v16 的 `version-16` 分支（2026年7月）已更新依赖要求，和早期的 v16 不同。

> 🚨 **版本现状（2026-08-16 已确认，勿再混淆）**：
> - **生产 erp.solua.one = Frappe 16.27.0 + ERPNext 16.28.0（v16 家族）**——所有已上线功能、定制、踩坑记录均以此版本为基准
> - **本地 WSL 开发环境 = ERPNext 17.0.0-dev（develop 分支）**——与生产版本**不一致**！
> - 本地 v17 上测试通过 ≠ 生产 v16 行为一致，**一切以生产实测为准**；差异注意点见 **3.12**
> - 下表依赖要求是 **v16 安装** 所需（对齐生产时用）；本地 v17 若已装好可跳过安装章节

| 组件 | 版本要求 | 安装方式 | 验证命令 |
|------|---------|---------|---------|
| **Python** | **>= 3.14** | `deadnakes PPA` | `python3.14 --version` |
| **Node.js** | **>= 24** | `nvm install 24` | `node --version` |
| **npm** | (随 Node 自带) | - | `npm --version` |
| **yarn** | 最新版 | `npm install -g yarn` | `yarn --version` |
| **MariaDB** | 10.6+ | `sudo apt install` | `mariadb --version` |
| **Redis** | 6+ | `sudo apt install redis-server` | `redis-server --version` |
| **MariaDB 认证** | `mysql_native_password` | `ALTER USER` （见 3.4 节关键坑） | — |
| **bench** | 5.x | `pipx install frappe-bench` | `bench --version` |
| **uv** | 最新版 | `curl ... \| sh` | `uv --version` |

### 实际安装过程踩坑记录

| 错误信息 | 原因 | 解决办法 |
|---------|------|---------|
| `externally-managed-environment` | Ubuntu 24.04 PEP 668 保护 | 用 `pipx` 而非 `pip3` 安装 bench |
| `FileNotFoundError: 'uv'` | bench 5.x 依赖 `uv` 管理虚拟环境 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `pkg-config is not installed` | 编译依赖缺失 | `sudo apt install -y pkg-config` |
| `Python>=3.14,<3.15` not satisfied | v16 分支最新版要求 Python 3.14+ | 安装 Python 3.14 |
| `Expected node >=24` | v16 分支最新版要求 Node 24+ | `nvm install 24` |
| `Access denied for user 'root'@'localhost'` | MariaDB 使用 unix_socket 认证 | 执行 `ALTER USER ... IDENTIFIED BY` |
| `Error 111 connecting to Redis port 11000` | bench 的 Redis 与系统 Redis 不同 | 先用 `bench start` 启动再安装 |
| `Address already in use` (11000/13000) | 上次 WSL 关闭后进程残留 | `sudo fuser -k 11000/tcp 13000/tcp` |
| `schedule.1 stopped (rc=0)` 后全部关闭 | honcho 因任何进程退出而终止全部 | 从 Procfile 移除 `schedule:` 行 |
| `syntax error near ('` | PATH 包含 Windows 路径括号 | 设置干净 PATH，不引用 `$PATH` |
| `node: not found` | 新终端 nvm 未加载 | start.sh 中加载 nvm |
| `Access denied for root@localhost` (服务器) | 服务器 MariaDB 同样需要 `mysql_native_password` | 执行 `ALTER USER` |
| `.mo` 文件编译后页面仍为英文 | 旧 .mo 文件损坏，不含中文翻译 | 删除旧 .mo 后重新编译 `compile-po-to-mo` |
| `bench build` 总是使用系统 Node v20 | `bench build` 不加载 nvm 的 PATH | 手动设置 `PATH=.../node/v24/bin:$PATH` 或更新 supervisor |

---

## 3. WSL2 开发环境搭建

> 🚨 **现状（2026-08-16 确认）**：本地 WSL 的 bench 实际运行的是 **ERPNext 17.0.0-dev（develop 分支）**，并不是本节 v16 流程装出来的。本节保留为「对齐生产 v16」的参考流程：本地已跑 v17、只作探索的话可直接跳到 **3.12** 看差异注意点。

### 3.1 安装 WSL2

在 **Windows PowerShell（管理员）** 中运行：

```powershell
# 安装 Ubuntu 24.04
wsl --install -d Ubuntu-24.04

# 重启电脑后，设置 Ubuntu 的用户名和密码

# 验证版本
wsl -l -v
# 应显示: Ubuntu-24.04  Running  2
```

> 🔑 **注意**：安装后默认使用普通用户（如 `yang`）。**所有 bench 操作都用普通用户**，只有 `sudo apt install` 时才提权。不要用 root 用户操作 bench。

### 3.2 配置 WSL（推荐）

在 Windows 用户目录创建 `%USERPROFILE%\.wslconfig`：

```ini
[wsl2]
memory=8GB
processors=4
localhostForwarding=true
networkingMode=mirrored
```

然后重启 WSL：

```powershell
wsl --shutdown
wsl
```

### 3.3 安装系统依赖

在 **WSL2 Ubuntu 终端** 中执行：

```bash
# 更新包列表
sudo apt update

# 安装全部依赖
sudo apt install -y \
    git curl wget \
    python3-dev python3-pip python3-setuptools python3-venv \
    mariadb-server mariadb-client \
    redis-server \
    pkg-config \
    libmysqlclient-dev libffi-dev libcairo2 \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libxslt1-dev libssl-dev libsasl2-dev libldap2-dev \
    libpq-dev libjpeg-dev libpng-dev \
    fontconfig libxrender1 libxtst6 \
    xfonts-75dpi xfonts-base \
    nginx supervisor

# 验证
python3 --version   # 应 >= 3.12（系统自带）
pip3 --version      # 应正常显示
```

### 3.4 配置 MariaDB

```bash
# 启动 MariaDB
sudo service mariadb start

# 安全配置（交互式）
sudo mysql_secure_installation
```

回答如下：

| 问题 | 回答 |
|------|------|
| Enter current password for root | 直接按回车（无密码） |
| Switch to unix_socket authentication? | `N` |
| Change the root password? | `Y` → 设置密码（**务必记下！**） |
| Remove anonymous users? | `Y` |
| Disallow root login remotely? | `Y` |
| Remove test database? | `Y` |
| Reload privilege tables now? | `Y` |

验证：

```bash
sudo mysql -u root -p
# 输入密码，看到 MariaDB [(none)]> 就成功了
# 输入 exit 退出
```

#### ⚠️ 关键坑：`root@localhost` 认证方式

`mysql_secure_installation` 后，默认使用 `unix_socket` 认证，**只能通过 `sudo mysql` 登录**，bench 无法连接。

如果 `bench new-site` 报 `Access denied for user 'root'@'localhost'`，需要改回密码认证：

```bash
sudo mysql -u root
# 在 MariaDB 提示符中执行：
ALTER USER 'root'@'localhost' IDENTIFIED BY '你的密码';
FLUSH PRIVILEGES;
EXIT;
```

### 3.5 安装 Python 3.14

> ⚠️ **注意**：ERPNext v16 分支最新版要求 Python 3.14+。Ubuntu 24.04 自带的 Python 3.12 不够。

```bash
# 添加 deadsnakes PPA（提供最新 Python）
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# 安装 Python 3.14
sudo apt install -y python3.14 python3.14-dev python3.14-venv

# 验证
python3.14 --version   # 应显示 Python 3.14.x
```

### 3.6 安装 Node.js + Yarn

```bash
# 安装 nvm（Node Version Manager）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc

# 安装 Node.js 24（ERPNext v16 最新版要求 Node 24+）
nvm install 24
nvm alias default 24

# 安装 yarn
npm install -g yarn

# 验证
node --version   # v24.x.x
npm --version    # 10.x.x
yarn --version   # 1.22.x
```

### 3.7 安装 uv（Python 包管理工具）

> ⚠️ **注意**：bench 5.x 依赖 `uv` 来管理虚拟环境。Ubuntu 24.04 的 apt 源中没有 uv，需用官方脚本安装。

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 验证
uv --version
```

### 3.8 安装 Bench

> ⚠️ **注意**：Ubuntu 24.04 有 PEP 668 保护，禁止 `pip3` 直接全局安装。必须用 `pipx`。

```bash
# 安装 pipx
sudo apt install -y pipx
pipx ensurepath
source ~/.bashrc

# 用 pipx 安装 bench（会自动创建隔离环境）
pipx install frappe-bench

# 验证
bench --version   # 应显示 5.x.x
```

### 3.9 初始化 Bench 并安装 ERPNext v16（对齐生产用；本机现状为 v17，见 3.12）

```bash
# 初始化 bench（用 frappe v16 + Python 3.14）
cd ~
bench init frappe-bench --frappe-branch version-16 --python python3.14

# 进入 bench 目录
cd frappe-bench

# 获取 ERPNext v16
bench get-app erpnext --branch version-16

# 创建开发站点
bench new-site dev.localhost
# 提示输入 MariaDB root 密码 → 输入你设的密码
```

> 💡 **提示**：如果 `bench new-site` 失败（如 Redis 未启动、密码错误），残留的站点需要用 `--force` 重新创建：
> ```bash
> bench new-site dev.localhost --force
> ```

```bash
# ⚠️ 安装 ERPNext 需要 Redis 在 11000 端口监听
# 方法 1：先在一个终端启动 bench start，保持运行
# 终端 1：
bench start

# 终端 2（新开一个 WSL 窗口）：
bench --site dev.localhost install-app erpnext

# 方法 2：或者先手动启动 Redis（如果系统 Redis 配置了对应端口）
# 安装完成后启动开发服务器
bench start
```

> 🔑 **安装 ERPNext 提示 `Error 111 connecting to Redis`？**
> 这是因为 bench 的 Redis 是 `bench start` 时由 bench 管理的（端口 11000/13000），
> 跟系统 Redis 服务不同。简单做法：开两个终端，一个跑 `bench start`，一个跑安装。

### 3.10 验证安装

浏览器打开：**http://dev.localhost:8000** 或 **http://localhost:8000**

登录：
- 用户名: `Administrator`
- 密码: 创建站点时设置的密码

### 3.11 配套脚本（一键安装 & 快速启动）

本手册配套提供了 3 个脚本文件，与手册放在同一目录下：

| 脚本 | 用途 | 运行方式 |
|------|------|---------|
| `setup-erpnext.sh` | 🚀 **一键安装脚本**（从 0 到 ERPNext） | `bash setup-erpnext.sh` |
| `start-dev.sh` | 🟢 **启动脚本（带状态检查）** | `bash start-dev.sh` |
| `start.sh` | ⚡ **启动脚本（极简版）** | `bash start.sh` |

#### 3.11.1 一键安装脚本 `setup-erpnext.sh`

包含完整的交互式安装流程，每一个步骤都会检测是否已完成，支持断点续传。

```bash
# 使用方法：在 WSL2 终端中执行
cd ~/frappe-bench
bash /path/to/setup-erpnext.sh
```

> 📌 脚本路径根据你把它们放在哪来定。如果放在 Windows 桌面上：
> ```bash
> bash /mnt/c/Users/Yang/Desktop/setup-erpnext.sh
> ```
> 建议复制到 WSL2 内部：
> ```bash
> cp /mnt/c/Users/Yang/solua-home/sites/erpnext/setup-erpnext.sh ~/
> bash ~/setup-erpnext.sh
> ```

#### 3.11.2 日常启动脚本 `start-dev.sh` / `start.sh`

推荐复制到 `~/frappe-bench/` 目录下，以后只需一条命令：

```bash
# 把脚本复制到 bench 目录
cp /mnt/c/Users/Yang/solua-home/sites/erpnext/start.sh ~/frappe-bench/

# 以后每次开发只需
cd ~/frappe-bench && bash start.sh
````start.sh` 会自动完成三件事：
1. 启动 MariaDB
2. 启动 Redis
3. 启动 bench 开发服务器

`start-dev.sh` 在此基础上增加了状态检查、目录切换等更完善的提示。

### 3.12 本地 v17 vs 生产 v16 差异注意点（2026-08-16 已确认）

**版本事实**（实测命令：`pip show frappe` / `grep __version__ apps/erpnext/erpnext/__init__.py`）：

| 环境 | Frappe | ERPNext | 定位 |
|------|--------|---------|------|
| **生产** erp.solua.one | 16.27.0 | 16.28.0 | 所有上线功能/定制/踩坑以此为基准 |
| **本地 WSL** | v17 配套 | 17.0.0-dev（develop 分支） | 仅开发探索；行为可能与生产不同 |

**生产 v16 实测到的行为**（本地 v17 是否一致**未验证**，勿照搬测试结论）：

| # | v16 实测行为 | 影响 |
|---|------------|------|
| 1 | `flt` / `cint` 是**全局函数**（`window.flt`），`frappe.utils.flt` 不存在（前端自定义 JS 里直接用 `flt(...)`，与 erpnext 自带代码一致） | 自定义 JS 写 `frappe.utils.flt` 会报 `is not a function` |
| 2 | 生产模式下 Page 文档（**含 page_js 自定义脚本**）会被缓存进浏览器 localStorage，Ctrl+Shift+R 也清不掉 → 已用 `override/desk_page.py` 置 `_dynamic_page=1` 根治 | 改 pos_custom.js 后不生效，通常不是缓存问题（已根治） |
| 3 | master 单据（如 `Sales Taxes and Charges Template`）导入时 docstatus 可能异常为 1（is_submittable=0 却标已提交），锁死后续修改（报 UpdateAfterSubmitError） | 修改前先归 0；install.py 的 `configure_pos_tax()` 已内置处理 |
| 4 | 子表（如 `POS Profile User`）对低权限角色默认**无读权限**，前端 `frappe.db.get_list` 抛 Insufficient Permission、promise 静默断裂 | 前端优先复用 whitelisted 查询方法（如 `pos_profile_query`），不要直查无权限子表 |
| 5 | `frappe.throw` 内部会先 `msgprint` 写 message_log 再抛异常——try/except 接住异常后消息仍会随 API 响应弹到前端 | 封装 decrypt 等函数前先判输入格式，避免误触发 throw 副作用 |
| 6 | POS 相关：`search_by_term` 扫模板条码直接返回模板并自动加购、开店对话框 POS Profile 必填无默认、付款单银行科目强制填参考号等 | 收银员最小权限下的行为需在 v16 实测 |

**工作准则**：
1. **自定义功能以生产 v16 实测为准**；本地 v17 仅用于语法检查、代码探索
2. 在本地 v17 开发的改动，上生产前必须在 v16 重新实测（部署流程见第 8 章）
3. 若要彻底消除版本差异：按 3.9 重装 v16（`bench init --frappe-branch version-16` + `bench get-app erpnext --branch version-16`）对齐生产，或明确本地仅作探索、不承诺行为一致

### 3.13 Docker 版 ERP 已移除，自启已禁用（2026-08-16）

> 本机只保留 **bench 版**（`~/frappe-bench`，dev.localhost:8000）。曾装过的 Docker 版（frappe_docker，v16.23.1）已**全部删除**：容器、镜像、数据卷、源码目录 `~/frappe_docker`，且残留的 84 个悬空卷也已 `docker volume prune -f` 清空。

**Docker 自启状态**（两次重启 WSL 实测确认，已彻底禁用）：

| 单元 | 自启 | 说明 |
|------|------|------|
| `docker.service` | disabled | 已禁用 |
| `docker.socket` | disabled | 已禁用（否则 socket 激活会在有客户端连接时自动拉起 dockerd） |
| `containerd.service` | disabled | 已禁用 |
| `erpnext-compose.service` | **已删除** | ⚠️ 真正自启源头，见下方坑 |

> 🚨 **坑：禁用 docker 三单元后 dockerd 仍会自启——是别的单元把它拽起来的**
>
> frappe_docker 时代遗留的 `/etc/systemd/system/erpnext-compose.service`（`Requires=docker.service` + `WantedBy=multi-user.target`）在每次开机时把 docker 一起拉起，它自己因 `~/frappe_docker` 已删而启动失败（failed），但依赖已生效。
>
> 排查命令：`journalctl -b -u docker.service`（看谁启动的）+ `systemctl list-unit-files --state=enabled | grep -i docker`（找依赖 docker 的单元）。
>
> 根治（需要 root）：
>
> ```bash
> wsl -u root -e systemctl stop docker docker.socket containerd erpnext-compose.service
> wsl -u root -e systemctl disable erpnext-compose.service
> wsl -u root -e rm -f /etc/systemd/system/erpnext-compose.service
> ```

**验证**：重启 WSL（`wsl --shutdown` 后重新进入）后执行 `wsl -e bash -lc "systemctl is-enabled docker docker.socket containerd"` 应全部输出 `disabled`、`systemctl is-active docker docker.socket` 输出 `inactive`、无 dockerd 进程、无 `/var/run/docker.sock`；`docker ps` 报 `Cannot connect to the Docker daemon` 即为正常（无自启）。

**日后要用 Docker 时手动启动**：

```bash
wsl -u root -e systemctl start docker
```

> 💡 Docker 与 bench 版互不依赖（bench 用 MariaDB/Redis），停用 Docker 不影响 dev.localhost。

---




## 4. 日常开发工作流

### 4.1 每天开始工作

```bash
# 打开 WSL2 终端
wsl

# 启动服务
sudo service mariadb start
sudo service redis-server start

# 进入 bench 目录
cd ~/frappe-bench

# 启动开发服务器（保持运行，不要关）
bench start

# 在浏览器打开 http://dev.localhost:8000
# 用 Administrator + 你的密码登录
```

> 📌 **需要开第二个终端？** 再开一个 WSL 窗口，同样 `cd ~/frappe-bench`，
> 在这个终端执行其他命令（`bench migrate`、`bench console` 等）。

### 4.2 如何选择正确的 WSL 终端路径

```bash
# ❌ 错误：在 Windows 路径下（/mnt/c/...）执行 bench 命令
# /mnt/c/Users/Yang$ bench --site dev.localhost install-app erpnext
# → 报错：Command not being executed in bench directory

# ✅ 正确：先进入 bench 目录
cd ~/frappe-bench
# 然后再执行 bench 命令
bench --site dev.localhost install-app erpnext
```

> 💡 每次新打开 WSL 终端，第一件事就是 `cd ~/frappe-bench`！

### 4.2 开发循环

```
修改代码 → 保存文件 → 刷新浏览器页面
```

**无需重启服务器！** Frappe 开发模式会自动重载。

### 4.3 安装 Redis 连接错误的处理

**问题现象**：安装 ERPNext 时反复报 `Error 111 connecting to 127.0.0.1:11000. Connection refused`

**原因**：bench 管理自己的 Redis 实例（端口 11000 和 13000），这些实例由 `bench start` 启动。
`sudo service redis-server start` 启动的是系统 Redis（默认端口 6379），两者不同。

**解决**：开两个终端：

```bash
# 终端 1：运行 bench start（会自动启动 Redis）
cd ~/frappe-bench
bench start

# 终端 2：在另一个 WSL 窗口执行安装
wsl
cd ~/frappe-bench
bench --site dev.localhost install-app erpnext
```

### 4.4 使用 VS Code

```bash
# 在 WSL2 中直接打开 VS Code
cd ~/frappe-bench
code .
```

> 需要安装 VS Code 的 **Remote - WSL** 扩展。VS Code 会自动连接到 WSL2，你可以在 Windows 的 VS Code 界面中编辑，命令在 WSL2 中执行。

---

## 5. 创建自定义 App

### 5.1 创建新 App

```bash
cd ~/frappe-bench
bench new-app solua_home
```

交互式问答：

| 问题 | 示例回答 |
|------|---------|
| App Name | `solua_home`（正式生产模块名，2026-08-06 从 my_custom_app 重命名） |
| App Title | `Solua Home 定制` |
| App Description | `Solua Home 生产定制：POS 扫码选色、多规格变体、中文翻译、业务校验` |
| App Publisher | `Solua Home, Lda` |
| App Email | `admin@solua.one` |
| App License | `GNU General Public License (v3)` |

### 5.2 安装到站点

```bash
bench --site dev.localhost install-app solua_home
bench --site dev.localhost migrate
```

#### ⚠️ 常见问题：`No module named 'solua_home'`

| 可能原因 | 排查方法 | 解决 |
|---------|---------|------|
| App 未注册到 `apps.txt` / `apps.json` | `cat sites/apps.txt` 看看是否有你的 app | `echo "solua_home" >> sites/apps.txt` |
| Python 模块不可导入 | `cd ~/frappe-bench && source env/bin/activate && python3 -c "import solua_home"` | 检查 `__init__.py` 是否存在，或创建 symlink |
| pip editable install 未生效 | `pip show solua_home` | `pip install -e . --no-build-isolation` |
| hooks.py 引用了不存在的模块 | 看报错中 `No module named ...` 的路径 | 创建缺失的文件或移除 hooks.py 中的引用 |

**最可靠的解决流程（当手动创建 App 时）：**

```bash
# 1. 确认目录结构正确（hooks.py 在 apps/solua_home/ 根目录）
ls ~/frappe-bench/apps/solua_home/hooks.py

# 2. 在 site-packages 中创建 symlink（如果 pip install 不生效）
cd ~/frappe-bench
source env/bin/activate
ln -sf /home/$(whoami)/frappe-bench/apps/solua_home env/lib/python3.14/site-packages/solua_home

# 3. 注册到 apps.txt 和 apps.json
python3 -c "
import json
# apps.txt
with open('sites/apps.txt') as f:
    apps = f.read().strip().split('\n')
if 'solua_home' not in apps:
    apps.append('solua_home')
    with open('sites/apps.txt', 'w') as f:
        f.write('\n'.join(apps) + '\n')
# apps.json
with open('sites/apps.json') as f:
    reg = json.load(f)
if 'solua_home' not in reg:
    reg['solua_home'] = {
        'is_repo': False, 'resolution': {'commit_hash': None, 'branch': None},
        'required': [], 'idx': 3, 'version': '0.0.1'
    }
    with open('sites/apps.json', 'w') as f:
        json.dump(reg, f, indent=2)
print('✅ 已注册')
"

# 4. 安装到站点
bench --site dev.localhost install-app solua_home
```

### 5.3 目录结构

```
~/frappe-bench/apps/solua_home/
├── solua_home/
│   ├── __init__.py
│   ├── hooks.py              # ★ 核心文件：注册所有扩展点
│   ├── api.py                # API 方法
│   ├── setup.py              # 安装/迁移时执行
│   ├── doctype/              # 自定义 DocType
│   │   └── __init__.py
│   ├── override/             # 重写 ERPNext 类
│   │   └── __init__.py
│   └── public/               # 前端资源（JS/CSS）
├── setup.py
├── setup.cfg
└── README.md
```

### 5.4 常用操作

```bash
# 创建新 DocType
bench new-doctype CustomContract

# 应用变更后迁移
bench --site dev.localhost migrate

# 构建前端资源
bench build

# 清理缓存
bench --site dev.localhost clear-cache
```

---

## 6. 定制开发模式

### 6.1 模式一：DocEvents（最常用）

在 `hooks.py` 中注册事件，在 `api.py` 中写逻辑：

```python
# hooks.py
doc_events = {
    "Sales Invoice": {
        "validate": "solua_home.api.validate_sales_invoice",
        "on_submit": "solua_home.api.on_invoice_submitted",
        "on_cancel": "solua_home.api.on_invoice_cancelled",
    },
    "Purchase Order": {
        "validate": "solua_home.api.validate_purchase_order",
    },
    "Customer": {
        "before_insert": "solua_home.api.before_customer_created",
        "validate": "solua_home.api.validate_customer",
    },
    "Item": {
        "validate": "solua_home.api.validate_item",
    },
}
```

```python
# api.py
import frappe
from frappe import _

@frappe.whitelist()
def validate_sales_invoice(doc, method=None):
    """销售发票保存时验证"""
    if doc.grand_total > 100000:
        frappe.throw(_("金额超过 100,000，需要额外审批"))

@frappe.whitelist()
def on_invoice_submitted(doc, method=None):
    """销售发票提交后执行"""
    frappe.msgprint(_("发票 {0} 已成功提交").format(doc.name))
    # 可以调用外部 API、发送通知等
```

### 6.2 模式二：Override 类（重写方法）

```python
# override/sales_invoice.py
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class CustomSalesInvoice(SalesInvoice):
    def validate(self):
        # 先执行原逻辑
        super().validate()
        # 再执行你的逻辑
        self.custom_validation()

    def custom_validation(self):
        if self.custom_field == "特殊":
            frappe.throw(_("特殊条件不满足"))
```

```python
# hooks.py 中注册
extend_doctype_class = {
    "Sales Invoice": "solua_home.override.sales_invoice.CustomSalesInvoice",
}
```

### 6.3 模式三：添加自定义字段

方法 A（通过代码，推荐）：

```python
# setup.py（在 after_install 或 after_migrate 中执行）
def add_custom_fields():
    """安装后自动添加自定义字段"""
    fields = [
        {
            "dt": "Sales Invoice",
            "fieldname": "custom_my_field",
            "label": "自定义字段",
            "fieldtype": "Data",
            "insert_after": "grand_total",
        },
        {
            "dt": "Customer",
            "fieldname": "custom_等级",
            "label": "客户等级",
            "fieldtype": "Select",
            "options": "\n普通\nVIP\nVVIP",
            "insert_after": "customer_name",
        },
    ]
    for field in fields:
        if not frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
            frappe.get_doc({"doctype": "Custom Field", **field}).insert()
    frappe.db.commit()
```

方法 B（通过 UI）：\
设置 → 自定义 → 自定义表单 → 选择 DocType → 添加字段

### 6.4 完整 hooks.py 示例

```python
# solua_home/hooks.py
app_name = "solua_home"
app_title = "我的定制"
app_publisher = "你的名字"
app_description = "ERPNext 中文定制功能"
app_icon = "fa fa-cog"
app_color = "#3498db"
app_email = "your@email.com"
app_license = "GNU General Public License (v3)"

# ------------------- 事件钩子 -------------------
doc_events = {
    "Sales Invoice": {
        "validate": "solua_home.api.validate_sales_invoice",
        "on_submit": "solua_home.api.on_invoice_submitted",
    },
    "Purchase Order": {
        "validate": "solua_home.api.validate_purchase_order",
    },
}

# ------------------- 类重写 -------------------
extend_doctype_class = {
    "Sales Invoice": "solua_home.override.sales_invoice.CustomSalesInvoice",
}

# ------------------- 安装/迁移 -------------------
after_install = "solua_home.install.after_install"
after_migrate = "solua_home.install.after_migrate"

# ------------------- 权限 -------------------
permission_query_conditions = {}
has_permission = {}

# ------------------- 调度任务 -------------------
scheduler_events = {
    "daily": [
        "solua_home.tasks.daily_task",
    ],
    "hourly": [],
}
```

### 6.5 多规格（Item Variant）方案

> **适用场景**：成品窗帘、服装、鞋子等同一款号有不同颜色/尺码的商品
> **核心需求**：一个条码对应多个颜色，扫码后选颜色，库存按颜色分别统计

#### 6.5.1 数据模型

```
模板 Item（窗帘款号，条码放在这里）
  ├── item_code: CR-001
  ├── item_name: Cortina Roman 2.5m
  ├── has_variants: 1
  ├── barcodes: [6901234567890]
  ├── attributes: [Cor (颜色)]  ← 属性名用葡语
  └── Variants（每个颜色一个，真正管库存和交易）
        ├── CR-001-BR → Cortina Roman 2.5m - Branco
        ├── CR-001-PR → Cortina Roman 2.5m - Preto
        ├── CR-001-AZ → Cortina Roman 2.5m - Azul
        ├── CR-001-VM → Cortina Roman 2.5m - Vermelho
        ├── CR-001-BG → Cortina Roman 2.5m - Bege
        └── CR-001-CZ → Cortina Roman 2.5m - Cinza
```

| 层级 | ERPNext 实现 | 作用 |
|------|-------------|------|
| **SPU**（商品款号） | Template Item（`has_variants=1`） | 管理主信息、条码、品类 |
| **SKU**（颜色变体） | Variant Item（`variant_of=模板`） | 真正参与库存、POS、销售 |
| **属性**（颜色） | Item Attribute（`Cor`） | 生成 Variant 的维度 |

#### 6.5.2 条码策略（方案 A）

**条码只挂在 Template Item 上**，不在 Variant 上。

原因：ERPNext 强制条码唯一，同款不同色使用同一已印好的条码。

```python
# 模板创建时设置条码
item = frappe.get_doc({
    "doctype": "Item",
    "item_code": "CR-001",
    "has_variants": 1,
    "barcodes": [{"barcode": "6901234567890", "barcode_type": "Code128"}],
    ...
})
```

> ⚠️ 注意：如果使用真实 EAN 条码，ERPNext 会校验最后一位（校验码）。
> 测试时可用 `Code128` 类型绕过校验。正式数据用实际条码即可。

**生产共享条码规则（2026-09-20）**：所有 `Cor` 颜色变体共用模板的唯一非空原包装条码。原生 `Item Barcode` 只保留在模板；变体的 `custom_label_barcode` 与该值相同，禁止把同一原生条码重复添加到每个变体，也不把变体 `item_code` 当作标签条码。`solua_home.api.stock.validate_item` 在 Item 保存/创建时执行继承；模板缺条码或有多个不同条码时保留当前值并显示提示，不猜测。标签 Print Format 经 `solua_home.printing.label_helpers._get_barcode` 优先打印 `custom_label_barcode`；`solua_home.api.label_print._get_barcodes` 不再为颜色变体合成货号条码。POS 扫码由 `solua_home.api.pos.scan_barcode_for_pos` 返回模板与颜色选项，`public/js/pos_custom.js` 再打开选色弹窗。

本次生产回读覆盖 7 个模板、66 个启用颜色变体（窗帘 46 个，窗帘杆 20 个）：模板条码均唯一且无跨模板冲突，已修正 66 个变体 `custom_label_barcode`；审计发现变体原生 `Item Barcode` 行为 0，因此删除数为 0、无模板例外。POS 扫码与标签搜索均对 7 个模板逐一通过。Item Price 158 条、图片、`variant_of`、颜色属性与 Bin 库存快照保持不变；窗帘杆仍为 8040 根、库存价值 2,444,640 MZN。变更前完整备份标识：`20260920_214231`。

#### 6.5.3 多语言策略

| 用户 | 语言设置 | 看到的内容 |
|------|---------|-----------|
| **管理员（你）** | 中文 | DocType 标签中文，属性值葡语（学几个颜色词） |
| **员工** | Português | DocType 标签葡语，属性值葡语 |

**属性值（颜色名）直接存葡语**，因为 Frappe 的属性值不会自动翻译：

```python
# Item Attribute "Cor" 的值
{"attribute_value": "Branco", "abbr": "BR"},
{"attribute_value": "Preto", "abbr": "PR"},
{"attribute_value": "Azul", "abbr": "AZ"},
...
```

常用颜色葡语速记：

| Português | 中文 |
|-----------|------|
| Branco | 白色 |
| Preto | 黑色 |
| Azul | 蓝色 |
| Vermelho | 红色 |
| Bege | 米色 |
| Cinza | 灰色 |
| Verde | 绿色 |
| Rosa | 粉色 |
| Amarelo | 黄色 |
| Marrom | 棕色 |

#### 6.5.4 自定义 POS 扫码（颜色选择器）

**需求**：扫条码 → 找到模板 → 弹窗选颜色 → 加对应 Variant 到购物车

**方案**：保留标准 POS 全部功能，只替换扫码行为。

##### 后端 API：`solua_home/api/pos.py`

> ✅ **已实现（2026-08）**。完整代码见 `my_custom_app_example/solua_home/api/pos.py`，以下是核心函数。

```python
@frappe.whitelist()
def scan_barcode_for_pos(barcode):
    """扫码查找商品。

    如果条码对应模板物料（有 Variant），返回该模板的所有颜色选项。
    如果条码直接对应 Variant 或普通物料，直接返回该物料信息。
    如果未找到，返回 not_found。
    """
    if not barcode:
        return {"type": "not_found"}

    try:
        # 1. 查找条码（条码存在 Item Barcode 子表中，与 erpnext.stock.utils.scan_barcode 一致）
        item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
        if not item_code:
            return {"type": "not_found"}

        has_variants = frappe.db.get_value("Item", item_code, "has_variants")

        # 2. 如果是模板物料
        if has_variants:
            template_name = frappe.db.get_value("Item", item_code, "item_name")
            # custom_swatch_image 是可选自定义字段，未创建时跳过避免报错
            item_fields = ["item_code", "item_name", "image"]
            if frappe.db.has_column("Item", "custom_swatch_image"):
                item_fields.append("custom_swatch_image")

            variants = frappe.get_all(
                "Item",
                filters={"variant_of": item_code, "disabled": 0},
                fields=item_fields,
                order_by="item_code asc",
            )
            color_options = []
            for v in variants:
                cor = frappe.db.get_value(
                    "Item Variant Attribute",
                    {"parent": v.item_code, "attribute": "Cor"},
                    "attribute_value",
                )
                if not cor:
                    attrs = frappe.get_all(
                        "Item Variant Attribute",
                        filters={"parent": v.item_code},
                        fields=["attribute", "attribute_value"],
                        limit=1,
                    )
                    if attrs:
                        cor = attrs[0].attribute_value
                    else:
                        cor = v.item_name
                color_options.append({
                    "variant_code": v.item_code,
                    "variant_name": v.item_name,
                    "cor": cor,
                    "image": v.image or "",
                    "swatch": getattr(v, "custom_swatch_image", "") or "",
                })
            return {
                "type": "template",
                "template_code": item_code,
                "template_name": template_name,
                "colors": color_options,
            }

        # 3. 如果是 Variant 或普通物料
        item_name = frappe.db.get_value("Item", item_code, "item_name")
        return {
            "type": "variant",
            "item_code": item_code,
            "item_name": item_name,
        }
    except Exception as e:
        frappe.log_error(f"POS 扫码查询失败 ({barcode}): {e!s}", "solua_home")
        return {"type": "error", "message": str(e)}
```

> ⚠️ **踩坑记录**：条码**不能**用 `frappe.db.get_value("Item", {"barcode": barcode}, "name")` 查询——`Item` 主表没有 `barcode` 列（条码存在 `tabItem Barcode` 子表），这样写会抛 `Unknown column` 异常。正确做法是直接查 `Item Barcode` 子表的 `parent` 字段（= Item name = item_code）。

**返回约定（前后端契约）**：

| `type` | 说明 | 返回内容 |
|--------|------|---------|
| `template` | 模板商品（有 Variant） | `template_code`、`template_name`、`colors[]`（每项含 `variant_code`/`variant_name`/`cor`/`image`/`swatch`） |
| `variant` | Variant 或普通商品 | `item_code`、`item_name` |
| `not_found` | 条码不存在 | — |
| `error` | 数据库/权限异常 | `message`（详情同时写入 `frappe.log_error`） |

##### 前端自定义 JS：`solua_home/public/js/pos_custom.js`

通过 `hooks.py` 的 `page_js` 注入到 POS 页面：

```python
# hooks.py
page_js = {
    "point-of-sale": "public/js/pos_custom.js",
}
```

JS 核心逻辑（完整代码见 `my_custom_app_example/solua_home/public/js/pos_custom.js`）：

> 💡 **关键设计**：POS 每次刷新（新建开单、重新进入）都会**重建 ItemSelector 并重新执行 `bind_events`**。因此不能只 `detachFrom` 一次，而要把替换逻辑**挂在 `ItemSelector.prototype.bind_events` 上**（原型方法包装），保证每次重建后自定义监听都生效。

```javascript
// 1. 等待 POS bundle 加载完成后，包装 ItemSelector.prototype.bind_events
function apply_custom_barcode_handler() {
    if (applied) return;

    // 等待 point-of-sale.bundle.js 加载（ItemSelector 类定义于此）
    // 最多轮询 60 次（约 30 秒），超时静默放弃
    if (!window.erpnext?.PointOfSale?.ItemSelector) {
        if (poll_attempts++ < 60) setTimeout(apply_custom_barcode_handler, 500);
        return;
    }
    applied = true;

    const original_bind_events = erpnext.PointOfSale.ItemSelector.prototype.bind_events;

    // 每次重建 ItemSelector 都会重新执行 bind_events → 自定义监听始终生效
    erpnext.PointOfSale.ItemSelector.prototype.bind_events = function () {
        original_bind_events.call(this);  // 保留原逻辑（含 window.onScan 赋值）
        if (!window.onScan) return;
        window.onScan.detachFrom(document);   // 移除默认监听
        window.onScan.attachTo(document, {
            onScan: (sScancode) => handle_barcode_scan.call(this, sScancode),
        });
    };

    // 极端时序兜底：若组件已构建完成，立即对当前实例生效
    if (window.cur_pos?.item_selector && window.onScan) {
        window.onScan.detachFrom(document);
        window.onScan.attachTo(document, {
            onScan: (sScancode) => handle_barcode_scan.call(window.cur_pos.item_selector, sScancode),
        });
    }
}

// 2. 自定义扫码处理：先问后端，按 type 分流
function handle_barcode_scan(barcode) {
    const item_selector = this;  // ItemSelector 实例
    if (!item_selector?.search_field || !item_selector.$component.is(":visible")) return;

    frappe.call({
        method: "solua_home.api.pos.scan_barcode_for_pos",
        args: { barcode },
        callback: (r) => {
            if (r.exc) { alert_error(); return; }          // 网络/权限异常
            const res = r.message;
            if (res?.type === "error")     { alert_error(); return; }  // 后端返回错误
            if (res?.type === "template")  { show_color_picker(res); return; }  // ← 弹窗选颜色
            if (!res || res.type === "not_found") {
                item_selector.search_field.set_focus();
                frappe.show_alert({ message: __("未找到条码 {0} 对应的商品", [barcode]), indicator: "orange" });
                frappe.utils.play_sound("error");
                return;
            }
            // variant 或普通商品 → 保持 ERPNext 标准扫码行为
            item_selector.search_field.set_focus();
            item_selector.set_search_value(res.item_code || barcode);
            item_selector.barcode_scanned = true;
        },
    });
}

// 3. 颜色选择弹窗（frappe.ui.Dialog + HTML 字段渲染色块网格）
function show_color_picker(data) {
    if (active_dialog) active_dialog.hide();  // 防堆叠
    const dialog = new frappe.ui.Dialog({
        title: __("选择颜色"),
        static: true,
        fields: [{ fieldtype: "HTML", fieldname: "color_picker_html", options: build_html(data) }],
        primary_action_label: __("取消"),
        primary_action() { dialog.hide(); },
    });
    active_dialog = dialog;
    dialog.onhide = () => { if (active_dialog === dialog) active_dialog = null; };
    dialog.show();

    // 点击色块 → 加入购物车
    dialog.$wrapper.find(".color-picker-item").on("click", function () {
        const variant_code = $(this).attr("data-variant-code");
        if (!variant_code) return;
        dialog.hide();
        add_variant_to_cart(variant_code);
    });
}

// 4. 把选中的 Variant 加入 POS 购物车
// 复用标准 POS「搜索 → 渲染 → 点击 .item-wrapper」流程，
// 价格 / UOM / 税率等由 ERPNext 标准逻辑自动带出
function add_variant_to_cart(variant_code) {
    const item_selector = window.cur_pos?.item_selector;
    if (!item_selector?.set_search_value) return;

    item_selector.set_search_value(variant_code);

    let attempts = 0;
    const timer = setInterval(() => {
        attempts++;
        // 精确匹配目标 Variant（避免点错同名前缀商品）
        const $exact = item_selector.$items_container.find(".item-wrapper").filter(function () {
            return $(this).attr("data-item-code") === variant_code;
        });
        if ($exact.length) {
            clearInterval(timer);
            $exact.trigger("click");
            item_selector.set_search_value("");
            frappe.utils.play_sound("submit");
        } else if (attempts > 20) {  // 6 秒超时
            clearInterval(timer);
            item_selector.set_search_value("");
            frappe.show_alert({ message: __("未找到商品 {0}，请检查价格表设置", [variant_code]), indicator: "orange" });
            frappe.utils.play_sound("error");
        }
    }, 300);
}
```

**前端注意点**：
- 所有后端返回的字段（`template_name`/`cor`/`variant_code`/图片 URL）在拼 HTML 时用 `frappe.utils.escape_html()` 转义，防 XSS。
- 弹窗色块用 CSS 网格布局（`repeat(auto-fill, minmax(92px, 1fr))`），色卡图优先用 `swatch`（色卡图），其次 `image`。
- 扫码失败的场景（`not_found`/`error`/`r.exc`）都恢复搜索框焦点，保证下一单连续扫码不受影响。

##### 扫码流程完整时序

```
用户扫码 6901234567890
  │
  ▼
onScan 捕获键盘输入
  │
  ▼
调用 solua_home.api.pos.scan_barcode_for_pos
  │
  ▼
返回 {"type": "template", "colors": ["Branco", "Preto", "Azul"...]}
  │
  ▼
显示颜色选择弹窗
  │
  ▼ (用户点击 "Branco")
  │
  ▼
addVariantToCart("CR-001-BR")
  → 搜索 CR-001-BR
  → 自动点击搜索结果
  → Variant 加入购物车
```

#### 6.5.5 测试数据快速创建

```bash
cd ~/frappe-bench
source env/bin/activate

# 创建 Cor 属性 + 模板 + 6 个颜色 Variant
bench --site dev.localhost execute solua_home.api.pos.create_test_data
```

> ✅ 该函数**已实现**于 `api/pos.py`，可随时执行。
> 💡 测试完成后，建议删除 `api/pos.py` 中的 `create_test_data()` 函数（它不属于生产代码）。

这会创建：

| 项目 | 值 |
|------|-----|
| Item Attribute | `Cor`（Branco/Preto/Azul/Vermelho/Bege/Cinza） |
| Template Item | `CR-001` - Cortina Roman 2.5m（条码: 6901234567890，Code128 类型） |
| Variants | `CR-001-BR` ~ `CR-001-CZ`（6个颜色，`item_name` = "Cortina Roman 2.5m / Branco"） |

#### 6.5.6 初始化代码（install.py）✅ 已实现

> ✅ 完整代码见 `my_custom_app_example/solua_home/install.py`，通过 `after_install` / `after_migrate` 自动执行。
> `hooks.py` 中已注册：`after_install = "solua_home.install.after_install"`。
> `install.py` 会**复用** `setup.py` 中的翻译与基础字段逻辑（`add_translations` / `add_custom_fields`），
> 因此只需 `bench migrate` 即可完成多规格初始化。

**① 初始化商品属性 `add_item_attributes()`**：

```python
def add_item_attributes():
    """初始化商品属性（颜色、尺码等）"""
    attributes = {
        "Cor": {
            "values": [
                ("Branco", "BR"), ("Preto", "PR"), ("Azul", "AZ"),
                ("Vermelho", "VM"), ("Bege", "BG"), ("Cinza", "CZ"),
            ],
        },
    }
    for attr_name, attr_data in attributes.items():
        if not frappe.db.exists("Item Attribute", attr_name):
            doc = frappe.get_doc({
                "doctype": "Item Attribute",
                "attribute_name": attr_name,
                "item_attribute_values": [
                    {"attribute_value": v, "abbr": a}
                    for v, a in attr_data["values"]
                ],
            })
            doc.insert(ignore_permissions=True)
    frappe.db.commit()
```

**② 多规格自定义字段 `add_variant_custom_fields()`**（含 POS 用到的 `custom_swatch_image` 色卡图）：

```python
def add_variant_custom_fields():
    """添加多规格相关的自定义字段到 Item"""
    fields = [
        {"dt": "Item", "fieldname": "custom_spu_code", "label": "SPU编码",
         "fieldtype": "Data", "insert_after": "item_code", "description": "商品款号/主款编码"},
        {"dt": "Item", "fieldname": "custom_chinese_name", "label": "中文显示名",
         "fieldtype": "Data", "insert_after": "item_name"},
        {"dt": "Item", "fieldname": "custom_spec_summary", "label": "规格摘要",
         "fieldtype": "Data", "insert_after": "custom_chinese_name"},
        {"dt": "Item", "fieldname": "custom_pos_short_name", "label": "POS收银简称",
         "fieldtype": "Data", "insert_after": "custom_spec_summary"},
        {"dt": "Item", "fieldname": "custom_swatch_image", "label": "色卡图",
         "fieldtype": "Attach Image", "insert_after": "image"},
    ]
    for field in fields:
        if not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": field["fieldname"]}):
            frappe.get_doc({"doctype": "Custom Field", **field}).insert(ignore_permissions=True)
    frappe.db.commit()
```

**③ 配置 Item Variant Settings `configure_item_variant_settings()`**（决定哪些字段从模板自动继承到 Variant）：

```python
def configure_item_variant_settings():
    """配置哪些字段从模板自动继承到 Variant"""
    doc = frappe.get_doc("Item Variant Settings")
    if doc.get("fields"):
        return    # 已配置过则跳过，避免覆盖管理员的手动调整
    fields = [
        {"field_name": "item_name"},
        {"field_name": "description"},
        {"field_name": "image"},
        {"field_name": "stock_uom"},
        {"field_name": "brand"},
        {"field_name": "item_group"},
        {"field_name": "is_stock_item"},
        {"field_name": "custom_swatch_image"},   # 自定义字段也可继承
    ]
    doc.set("fields", fields)
    doc.save()
```

> 📌 用法与 ERPNext 官方测试 `set_item_variant_settings()` 一致（`erpnext/stock/doctype/item/test_item.py`）。
> 执行方式：`bench --site dev.localhost migrate` 或 `bench --site dev.localhost execute solua_home.install.after_migrate`。

#### 6.5.7 实施步骤

```
1. 定义属性（Item Attribute: Cor）← install.py 自动创建
2. 建模板商品（Item, has_variants=1）← 手动或代码创建
3. 在模板上挂属性（Attributes: Cor）← 手动或代码创建
4. 生成 Variant（每颜色一个）← 通过 Make Variant 或代码批量生成
5. 模板上放条码（不放在 Variant 上）
6. 使用自定义 POS 扫码选颜色
```

#### 6.5.8 部署与验证（已实现功能）

本次 POS 扫码选色功能涉及 3 个文件：

| 文件 | 作用 |
|------|------|
| `solua_home/api/pos.py` | 后端 API：`scan_barcode_for_pos()`（模板 → 颜色列表；Variant/普通 → 直接返回） |
| `solua_home/public/js/pos_custom.js` | 前端：onScan 重绑定 + 颜色弹窗 + 加入购物车 |
| `solua_home/hooks.py` | 注册 `page_js = {"point-of-sale": "public/js/pos_custom.js"}` |

##### 本地开发（WSL2）

```bash
# 1. 把三个文件放到 apps/solua_home 对应位置（或 git pull）
# 2. 后端 Python 文件：开发模式自动重载，无需重启
# 3. 前端 page_js：开发模式直接生效，刷新页面即可
bench --site dev.localhost clear-cache   # 保险起见清一次缓存
# 4. 浏览器打开 http://dev.localhost:8000/app/point-of-sale 验证
```

##### 生产服务器（Git 工作流，参照第 8 节）

```bash
# 本地提交推送
cd ~/frappe-bench/apps/solua_home
git add -A && git commit -m "feat: POS 扫码选颜色" && git push

# 服务器拉取部署
ssh qq 'sudo -u frappe -i bash -l -c "
  cd /home/frappe/frappe-bench/apps/solua_home
  git pull
  cd /home/frappe/frappe-bench
  source env/bin/activate
  bench --site erp.solua.one migrate
  bench --site erp.solua.one clear-cache
  sudo supervisorctl restart all
"'
```

> ⚠️ **重要**：前端 `page_js` 在生产环境（supervisor/nginx）需要**构建资源**才会生效：
> ```bash
> # 在服务器 bench 目录执行（确保用 Node 24，见 12.6 节）
> PATH=/home/frappe/.nvm/versions/node/v24.18.0/bin:$PATH bench build
> sudo supervisorctl restart all
> ```
> 后端 `api/pos.py` 不需要 build，重启即生效。

##### 验证清单

| # | 验证项 | 预期 |
|---|--------|------|
| 1 | 扫模板条码 `6901234567890` | 弹出颜色选择弹窗（6 个颜色） |
| 2 | 点击 "Branco" | `CR-001-BR` 加入购物车，价格/UOM 正确 |
| 3 | 扫普通物料条码 | 标准 POS 行为（搜索框填入，回车加购） |
| 4 | 扫不存在的条码 | 橙色提示"未找到条码"，不报错 |
| 5 | 连续扫多单 | 弹窗不堆叠，搜索框焦点正常恢复 |

##### 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 扫码无反应 | `page_js` 未生效（生产环境未 build） | 执行 `bench build` + 重启 |
| 弹窗提示"未找到商品" | Variant 未在价格表（Selling Price List）中 | Selling → Item Price 为 Variant 设置价格（见 6.5 自动价格方案） |
| 扫码报 `Unknown column` | 后端用了 `get_value("Item", {"barcode":...})` 旧写法 | 改用 `get_value("Item Barcode", {"barcode":...}, "parent")` |
| 色卡图不显示 | `custom_swatch_image` 字段未创建 | 运行 `install.py` 的 `add_variant_custom_fields()` 或手动建字段 |
| 扫码报 403「Item Price 权限不足」 | 生产站点 Item Price 仅授权 `Purchase/Sales Master Manager`，`Sales User` 无读权限 | 给收银员角色加 Item Price 读权限（或按用户授予 Master Manager） |
| 点色报「仓库 X 中无此物料」 | Variant 无库存 | 用 Stock Reconciliation / 收货单补库存 |

#### 6.5.9 生产验收记录（2026-08-06，erp.solua.one）

> 完整升级部署（commit `1e2236a`）后，**扫码选色全流程浏览器实测通过**。以下为验收记录与踩坑，供后续部署/排错参考。

##### 测试数据

| 数据 | 内容 |
|------|------|
| **属性** | `Cor`（值：Branco/Preto/Azul/Vermelho/Bege/Cinza，abbr BR/PR/AZ/VM/BG/CZ） |
| **模板** | `CR-001` Cortina Roman 2.5m，`has_variants=1`，条码 `6901234567890` |
| **Variant** | `CR-001-AZ/BG/BR/CZ/PR/VM`（6 个颜色变体） |
| **价格** | Standard Selling，1200–1450 MZN，6 条（Variant 创建时自动生成） |
| **库存** | Stock Reconciliation `MAT-RECO-2026-00002`，每个 10 件（Finished Goods - SHD） |
| **测试环境** | 用户 `pos.test@solua.one`（Sales User/Accounts User/Sales Master Manager）、POS Profile `收银方式1-Test`（顾客=Walkin）、开店单 `POS-OPE-2026-00003` |

##### 端到端实测结果（浏览器真实操作）

| 步骤 | 结果 |
|------|------|
| 打开 POS 页面 | ✅ 秒开，空态提示「请扫码或搜索商品」（默认不加载全量物料，扫码/搜索才出商品） |
| 顾客默认值 | ✅ `Walkin` |
| 搜索框输入条码 `6901234567890` | ✅ 弹出「选择颜色」弹窗，6 个色块全显示 |
| 点击 Branco | ✅ 弹窗关闭，购物车加入 `CR-001-BR` × 1 |
| 购物车价格 | ✅ MZN 1,200.00 |
| JS 控制台 / 服务器错误日志 | ✅ 均无错误 |

##### 过程中发现并解决的问题

| 问题 | 根因 | 解决 |
|------|------|------|
| 🔴 扫码报 403「Item Price 权限不足」 | 生产站点 Item Price 仅授权 `Purchase/Sales Master Manager`，`Sales User` 无读权限（与默认权限不同） | 测试用户补 `Sales Master Manager` 角色；**真实收银员需另行决策授权方式** |
| 🔴 点色报「仓库 Finished Goods - SHD 中无此物料 CR-001-BR」 | Variant 无库存（Bin 记录为空） | Stock Reconciliation 补库存（`MAT-RECO-2026-00002`，10 件/色） |
| 🟡 补库存时 `LinkValidationError: 找不到物料` | Variant 编码写错（BE/CI/VE 与实际 BG/CZ/VM 不符） | 以 `frappe.get_all("Item", filters={"variant_of": "CR-001"})` 查实际编码为准 |

##### 遗留事项

- [x] **权限决策（已完成）**：已给 `Sales User` 角色添加 Item Price **读权限**（仅 read，最小权限）；收银员账号扫码正常，无需再逐个授权
- [ ] **清理测试数据**：`pos.test` 用户、`收银方式1-Test` Profile、CR-001 测试物料与库存、测试开店单
- [ ] POS 页面首屏按物料分组点击不放行（无搜索词返回空）——如需「点分组即显示该组商品」可调整 `get_items` 逻辑

#### 6.5.10 窗帘建档与颜色维护操作指南（日常操作）

> **适用**：新增一款窗帘、给某款加/减/改颜色、颜色字典加新色。
> 核心概念：**颜色字典（Cor 属性，全店共享）** + **每款窗帘的颜色组合（模板 attributes，独立配置）** + **Variant（生成的实物 SKU，管库存/销售/价格）**。

##### 场景 A：新建一款窗帘（示例：CR-002，只有白/黑两色）

1. 新建 Item：`item_code = CR-002`，**勾选 has_variants=1**
2. 在 **attributes** 子表加两行：`Cor = Branco`、`Cor = Preto`（从属性下拉选择，无需手输）
3. 保存后点 **「创建变体」**（Create Variants）→ 自动生成 `CR-002-BR`、`CR-002-PR`
4. 给 Variant 设价（**详见下方「定价规则」**）：价格 = 标签价（含 IVA）；**模板 standard_rate 不要填**；建完变体后到 Selling → **Item Price（Standard Selling）** 批量加价（⋮ → Add Multiple Items）
5. 重复步骤 4 前，先在模板 attributes 中把所有颜色加齐，一次性创建全部 Variant

##### 场景 B：颜色字典里没有的新颜色（示例：新增 Verde 绿）

1. 打开 **Item Attribute → Cor**，在 attribute_values 加一行：`attribute_value = Verde`，`abbr = VE`
2. 保存后该颜色**全店可用**（其他款窗帘也能用）
3. 回到需要此色的窗帘模板，attributes 加行 `Cor = Verde` → 创建变体 → 生成 `CR-003-VE`

> ⚠️ 若使用真实 EAN 条码，注意 `Code128` 类型可绕过校验（见 6.5.2）。`Cor` 颜色 Variant 不添加原生 Item Barcode；其 `custom_label_barcode` 必须等于模板唯一的原包装条码。扫描仍由模板条码触发颜色选择，标签也打印该共享条码。

##### 场景 C：修改一款窗帘的颜色

| 操作 | 做法 |
|------|------|
| **加一个颜色** | 模板 attributes 加行 → 创建变体 |
| **去掉一个颜色** | 找到对应 Variant → **禁用**（Disabled=1，不影响历史单据）；若还没有库存/单据可直接删除 |
| **改名（颜色值）** | 改 Cor 属性 attribute_value（abbr 不变则 Variant 编码不变）；注意同名不允许重复 |
| **停产一款窗帘** | 模板 attributes 全删 + 所有 Variant 禁用 |

> ⚠️ **删除 vs 禁用**：已有库存或单据引用的 Variant 无法删除，会报错；一律用**禁用**下架。

##### 定价规则（标签价含税，2026-08-16 起生效）

> **一句话**：`standard_rate` 与 Item Price 价格 = **标签打印价 = 顾客实付价（已含 IVA 16%）**，不要再填净价。

| 项 | 说明 |
|----|------|
| **填什么** | 标签上要印的最终价（含税）。例：标签印 1500 → 填 1500 |
| **系统怎么算** | POS 结账自动按价内税拆分：1500 → 净额 1293.10 + IVA 206.90；顾客实付仍 1500，账上税照记（税模板 `IVA - SH`，价内税 included_in_print_rate=1） |
| **价格存哪（一处）** | **Item Price（Standard Selling）**：POS 取价和价格标签「现价」都读它（label_helpers.get_selling_price）。**改价只改这一处，两处自动一致**，无需再改 Item.standard_rate |
| **新建 Variant 批量加价** | **模板 standard_rate 不要填**（会触发自动建价并报错）；向导/原生创建变体都不带价（继承模板价，模板没价=没价），建完后批量加价：Selling → **Item Price → ⋮ → Add Multiple Items**（按物料列表统一设价） |
| **改价流程** | 改 Item Price（Standard Selling）的 price_list_rate → 重打标签，POS 同步生效 |
| **税费配置（已就位）** | `IVA - SH` 税行 = 价内税；POS Profile「收银方式1 - SH」已挂 `IVA - SH`；重复模板 `Mozambique Tax - SH` 已停用 |

> ⚠️ **两种模式不要混用**：模式 A（本规则，价内税，顾客付标签价）与模式 B（净价+加税，顾客多付 16%）不可并存。所有物料统一按模式 A 建档。

##### 注意事项

- **Variant 编码规则**：`模板码-颜色缩写`（如 CR-001-BR），由 **Item Variant Settings** 控制（本项目已配置 81 个继承字段）
- **颜色名保持葡语**（决策 2026-08-06）：属性值是数据、不自动翻译，与实物包装标签（葡语 Branco/Preto...）一致；界面按钮/菜单的英文走第 7 章翻译机制
- **建 Variant 前确认**：模板 attributes 一次加齐所有颜色再点创建变体，避免反复生成

##### 变体生成三条路径速查（2026-09-08 补充）

> 给模板生成变体共三条路径：**界面按钮（日常）**、**官方 API（批量/集成）**、**本项目向导（推荐批量）**。
> 三条路径都基于同一套底层逻辑（`erpnext/controllers/item_variant.py`），只是入口不同，产物等价（均为 `variant_of=模板` 的 SKU）。

**路径一：界面标准操作（日常单款维护）**

1. 新建/打开模板 Item：勾选 **has_variants=1**，`variant_based_on = Item Attribute`，在 attributes 子表加好属性行（本项目=Cor 颜色）
2. 工具栏点 **「Make Variant / 创建变体」** 按钮 → 按属性值组合逐个生成；或模板保存后点 **「Create Variants」** 一键生成全部组合
3. 变体编码由 `make_variant_item_code()` 自动生成（本项目规则 `模板码-颜色缩写`，如 CR-001-BR）
4. 给变体批量定价：Selling → **Item Price → ⋮ → Add Multiple Items**（模板 standard_rate 不要填，见上方定价规则）

> ⚠️ 模板本身不能进业务单据（`ItemTemplateCannotHaveStock`），库存/POS/销售一律走变体。

> **成本价建档规则**：普通库存物料和具体 Variant 建档时必须填写大于 0 的「成本价（Valuation Rate）」，否则不能保存；`has_variants=1` 的模板仅用于生成 Variant，可以暂不填写成本价。创建 Variant 时，系统会自动继承模板的成本价；如果模板成本价为空，会阻止 Variant 创建，需先补充模板的默认成本价。该规则不适用于非库存物料或受托加工物料。

**路径二：官方代码/API（批量、自动化）** — `erpnext/controllers/item_variant.py`

| 函数 | 作用 |
|------|------|
| `get_variant(template, args)` | 按属性组合查**已存在**的变体（args 如 `{"Cor": "Branco"}`，找不到返回 None） |
| `create_variant(item, args, use_template_image)` | 创建**单个**变体（内部 `copy_attributes_to_variant` 自动复制 Item Variant Settings 勾选的继承字段） |
| `create_multiple_variants(item, args)` | **批量**：传 `{"Cor": ["Branco", "Preto"]}` 自动做笛卡尔积生成全部组合 |
| `enqueue_multiple_variant_creation()` | 组合数 ≥10 自动丢后台队列；>500 拒绝 |

**路径三：本项目自定义向导（推荐批量，第十一会话已交付）**

- 入口：物料列表页 → 顶部按钮 **「批量生成变体」**（`item_variant_wizard.js`，注册于 hooks `page_js`）
- 流程：选模板 → 勾颜色（Cor 颜色池，6→16 色已扩容、缩写去冲突）→ 服务端批量建变体
- API：`solua_home.api.variants.bulk_create_variants(template_item, attribute_values=None, price_list=None)`（`my_custom_app_example/solua_home/api/variants.py`）
  - `attribute_values=None` = 属性全部值；传列表 = 只生成勾选颜色
  - 已存在同属性组合的变体自动跳过，返回 `{created, skipped, errors}`
  - 支持价格表参数（默认 Standard Selling），可与批量定价一步完成

#### 6.5.11 零售环境瘦身：POS 限组 + 隐藏工厂模块（2026-08-06 已执行）

> **背景**：POS 页面物料分组树显示了系统自带的空组（Raw Material/Sub Assemblies/Consumable）和演示数据组（Demo Item Group），且桌面有工厂类模块（制造/项目/质量等）。零售店不需要，做了两处清理：

##### 1. POS Profile 限制物料组（只显示成品）

在 POS Profile → 物料组（item_groups）子表添加 `Products`（或自己需要的组）：

```python
pp = frappe.get_doc("POS Profile", "收银方式1")
pp.append("item_groups", {"item_group": "Products"})
pp.save(ignore_permissions=True)
```

- 效果：POS 分组树只显示配置的组（含子组），`get_items` 只返回组内物料
- 验证：`get_item_groups("收银方式1")` → `[Products]`；`get_parent_item_group` → `Products`

##### 2. 隐藏模块 Workspace（对非管理员生效）

Frappe 桌面侧边栏来自 Workspace（`frappe/desk/desktop.py` 的 `get_workspaces`），每个模块对应一个 Workspace，`is_hidden=1` 即从侧边栏隐藏：

```python
ws = frappe.get_doc("Workspace", "Manufacturing")
ws.is_hidden = 1
ws.save(ignore_permissions=True)
```

| 已隐藏 | 说明 |
|--------|------|
| Manufacturing 制造 | 生产/工单/BOM，零售不用 |
| Projects 项目 | 项目管理 |
| Quality 质量（name=Quality，module=Quality Management） | 质检流程 |
| Subcontracting 分包 | 委外加工 |

> ⚠️ **注意**：
> - **管理员（has_access）仍可见**所有 Workspace，隐藏只对普通用户生效——这是 Frappe 系统设计，日常操作建议用普通账号（如收银员 Sales User），管理员仅做配置
> - 无独立 Workspace 的模块（如 Maintenance、EDI）本来就不显示在侧边栏，无需处理
> - 恢复：`ws.is_hidden = 0` 即可；纯界面级，零风险
> - 清缓存：`bench --site erp.solua.one clear-cache`

##### 附：模块清单分类（决定隐藏时参考）

| 分类 | 模块 |
|------|------|
| ✅ 业务核心（保留） | Accounts/Buying/Selling/Stock/Setup + frappe 基础（Core/Custom/Desk/Contacts/Email/Printing/Geo） |
| 🟡 视情况 | Support（售后工单）/Assets（固定资产）/Portal（客户门户）/CRM（保留，用到客户） |
| 🟢 可隐藏 | Manufacturing/Quality/Projects/Maintenance/Subcontracting/Telephony/EDI/Website |

##### 附：隐藏表单评论输入框（保留活动时间线）（2026-08-07 已执行）

> **背景**：所有表单页底部有「评论输入框 + 活动时间线」，零售场景不需要员工在单据上评论，但**活动时间线**（创建/修改/状态记录）仍有审计价值，需保留。

- **实现**：`solua_home/public/css/hide_comments.css`（隐藏 `.comment-box`，不动 `.timeline`）+ hooks.py 注册 `app_include_css`

```css
/* hide_comments.css —— 只隐藏评论输入框，保留活动时间线 */
.comment-box { display: none !important; }
```

```python
# hooks.py
app_include_css = [
    "/assets/solua_home/css/hide_comments.css",
]
```

- **部署**：同步三处（本地/GitHub/服务器）→ `bench build --app solua_home`（**必须用 Node 24**，见第五节）→ 重启 supervisor → 浏览器强刷（Ctrl+Shift+R）
- **验证**：`curl -k https://erp.solua.one/assets/solua_home/css/hide_comments.css` → 200
- **提交**：`87444ed`（GitHub solua-erp）

#### 6.5.12 员工账号创建与角色分配（日常运维）

> **适用**：给收银员/店员/店长建账号。员工用邮箱+密码登录，界面语言可设中文。

##### 方式一：管理员在界面创建（推荐）

1. 管理员登录 → 右上角头像 → **设置**（或地址栏直接访问 `/app/user`）
2. 点 **+ 新建**，填写：

| 字段 | 填什么 |
|------|--------|
| **Email** | 员工登录名（如 `ana@solua.one`，须为有效邮箱格式） |
| **First Name / Full Name** | 员工姓名 |
| **语言** | 简体中文 |
| **角色** | 按岗位勾选（见下表） |
| **新密码** | 初始密码（或发邀请邮件让员工自设） |

3. **保存** → 员工即可用邮箱+密码登录。

##### 角色选择（决定员工权限）

| 岗位 | 推荐角色组合 | 能干什么 |
|------|------------|---------|
| **收银员** | `Sales User` + `Accounts User`（+ **`POS Cashier`** 若需自助开店/关店） | POS 收银、开销售单、收款、看自己单据 |
| **店员/销售** | `Sales User` | 录销售订单、报价单 |
| **店长/主管** | `Sales User` + `Accounts User` + `Sales Master Manager` + `Accounts Manager` | 以上全部 + 改价格、看财务、撤销单据 |
| **店主** | 保持 Administrator 唯一；日常操作建议用店长号（管理员界面不受模块隐藏影响） | — |

> 💡 Item Price 读权限已授 `Sales User`（2026-08-06），收银员扫码看价格无障碍。

##### 员工首次使用

- 员工首次 POS 收银前需先「开店」（POS Opening Entry）
- 若员工需用特定收银台，在 POS Profile → 适用用户（applicable_for_users）中添加该员工
- 员工账号登录后侧边栏只显示有权限的模块（工厂类模块已隐藏，见 6.5.11）

##### ⚠️ 开店/关店权限（2026-08-07 实战补充）

ERPNext 默认**只给 `Sales Manager` / `System Manager` 开店关店权限**（`POS Opening Entry` / `POS Closing Entry` 的 submit），纯收银员（Sales User + Accounts User）**无法自助开店**——POS 页面会报权限错误。若门店需要收银员自己开/关店，创建自定义角色：

```python
import frappe
from frappe.permissions import add_permission

# 1. 建角色（一次）
if not frappe.db.exists("Role", "POS Cashier"):
    frappe.get_doc({"doctype": "Role", "role_name": "POS Cashier",
                    "desk_access": 0, "is_custom": 1}).insert(ignore_permissions=True)

# 2. 配权限（v16 写入 Custom DocPerm；add_permission 每 ptype 建一行，再 UPDATE 配齐）
for dt in ["POS Opening Entry", "POS Closing Entry"]:
    add_permission(dt, "POS Cashier", permlevel=0, ptype="read")
    frappe.db.sql(
        "UPDATE `tabCustom DocPerm` SET `read`=1, `create`=1, `write`=1, `submit`=1, "
        "`delete`=0, `amend`=0, `if_owner`=0, `permlevel`=0 "
        "WHERE parent=%s AND role='POS Cashier' AND if_owner=0", (dt,))
frappe.db.commit()

# 3. 绑定角色 + 默认公司 + 静音
for email in ["pos1@solua.one", "pos2@solua.one"]:
    u = frappe.get_doc("User", email)
    u.append("roles", {"role": "POS Cashier"})
    u.mute_sounds = 1  # 静音
    u.save(ignore_permissions=True)
    frappe.defaults.set_user_default("company", "Solua Home, Lda", user=email)
```

> 💡 2026-08-07 已在生产创建 `POS Cashier` 角色并绑定 pos1/pos2（最小权限：仅开店/关店两个单据，不含其他权限）。
> ⚠️ 注意：`POS Profile` 的 `applicable_for_users` 子表一旦非空，该 Profile **只对子表内用户可见**（`pos_profile_query` 逻辑），记得把管理员也加进去，避免管理员被排除。
> ⚠️ 若收银员每天上班需要固定收银台，可考虑开店后保持 Open 状态到下班；管理员可见所有 Profile 不受子表限制。

##### 方式二：命令行创建（脚本）（2026-08-07 实战版，含绑定/静音/默认公司）

```python
import frappe
from frappe.utils.password import update_password

u = frappe.new_doc("User")
u.email = "ana@solua.one"
u.first_name = "Ana"
u.enabled = 1
u.send_welcome_email = 0
for role in ["Sales User", "Accounts User"]:
    u.append("roles", {"role": role})
u.insert(ignore_permissions=True)
update_password("ana@solua.one", "初始密码")
frappe.db.commit()
```

### 7.1 汉化策略概览

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **UI 翻译** | 少量补充翻译 | 最快，无需代码 | 不便批量管理 |
| **CSV 文件** | 批量导入翻译 | 可版本管理 | 需运行命令 |
| **Python 代码** | 自动批量导入 | 自动化，可集成到安装流程 | 需写代码 |
| **po 文件** | 完整的语言包 | 官方标准方式 | 更新时可能被覆盖 |

### 7.2 方式一：通过 UI 翻译（最简单）

> 设置 → 系统设置 → 翻译 → 新增

| 字段 | 填写 |
|------|------|
| 源文本 | `Overdue` |
| 翻译 | `逾期` |
| 语言 | `简体中文 (zh-CN)` |

### 7.3 方式二：通过 CSV 文件批量导入

创建 `apps/solua_home/translations/zh.csv`：

```csv
"Source","Target"
"Overdue","逾期"
"Sales Invoice","销售发票"
"Customer","客户"
"Purchase Order","采购订单"
"Item","物料"
```

> **注意**：`import-translations` 命令在 bench 5.x 中不可用。推荐使用下方的**方式三（代码自动翻译）**，
> 翻译会在 `bench migrate` 时通过 `after_migrate` 钩子自动导入。

### 7.4 方式三：通过代码自动翻译（推荐）

> ⚠️ **重要**：Frappe v16 的 Translation DocType 字段名是 `source_text` 和 `translated_text`，语言代码用 `zh` 不是 `zh-CN`

在 `install.py` （注意不是 `setup.py`，避免与打包配置重名）中实现：

```python
# solua_home/install.py
import frappe

def after_install():
    add_translations()
    frappe.db.commit()

def after_migrate():
    after_install()

def add_translations():
    """批量添加中文翻译"""
    translations = {
        # 销售模块
        "Sales Invoice": "销售发票",
        "Sales Order": "销售订单",
        "Customer": "客户",
        "Overdue": "逾期",
        "Pending Approval": "待审批",
        "Approved": "已审批",
        "Fully Paid": "已全额付款",
        # 采购模块
        "Purchase Order": "采购订单",
        "Supplier": "供应商",
        # 库存模块
        "Item": "物料",
        "Warehouse": "仓库",
        # 更多翻译...
    }

    for source, target in translations.items():
        try:
            if not frappe.db.exists("Translation", {
                "source_text": source,        # 不是 "source"
                "language": "zh"              # 不是 "zh-CN"
            }):
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "source_text": source,          # 不是 "source"
                    "translated_text": target,      # 不是 "target"
                    "language": "zh",               # 不是 "zh-CN"
                    "contributed": 0,
                })
                doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"翻译插入失败: {source}: {e}", "solua_home")
            continue
```

在 `hooks.py` 中注册：

```python
after_install = "solua_home.install.after_install"
after_migrate = "solua_home.install.after_migrate"
```

### 7.5 翻译实践建议

1. **优先翻译常用模块**：Sales Invoice（销售发票）、Purchase Order（采购订单）、Item（物料）、Customer（客户）
2. **保持翻译一致性**：同一术语全系统一致
3. **注意中文标点**：使用中文标点（，。：；）
4. **测试翻译效果**：翻译后切到中文界面检查
5. **翻译保存在两个地方**：CSV 文件（用于导入）和 `install.py`（通过代码自动添加），两者应保持一致
6. **覆盖热门模块**：建议覆盖销售、采购、库存、财务、制造、CRM、项目、人事等核心模块

---

## 8. 部署到服务器

### 8.1 准备工作

```bash
# 在本地 WSL2 中
cd ~/frappe-bench/apps/solua_home

# 初始化为 Git 仓库
git init
git add .
git commit -m "初始提交"

# 在 GitHub/Gitee/GitLab 上创建仓库
git remote add origin https://github.com/a83986475/solua-erp.git
git push -u origin main
```

### 8.2 在服务器上拉取并安装

```bash
# 登录到服务器
ssh user@your-server

# 进入 bench 目录
cd /path/to/bench

# 获取自定义 app
bench get-app https://github.com/a83986475/solua-erp.git

# 安装到生产站点
bench --site your-production-site install-app solua_home

# 迁移
bench --site your-production-site migrate

# 构建前端
bench build --app solua_home

# 重启
sudo supervisorctl restart all

# 清理缓存
bench --site your-production-site clear-cache
```

> **注意**：如果是手动部署（没有 git 仓库），需要额外注册：
> 1. 创建 Python symlink：`ln -sf 你的路径 env/lib/python3.*/site-packages/solua_home`
> 2. 注册到 `apps.txt` 和 `apps.json`
> 3. 然后执行 `install-app` 和 `migrate`

### 8.3 Git 工作流（推荐）

```
本地开发 → git push → 服务器上 git pull → bench migrate → supervisor restart
```

#### 8.3.1 本地初始化

```bash
cd ~/frappe-bench/apps/solua_home

# 创建 .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*.egg-info/
.idea/
.vscode/
.DS_Store
*.tar.gz
node_modules/
EOF

git init
git add -A
git commit -m "初始提交"

# 在 GitHub 上创建仓库后关联
git remote add origin https://github.com/a83986475/solua-erp.git
git push -u origin main
```

#### 8.3.2 服务器上首次部署

```bash
ssh qq 'sudo -u frappe -i bash -l -c "
  cd /home/frappe/frappe-bench
  rm -rf apps/solua_home
  git clone https://github.com/a83986475/solua-erp.git apps/solua_home
  ln -sf /home/frappe/frappe-bench/apps/solua_home env/lib/python3.14/site-packages/solua_home
  source env/bin/activate
  bench --site erp.solua.one install-app solua_home
  bench --site erp.solua.one migrate
  sudo supervisorctl restart all
"'
```

#### 8.3.3 后续更新

```bash
# 本地
cd ~/frappe-bench/apps/solua_home
git add -A && git commit -m "新功能: xxx"
git push

# 服务器（一键更新）
ssh qq 'sudo -u frappe -i bash -l -c "
  cd /home/frappe/frappe-bench/apps/solua_home
  git pull
  cd /home/frappe/frappe-bench
  source env/bin/activate
  bench --site erp.solua.one migrate
  bench --site erp.solua.one clear-cache
  sudo supervisorctl restart all
"'
```

---

## 9. 上线前核对清单（上线 SOP）

> 来源：2026-08-16 生产实测核对（erp.solua.one），2026-08-17 更新（仓库统一落库、CR-002 资料补全、物料资料向导上线）。上线前逐项核对，每完成一项打勾。

### 9.1 核对清单

**🔴 上线必做**

| # | 事项 | 实测状态（2026-08-17） | 上线前动作 |
|---|------|----------------------|-----------|
| 1 | 公司 tax_id（NUIT） | 空 | 填莫桑比克 NUIT 税号（发票打印需要，号码由公司提供） |
| 2 | 库存 | 491 件**测试库存**（6 变体，CR-001-PR=0） | 真实物料 + 真实库存盘点（Stock Reconciliation 入库到 Finished Goods - SH，建议带成本价） |
| 3 | Item 自定义字段 | ✅ CR-001/CR-002 系列已填（中文名/SPU/POS简称/最低库存，2026-08-17 向导补全） | 正式物料用「物料资料补全」向导批量维护；规格摘要可选 |
| 4 | 正式仓库 | ✅ **Finished Goods - SH**（Item Defaults 13 条已统一，2026-08-16/17） | 已解决，勿再改回 Stores - SH |
| 5 | 收银员账号 | ✅ pos1/pos2 已建、已启用、已绑定「收银方式1 - SH」 | 上线时重置密码交接 |

**🟡 建议做**

| # | 事项 | 实测状态 | 说明 |
|---|------|---------|------|
| 6 | 供应商 | 0 个 | 首次采购前建 |
| 7 | 采购价表 | Standard Buying 仅 1 条测试价（800 MZN） | 正式采购按供应商补 |
| 8 | 银行账户 | 0 条（Credit Card 已指向 Bank - SH 科目） | 不阻塞收银；银行对账/转账时需要时建 |
| 9 | 成本价 valuation_rate | 全空 | 首批真实物料建档/入库时带上，否则利润报表算不出 |
| 10 | 最低库存 | CR-002=10、CR-001=0 | 按产品线定水位（daily_tasks 低库存预警依赖此字段） |

**🟢 可延后**
- CR-002 系列测试物料（半成品档案）→ 上线前清理或重置
- **小票版式未定**（58/80mm 热敏纸宽度未确认）——每天收银都要用，上线前必须定（设计入口：Print Designer 可视化拖拽，画布设 80mm 宽）
- （仓库策略已统一，不再待办）

### 9.2 已解决项备忘

- **正式仓库 = Finished Goods - SH**：库存 100% 在 FG、POS Profile 本就指向 FG；Stores - SH 空仓保留（防未来多门店），Goods In Transit - SH 预留采购在途。Item Defaults 12 条 Stores→FG + Solua 原 FG = 13 条全部一致。⚠️ 教训：2026-08-16 首次执行漏 `frappe.db.commit()` 被回滚，08-17 补 commit 才真正落库——**服务端脚本改数据后必须显式 commit，验证用独立进程**。
- **物料资料补全/校验向导**（2026-08-17 上线）：物料列表 →「物料资料补全」→ 选模板自动预填（中文名=模板中文名、SPU=模板SPU、POS简称=颜色、最低库存默认 10）→ 行内改 → 保存；「校验全部物料完整性」出全量报告（必填：中文名/SPU/变体POS简称/条码/默认仓库/售价[模板除外]；警告：规格摘要/最低库存/成本价）。API：`solua_home.api.item_data`（get_item_data / bulk_update_item_data / validate_item_master）。⚠️ 注册在 hooks `doctype_list_js`——**Item 是 DocType，`page_js` 对 DocType 列表页不生效**（只对 Page 文档生效）。

### 9.3 上线执行顺序（SOP）

1. **填公司资料**：公司 → 填 tax_id（NUIT 号码由公司提供）
2. **定小票版式**：确认热敏纸宽度（58/80mm）→ Print Designer 做「小票」格式 → POS Profile 挂接
3. **真实物料建档**：按 6.5.10 窗帘建档流程（建模板 → 批量生成变体 → 物料资料补全向导填中文名/SPU/POS简称/最低库存 → Item Price 批量定价；**standard_rate = 标签价 = 顾客实付价（含 IVA）**）
4. **真实库存盘点**：Stock Reconciliation 入库到 Finished Goods - SH（含成本价 valuation_rate）
5. **收银员交接**：重置 pos1/pos2 密码，分配 PIN
6. **清理测试数据**：CR-002 半成品测试档案、测试单据（对照 SHD 删除记录档）
7. **全量校验**：物料列表 →「物料资料补全」→「校验全部物料完整性」→ 必填项全部通过
8. **试营业实测**：POS 开店/收银/扫码选色/折扣审批/静默打印/交班全流程各跑一遍

### 9.4 标签打印功能使用说明（员工培训）

> 本节供收银员/仓管员日常使用，非技术人员可直接阅读。

#### 功能简介

标签打印功能用于为商品打印价格标签。操作员可通过扫描条码或输入关键词快速定位物料，选择打印模板和数量后批量打印。

#### 打开方式

| 方式 | 操作 |
|------|------|
| **键盘快捷键** | 在系统任意页面按 **Ctrl + L** |
| **浮动按钮** | 点击页面右下角的 🏷️ 蓝色圆形按钮 |

> POS 收银页面内不显示浮动按钮（避免干扰收银），但仍可用 Ctrl+L 打开。

#### 操作流程

**第一步：搜索物料**

1. 打开标签打印界面后，光标自动定位在搜索框
2. **扫码枪扫描**：直接扫商品条码，系统自动搜索并显示结果
3. **手动输入**：输入物料编码（如 `CR-001-BR`）、中文名（如「罗马帘」）或葡语名，按 **Enter** 或点击「🔍 搜索」

搜索结果会显示：
- ✅ 物料图片缩略图（点击可放大预览）
- ✅ 物料名称（中文名/葡语名）
- ✅ 物料编码
- ✅ 条码列表
- ✅ **库存数量**（绿色数字表示有库存，红色「⚠️ 无库存」表示缺货）
- ✅ 售价

**第二步：选择物料**

- 勾选要打印的物料（支持多选，批量打印）
- 模板类物料（如 CR-001）会自动展开为各颜色变体
- 快捷键：**Space** 切换选中、**↑↓** 导航、**Ctrl+A** 全选

**第三步：设置打印参数**

- **打印格式**：选择标签模板（如「价格标签 50x30」）
- **每件数量**：设置每个物料打印几张标签（默认 1）
- 快捷键：**+/-** 增减数量

**第四步：打印**

- 点击「🖨️ 打印」或按 **Ctrl + P**
- 系统自动弹出新窗口生成标签预览
- 浏览器打印对话框弹出 → 选择标签打印机 → 确认打印
- 打印完成后关闭预览窗口即可

#### 打印历史

- 点击顶部「📋 打印历史」Tab（或按 **Ctrl + H**）查看最近打印记录
- 每次打印自动记录：打印时间、操作员、物料、格式、数量
- 点击「🔄 重打」按钮可快速重新搜索并打印同一物料

#### 快捷键速查表

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + L` | 打开 / 关闭标签打印界面 |
| `F2` | 聚焦搜索框（扫码枪自动触发搜索） |
| `Ctrl + P` | 打印选中物料 |
| `Ctrl + H` | 切换到打印历史 |
| `Esc` | 关闭界面 / 清空搜索 |
| `↑ ↓` | 上下导航搜索结果 |
| `Space` | 切换当前项选中/取消 |
| `+` / `-` | 增减打印数量 |
| `Ctrl + A` | 全选 / 取消全选 |

#### 常见问题

| 问题 | 解决方法 |
|------|----------|
| 按 Ctrl+L 没反应 | 检查是否在输入框内（需先点击空白区域退出输入框），或刷新页面 |
| 搜索无结果 | 确认条码/名称输入正确；检查物料是否已停用 |
| 库存显示 0 | 该物料未入库或库存已清零，但不影响打印标签 |
| 打印窗口被拦截 | 浏览器地址栏右侧点击「允许弹窗」，然后重试 |
| 标签内容不完整 | 联系管理员检查打印格式（Print Format）配置 |
| 无可用打印格式 | 联系管理员在后台创建 Item 打印格式 |

---

## 10. 常用命令速查

### 10.1 环境管理

```bash
# 打开 WSL2
wsl

# 启动服务
sudo service mariadb start
sudo service redis-server start

# 启动开发服务器
bench start

# 指定端口启动
bench start --port 8001
```

### 10.2 Bench 命令

```bash
bench --version                          # 查看版本
bench new-app app_name                   # 创建新 app
bench new-doctype DocTypeName            # 创建新 DocType
bench get-app git-url                    # 获取 app
bench --site site-name install-app app   # 安装 app
bench --site site-name uninstall-app app # 卸载 app
bench --site site-name migrate           # 数据库迁移
bench --site site-name clear-cache       # 清理缓存
bench --site site-name console           # Python 交互式控制台
bench build                              # 构建前端资源
bench restart                            # 重启
bench update                             # 更新所有 app
```

### 10.3 调试命令

```bash
bench --site dev.localhost run-tests            # 运行测试
bench --site dev.localhost run-tests --module solua_home.tests  # 运行指定测试
bench console                                    # Python shell
bench --site dev.localhost export-fixtures       # 导出 fixtures
```

### 10.4 站点管理

```bash
bench new-site site-name                    # 创建新站点
bench --site site-name reinstall            # 重新安装
bench drop-site site-name                   # 删除站点
bench --site site-name list-apps            # 列出已安装 app
bench --site site-name backup               # 备份
bench --site site-name restore 备份文件路径   # 恢复
```

---

## 11. 安装问题排查

### 11.1 pip3 install 报 `externally-managed-environment`

**错误信息**：`This environment is externally managed`

**原因**：Ubuntu 24.04 的 PEP 668 保护机制，禁止 `pip3` 直接全局安装包。

**解决**：
```bash
# 用 pipx 代替 pip3
sudo apt install -y pipx
pipx ensurepath
source ~/.bashrc
pipx install frappe-bench
```

### 11.2 bench init 报 `No such file or directory: 'uv'`

**错误信息**：`FileNotFoundError: [Errno 2] No such file or directory: 'uv'`

**原因**：bench 5.x 使用 `uv` 管理虚拟环境，但系统未安装。

**解决**：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version   # 验证
```

### 11.3 bench init 报 `pkg-config is not installed`

**错误信息**：`pkg-config is not installed. Please install it before proceeding.`

**原因**：编译 frappe 的 Python 依赖时需要 `pkg-config`。Ubuntu 24.04 默认未安装。

**解决**：
```bash
sudo apt install -y pkg-config
```

### 11.4 bench init 报 `Python>=3.14,<3.15` 不满足

**错误信息**：`Because the current Python version (3.12.3) does not satisfy Python>=3.14`

**原因**：ERPNext v16 的 `version-16` 分支最新版要求 Python 3.14+。

**解决**：
```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.14 python3.14-dev python3.14-venv
# 然后 bench init 时指定 python3.14
bench init frappe-bench --frappe-branch version-16 --python python3.14
```

### 11.5 bench build 报 `Expected node >=24`

**错误信息**：`The engine "node" is incompatible with this module. Expected version ">=24"`

**原因**：ERPNext v16 最新版要求 Node 24+。

**解决**：
```bash
nvm install 24
nvm alias default 24
node --version   # 验证为 v24.x.x
```

### 11.6 使用 root 用户操作导致的权限问题

**问题**：用 `sudo bench init` 后，文件所有者变为 root，普通用户无法编辑。

**解决**：
```bash
# 退出 root
exit
# 重新以普通用户操作
# 如果已经用了 sudo bench init，需要改回权限
sudo chown -R $(whoami):$(whoami) ~/frappe-bench
```

### 11.7 安装过程中断后重试

bench init 支持断点续传。如果中途失败：

```bash
# 如果提示回滚，选 N（不回滚，保留已下载内容）
Do you want to rollback these changes? [y/N]: N

# 修复问题后，重新执行同一命令即可
bench init frappe-bench --frappe-branch version-16 --python python3.14

# 如果之前已经删掉了目录，就直接重来
rm -rf ~/frappe-bench
bench init frappe-bench --frappe-branch version-16 --python python3.14
```

---

## 12. 服务器运维问题排查

### 12.1 supervisor 没有加载 frappe 进程组

**问题现象**：`bench restart` 报 `restarting supervisor group 'frappe:' failed`，`supervisorctl status` 为空或报 `no such group`。

**原因**：bench 已生成 supervisor 配置文件，但未链接到 `/etc/supervisor/conf.d/`，导致 supervisor 没有加载。

**解决**：

```bash
# 1. 检查 bench 是否已生成 supervisor 配置
ls -l ~/frappe-bench/config/supervisor.conf
# 应该显示文件存在

# 2. 链接到 supervisor 配置目录
cd ~/frappe-bench
sudo ln -s $(pwd)/config/supervisor.conf /etc/supervisor/conf.d/frappe-bench.conf

# 3. 重新加载 supervisor 配置
sudo supervisorctl reread
sudo supervisorctl update

# 4. 检查状态
sudo supervisorctl status
# 应该看到以下进程组：
# frappe-bench-redis-cache       RUNNING
# frappe-bench-frappe-web        RUNNING
# frappe-bench-node-socketio     RUNNING
# frappe-bench-frappe-long-worker-0  RUNNING
# frappe-bench-frappe-short-worker-0 RUNNING
# frappe-bench-frappe-schedule   RUNNING
```

### 12.2 nginx 配置检查

```bash
# 检查 nginx 配置是否正确
sudo nginx -t

# 重新加载 nginx
sudo systemctl reload nginx
```

### 12.3 站点维护模式

```bash
# 检查站点状态
bench --site your-site doctor

# 关闭维护模式（如果站点显示维护中）
bench --site your-site set-maintenance-mode off
```

### 12.4 服务器备份与恢复

```bash
# 备份单个站点
bench --site your-site backup

# 备份所有站点
bench --site all backup

# 备份文件位置：~/frappe-bench/sites/your-site/private/backups/

# 恢复站点
bench --site your-site restore /path/to/backup/file.sql.gz
```

### 12.5 服务器中文翻译不生效

**问题现象**：系统设置切换到中文后，页面仍显示英文。

**原因**：生产模式下（supervisor/nginx），翻译从 `.mo` 文件加载。旧 `.mo` 文件可能损坏或不含中文翻译。

**解决**：
```bash
# 1. 删除旧的错误 .mo 文件（关键！）
rm -f sites/assets/locale/zh/LC_MESSAGES/erpnext.mo
rm -f sites/assets/locale/zh/LC_MESSAGES/frappe.mo

# 2. 重新编译（强制从 .po 源文件生成）
bench --site your-site compile-po-to-mo --locale zh --force

# 3. 清理缓存
bench --site your-site clear-cache

# 4. 重启服务
sudo supervisorctl restart all
```

**验证方法**：
```bash
bench --site your-site execute frappe.translate.get_all_translations --args "('zh',)" | wc -c
# 应返回 1.27MB+ 的数据
```

> ⚠️ 注意：
> - 命令是 `compile-po-to-mo`，不是 `compile-translations`（不存在）
> - 参数是 `--locale zh`，不是 `--language zh`
> - `.po` 源文件在 `apps/erpnext/erpnext/locale/zh.po`（非 `LC_MESSAGES` 目录）
> - 必须先删除旧 `.mo` 文件再编译，否则可能仍使用缓存

### 12.6 服务器 Node 版本切换

**问题**：`bench build` 总是使用系统 Node v20，忽略 nvm 安装的 Node 24。

**原因**：
1. supervisor 不加载 `.bashrc`，使用系统 PATH 中的 `/usr/bin/node`（v20）
2. 即使 nvm 安装了 Node 24，`bench build` 内部调用的 yarn 仍使用系统 Node

**解决**：更新 supervisor 配置，为 node-socketio 进程添加 PATH 环境变量

```bash
# 1. 备份原配置
cp config/supervisor.conf config/supervisor.conf.bak

# 2. 修改 supervisor.conf，在 [program:frappe-bench-node-socketio] 段添加：
environment=PATH=/home/frappe/.nvm/versions/node/v24.18.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 3. 重载配置并重启
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart all

# 4. 验证 socketio 使用的 Node 版本
ps aux | grep socketio
# /home/frappe/.nvm/versions/node/v24.18.0/bin/node ...
```

**同时更新 .bashrc** 让交互式登录也默认使用 Node 24：
```bash
echo 'export PATH=/home/frappe/.nvm/versions/node/v24.18.0/bin:$PATH' >> ~/.bashrc
```

---

## 13. 开发问题排查

### 13.1 WSL2 中 supervisor 警告（正常现象）

**问题现象**：在 WSL2 开发环境中执行 `bench build` 或 `bench restart` 时，看到：
```
WARN: restarting supervisor group `frappe:` failed. Use `bench restart` to retry.
```

**原因**：这是**正常的**。WSL2 开发环境使用 `bench start` 直接启动开发服务器，不依赖 supervisor。这条警告只是因为 bench 尝试重启 supervisor 管理下的进程，但在开发环境中 supervisor 没有被配置。

**处理**：忽略即可。开发时用 `bench start` 启动服务，这个警告不影响任何功能。

### 13.2 bench build 报 "Assets for Release ... don't exist"

**问题现象**：
```
Assets for Release v16.27.0 don't exist
✔ Application Assets Linked
```

**原因**：这是**正常的**。开发模式下没有预构建的生产环境静态资源包，bench 自动将源码链接为资产。

**处理**：无需处理。生产部署时才需要构建完整的资产包。

---

## 14. 自定义 App 开发问题排查

### 14.1 手动创建 App 后 `install-app` 报 `No module named 'X'`

**问题现象**：`bench --site dev.localhost install-app solua_home` 报 `No module named 'solua_home'`

**原因**：
1. App 目录结构不正确（hooks.py 放在嵌套目录中）
2. App 未注册到 `sites/apps.json`
3. Python 无法导入该模块

**App 的正确目录结构**：
```
apps/solua_home/          ← 这就是 solua_home 模块
├── __init__.py              ← 必须有！使 Python 可导入
├── hooks.py                 ← Frappe 读取 solua_home.hooks
├── api/
│   ├── __init__.py
│   └── sales.py
├── override/
│   ├── __init__.py
│   └── sales_invoice.py
├── install.py               ← after_install / after_migrate 函数
├── setup.py                 ← Python 打包配置（setuptools）
├── setup.cfg
├── requirements.txt
└── MANIFEST.in
```

> ❌ **常见错误**：如果误建成了两层 `apps/solua_home/solua_home/hooks.py`，Frappe 会找不到模块。
> `hooks.py` 必须直接在 `apps/solua_home/` 根目录下！

### 14.2 `setup.py` 和 `install.py` 的冲突

**问题**：Frappe App 有两个用途不同的 `setup.py`：
1. Python 打包配置（`from setuptools import setup, find_packages`）—— 在 App 根目录
2. Frappe 安装/迁移钩子（`after_install`, `add_translations`）—— 在模块内部

**如果两者重名**，Python 打包时会找不到包。**解决方案**：把 Frappe 安装函数改名为 `install.py`，并更新 `hooks.py` 引用：
```python
# hooks.py 中
after_install = "solua_home.install.after_install"   # 指向 install.py
after_migrate = "solua_home.install.after_migrate"  # 指向 install.py
```

### 14.3 Translation 字段名变更

**问题**：`frappe.get_doc({"doctype": "Translation", "source": ..., "target": ...})` 报 `MandatoryError`

**原因**：Frappe v16 的 Translation DocType 字段名是 `source_text` 和 `translated_text`，不是 `source` 和 `target`。

**解决**：
```python
# 正确字段名
{
    "doctype": "Translation",
    "source_text": "Overdue",          # 不是 "source"
    "translated_text": "逾期",        # 不是 "target"
    "language": "zh",                 # 不是 "zh-CN"
    "contributed": 0,
}

# 查询时也一样
frappe.db.exists("Translation", {
    "source_text": "Overdue",         # 不是 "source"
    "language": "zh"                  # 不是 "zh-CN"
})
```

### 14.4 `notification_config` 导致 migrate 失败

**问题**：migrate 时报 `ValueError: dictionary update sequence element`

**原因**：`hooks.py` 中的 `notification_config` 指向一个不存在或返回值格式错误的函数。

**解决**：如果不需要自定义通知，直接删除 hooks.py 中的 `notification_config` 行：
```python
# 删除这行
notification_config = "solua_home.config.notifications.get_notification_config"
```

### 14.5 `sites/apps.json` 注册

**问题**：手动创建的 App 无法被 bench 识别

**原因**：bench 不仅检查 `apps.txt`，还检查 `sites/apps.json` 中的注册信息

**解决**：
```python
python3 -c "
import json
with open('sites/apps.json') as f:
    reg = json.load(f)
reg['solua_home'] = {
    'is_repo': False,
    'resolution': {'commit_hash': None, 'branch': None},
    'required': [],
    'idx': 3,
    'version': '0.0.1'
}
with open('sites/apps.json', 'w') as f:
    json.dump(reg, f, indent=2)
print('✅ 已注册到 apps.json')
"
```

### 14.6 Redis 端口冲突：`Address already in use`

**问题现象**：启动 `bench start` 时报 `Failed listening on port 11000/13000, aborting`

**原因**：上次关闭 WSL 后，Redis 进程未完全退出，端口仍被占用。

**解决**：
```bash
# 杀掉占用 11000 和 13000 端口的残留进程
sudo fuser -k 11000/tcp 13000/tcp

# 然后重新启动
cd ~/frappe-bench && bash start.sh
```

**建议**：把清理命令加到 `start.sh` 中：
```bash
#!/bin/bash
cd "$(dirname "$0")"
sudo fuser -k 11000/tcp 13000/tcp 2>/dev/null   # ← 加这行
sudo service mariadb start
sudo service redis-server start
bench start
```

### 14.7 `bench start` 闪退：Scheduler 退出导致全部进程关闭

**问题现象**：`bench start` 启动约 1 秒后所有进程自动关闭
```
schedule.1 stopped (rc=0)
system | sending SIGTERM to redis_cache.1
system | sending SIGTERM to web.1
...
```

**原因**：`bench start` 使用 **honcho** 管理进程（读取 `Procfile`）。Procfile 中的 `schedule` 进程启动后立即退出（rc=0），因为 Scheduler 没有待执行的任务。honcho 发现任何进程退出就会**关闭全部进程组**。

**解决**：从 `Procfile` 中移除 `schedule:` 行：
```bash
cd ~/frappe-bench
cp Procfile Procfile.bak                 # 备份
grep -v "^schedule:" Procfile > Procfile.tmp && mv Procfile.tmp Procfile
bash start.sh                            # 正常启动
```

需要手动运行调度任务时：
```bash
bench --site dev.localhost schedule
```

恢复原始 Procfile：
```bash
cp Procfile.bak Procfile
```

### 14.8 `start.sh` PATH 中 Windows 路径导致语法错误

**问题现象**：运行 `start.sh` 报 `syntax error near unexpected token ('`

**原因**：`export PATH="$HOME/.local/bin:$PATH"` 中 `$PATH` 展开后包含 Windows 路径的括号 `Program Files (x86)`，Shell 语法解析失败。

**解决**：设置干净的 PATH，不引用 `$PATH`：
```bash
export PATH=/home/yang/.local/bin:/home/yang/.nvm/versions/node/v24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### 14.9 新开 WSL 终端后 `node` 找不到

**问题现象**：新开 WSL 终端后 `bench start` 报 `node: not found`

**原因**：nvm 的配置在 `.bashrc` 中，新终端需要手动加载

**解决**：在 `start.sh` 中添加 nvm 加载：
```bash
export NVM_DIR=/home/yang/.nvm
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

## 15. 开发问题排查

### 15.1 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8000

# 换端口启动
bench start --port 8001
```

### 15.2 数据库连接失败

```bash
# 检查 MariaDB 是否在运行
sudo service mariadb status

# 启动 MariaDB
sudo service mariadb start

# 手动连接测试
sudo mysql -u root -p
```

### 15.3 缓存问题

```bash
# 开发时发现修改没生效，先清缓存
bench --site dev.localhost clear-cache

# 如果还不行，重建前端
bench build
```

### 15.4 Python 调试

```python
# 在代码中添加
import pdb; pdb.set_trace()

# 或者用 frappe 日志
frappe.log_error("错误信息", "自定义模块")

# 显示消息
frappe.msgprint("这是一条提示消息")

# 抛出错误
frappe.throw("必填字段不能为空")
```

### 15.5 JavaScript 调试

```javascript
// 在浏览器控制台
console.log("调试数据:", data);
frappe.msgprint("调试信息");

// frappe 表单事件
frappe.ui.form.on("Sales Invoice", {
    validate: function(frm) {
        console.log("表单数据:", frm.doc);
    }
});
```

---

## 16. 零售参数设置

### 16.1 访问方式

| 方式 | 操作 |
|------|------|
| **直接访问** | 浏览器地址栏输入 `/app/retail-settings` |
| **Workspace 入口** | 设置（Setup）页面 → 「零售参数设置」快捷方式 |
| **JS 调用** | F12 控制台输入 `solua_home.retail_settings.open()` |

### 16.2 参数说明

参考智百威零售参数设置，包含以下分组：

**小票设置**
- 标题1/标题2：小票顶部打印的公司名称和副标题
- 页脚1-4：小票底部打印的脚注（如感谢语、网址等）

**打印设置**
- 纸宽：80mm 或 58mm（取决于小票打印机）
- 打印份数：同一小票打印几张
- 抹零方式：不处理/四舍五入到角/到元/舍去分/舍去角
- 打印公司名称/日期时间/找零金额：控制小票上显示哪些信息

**小票显示元素**
- 控制小票上显示哪些项目：条码、商品名称、原价、折扣、数量、单位、小计、机号

**价格控制**
- 允许前台改价：收银员是否可以在 POS 修改商品价格
- 改价需要审批密码：改价时是否需要管理员密码确认

**其它设置**
- 允许前台盘点：收银员是否可以在 POS 做库存盘点
- 扫码自动加购：扫条码后自动加入购物车（无需点击确认）

### 16.3 Solua Home 首页库存快捷操作

首页地址：`/desk/solua-home`。库存快捷入口使用 ERPNext 原生 `Stock Entry` 新建草稿，不在首页复制库存单页面。点击后由 `frappe.route_options` 同时预填 `purpose` 和 `stock_entry_type`：

| 入口 | Purpose | Stock Entry Type |
|------|---------|------------------|
| 库存入库 | `Material Receipt` | `Material Receipt` |
| 物料出库 | `Material Issue` | `Material Issue` |
| 领用 | `Material Issue` | `领用` |
| 损耗 | `Material Issue` | `损耗` |

“领用”和“损耗”是长期分类，不用备注文字代替。安装/迁移钩子会幂等复用已有等价 Material Issue 类型；缺少时才创建最少的两个 `Stock Entry Type`。首页接口把实际类型名返回给按钮，因此已有 `Consumption`/`Wastage` 等价类型也能正常使用。首页按钮只打开草稿，员工必须按现有权限填写、保存和提交，测试入口不得提交真实库存单。

---

## 💡 最后提醒

> 📅 最后更新: 2026-09-15 | 第17章 xPos 桌面 POS 系统；第18章补充最终运行规则、商品建档、09-02 UAT 与 Hub/Till 首包；第19章补充 09-08—09-09 当前角色包和本地扫码修复；补充 09-15 生产物料主数据操作

| 编号 | 原则 |
|------|------|
| ✅ | **所有修改都在自定义 App 中**，不碰 erpnext 和 frappe 源码 |
| ✅ | **代码放 WSL2 内部文件系统**（`~/frappe-bench/`），不放 `/mnt/c/` |
| ✅ | **善用 Git 进行版本管理**，本地开发 → git push → 服务器 pull |
| ✅ | **翻译建议写在代码里**（`setup.py`），自动执行，不遗漏 |
| ✅ | **善用 VS Code Remote-WSL**，Windows 界面编辑，Linux 环境运行 |
| ✅ | **永远用普通用户操作 bench**，只有 `sudo apt install` 时才提权 |
| ✅ | **版本不匹配时先检查 Python 和 Node 版本**（v16 最新版要求 Py3.14 + Node24） |

---

## 17. xPos — 桌面 POS 收银系统（Electron）

> xPos 是基于 Frappe/ERPNext 的离线 POS 应用，支持热敏打印机、钱箱、扫码枪直连。
> 项目地址: https://github.com/kodlyft/xpos

### 17.1 安装 xPos（本地 WSL 开发环境）

```bash
# 1. 克隆 xPos 到 bench apps
cd ~/frappe-bench
bench get-app https://github.com/kodlyft/xpos.git

# 2. 安装到 dev.localhost 站点
bench --site dev.localhost install-app xpos

# 3. 安装前端依赖
cd apps/xpos/frontend
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh"
yarn install

# 4. 构建前端
yarn build

# 5. 安装 xPos 自定义字段和 POS Roles
bench --site dev.localhost console
```

在 console 中执行:
```python
import frappe
from xpos.install import seed_pos_permissions, seed_default_roles
seed_pos_permissions()
seed_default_roles()
frappe.db.commit()
print('xPos roles and permissions installed')
```

### 17.2 配置 POS Profile

xPos 需要 POS Profile 上有自定义字段（由 `xpos/x_pos/custom/pos_profile.json` 定义）。

**安装自定义字段:**
```python
# 在 bench console 中执行
import json
with open('/home/yang/frappe-bench/apps/xpos/xpos/x_pos/custom/pos_profile.json') as f:
    data = json.load(f)
for cf in data.get('custom_fields', []):
    dt = cf.get('dt', 'POS Profile')
    fieldname = cf.get('fieldname')
    if not fieldname or frappe.db.exists('Custom Field', {'dt': dt, 'fieldname': fieldname}):
        continue
    doc = frappe.get_doc({
        'doctype': 'Custom Field', 'dt': dt, 'fieldname': fieldname,
        'fieldtype': cf.get('fieldtype', 'Data'), 'label': cf.get('label', ''),
        'insert_after': cf.get('insert_after', ''), 'default': cf.get('default'),
        'module': cf.get('module', 'X POS'),
    })
    doc.insert(ignore_permissions=True)
frappe.db.commit()
```

**关键 POS Profile 设置:**
| 字段 | 说明 | 推荐值 |
|------|------|--------|
| `use_customer_credit` | 启用储值/客户信用 | ✅ 开启 |
| `tax_inclusive` | 含税模式 | ✅ 开启（莫桑比克） |
| `allow_return` | 允许退货 | ✅ 开启 |
| `max_discount_percentage_allowed` | 最大折扣比例上限（可在设置中调整） | 按门店政策设置；不得使成交价低于成本 |
| `use_offline_mode` | 离线模式 | ✅ 开启 |
| `allow_negative_stock`（Stock Settings） | 允许库存为负；库存为 0 仍可过账销售 | ✅ 开启（当前生产配置） |
| `block_sale_beyond_available_qty`（POS Profile） | 禁止销售超过可用库存 | ❌ 关闭（与上项联动） |

#### 库存为 0 销售：两个设置的位置与联动

这两个设置必须按“业务状态”保持一致，但由于字段含义相反，数值是反向的：

| 业务状态 | ERPNext 后台：Stock Settings | ERPNext 后台：POS Profile |
|----------|------------------------------|----------------------------|
| 允许库存为 0/不足时销售并过账 | `allow_negative_stock = 1` | `block_sale_beyond_available_qty = 0` |
| 库存不足时禁止销售 | `allow_negative_stock = 0` | `block_sale_beyond_available_qty = 1` |

**后台位置：**

1. 全局设置：ERPNext → **设置（Settings）** → **库存设置（Stock Settings）** → **允许负库存（Allow Negative Stock）**。
2. POS设置：ERPNext → **销售（Selling）** → **POS Profile** → 打开 `收银方式1 - SH` → **禁止销售超过可用库存（Block Sale Beyond Available Qty）**。

当前生产环境已开启第一种业务状态：允许负库存为 1、POS Profile 禁止超卖为 0。系统已配置双向联动：修改 Stock Settings 会同步所有 POS Profile；修改任一 POS Profile 的“禁止超卖”会反向同步 Stock Settings 和其他 POS Profile。xPos 桌面端不单独维护这两个值，而是在同步 POS Profile 时获取最新配置。

> 注意：`允许负库存`是 ERPNext 的全局设置，会影响 POS、采购、交货和其他库存单据；开启后库存可能显示为负数。`隐藏无库存商品（hide_unavailable_items）`只控制商品是否在POS列表显示，不控制能否销售。`update_stock`应保持开启，否则销售过账不会扣减库存。

**当前折扣规则（最终确认）**：收银员可以输入折扣，但任何大于 0% 的行折扣或整单折扣都必须输入管理员/经理审批密码；上限由零售设置自定义，系统同时拦截折后价低于成本的情况。离线时不能联系服务器，改由本机经理账号审批；没有可用经理账号时禁止折扣，不自动放行。

### 17.3 中文/葡语翻译

xPos 翻译文件位于 `apps/xpos/xpos/translations/`。

**补全翻译（关键 POS 术语）:**
```bash
# 翻译文件位置
ls apps/xpos/xpos/translations/
# zh.csv - 中文（717 条，已补全）
# pt.csv - 葡萄牙语/莫桑比克（717 条，已补全）
# pt-BR.csv - 巴西葡语
```

**切换语言:**
- 设置 → 用户 → 语言 → 选择 `中文 (zh)` 或 `Português (pt)`
- 或在 xPos 界面右上角切换

**翻译验收规则（当前项目）**：菜单栏 `File / Finance / View / Help` 及其子菜单、Report/Purchase/Finance 页面、直接采购收货字段、同步状态条和弹窗中的动态文字都必须使用 `__()` 翻译键；禁止在新增界面直接写死英文。当前业务不使用 `APPLY TAX WITHHOLDING`，xPos 不显示该入口或字段。中文先作为主语言，葡语翻译后续补齐；英文只允许作为缺失翻译的临时回退，不能视为完成。

### 17.4 访问 xPos

| 方式 | URL | 说明 |
|------|-----|------|
| **Web 版** | `http://dev.localhost:8000/xpos` | 浏览器访问（无离线） |
| **Electron 版** | `C:\xpos\X POS.exe` | 桌面应用（离线 + 打印机） |
| **生产 Web** | `https://erp.solua.one/xpos` | 需安装 xPos 到生产服务器 |

### 17.5 xPos 功能一览

| 功能 | 入口 | 说明 |
|------|------|------|
| **收银** | 侧边栏 Cashier | 加购 → 结账 → 打印小票 |
| **标签打印** | 侧边栏 Barcode Printer | 搜索物料 → 选条码/尺寸 → 打印 |
| **交班** | POS 页面 → 关闭班次 | 自动汇总当日销售/收款 |
| **退货** | POS 页面 → 退货模式 | 扫原发票条码退货 |
| **折扣** | 购物车 → 折扣按钮 | 行折扣 + 整单折扣（超限需审批） |
| **忠诚度** | 支付对话框 → 忠诚度 | 积分兑换 |
| **客户信用** | 支付对话框 → 客户信用 | 储值支付 |
| **采购** | 侧边栏 Purchase Order | 创建/接收采购订单 |
| **直接采购收货** | 侧边栏 Stock Receiving | 不依赖采购订单直接建立 Purchase Receipt；仅管理员/具备采购权限的账号可见，Cashier 不显示 |
| **库存** | 侧边栏 Stock Receiving | 按采购订单或直接采购收货入库 |
| **费用** | 侧边栏 Expense | POS 费用录入 |
| **银行存款** | 侧边栏 Bank Drop | 现金存银行 |
| **设置** | 侧边栏 Settings | POS Profile / 打印格式 / 离线模式 |
| **权限** | 侧边栏 Role Permissions | Cashier / Manager 角色配置 |

**收银员功能边界**：Cashier 只显示销售/收银相关入口。退货可以由 Cashier 发起，但最终确认必须输入管理员/经理密码；Report、Purchase、Finance、直接采购收货等入口只对管理员或明确授权的角色显示。POS Profile 可由多个收银员共用，不要求“一人一个 Profile”。

### 17.6 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+G` | 重复上一张发票 |
| `Ctrl+K` | 搜索物料 |
| `Ctrl+Enter` | 结账 |
| `F2` | 新建客户 |
| `F3` / `#` | 扫码模式 |
| `F4` | 切换客户 |
| `F5` | 刷新 |
| `F8` | 费用录入 |
| `Esc` | 关闭对话框 |

### 17.7 Electron 桌面版构建

**从 WSL 交叉编译 Windows 版:**
```bash
cd ~/frappe-bench/apps/xpos/frontend

# 1. 安装依赖
yarn install

# 2. 构建 Electron 前端
yarn build:electron

# 3. 打包 Windows 版（未打包版，无需 Wine）
node scripts/build-win.mjs

# 4. 输出位置
ls release/win-unpacked/X\ POS.exe
# 复制到 Windows
```

**从 Windows 直接运行:**
```
# 将 release/win-unpacked/ 复制到 C:\xpos\
# 双击 X POS.exe 启动
# 首次启动配置:
#   Server URL: https://erp.solua.one
#   用户名/密码: ERPNext 登录凭证
```

### 17.8 Electron 版功能优势

| 功能 | Web 版 | Electron 版 |
|------|--------|-------------|
| 热敏打印机直连 | ❌ 需 QZ Tray | ✅ 直连 |
| 钱箱控制 | ❌ 依赖打印机 | ✅ 通过打印机指令 |
| 离线收银 | ⚠️ PWA 缓存 | ✅ SQLite 本地数据库 |
| 自动同步 | ✅ | ✅ 恢复网络自动推 |
| 扫码枪 | ✅ 键盘模式 | ✅ 同理 |
| 摄像头扫码 | ✅ | ✅ |
| 多终端同步 | ❌ | ✅ Hub & Spoke 架构 |

### 17.9 xPos 与 solua_home 对比

| 功能 | solua_home | xPos |
|------|-----------|------|
| 收银/结账 | ✅ | ✅ |
| 标签打印 | ✅ | ✅ |
| 交班/日结 | ✅ | ✅ |
| 忠诚度积分 | ✅ | ✅ |
| 储值支付 | ✅ (自定义字段) | ✅ (Customer Credit) |
| 促销/Pricing Rule | ✅ | ✅ |
| 折扣审批 | ✅ | ✅ |
| 改价 | ✅ | ✅ |
| 商品打包 | ✅ | ✅ |
| 采购订单 | ❌ | ✅ |
| 收货 | ❌ | ✅ |
| 银行存款 | ❌ | ✅ |
| 费用管理 | ❌ | ✅ |
| 离线支持 | ❌ | ✅ |
| 热敏打印机直连 | ❌ | ✅ (Electron) |

### 17.10 常见问题

**Q: xPos 页面报 "No profiles found"?**
A: 确保用户已登录，且 POS Profile 的 `applicable_for_users` 包含当前用户。

**Q: POS Profile 加载报 "单据类型 None 未找到"?**
A: xPos 自定义 Table 字段缺少子表 DocType。需创建缺失的 DocType（如 `POS Profile Tax`）。

**Q: Electron 版连接不上服务器?**
A: 检查 Server URL 是否正确、网络是否通、ERPNext 是否允许 API 访问。

**Q: 打印机不出纸?**
A: Electron 版通过系统打印 API 直连。检查：① 打印机已连接并开机 ② Windows 设置为默认打印机 ③ 纸张尺寸匹配。

---

> 📝 **备忘：当前环境信息**
>
> - 服务器: Ubuntu 24.04（通过 bench 直接安装，supervisor + nginx）
> - 本地开发: WSL2 (Windows 11 + Ubuntu 24.04)
> - ERPNext 版本: v16（`version-16` 分支）
> - Python: 3.14.x（通过 deadsnakes PPA 安装）
> - Node.js: 24.x（通过 nvm 管理，服务器 system node 仍为 v20）
> - bench: 5.31.0（通过 pipx 安装）
> - 自定义 App 名: `solua_home`
> - POS 系统: xPos v1.0.9 (Electron)
> - 开发站点: `dev.localhost:8000`
> - 生产站点: `erp.solua.one`
> - SSH: `ssh qq`（用户 ubuntu，sudo 免密）
> - GitHub: `https://github.com/a83986475/solua-erp.git`

### 生产命令执行用户规则（必须遵守）

`ubuntu` 仅用于只读检查和系统级命令（如 `sudo supervisorctl`）。所有 `bench`、Python、pip、yarn/npm、Vite、Electron 构建，以及写入 `/home/frappe/frappe-bench` 的操作，必须通过 `sudo -u frappe -i` 执行；禁止直接用 `ubuntu` 构建或写入应用目录。否则可能产生 `node_modules/.vite-temp` 等文件归属错误，后续由 `frappe` 执行会报 `EACCES`。2026-09-08 已记录一次该问题：xPos web build 用 `ubuntu` 失败，改用 `frappe` 成功。

---

## 18. xPos 最终架构、同步排错与商品建档记录

> 本章记录 2026-08-24 至 2026-09-04 的实际决策、故障根因和生产数据结果。与第 17 章的安装说明配合使用；若旧说明与本章冲突，以本章为准。18.8 为 09-02 生产 UAT 轮次与退货修复，18.9 为 09-04 首次 Hub/Till 角色安装包；09-08—09-09 的增量修复见第 19 章。

### 18.1 账号、API 与 POS Profile 的边界

必须把三种身份分开管理：

| 身份 | 所在位置 | 作用 | 是否用于同步 API |
|------|---------|------|------------------|
| **ERPNext `Administrator`** | 云端 ERPNext | 服务器超级管理员、配置和审批 | 不建议放在收银终端 |
| **ERPNext 收银员** | 云端 ERPNext | 真实业务操作人，销售/退货/交班审计归属此人 | 不使用其个人 API Key |
| **xPos 本地 `admin`** | 每台 Electron 电脑的本地 SQLite | 管理该终端的本地设置/故障处理 | 不是云端 `Administrator` |
| **xPos 同步服务账号** | 云端 ERPNext | 作为同步请求的“运输账号”，只授予同步所需权限 | 使用专用 API Key/Secret |

- `Administrator`、本地 `admin`、`posmanager`（若存在）不是同一个账号，不能通过名字判断身份。
- 收银员登录后，服务端应校验该收银员是否属于当前 POS Profile，再把收银员身份写入销售、退货和交班记录；服务账号只负责传输请求。
- 一个 POS Profile 可以被多个收银员共用。通过 `applicable_for_users` 绑定允许使用的收银员，不需要为每人复制一个 Profile。
- 旧的单机直连模式：安装 xPos → 填生产 Server URL → 在受保护配置中写入专用同步服务账号的 API Key/Secret → 让收银员用自己的 ERPNext 账号登录 → 检查其可用 POS Profile。API Key/Secret 不写入手册、截图或聊天记录。
- 当前新门店推荐 Hub/Till 模式：只有 Hub 安装时读取同步凭据并连接云端；Till 只填写 Hub 的局域网 IPv4（端口 6789），不接收 ERPNext API Key/Secret。收银员仍用自己的 ERPNext 账号登录，业务归属与权限校验不变。凭据重置后只更新 Hub 的受保护配置，不逐台写入收银机。

### 18.2 收银员权限与审批规则

当前推荐的 Cashier 是最小权限角色组合（Sales User、Accounts User，按需要加 POS Cashier 开/关班权限）。收银员界面只显示销售/收银相关功能；Report、Purchase、Finance、直接采购收货对管理员或明确授权角色开放。

业务规则：

1. Cashier 可以发起退货，但最终确认必须输入管理员/经理密码。
2. 任何大于 0% 的行折扣或整单折扣都必须输入管理员/经理审批密码；审批阈值在设置中可调整，默认规则为 0%。
3. 折扣后的实际售价不得低于成本价；这是硬性限制，管理员也不能绕过。
4. 离线时无法访问服务器，折扣改由本机经理账号审批；没有本机经理账号时禁止折扣。
5. 直接采购收货不显示给 Cashier；管理员/采购授权账号可不依赖采购订单直接创建 Purchase Receipt。

### 18.3 同步间隔、卡住状态与 HTTP 错误

- 自动同步周期是 **5 分钟**；打开页面、网络恢复或手动点击同步可能立即启动一轮，所以看到短暂的“同步中”不等于实时不停同步。
- 单个请求必须有超时保护；异常记录保留在本地队列，标记为 `failed` 或 `dead_letter`，不得删除业务数据，也不能因为一条采购订单关闭整条同步队列。
- 排查时先看本地队列表和 `sync_id_map`，再对照服务器单据名称。同步状态英文只是翻译键缺失，不代表同步逻辑本身失败。

常见错误含义：

| 错误 | 实际含义 | 正确处理 |
|------|----------|----------|
| `HTTP 417` | 服务端业务校验未满足，常见于字段、状态或身份不符合要求 | 查看服务器响应正文和日志，修正业务数据后重试 |
| `HTTP 500` | 服务端代码/异常或进程未加载模块 | 先看 gunicorn/bench 日志，修复后重试 |
| `HTTP 403` | API 用户无角色权限，或方法没有 `@frappe.whitelist()` | 给同步服务账号授予最小读取/写入权限，并确认方法白名单 |
| `HTTP 404` | 本地 ID 被当作服务器单据名称，或删除检查端点不存在 | 用本地 ID→服务器 `name` 映射；不删除本地记录 |

**交班特别注意**：错误“POS 开班班次 3 未找到”不是因为没有现金。Electron 本地的数字 `3` 只是 SQLite 自增 ID，服务器需要类似 `POS-OPE-...` 的真实单据名称。开班成功后必须保存 `erp_id` 并写入 `sync_id_map`；查询汇总、关班和上传发票都使用服务器名称。

**安全恢复原则**：保留原采购订单/销售记录，将卡住记录隔离为“同步失败/需要处理”，提供人工重试；不要删除订单、不要关闭整个采购同步队列。同步服务账号必须能读取 Companies、Warehouses、Accounts、Cost Centers、Price Lists、Items、Item Groups、POS Profiles 等主数据，否则会连续出现 403。

### 18.4 语言、状态条和窗口显示

当前验收范围不只是 POS 主页面，还包括：

- 顶部菜单 `File`、`Finance`、`View`、`Help` 和全部子菜单；
- Report、Purchase、Finance 页面，以及直接采购收货页面中的字段、按钮、占位文字、表格说明；
- 同步状态条（同步中、待同步、同步失败、已同步、离线、上次同步时间）；
- 关闭班次、快捷键、折扣审批和退货确认弹窗。

新增 UI 必须把动态文字包在 `__()` 中并同时加入中文翻译键；中文是当前主语言，葡语后续补充。`APPLY TAX WITHHOLDING` 不是本项目业务功能，xPos 不显示它，不能用 CSS 隐藏来代替移除入口。

若改动后仍看到旧英文或顶部账户图标缺失，优先检查：Electron 是否使用了最新构建、是否清除了旧 asar/缓存、组件是否只注册一次；不要先改服务器数据。

### 18.5 2026-08-31 窗帘商品主数据导入结果

来源：`SOLUA HOME窗帘 建档.xlsx`。导入前已核对 12 个物料编码和条码均无重复；所有记录均为成品库存物料，规格为 `140 × 260 cm`，销售单位为“条”，物料组为“窗帘成品”，中文先建档。

| 商品 | 款号（内部 SPU） | 物料编码 | 成本/MZN | 批发/MZN | 零售/MZN | 图片 |
|------|------------------|----------|---------:|---------:|---------:|------|
| 素雅 1 | C-MB | SH151015 | 192.10 | 260 | 399 | ✅ |
| 素雅 2 | C-KJ | SH151039 | 167.24 | 260 | 399 | ✅ |
| 幻纱 | C-GS | SH151091 | 180.80 | 260 | 399 | ✅ |
| 极夜 1（100%遮光） | C-TC | SH151077 | 266.36 | 350 | 550 | ✅ |
| 极夜 2（100%遮光） | C-CM | SH151084 | 259.90 | 350 | 550 | ✅ |
| 静谧绒（85%遮光） | C-RB | SH151053 | 286.27 | 390 | 550 | ✅ |
| 莫兰迪（95%遮光） | B-SW | SH151114 | 293.80 | 390 | 650 | ✅ |
| 暗影（95%遮光） | B-DY | SH151046 | 327.70 | 430 | 699 | ✅ |
| 光感绒（80%遮光） | B-DR | SH151060 | 334.16 | 430 | 699 | 暂无 |
| 鎏金（95%遮光） | B-ST | SH151107 | 327.70 | 430 | 699 | ✅ |
| 高奢 1（95%遮光） | B-XP | SH151121 | 366.12 | 490 | 980 | ✅ |
| 高奢 2（95%遮光） | A-HS | SH151022 | 474.60 | 590 | 1,300 | ✅ |

价格写入方式：

- 成本/采购单价 → `Standard Buying`（MZN）；
- 批发价 → `Wholesale Selling`（MZN）；
- 零售价 → `Standard Selling`（MZN）；
- 价格区间按用户要求取高值：高奢 1 = 980、高奢 2 = 1,300；
- 成本金额按货币精度四舍五入到 2 位；
- 款号只写内部 SPU 编码，不放入 POS 商品名称或客户展示字段；
- 本次只建立主数据和价格，未导入期初库存；库存需通过采购收货、直接采购收货或库存入库建立。

**ERPNext 成本注意**：`Standard Buying` 是采购价格表；折扣/售价低于成本的运行时检查优先读取仓库 `Bin` 的加权成本，其次读取 `Item.valuation_rate`。首次真实收货后应核对 valuation rate，不能只因为有采购价格表就认为库存成本已经建立。

### 18.5.1 2026-09-15 生产基础数据与 Cor 颜色属性操作记录

本节为生产 `erp.solua.one` 的定向主数据操作记录；与早期颜色池、窗帘导入记录相冲突时，以本节的当前回读结果为准。执行身份为服务器 `frappe`，只操作明确列出的主数据，不创建 Item、Item Variant、库存或销售/采购交易。

**执行前核对：**

- Item Group `窗帘`、`窗帘杆`、`地板革` 不存在；父组 `All Item Groups` 存在。
- UOM `条` 已存在，但 `must_be_whole_number=0`；UOM `根`、`卷` 不存在。
- `Item Attribute: Cor` 已存在，原有 16 个颜色值及缩写均存在且无重复。

**实际写入：**

| 对象 | 操作 | 实际结果 |
|------|------|----------|
| Item Group | 缺失时创建，父组为 `All Item Groups`，`is_group=0` | 创建 `窗帘`、`窗帘杆`、`地板革` |
| UOM | 缺失时创建，启用且只允许整数 | 创建 `根`、`卷` |
| UOM `条` | 将 `must_be_whole_number` 从 `0` 改为 `1` | 已改为只允许整数 |
| Item Attribute `Cor` | 缺失时追加，不重复覆盖 | 为 14 个非黑白基础色各追加 `{基础颜色} Escuro`、`{基础颜色} Claro`，共 28 个 |

颜色属性的新增值采用现有葡萄牙语命名和缩写规则，例如 `Azul Escuro / AZ-E`、`Azul Claro / AZ-C`；`Branco`、`Preto` 不增加派生值。写入后回读结果：总值 44、颜色名称唯一、缩写唯一、黑白派生值为 0。

**物料组确认（2026-09-19）**：`窗帘成品` 是历史导入时使用的 Item Group，现已删除。成品窗帘统一使用 `窗帘`，不再使用 `窗帘成品`；本次窗帘导入草稿按 `窗帘` 填写。

**验证与边界：**

- 验证路径：`ssh qq` → `sudo -u frappe` → `/home/frappe/frappe-bench` → `bench --site erp.solua.one console`。
- 定向脚本采用幂等判断；异常时回滚，成功后提交并立即回读。
- 本次没有创建具体颜色变体；后续创建窗帘杆/窗帘模板及变体时，使用 `Cor` 的具体颜色值，并为每个变体配置独立货号和条码。
- 没有运行广泛 `bench migrate`、`after_install` 或颜色池重建逻辑；没有改动价格、库存、客户或历史交易。

### 18.6 图片导入的重复附件坑

本次导入曾发现每张图片出现两条 `File` 数据库关联记录：一条是普通附件，一条是 `Item.image` 字段附件；两条记录指向同一个实际文件，并非图片内容重复。原因是先用普通附件方式上传，再设置 Attach Image 字段触发了 ERPNext 的自动关联。

处理结果：删除 11 条无字段的多余关联记录，保留 11 条 `attached_to_field=image` 记录；商品图片仍全部可用。今后批量导入图片必须直接以 `image` 字段关联，并按 `attached_to_field`/`file_url` 做幂等检查，不能先普通上传再补写 `Item.image`。

### 18.7 新增/部署后的最小验收清单

- [ ] 用真实 Cashier 登录，确认只能看到 Sales/Cashier，不能看到 Report/Purchase/Finance
- [ ] 确认 Cashier 能发起退货，但提交前出现经理密码确认
- [ ] 输入任意大于 0% 折扣，确认出现审批；输入使售价低于成本的折扣，确认硬拦截
- [ ] 新建/共用 POS Profile，确认每个允许的收银员都能看到且未授权用户看不到
- [ ] 断网后检查本地销售记录仍保留；恢复网络后同步每 5 分钟运行，不因单条失败永久显示“同步中”
- [ ] 复核开班→销售→关班使用服务器 `POS Opening Shift` 名称，而不是本地数字 ID
- [ ] 检查主菜单、Report/Purchase/Finance、直接采购收货和状态条没有新增硬编码英文
- [ ] 商品扫码验证 12 个条码；核对“条”单位、三套价格和 11 张图片；补图后再更新 `SH151060`

### 18.8 2026-09-02 生产环境全链路 UAT（R1–R4）与 POS 退货修复

**目标**：在生产库按真实链路验证「开班 → 销售/折扣审批 → 退货退款 → 班次汇总 → 关班」，并固定桌面端上传走同步服务账号的路径。测试身份：`pos_manager@solua.one`（开班/业务归属）+ `xpos_sync@solua.one`（同步运输账号，上传销售），POS Profile `收银方式1 - SH`、Company `Solua Home, Lda`、Warehouse `Finished Goods - SH`、`Cash` 支付。验收数字以 R4 脚本 `.codex-xpos-full-uat.py`（md5 `273ea6a1…`，与服务器 `/tmp` 副本一致）为准：

| 检查点 | 期望值 |
|--------|--------|
| 起始状态 | `pos_manager` 无未关开班 |
| 物料收货 | 2 × 100 入库单已提交 |
| 开班 | 现金 1000 |
| 现金销售 | 1 × 120 → 含税 **139.2** |
| 折扣审批销售 | 1 × 120、10% 折扣、`custom_discount_approved` → **125.28** |
| 退货退款 | 对现金销售退货 → **−139.2**（`custom_return_approved` + 审批人 `pos_manager`） |
| 班次汇总 | 3 张发票、1 张退货、合计 **125.28** |
| 关班 | 3 张发票、1 张退货、总额 **125.28**（期望 1125.28 = 1000 + 139.2 + 125.28 − 139.2） |

**轮次与服务器证据**（按 09-02 22:00–22:13 本地时间在库里的提交记录还原）：

- **R1/早期轮次**：多轮尝试后留下取消/未删单，编写幂等清理脚本 `.codex-cleanup-uat.py`、`.codex-cleanup-uat-r2.py`、`.codex-cleanup-uat-r3.py`、`.codex-repair-uat-cleanup.py` 处理（取消 → 删依赖序），并用 `.codex-final-uat-state.py` 核查残留。
- **R2（22:09，发票 `ACC-SINV-2026-00049/50/51`）**：现金 139.2 + 折扣 125.28 + 退货 −139.2 均成功提交并关班（`POS-CS-26-0000002`，22:09:37）。R2 清理未完全跑完，**3 张发票至今仍为已取消（docstatus=2）留在库里**，开班 `POS-OS-26-0000002` 也已取消——见下方遗留待办。
- **R3（22:10）**：完整跑通；后续清理删除 `POS-OS-26-0000003`、`POS-CS-26-0000003`、`ACC-SINV-2026-00052/53/54` 及测试物料/客户，**R3 前缀零残留**。
- **R4（22:12:35，最终验收轮）**：同一脚本再跑完整链路，**R4 前缀（`UAT-20260902-R4`）在库中零残留**（发票/物料/客户/开班/关班均无），Error Log 窗口（09-02 20:00 → 09-03 08:00）除发票提交记录外无异常堆栈，证明脚本断言全部通过并完成自清理。

**POS 退货修复（09-02 22:09 部署）**：

- 现象：POS 退货支付行会被 ERPNext 在 validate 时按 POS Profile 重建，xPos 已提供的负数退款可能被改成正数，被退货校验拒绝（HTTP 417/500 类业务失败）。
- 修复：`solua_home` 用 `extend_doctype_class` 完全重写 `Sales Invoice`（`hooks.py` 第 67–68 行），在 `CustomSalesInvoice.set_missing_values()` 与 `verify_payment_amount_is_negative()` 中对 `is_pos and is_return` 的每个支付行执行 `amount = -abs(amount)`，先于标准校验归一化。
- 服务器文件 `/home/frappe/frappe-bench/apps/solua_home/solua_home/override/sales_invoice.py`（md5 `f2cb7e53…`，与本地 `.codex-custom-sales-invoice.py` 一致）已核对存在；`validate()` 保留父类全部校验并追加金额超 100,000 需审批人等自定义规则。
- 修复前（22:00–22:08）多次尝试均止步于退货提交；**R2 首次完整三单（22:09:36 提交 `ACC-SINV-2026-00051` 退货 −139.2）即验证修复生效**，R3/R4 连续通过。

**遗留待办**：R2 的 3 张已取消发票（`ACC-SINV-2026-00049/50/51`，docstatus=2）+ 已取消开班 `POS-OS-26-0000002` + 对应关班 `POS-CS-26-0000002` 仍在库，可在下次维护窗口运行 `.codex-cleanup-uat-r2.py` 幂等清理；`.codex-final-uat-state.py` 可用于复查零残留。

### 18.9 2026-09-04 XPos Hub / Till 角色安装包

**角色划分**（一套局域网门店双角色）：

- **Hub（主机角色）**：门店局域网内一台主机。内置 MariaDB 11.4.13（端口 3307）与 Hub 服务（端口 6789），连接云端 ERPNext 负责同步；安装时自动选用可用局域网 IPv4。
- **Till（收银机角色）**：店内各收银终端。只填 Hub 的 IPv4 地址（端口固定 6789），自动生成本机 Till ID，用本机 MariaDB 做缓存与离线队列；Till 包不含 ERPNext API Key。

**安装前提与流程**（详见 `release/_role-templates/README-Hub.txt`、`README-Till.txt`）：

1. 单机模式仍可用 09-02 的 `release/XPos-Windows-Setup.zip`；**09-04 起的新门店用双包**：`release/XPos-Hub-Setup.zip` + `XPos-Till-Setup.zip`（各约 210 MB，09-04 00:39 构建，内含 `SHA256SUMS.txt`）。
2. **Hub 先装**：解压 → 把外置 `XPOS-HUB-KEY.json`（U 盘根目录）插入 → 右键管理员运行 `Install-XPos-Hub.ps1`。安装器固定 MariaDB 11.4.13、3307 端口、6789 Hub 端口；发现 `C:\xpos` 先改名为 `C:\xpos.backup-时间戳` 不直接删除；装完桌面出现 “X POS Hub”，`C:\xpos\Hub-Address.txt` 记录当前 Hub 地址。
3. **Till 后装**：右键管理员运行 `Install-XPos-Till.ps1`，只填 Hub 主机 IPv4；脚本先探测 `http://Hub-IP:6789/api/health`，成功才写配置并安装。
4. **Hub U 盘密钥文件生成**：在原 xPos Windows 主机上用同一 Windows 用户运行 `release/_role-templates/Build-XPos-RolePackages.ps1`，输出 `XPOS-HUB-KEY.json`；脚本会从本机 MariaDB/Electron 受保护配置读取同步凭据导出为**可移植明文（format 1）**或**同机继承密文（format 2）**。format 2 只能在生成它的原主机与原 Windows 用户下安装 Hub。密钥文件**不得放入安装 ZIP、不得写入手册/截图/聊天**；安装完成后即可拔 U 盘。
5. 每台新收银机最终仍按 18.1 用收银员本人 ERPNext 账号登录、服务账号负责同步；Hub/Till 包不包含测试订单或测试收银员账户。

**验收要点**：Hub 与 Till 必须处于同一可互通局域网（Windows 网络配置建议“专用”）；改动 Hub IP 后需重跑 Till 安装脚本更新本机 Hub 地址；两个 ZIP 均带逐文件 `SHA256SUMS.txt`，发布前可用 PowerShell `Get-FileHash` 核对。

---

## 19. xPos 角色包归档与本地扫码修复（2026-09-08—09-09）

> 本章是第 18 章之后的增量记录。它描述当前工作区中 09-09 重新生成的 Hub/Till 安装包，以及已经在本地 xPos 验证通过的离线条码修复。不要把旧的 09-04 记录、当前 ZIP 和外置凭据文件混为一谈。

### 19.1 当前 Hub/Till 安装包

当前工作区产物（构建时间均为 2026-09-09 23:19 左右）如下：

| 角色 | 文件 | SHA256 | 校验结果 |
|------|------|--------|----------|
| Hub | `release/XPos-Hub-Setup.zip` | `B3620AA9F53177F60808CF997143662538AA107693E7D0DA5E62B13DC58EA6A6` | 78 个文件，清单通过 |
| Till | `release/XPos-Till-Setup.zip` | `CF23B7753276549C33A8C36BABB18A1522560D13911DB3510BD739D905EBB545` | 78 个文件，清单通过 |

- 两个 ZIP 都不包含 ERPNext API Key/Secret；包内 `app.asar` 当前 SHA256 为 `B68C4BA263288E438A6B5D7E7446CCC7543FED17E48F6334F3303D1CDF76F169`。
- Hub 凭据文件仍是工作区根目录的 `XPOS-HUB-KEY.json`，只作为安装时的外置文件放在 U 盘根目录；该文件含敏感凭据，不得提交 Git、放入 ZIP、截图、手册或聊天记录，安装完成后拔出 U 盘并妥善销毁/保管副本。
- Hub 安装后以 `C:\xpos\Hub-Address.txt` 提供局域网地址；Till 安装脚本先访问 `http://Hub-IP:6789/api/health`，通过后才写入配置。Hub IP 变化时必须重新运行 Till 安装脚本。
- 新门店只采用“Hub 先装、Till 后装”的双角色流程；单机直连包仅用于兼容旧测试环境。任何新 Till 都不应保存云端同步密钥。

### 19.2 本地离线扫码修复

**现象**：同步完成后，本地 xPos 扫描条码 `6901234567893` 仍提示找不到商品；联网状态和同步状态均正常。

**根因**：Electron `searchByBarcode()` 原先调用 `db:get-items`。查询 SQL 可以用 `Item Barcode` 子表过滤，但没有把 `ib.barcode` 返回到结果对象；随后前端再执行 `item.barcode === 扫码值`，把实际已同步的商品误过滤掉。

**修复后的固定流程**：

1. 先用本地 `db:get-item-by-barcode` 做精确条码查询；
2. 再用本地 `db:get-items` 补充价格和库存；
3. 保留直接输入货号的路径；
4. 不增加在线回退，不因扫码临时联网，也不改变同步配置。

验证记录：`yarn typecheck` 通过，`yarn dist:win` 生成新包并部署到 `C:\xpos\resources\app.asar`；旧包备份为 `C:\xpos\resources\app.asar.bak-barcode-20260908-2312`。用户在 2026-09-09 确认本地扫描 `6901234567893` 已正常加购，说明修复生效。

**后续改动约束**：xPos 的离线扫码只能依赖本地镜像；后台同步必须同步 `Item`、`Item Barcode` 和价格数据，且 `Item Barcode` 增量记录必须包含 `modified` 字段，否则新增条码不会进入本地库。不要用在线接口作为扫码兜底来掩盖本地同步缺字段。

### 19.3 当前身份与同步边界（Hub/Till 版）

| 操作 | 实际身份/位置 |
|------|---------------|
| 收银、退货发起、交班审计 | 收银员本人 ERPNext 账号；退货确认/折扣仍按经理密码规则 |
| 离线缓存和队列 | Till 本机 MariaDB/SQLite |
| 云端主数据、销售上传 | Hub 上的专用同步服务账号与其最小权限角色 |
| 门店局域网连接 | Till → Hub `:6789`；Till 不直连 ERPNext 云端 |

同步账号此前为排障曾使用全角色兜底；正式上线前仍应收敛为 `XPos Sync Service`/`XPOS Sync` 专用最小权限角色，并清理不必要的 User Permission 限制。不要把 `Administrator` 或 Cashier 的 API 密钥复制到 Hub/Till 安装介质。

### 19.4 目前仍需处理的事项

- [ ] 对实体热敏打印机做现场打印测试（软件预览已通过）
- [ ] 导入 12 款窗帘的期初库存；当前只有主数据和三套价格
- [ ] 补齐 `SH151060`（光感绒）图片后更新 Item 图片
- [ ] 清理 09-02 R2 留下的 3 张已取消发票及对应开班/关班单据，并用最终状态脚本复核零残留
- [ ] 将同步服务账号从排障用全角色兜底收敛到专用最小权限角色
- [ ] 新门店按当前 ZIP 做 Hub/Till 安装验收：局域网、断网缓存、恢复同步、收银员登录和条码扫码各测一遍

### 19.5 2026-09-18 生产仓库树与库存转移回读

本节是 2026-09-18 对生产站点 `erp.solua.one` 的最新回读，涉及仓库、库位和 POS Profile 的内容以本节为准。生产公司为 **Solua Home, Lda**，地址为 **AV. DO TRABALHO, n.º 231, Cidade de Maputo**，NUIT 为 **402216468**。

当前仓库树如下：

```text
Warehouse - SH（组节点，父 All Warehouses - SH）
├─ Receiving - SH（实际库存节点，默认入库/待验收区）
├─ Dispatch - SH（实际库存节点，待配送区）
├─ Zone A - SH（组节点，窗帘）
│  ├─ A-R01-S01 - SH
│  ├─ A-R01-S02 - SH
│  └─ A-R02-S01 - SH
├─ Zone B - SH（组节点，窗帘杆）
└─ Zone C - SH（组节点，地板革）
```

20 个正库存物料已通过正式 Material Transfer 单 **MAT-STE-2026-00003** 从 `Stores - SH` 转入 `Receiving - SH`，合计 **8040 根**，库存价值 **2,444,640 MZN**；转移前后数量和价值一致。`Receiving - SH` 已设为 Stock Settings 默认仓库，20 个变体的默认仓库也为 `Receiving - SH`。

POS Profile「收银方式1 - SH」已改为 `Stores - SH`；`Finished Goods - SH` 已停用；`Stores - SH` 保留原名，不重命名。旧仓库不删除。组节点不能直接存库存；后续仓库分配必须使用 Material Transfer，不得直接做库存调整。变更前已完成生产备份，本文只记录单据号和回读事实，不记录密钥或完整备份内容。

后续操作：按“区域－货架－层”建立实际库位并张贴库位条码；货架分配完成后，再从 `Receiving - SH` 转移到末级库位。在此之前不使用 POS 进行正式销售。

### 19.6 2026-09-19 窗帘杆物料统一回读

生产 `erp.solua.one` 的窗帘杆范围为 4 个模板和 20 个颜色变体，覆盖 2 米/3 米单杆和双杆。中文 `item_name`、`description` 保留；英文和葡语资料写入以下 Item 自定义字段，字段可供 Print Format、API 和报表直接调用：

| 用途 | 实际 fieldname | Label |
|------|----------------|-------|
| 颜色缩写完整货号（备用） | `custom_color_abbreviation_item_code` | Color Abbreviation Item Code |
| 英文品名 | `custom_item_name_en` | English Item Name |
| 英文描述 | `custom_item_description_en` | English Item Description |
| 葡语品名 | `custom_item_name_pt` | Portuguese Item Name |
| 葡语描述 | `custom_item_description_pt` | Portuguese Item Description |

正式颜色后缀规则已由 ERP `Cor` 属性和用户确认的实物色卡共同核定：`1 = Vermelha / Red Antique`、`2 = Bronze Antigo / Antique Bronze`、`3 = Prateado / Silver`、`4 = Dourado / Gold`、`5 = Preto / Black`。因此 12 个旧缩写变体已使用 Frappe 原生 `frappe.rename_doc` 完成：`PT → 3`、`DR → 4`、`PR → 5`；旧的 12 个完整缩写货号保存在 `custom_color_abbreviation_item_code`。没有使用 SQL 直接改名，也没有发生目标编码冲突。

变更后独立回读：24 个 Item（4 模板、20 变体）、20 条 Standard Selling 售价、4 个模板条码、20 个变体图片、40 个 Bin；20 个变体均保持 `disabled=0` 且 `is_sales_item=1`。库存为 **8040 根**、库存价值 **2,444,640 MZN**，与变更前一致；未修改 Item Price、Bin、Warehouse 或条码。审计导出（含 Item、属性、条码、价格和 Bin 明细）保存在本地 `outputs/curtain_rod_item_normalization_20260919/`，生产变更前完整备份已完成并校验。

### 19.7 2026-09-21 窗帘变体、色卡与库存最终回读

生产现有 **64 个启用、可销售、非模板窗帘 Item**：8 款普通 Item，加 4 款模板下的 56 个颜色变体。四款模板及变体数量为：`SH151046` 10 色、`SH151060` 10 色、`SH151107` 18 色、`SH151114` 18 色。56 个变体的 `custom_swatch_image` 均非空；ERP 色卡文件采用完整变体货号命名。批量导入时直接用文件名（去扩展名）匹配 Item 即可，不再重复建立人工映射表；上传必须直接关联目标 Attach Image 字段，并按 `attached_to_field`、`file_url` 做幂等检查，避免生成重复 File 关联。

`SH151060` 原先被误建为普通 Item。生产现状已修正为模板：旧记录保留为停用的 `SH151060-LEGACY`，库存为 0；新模板 `SH151060` 下有 `04、06、07、09、11、13、14、15、16、20` 十个变体，每个在 `Receiving - SH` 存 70 条，单位估值 `334.157142857 MZN`，合计 **700 条、233,910 MZN**。不要删除 LEGACY 或直接改库存账；后续类似修正应保留历史物料，并使用 ERPNext 原生库存单据转移价值。

全部窗帘库存最终回读为 **28,370 条、7,253,131 MZN**，位于 `Receiving - SH`。其中 8 款不分色商品继续使用普通 Item；只有有明确色卡和固定色号的款式使用模板/变体。

### 19.8 窗帘四级价格表规则与修正结果

窗帘价格必须使用下列固定映射；不能把 Home Store 价写入 `Standard Selling`：

| 业务含义 | ERP Price List |
|---|---|
| 成本价 | `Standard Buying` |
| Home Store 价 | `Wholesale Selling 3` |
| 批发价 | `Wholesale Selling` |
| 建议零售价 | `Standard Selling` |

2026-09-21 已通过 Frappe `Item Price` DocType 修正全部 64 个在售窗帘：新增 64 条 `Wholesale Selling 3`，更新 64 条 `Standard Selling`；原有 `Standard Buying` 与 `Wholesale Selling` 经核对正确，未改动。回读为四张价目表各 64 条、共 256 条，货币均为 MZN、UOM 均为“条”，零异常。建议零售价区间按项目既定规则取最高值。变更前完整备份位于生产站点 `private/backups/20260921_085807-erp_solua_one-*`。

价格批量维护的最小安全流程：精确枚举启用且可销售的非模板 Item；排除停用/LEGACY；备份；使用 DocType API 仅写差异；最后逐物料回读价格表、金额、货币和 UOM。禁止直接 SQL 写入 Item Price。

### 19.9 智能体执行与验收规则

- 独立任务可能把“向主任务汇报”误解为再次调用 `send_message_to_thread`。经验收类任务不要让智能体互相转发；主任务直接读取其最终记录。
- “已发送指令”不等于“已执行”。生产变更只有在备份存在、DocType 写入完成、生产回读通过后才能报告完成。
- 一个智能体只承担一个单一目标。生成色卡、上传附件、转换模板、调整库存、修正价格应分别说明边界，避免旧任务中的“禁止上传”和新任务中的“导入生产”互相冲突。
- 汇报中的记录数必须标明对象。例如“30 条价格记录”表示 10 个变体乘 3 张价目表，不是库存 30 条。

### 19.10 2026-09-21 首页交货单入口、销售单打印格式可编辑化

本次共三处变更，均已在生产 `erp.solua.one` 定向部署并回读；未执行 `migrate`、`after_install` 或 `after_migrate`。部署前完成站点备份（`20260921_225733-erp_solua_one-*`，含数据库/公开/私有文件），变更前的两份文件保存在 `sites/erp.solua.one/private/backups/20260921-sales-invoice-print/`。

#### ① 首页「销售与交货」组

首页快捷操作顶部新增独立分组（原「订单与客户」组内的新建交货单已移入，不再重复）：

| 入口 | 行为 | 权限 |
|---|---|---|
| 新建交货单 | `frappe.new_doc("Delivery Note")` 空白新建 | 交货单 create 权限 |
| 按销售订单开交货单 | 弹窗选销售订单（仅列 `docstatus=1`、`per_delivered<100`、状态未关闭）→ 调 `erpnext.selling.doctype.sales_order.sales_order.make_delivery_note` → 直接打开生成的交货单 | 交货单 create 权限 |
| 销售单格式（标签打印组） | 打开 Print Format「批发销售单（颜色版）」；格式不存在时回退到按 Sales Invoice 过滤的打印格式列表 | Print Format read 权限 |

#### ② 批发销售单（颜色版）改为可编辑格式

问题：该格式把模板存放在 `raw_commands`、`html` 为空且 `raw_printing=1`。Frappe 因此按“原始打印格式”处理：`Print Settings.enable_raw_printing=0` 时不出现在打印格式下拉、打印页隐藏预览/PDF 按钮、编辑界面 HTML 为空 → 用户无法自行编辑。

修复：模板移入 `html`、`raw_commands` 清空、`raw_printing=0`（`custom_format=1`、`standard=No` 不变）。源码同步修正 `my_custom_app_example/solua_home/print_format/sales_invoice_wholesale_color/sales_invoice_wholesale_color.json`，并加入 `tests/release_whitelist.txt`，避免 `after_migrate` 的 `sync_standard_print_formats()` 再次导入回原始打印态。

回读（生产）：`html_len=2835`、`raw_commands_len=0`、`raw_printing=0`、`disabled=0`。真实数据渲染验证：取在售变体 `SH151046-09`（Standard Selling 900 MZN/条），开启图片与二维码两个开关后渲染 2570 字符，含颜色图与色卡二维码各 1 处，无未解析的 Jinja 标记。现在可在「打印格式」界面直接编辑该模板。

#### ③ 停用多余销售单打印格式

按“只停用不删除”处理，保留可随时恢复：

| 格式 | 处理 | 依据 |
|---|---|---|
| Tax Invoice / Simplified Tax Invoice / Detailed Tax Invoice | 停用（原已停用） | ERPNext 印度税务区域格式，无任何引用 |
| Sales Auditing Voucher | 本次停用 | 未作为默认、未被引用 |
| Sales Invoice Standard / with Item Image / Return / Sales Invoice PD Format v2 / 批发销售单（颜色版） | 保留启用 | 标准回退、退货与既有发票版式 |

无任何 DocType 设置 `default_print_format`，故停用不会影响现有打印入口。

#### 验证与复现

```bash
node  my_custom_app_example/solua_home/tests/wholesale_page_check.cjs
python my_custom_app_example/solua_home/tests/wholesale_print_check.py
```

- 页面测试新增断言：顶部「销售与交货」组位置、新建交货单仅出现一次、弹窗过滤条件（`docstatus=1`、`per_delivered<100`、状态排除 Closed/Completed/Cancelled）、`make_delivery_note` 调用与随后打开交货单、销售单格式入口路由。
- 打印测试新增断言：发票格式必须是 `html` 非空、`raw_printing=0`、`raw_commands` 为空、模块与 doc_type 正确，并完成一次严格 Jinja 渲染（真实生产数据渲染已在服务端另行执行）。
- 部署校验：本地与生产两份文件 SHA256 一致（`solua_home.js` = `1b08bda9…9406`，格式 JSON = `294a2026…db3e`）。

遗留：真实浏览器里点「按销售订单开交货单」生成交货单、以及自行编辑打印格式后的预览，仍需在登录会话中人工过一遍。

### 19.11 2026-09-21 单据类型（DocType）列表瘦身

需求：`/desk/doctype` 里有很多用不上的 ERPNext 单据类型，希望看不到它们。

#### 为什么不删除

生产共有 **833 个 DocType**；“用不上的模块”几乎都被核心单据以 Link 字段引用（删表会导致 Link 指向不存在的 DocType、报表/钩子报错）：

| 候选模块 | DocType 数 | 被引用的位置（部分） |
|---|---|---|
| Manufacturing | 48 | Item / 采购与销售明细 → **BOM**；Stock Entry → Work Order、Job Card；Material Request → Work Order；Pick List → Work Order |
| Projects | 15 | **Project** 被 GL Entry、Sales/Purchase Invoice、Payment Entry、Stock Entry、Delivery Note、Budget、Journal Entry 等 20+ 个核心单据引用 |
| Assets | 26 | Item → Asset Category；Sales/Purchase/POS Invoice Item → Asset；Serial No → Asset |
| Subcontracting | 13 | Purchase Receipt → Subcontracting Receipt；Stock Entry → Subcontracting Order |
| Website / CRM / Email / Integrations | 38 / 28 / 17 / 24 | 销售单据 → UTM Campaign/Medium/Source；Customer → Lead/Opportunity；System Settings / DocType → Email Template；Company → Campaign |
| Quality Management | 16 | 采购/收货/制造链路 |

另外，ERPNext 升级会重新安装 App 自带的 DocType，删了也会回来。因此结论：**不删除、不停用任何 DocType，只在列表默认隐藏**。

#### 做了什么

新增 `solua_home/public/js/doctype_module_filter.js`，通过 `hooks.py` 的 `doctype_list_js` 注册到 DocType 列表（Frappe 先加载 core 的 `doctype_list.js`，再由钩子追回我们的文件，因此只做追加合并，不会覆盖 `primary_action` / `new_doctype_dialog`）：

| 行为 | 实现 |
|---|---|
| 默认只显示在用模块 | `frappe.listview_settings["DocType"].filters` 返回 `[["module", "not in", HIDDEN_MODULES]]`（列表上方显示为可手动删除的筛选条件） |
| 一键显示全部 | 列表右上角按钮「显示全部单据类型 / 只看常用模块」，选择记在浏览器（localStorage），切换后刷新列表 |
| 兼容与兵底 | 若列表实例在读取 settings 之后才构造，则在 `ListView.prototype.setup_defaults` 补一次筛选（幂等，不重复添加，只对 DocType 生效） |

隐藏的 19 个模块：`Assets、Automation、Bulk Transaction、CRM、EDI、ERPNext Integrations、Integrations、LMS、Maintenance、Manufacturing、Projects、Quality Management、Regional、Shopping Cart、Subcontracting、Support、Telephony、Website、Workflow`。

保持可见：`Accounts、Stock、Selling、Buying、Setup、Core、Desk、Contacts、Custom、Printing、Email、Communication、Geo、Utilities、Portal、X POS`。

下拉效果：列表从 833 条减为显示 576 条（隐藏 257 条），数据库与字段完全未动。

#### 部署与回读

- 变更前备份：站点 `20260921_225733-erp_solua_one-*`；旧 `hooks.py` 存于 `sites/erp.solua.one/private/backups/20260921-sales-invoice-print/hooks.py.before`。
- 上线的两个文件（已去 CRLF 保持生产 LF 布局）：`apps/solua_home/public/js/doctype_module_filter.js`（SHA256 `35021449…0407`）、`apps/solua_home/hooks.py`（SHA256 `b1a95efb…592b`）；与备份逐行对比（忽略换行）仅新增 `doctype_list_js` 的 DocType 条目。
- 回读：`frappe.get_hooks("doctype_list_js")` 已含 `DocType`；用 `frappe.desk.form.meta.FormMeta("DocType").load_assets()` 组装出的 `__list_js` 为 7415 字节，含我们的模块筛选与「显示全部单据类型」按钮，且 core 的 `new_doctype_dialog` / `primary_action` 仍在。执行了 `bench --site erp.solua.one clear-cache`（hooks 缓存），未跑 migrate。
- 隔离测试：`node my_custom_app_example/solua_home/tests/doctype_module_filter_check.cjs`（验证默认筛选、核心设置保留、切换持久化、兵底幂等、不影响其他 DocType）。

遗留：真实浏览器里登录后打开 `/desk/doctype` 确认筛选生效与按钮位置（生产回读只能证明脚本被下发）。

> 注：本节“隐藏 19 个模块”的做法已被 **19.13** 替代（改为显式白名单，并覆盖打印格式的“单据类型”下拉框），下文模块清单不再生效，只作历史记录。

### 19.12 2026-09-21 首页「常用功能」改为模块分组 + 工作区入口

需求：首页快捷操作只有「新建销售单 / 新建交货单」这类新建入口，缺「查看」类；希望标题区就是进入大板块的入口，下面才是常用功能（例如标题「销售」下有销售订单、POS 销售单等）。

#### 结构

「快捷操作」更名为 **常用功能**，从 6 个平铺分组改为 6 个模块分组，**分组标题本身是可点击按钮**，点击进入对应工作区（`frappe.router.slug(工作区名)` → `frappe.set_route(slug)`，即 `/desk/selling` 这类 URL）；组内每个功能区分**新建**（`data-new-doc`）与**查看**（`data-view="list"`，进入列表）。分组标题若拿不到工作区权限，则退回该模块的首个列表页。

| 分组（标题可点，跳工作区） | 组内功能 |
|---|---|
| **销售** → Selling | 新建销售订单 / 销售订单 / 新建交货单 / 按销售订单开交货单 / 交货单 / 销售发票 / POS 销售单 / 报价单 / 客户门店 / 优惠促销管理 |
| **库存** → Stock | 新建物料 / 物料列表 / 库存入库 / 物料出库 / 领用 / 损耗 / 出入库记录 / 手机扫码盘点 / 盘点单 / 仓库与库位 |
| **采购** → Buying | 新建采购订单 / 采购订单 / 采购收货 / 收货记录 / 采购发票 / 供应商 |
| **财务** → Invoicing | 销售发票 / 采购发票 / 新建收款单 / 收付款单 |
| **打印与标签**（标题 → 打印格式列表） | 打印设置 / 打印设计 / 销售单格式 / 标签打印 |
| **其他入口**（不可点） | POS交班 / 公开色卡 / xPos 收银台 |

原「订单与客户」组撤销：新建销售订单、客户/门店并入「销售」；供应商并入「采购」；采购收货从「库存管理」移到「采购」；优惠/促销从独立分组并入「销售」；xPos 入口更名为「xPos 收银台」。

每个分组与每条功能都按权限显示：`api/home.py` 的 `_permissions()` 从 17 个标志位扩到 33 个，新增 `read_sales_order / read_delivery_note / read_sales_invoice / read_pos_invoice / read_quotation / read_stock_entry / read_warehouse / new_purchase_order / read_purchase_order / read_purchase_receipt / read_purchase_invoice / new_payment_entry / read_payment_entry / read_stock_reconciliation（已有）/ read_purchase_receipt` 等；某分组内一条可见功能都没有时整个分组不渲染。收银员 `pos1@solua.one` 实测可见销售、交货、POS 销售单、客户、仓库等，看不到库存/打印/采购下单（其角色确无权限）。

#### 部署与回读

- 三个文件（均为 LF、字节与本地一致）：`api/home.py`（SHA256 `1b2622fd…a022`，含另一处此前未提交的 `_resolve_warehouse` 修正：改为 Stock Settings 默认仓优先、用户默认仓兜底）、`solua_wholesale/page/solua_home/solua_home.js`（`aacb59b1…1fa1`）、同目录 `solua_home.css`（`d98e4ae6…966c`）。
- 变更前文件备份在 `sites/erp.solua.one/private/backups/20260921-homepage-actions/`（`home.py.before` / `solua_home.js.before` / `solua_home.css.before`）；未跑 migrate，只 `bench --site erp.solua.one clear-cache`。
- 回读方式（重要）：Desk Page 的脚本**不是**静态资源 URL，而是 `frappe/core/doctype/page/page.py:load_assets()` 从 `get_module_path(module)/page/<scrub(page)>/` 读取后内联返回，所以 `/assets/solua_home/solua_wholesale/page/...` 返回 404 属正常现象。正确回读是 `frappe.get_doc("Page","solua-home").load_assets()`：脚本 18330 字符（=文件 19394 字节 UTF-8），含 `data-workspace` 模板、`open_workspace`、`data-view="list"`，CSS 含 `.solua-home-group-title-link`。
- 工作区可用性回读：`Selling / Stock / Buying / Invoicing` 四个 Workspace 均 public 且无角色限制，出现在 boot 的 workspace pages 中。
- 隔离测试：`tests/wholesale_page_check.cjs` 断言 41 个功能标签、四个工作区入口、`data-view=list` 必须走列表而不新建单据、工作区缺失时退回列表；`wholesale_forms_check.cjs`、`wholesale_print_check.py`、`shared_barcode_check.py`、`doctype_module_filter_check.cjs` 全绿。

遗留：真实浏览器登录后点一次分组标题（应进入对应工作区）与「查看」按钮（应进入列表而非空白新建单）确认体验（服务端回读只能证明脚本已下发）。

### 19.13 2026-09-21 单据类型改为白名单（67 项），并覆盖打印格式下拉框

需求：“还是太多”；并指出真正常用的入口不是 `/desk/doctype` 列表，而是**编辑打印格式时「单据类型」的下拉框**。

关键发现：19.11 的做法（`frappe.listview_settings["DocType"].filters`）**只影响列表页**，对 Link 字段的下拉搜索完全没有效果；而且 833 → 576 的模块筛选仍然太宽。

#### 做法：一份显式白名单，两处生效

`public/js/doctype_module_filter.js` 从“隐藏模块”改为**显式白名单 `IN_USE_DOCTYPES`**，同一份清单同时服务两处：

| 位置 | 实现 | 切换按钮 |
|---|---|---|
| `/desk/doctype` 列表 | `listview_settings["DocType"].filters` 返回 `[["name", "in", 白名单]]` | 右上角「显示全部单据类型 / 只看常用单据类型」（刷新列表） |
| 打印格式表单 `doc_type` 下拉 | `hooks.py` 新增 `doctype_js = {"Print Format": "public/js/doctype_module_filter.js"}`，在 `onload/refresh` 里 `frm.set_query("doc_type", () => ({ filters: { name: ["in", 白名单] } }))` | 表单按钮同样切换，**即时生效不刷新**（切换后 `refresh_field("doc_type")`） |

切换状态按浏览器记忆（`localStorage` 键 `solua_home_doctype_show_all`），开关打开时两处都放开为全部 800+ 个单据类型；只改“筛选条件/下拉候选”，不删除、不停用、不修改任何 DocType、字段或数据。

白名单共 **67 项**（按用途分组，增减只需改 JS 里这一张表）：

| 用途 | 单据类型 |
|---|---|
| 销售与交货 | Quotation、Sales Order、Delivery Note、Sales Invoice、POS Invoice、POS Opening Entry、POS Closing Entry、Pick List、Vehicle |
| 采购 | Request for Quotation、Purchase Order、Purchase Receipt、Purchase Invoice |
| 收付款与总账 | Payment Entry、Journal Entry |
| 商品与库存 | Item、Item Price、Price List、Item Group、Item Attribute、Warehouse、UOM、Stock Entry、Stock Entry Type、Stock Reconciliation |
| 客户/供应商/地址 | Customer、Customer Group、Supplier、Supplier Group、Sales Person、Territory、Address、Contact |
| 公司与价格 | Company、Currency、Country、Mode of Payment、Payment Term、Payment Terms Template、Sales/Purchase Taxes and Charges Template、Tax Category、Cost Center、Pricing Rule |
| 打印与系统 | Letter Head、Print Format、Print Heading、Print Style、Report、DocType、Custom Field、Property Setter、Workspace、User、Role、File、Data Import |
| X POS 与自建单据 | POS Profile、POS Opening Shift、POS Closing Shift、POS Cash Movement、POS Offer、POS Coupon、XPOS Branding Settings、Scale Barcode Settings、Product Bundle Definition、Retail Settings |

效果：列表与下拉从“可见 472 个（含子表共 833）”缩到 **67 个**。

#### 部署与回读

- 备份：`sites/erp.solua.one/private/backups/20260921-doctype-scope/`（`hooks.py.before`、`doctype_module_filter.js.before`）。
- 上线两个文件（均为 LF）：`apps/solua_home/public/js/doctype_module_filter.js`（SHA256 `bd621ad7…e426`）、`apps/solua_home/hooks.py`（`50b32d65…a80e`）；hooks 与备份逐行比对（忽略换行）**仅新增** `doctype_js["Print Format"]` 一行与注释改写。
- 回读：`frappe.get_hooks("doctype_js")["Print Format"]` 已含本文件（与 print_designer 的 `print_format.js` 并存；后者不设置 `doc_type` 查询，无冲突）；白名单 67 项在该站**全部存在**且无子表；`FormMeta("Print Format").load_assets().__js`（11628 字节）含 `set_query("doc_type"`；`FormMeta("DocType").load_assets().__list_js`（9971 字节）含 `["name", "in"` 与切换按钮，core 的 `new_doctype_dialog` 仍在。未跑 migrate，只 `clear-cache`。
- 隔离测试：重写 `tests/doctype_module_filter_check.cjs`（白名单内容与规模、列表筛选、表单 `doc_type` 查询与切换、核心设置不被替换、幂等兵底），其余 3 个 node 测试与 2 个 python 测试保持全绿。

遗留：需在浏览器确认列表与打印格式下拉的实际效果；要加/删某个单据类型时只改 `IN_USE_DOCTYPES` 一处（后续可考虑把它做成 `Retail Settings` 里可配置的清单）。

### 19.14 2026-09-21 收银员首页 = 只有 POS（POS-only 模式）

需求：“收银员只有使用pos的权限”。

#### 先查清的事实

| 项目 | 生产现状 |
|---|---|
| pos1/pos2/pos_manager 的 Frappe 角色 | **Accounts User + POS Cashier + Sales User**（并非 POS-only） |
| 「POS Cashier」角色本身 | 只有 POS Opening/Closing Entry 的 Custom DocPerm（read/write/create/submit），无其它 DocPerm；单靠它无法新建 POS Invoice（POS Invoice 的 create/submit 只给 Accounts Manager/User） |
| xPos 桌面端鑴权 | API Key/Secret（同步身份 `xpos_sync@solua.one` 持 XPOS Sync 角色）；开单/改单全部 `ignore_permissions`，收银员自身角色不参与 |
| 收银员身份判定 | POS Profile 的 `applicable_for_users`（POS Profile User 子表），xPos 的 `resolve_pos_actor` / `is_pos_cashier` / POS Role 都基于它 |
| 收银方式1 - SH | 成员：pos1、pos2、pos_manager、Administrator；`pos_role`：pos1/pos2 空（xPos 默认 Cashier）、pos_manager=Manager；`is_cashier` 三人都是 0 |

结论：桌面上“能看到什么”与 xPos 能否开单无关，因此首页按“是否 POS Profile 收银员”切换即可，**不动任何角色与数据**。

#### 做了什么

- 后端 `api/home.py` 新增 `_pos_cashier_profile()`：当前用户不是 Guest/Administrator → 不具备 POS_MANAGER_ROLES（System/POS/Accounts/Sales/Stock Manager）→ 属于某个未停用的 POS Profile 的 `applicable_for_users` → 其 xPos POS Role 不在 (Manager/Administrator/Supervisor) 内。命中时 `get_dashboard_data()` 直接返回 `home_mode: "pos"` 的**最小载荷**（只含 company/currency/query_time/pos_profile/permissions），不跑开票额、未收款、待交付、逾期应收、库存预警、商品资料等聚合查询。
- 前端页面：收到 `home_mode == "pos"` 时隐藏「经营概览」「待处理」「资料准备」三块（`data-section` 开关），副标题改为「收银台 · 销售单与交班」，分组标题改为「收银」，只渲染三个入口：**开始收银（xPos）/ POS交班 / POS 销售单**；「商品查找」（查价）保留，双栏变单栏。
- 管理岗与主管不受影响：Administrator、System/Sales/Accounts/Stock Manager、以及 xPos POS Role=Manager 的 `pos_manager` 都继续看到完整首页。

#### 部署与回读

- 备份：`sites/erp.solua.one/private/backups/20260921-pos-cashier-home/`。上线三个文件（均 LF）：`api/home.py`（SHA256 `dd285228…9076`）、`solua_wholesale/page/solua_home/solua_home.js`（`f7a7e5ce…14ca`）、同目录 `solua_home.css`（`c10b8d49…5fcf`）；未跑 migrate，只 `clear-cache`。
- 回读：`get_dashboard_data()` 对 pos1/pos2 返回 `home_mode=pos`（8 个键，无任何业务字段），对 pos_manager/Administrator/xpos_sync 返回 `home_mode=desk`（18 个键）；`Page("solua-home").load_assets()` 的脚本含 `pos_actions` / `data-section` / 收银入口，CSS 含单栏规则。
- 隔离测试：`wholesale_page_check.cjs` 新增收银员场景（只显示收银入口、隐藏 13 个业务入口、三块面板 toggle、标题变「收银」、显示收银台名、管理员再次加载后恢复完整布局）；`wholesale_print_check.py` 新增 `_pos_cashier_profile()` 判定链（经理角色、主管 POS Role、停用 Profile、非成员）。

#### 遗留（需业务确认）

1. pos1/pos2 仍带着 **Sales User 与 Accounts User** 角色。若要让账面上真正“只有 POS 权限”，需去掉这两个角色、只留 POS Cashier；xPos 桌面端不受影响（走同步身份 + `ignore_permissions`），但网页端手工新建 POS/销售发票、看客户、以及内置网页收银台会失效。动之前建议备份角色并在收银机上跑一单验收。
2. 同步账号 `xpos_sync@solua.one` 当前挂 47 个角色（含 System Manager）——它是收银机的 API Key 身份，权限过大，比收银员更值得收敛。
3. POS Profile User 的 `is_cashier` 对 pos1/pos2 未勾选；当前 xPos 的结算校验跑在同步身份（System Manager）上所以不受影响，但一旦收敛同步账号就会开始拦截，届时要给收银员勾上 `is_cashier`。

### 19.15 本地销售订单条码、描述与打印显示开关（2026-09-22）

本地实现，尚未部署生产：

- 销售订单明细增加只读字段 `custom_item_barcode`，显示真实商品条码；变体没有独立条码时读取模板条码，绝不使用 `item_code` 冒充。
- 明细标准 `description` 优先写入 `custom_item_description_pt`，为空时清理 HTML 后回退 Item 标准描述。
- 「客户订单确认单（颜色版）」每行显示条码和描述。
- 销售订单打印按钮的「打印选项」增加三个独立开关：商品名称、SKU/货号、色号；默认全部开启。隐藏项目会从表格中移除，剩余列使用自动布局，不保留空列。
- `tests/sales_order_item_display_check.py` 覆盖模板条码继承、葡语描述回退、标准描述回退和禁止使用货号；`wholesale_print_check.py` 覆盖三个开关的 8 种组合。

### 19.16 2026-09-22 资料准备改为“点名清单 + 定向跳转”

需求：“商品资料：缺图片 4 · 缺固定色号 8 … 点击跳转到物料清单了，还是不知道问题是什么”。

#### 问题

首页「资料准备」只回传两个计数，行本身跳的是**未加筛选**的物料列表，用户看到的仍是全部 92 条物料，无法知道是哪几条、缺什么。

#### 做了什么

- 后端 `_item_data_status()`（`api/home.py`）不再只算数字：每个检查项都带上 `field`（要补的字段）、`hint`（一句话说明）以及**受影响物料清单** `items`（`name / item_name / item_group / variant_of`，上限 `ITEM_ISSUE_ROW_LIMIT = 200`，超出置 `truncated`）。颜色属性名抽成常量 `COLOR_ATTRIBUTE = "Cor"`。原有 `missing_image` / `missing_color_code` / `item_count` 字段保持不变，向后兼容。
- **检查范围只含单品/变体**（业务确认）：模板（`has_variants=1`）本身没有唯一商品图和唯一色号，是正常状态，不计入任何检查。新增 `checked_count`（参与检查的单品/变体数）与 `template_count`（被跳过的模板数）。
- 前端「资料准备」重写为可展开的问题清单：每行显示「检查项 + 条数 + 说明 + 前 3 个物料号」，点标题就地展开，展开后**每条物料是一行按钮，直接打开该物料表单**；底部「在物料列表中只看这 N 条」用 `data-filters` 深链，落到**只含这些物料**的列表（`frappe.route_options = {name: ["in", [...]]}`，超过 200 条或 `truncated` 时退回普通列表）。计数为 0 的检查显示「已齐全 ✓」，不再制造“0 个问题”的噪音。
- 样式新增 `.solua-home-issue*` 规则（展开箭头旋转、物料行为蓝色链接、已齐全行灰字）。

#### 生产回读（2026-09-22）

- 备份 `sites/erp.solua.one/private/backups/20260922-homepage-issue-drilldown/`（同一目录下的 `*.before` 已被第二版覆盖为前一版内容）；最终上线 `api/home.py`（`bb0cd7ad…8f8b`）、`solua_wholesale/page/solua_home/solua_home.js`（`6053d872…b86e`）、同目录 `solua_home.css`（`d9ab79db…34e7`，未再变），本地↔生产 SHA256 逐一致；未跑 migrate，只 `clear-cache`。（注意 `apps/solua_home/solua_home` 是指向 app 根目录自身的软链接，因此只有一套文件。）
- 首版上线后回读发现两个检查项命中的全部是模板（缺图片 4 = 4 个杆模板；缺固定色号 8 = 上述 4 个杆模板 + 4 个窗帘模板 `SH151046`/`SH151060`/`SH151107`/`SH151114`）。业务确认“模板就是无图无色号的，不是错误”，因此第二版把范围限定为单品/变体。
- 限定后回读：`item_count=92`、`checked_count=84`、`template_count=8`、`missing_image=0`、`missing_color_code=0` —— 两个检查项都显示「已齐全 ✓」，模板不再被报为问题；页面上方的汇总行会写明“共 92 条启用物料，其中 84 条单品/变体参与检查，模板 8 条不计”。
- `Page("solua-home").load_assets()` 回读：脚本含 `data-issue-toggle` / `data-issue-body` / `data-filters` / `render_item_data`，CSS 含 `.solua-home-issue-head` 等规则。
- 测试：`wholesale_page_check.cjs` 新增场景（面板写明检查总数、每条检查点名物料、展开按钮切换、`data-filters` 深链设置 `route_options` 并跳列表、坏 JSON 退回普通列表；顺手让测试用的 `__()` 支持 `{0}` 插值与 jQuery 式 `toggleClass`）；`wholesale_print_check.py` 新增 `_item_data_status()` 断言（状态/计数/检查项顺序/`field`/`items` 命名/`truncated`）。

#### 结论

- 两项检查现在只对**单品/变体**报数：模板有无图片、有无色号都不再算问题。若以后想改变这个口径（例如要求模板也必须有家族图），只需把 `sellable = [row for row in items if not int(row.get("has_variants") or 0)]` 这行的过滤条件改掉。

### 19.17 2026-09-22 物料列表显示「当前库存」与四档售价

需求：“物料页面，怎么能够显示当前的库存和不同的售价？”

#### 为什么原来看不到

- 列表里的「库存/价格」列取的是 ERPNext 自带字段 `total_projected_qty` / `standard_rate`，本站在库数据全写在 `Bin`、价格全写在 `Item Price`，这两个字段一直是 **0**，所以看着像没数据。
- 另一个坑：列表列的**顺序与可见数量**由 `List View Settings`（名称 = `Item`）的 `fields` JSON 控制，前端再按屏宽只显示 4 / 6 / 10 列（`≤1366px → 4`、`1367–1919px → 6`、`≥1920px → 10`）。所以只把字段加上 `in_list_view` 并不够，旧列已经占满了可见位。

#### 做了什么

- 新模块 `item_metrics.py`：把真实数据镜像到 6 个只读 Item 字段（`Currencies`/`Float`，都勾了列表可见）：

| 字段 | 含义 | 来源 |
|---|---|---|
| `custom_stock_qty` | 当前库存（各在用叶子仓库 `Bin.actual_qty` 合计） | 汇总 `tabBin`，排除 `is_group=1` 与 `disabled=1` 的仓库 |
| `custom_variant_stock_qty` | 变体库存合计（仅模板） | 模板下所有变体的库存 |
| `custom_rate_cost` | 成本价 | 价目表 `Standard Buying` |
| `custom_rate_home` | Home Store 价 | `Wholesale Selling 3` |
| `custom_rate_wholesale` | 批发价 | `Wholesale Selling` |
| `custom_rate_retail` | 建议零售价 | `Standard Selling` |

- 取价规则：只认**不带客户/供应商**的价目表行；同一档有多行时优先本位计量单位，再优先新的 `valid_from`（价格字段保留 2 位小数，原值仍在 `Item Price`）。
- 刷新时机（`hooks.py`）：库存类单据（Stock Entry / Stock Reconciliation / Purchase Receipt / Purchase Invoice / Delivery Note / Sales Invoice / POS Invoice）的 `on_submit` 与 `on_cancel`；`Item Price` 的 `on_update`/`after_delete`；`Item` 的 `on_update`。变体变动时会连带重算其模板的合计。**注意钩子必须挂在父单据上**：Bin 的写入发生在 `make_sl_entries → update_entries_after → update_bin`，即 SLE 提交之后，所以挂 Stock Ledger Entry 会读到旧值。
- 只在数值真变化时才写库（`update_modified=False`，不扰动物料的修改时间）；另有 `refresh_all_item_metrics()`（白名单方法，限 System/Stock/Item/Sales/Accounts Manager）+ 物料列表右上角**「刷新库存与售价」**按钮（`public/js/item_list_metrics.js`，经 `doctype_list_js["Item"]` 下发）与每日兜底任务（`tasks.daily_tasks`）供批量导入/补记后手动对齐。
- 列顺序：把「物料名称 / 状态 / 当前库存 / 成本价 / 批发价 / 建议零售价 / Home Store 价 / 变体库存合计」排到 `List View Settings(Item)` 的最前面，其余旧列（SPU/订货货号/标签条码/固定色号/估值价/色卡图/图片/分组/POS简称/描述）保留在后面（在列表右上角列设置里依旧可勾选、拖动）。原列顺序备份在 `sites/erp.solua.one/private/backups/20260922-item-metrics/item-list-columns.before.json`，如需回滚把它写回 `List View Settings(Item).fields` 即可。
- 旧列 `valuation_rate` 原本标着「成本价」但本期一直是 0/入库估值，已改名为「估值价（入库估值，非采购成本）」，真正的采购成本看新的「成本价」。

#### 生产回读（2026-09-22）

- 备份 `sites/erp.solua.one/private/backups/20260922-item-metrics/`（`hooks.py` / `tasks.py` / 列顺序 JSON）；上线 `item_metrics.py`（`86a9df98…b0e2`）、`public/js/item_list_metrics.js`（`e179d162…f7e4`）、`hooks.py`（`68defcce…96de`）、`tasks.py`（`1f6cea36…86e1`），本地↔生产 SHA256 逐一致；未跑 migrate（只清了缓存）。
- 建字段 + 首次回填：93 条物料全部重算；抽查 `SH151060-10`（库存 70 / 成本 334.16 / Home 430 / 批发 480 / 零售 900）、`SH151121`（1500 / 366.12 / 520 / 570 / 1280）、杆变体 `SH151169-3MD-1`（60 / 只有零售 660）、模板 `SH151060`（自身 0、变体合计 700）均正确；全库库存合计 **36,410** 与 Bin 一致，85 条有零售价、65 条有批发价与成本价。
- 钩子实测：把 `SH151060-01` 的库存镜偺值故意写成 0，再拿真实单据 `MAT-STE-2026-00004` 跑一遍 `on_stock_voucher_change`，值恢复为 70，且未触及不在该单据里的物料。
- `frappe.get_hooks` 回读：8 个单据均为 `on_submit`/`on_cancel` 接入 `solua_home.item_metrics.on_stock_voucher_change`，`after_migrate` 已加上 `solua_home.item_metrics.after_migrate`（迁移时自动补字段并重算）；`FormMeta("Item").load_assets().__list_js` 含刷新按钮脚本。
- 隔离测试：新增 `tests/item_metrics_check.py`（四档价目表映射、本位 UOM 优先、跳过客户专属价、只汇总叶子仓库、模板变体合计、变动才写库、钩子入参、字段创建幂等、权限门禁）与 `tests/item_list_metrics_check.cjs`（列宽覆盖不会被框架算出的值拉宽、保留其他 app 的 `onload`/设置、刷新按钮调用后端并重拉列表、缺少 `apply_column_widths` 时不报错）。
- 列宽上线：`public/js/item_list_metrics.js`（`859497c7…20b0`），变更前文件备份在同目录 `item_list_metrics.js.before`；回读 `FormMeta("Item").__list_js` 含 `COLUMN_WIDTHS`、`apply_column_widths`、刷新按钮。

#### 列宽（2026-09-22 补充）

Frappe 的列表列宽不是配置项：每次重绘时 `render_list()` 会按**单元格文字长度**算宽度（`textLength * 10 / 1.3`，空的单元格按 22.5 字算 = 约 173px，图片列也是这么被撑宽的），存进 `this.column_max_widths`，再由 `apply_column_widths()` 写成行内 `width` / `flex: 1 0 <px>`。这张表只会“变大不会变小”，所以长文本列（描述、订货货号）和空值列都会偏宽。

因此 `public/js/item_list_metrics.js` 里加了一张列宽表并在 `onload` 把实例的 `apply_column_widths` 包了一层：每次重绘后先把表里的值写回 `column_max_widths` 再交给原方法。好处是仍然走框架自己的机制（不写 `!important`、不依赖 DOM 结构），列宽在首次加载、刷新、改列设置后都生效；不同版本缺这个方法时会自动跳过，不影响页面。

当前生效的列宽（单位 px，改这一个表即可）：库存/变体库存 110/130、成本价 110、Home Store 价 120、批发价 110、建议零售价 110、固定色号 90、订货货号 130、SPU 120、标签条码 150、POS简称 110、物料分组 100、估值价 120、描述 220、图片/色卡图 90。

#### 使用提示

- 列表右上角「⚙ / 列设置」（Column Settings）可以勾选/拖动显示哪些列，新列已在候选里；只想要几个就取消其它勾选。
- 「当前库存」是各在用仓库**合计**；要按仓库/货架看，打开物料表单的 Bin/库存明细，或看模板的颜色库存明细。
- 物料的实际库存挂在**变体**上，所以模板行的「当前库存」为 0 是正常的，看旁边的「变体库存合计」。
- 杆类目前只有 `Standard Selling` 一张价目表，因此杆的成本/批发/Home Store 三列是空的——补价后列会自动出现数字。

### 19.18 2026-09-23 交货单提交受阻：门店比对放宽 + 订单反向回填

**现象**：`MAT-DN-2026-00001` 提交时连续被拦（“关联订单客户/门店/收货地址不一致” → 修完撞“尚未开票”）。

**根因**：`printing/wholesale.py::prepare_print_snapshot`（DN `before_submit`）要求 `SO.custom_store_name == DN.custom_store_name`，但 `api/stock.py::validate_delivery_note` 只做 **SO → DN 单向补空**，SO 门店永远为空 → 两边必不一致；生产上此前 0 张已提交 DN，该校验第一次真正生效就拦住第一单。叠加 `custom_invoice_plan` 为空触发第二条规则。

**修复**（两文件已上线，SHA：`wholesale.py 2bdbb503…bf69b0`、`stock.py 05cafbea…e646de`，备份在 `backups/20260923-dn-store-invoice-fix/`）：
1. 门店比对放宽：**SO 门店为空时以 DN 为准**，只有两边都填且不同才报“不一致”（拆单防线保留）；比较前 `.strip()` 防空格误判。
2. 反向回填：DN 保存时把 `custom_store_name/phone/customer_order_no/invoice_plan` 中 **订单侧为空** 的字段用 DN 值补上（只补空、不覆盖），下次开单不会再撞同一坑。
3. 数据修复：DN `custom_invoice_plan` = 「本单交货签收后开票」（规则要求 ≥8 字且非占位词，用户口述的“交货签收后开票”只 7 字，补足字数保留原意）。

**验证**：`wholesale_print_check.py` 新增断言（SO 门店空 → 不拦；回填只补空不覆盖、`set_value` 只写 Sales Order）。先在事务内试提交成功并回滚（不落库），随后**正式提交 `MAT-DN-2026-00001` 成功**：docstatus=1、状态 To Bill、64 行、64 条 Stock Ledger Entry（`Receiving - SH` 出库）、打印快照冻结 `store=1 店` / `invoice_plan=本单交货签收后开票` / 64 行明细，SO `SAL-ORD-2026-00011` 三字段（门店/电话/开票安排）已由反向回填补齐。

**部署注意**：gunicorn 是 `--preload` 常驻进程，Python 改动必须重启才生效；`bench restart` 会因 frappe 用户无 sudo 权限卡在内部 `sudo supervisorctl`，实际可用做法：`sudo -u frappe -i bash -c "kill -TERM <gunicorn 主进程 PID>"`（supervisor `autorestart=true` 会自动拉起，勿动 redis——session 在里面）。重启后 `ping` 200、新 PID 时间戳晚于文件 mtime 即可确认已加载新代码。

**注意**：开票安排是业务必填（≥8 字、非“后续开票/未维护”等占位词），除非该 DN 已有已提交销售发票关联。

### 19.19 2026-09-23 单据明细「总数量」与「导出表格」（Excel / CSV）

**需求**：① 销售订单 / 销售单 / 交货单 / 拣货单最下面都要显示总数量；② 这四张单据都要能“以表格格式导出”；③ 关闭“关联订单客户/门店/收货地址不一致，请拆分送货单”这条自定义校验。

#### 三处总数量

| 位置 | 实现 | 说明 |
|---|---|---|
| 打印表格底部 | 三个打印格式的 `<tfoot>` 新增一行 `Total Qty / 总数量`，值来自新 jinja helper `get_print_total_qty(p)` | 列数与开关联动（`show_images/item_name/sku/color_code/description/ordered_before`），不受列勾选影响 |
| 单据表单明细底部 | `public/js/document_table_export.js` 在 `refresh` 时往明细 grid 里插一行 `共 N 行 · 总数量 X · 明细金额合计 Y`（拣货单无金额），并包一层 `grid.refresh` 让增删改后自动更新 | 未保存的新单据也显示 |
| 导出表格最后一行 | `api/export.py::_total_row` 按选中的列给 `数量/已拣数量/订购数量/此前已交付/剩余数量/金额` 求和 | Excel 里可直接求和 |

`get_print_total_qty(data)`（`printing/wholesale.py`）对空快照、缺行、字符串数字都安全，快照与实时数据通用；打印格式里用 `{{ get_print_total_qty(p) }}`，已注册到 `hooks.jinja.methods`。

#### 导出表格（Excel / CSV）

- 后端：`api/export.py`（`@frappe.whitelist()`）：`get_export_options(doctype)` 给出可用列/默认勾选/格式；`export_document_table(doctype, name, columns, fmt, include_header, include_total)` 下载文件。白名单只有这四张单据，并且要 `has_permission(..., "read")`；`fmt=xlsx`（`build_xlsx_response`）或 `csv`（`provide_binary_file` + **UTF-8 BOM**，Excel 打开中文不乱码）。
- 列与打印表格一致：序号、货号、商品名称、订货货号、色号、颜色、条码、描述、数量、单位、单价、金额、仓库（交货单另有订购/此前已交付/剩余，拣货单有已拣数量）。数量与金额以**数字**写入，Excel 能直接求和；货号/色号/条码/描述复用打印用的 `get_wholesale_print_data` 与 `get_item_sales_display`。
- 前端：`public/js/document_table_export.js` 给四张单据在「打印」分组加「导出表格」按钮 → 弹窗勾选列 + 是否含抬头/合计行 → 「导出 Excel」/「导出 CSV」按钮打开 `/api/method/solua_home.api.export.export_document_table?...` 直接下载。
- 注册方式：`hooks.doctype_js`（值可以是**列表**，与其它 app 的脚本合并），不留会需要 `bench build` 的 `app_include_js`。

**拣货单的坑**：ERPNext 拣货单的明细子表是 **`locations`（Pick List Item）**，不是 `items`；前端与后端都按 `Pick List → locations` 取行，否则导出为空、底部总数量永远是 0。

#### 关闭“拆分送货单”校验

`printing/wholesale.py::prepare_print_snapshot` 里客户/门店/收货地址一致性检查整段注释掉（用户确认非自家规则、可关），**送货联系人一致性**仍然保留；`wholesale_print_check.py` 对应断言改为“门店不同不再拦截”。本次随同一批文件一起上线。

#### 部署与回读（2026-09-23）

- 备份 `sites/erp.solua.one/private/backups/20260923-doc-table-export/`（`hooks.py` / `wholesale.py` / 三个打印格式 JSON / 首次上线版 `export.py`、`document_table_export.js`）。
- 上线：`api/export.py`（`d7fba12b…81e4`）、`public/js/document_table_export.js`（`933e8fa6…b58d`）、`hooks.py`（`31762fb3…4545`）、`printing/wholesale.py`（`de63337b…3ec3`）、`print_format/sales_order_wholesale_color.json`（`af83c4f5…7fbc`）、`print_format/delivery_note_guia_remessa.json`（`2f5693cf…3cae`），本地↔生产 SHA256 逐一致；未跑 migrate。
- **销售单（Sales Invoice）打印格式例外的处理**：生产上的「批发销售单（颜色版）」html 比仓库里的版本旧（生产 2835 字、仓库 3736 字，仓库那版是另一条线的重构），所以**没有覆盖**，而是就地插入总数量行（用 `{% set ns = namespace(qty=0) %}` 循环求和，因为旧模板里没有 `p`）：DB 2835 → 3166，同步写回线上文件。
- DB 记录同步：`客户订单确认单（颜色版）` 4154 → 4407、`Guia de Remessa` 5303 → 5592、`批发销售单（颜色版）` 2835 → 3166。
- 回读：`frappe.get_hooks("doctype_js")` 四个单据都带 `document_table_export.js`；`hooks.jinja.methods` 含 `get_print_total_qty`；`FormMeta(<doctype>).as_dict()["__js"]` 里能看到脚本源码；`frappe.get_print("Sales Order", "SAL-ORD-2026-00011", print_format="客户订单确认单（颜色版）")` 与 `Guia de Remessa`（`MAT-DN-2026-00001`）渲染结果含 `Total Qty / 总数量` 且数字 = 1120（64 行合计，与 `doc.items` 独立求和一致）；销售单模板用假单据渲染出 `3.5`。
- 导出载荷：销售订单 CSV（BOM + 抬头 + 合计行 `1120 / 458550`）、交货单 XLSX（openpyxl 打开、16 列、合计行）；拣货单用内存单据验证取行（含 `已拣数量`）。HTTP 冒烟：`/api/method/solua_home.api.export.*` 对 Guest 返回 **403**（路由存在、需要登录），登录用户点按钮即可下载。
- 隔离测试：新增 `tests/document_export_check.py`（列定义/列过滤与顺序、抬头与合计行、单选列时标签不吃掉数字、CSV 的 BOM+CRLF、XLSX 载荷、拣货单 locations、白名单与权限）与 `tests/document_table_export_check.cjs`（四个单据注册、底部行数与总数量、grid 重绘不重复插入、导出弹窗列勾选与 xlsx/csv 链接、空选提示、无 grid 表单不报错）；`wholesale_print_check.py` 增加 `get_print_total_qty` 与“渲染出的打印 HTML 含总数量行”断言。11 个测试全绿。

**两个踩坑记录（下次别再踩）**

1. **独立 python 脚本改数据必须 `frappe.db.commit()`**：`frappe.db.set_value` 在脚本末尾能看到自己的写入，但进程退出时整个事务回滚——本次打印格式第一次“上线成功”其实没有落库，回读才发现（`raw sql` 里没有新行）。
2. **改 `hooks.py` 必须重启 gunicorn/worker**（`--preload` 常驻进程会缓存 hooks 与已导入的 python 模块）；`bench restart` 会卡在 `sudo supervisorctl`，用 `kill -TERM <gunicorn 主进程>` 让 supervisor 自动拉起（勿动 redis）。另外 `scp` 到 /tmp 的目录要 `chmod 755`，否则 frappe 用户读不到（umask 会让目录变成 744）。

### 19.20 2026-09-23 拣货单打印格式 + 批发销售单（颜色版）新版

#### 拣货单（颜色版）——新格式，纸面带总数量

- 新建 `print_format/pick_list_color/pick_list_color.json`（doc_type=Pick List，module=Solua Wholesale，自定义 HTML+A4 CSS）。明细取 **`locations`**（与导出/表单同一套取数 `get_pick_list_print_data(doc)`，`printing/wholesale.py`），列：序号/图片/商品/SKU/色号/条码/描述/仓库/已拣数量/数量/单位/来源单据，底部 `Total Qty / 总数量` 两行（数量与已拣数量）。
- DB 记录名「拣货单（颜色版）」，并把 **DocType(Pick List).default_print_format** 指向它——原标准格式 `Pick List`（Stock 模块）保留未动，可随时切回。
- 回读：内存拣货单渲染 1610 字节，总数量行、`7.5/6.5` 合计、条码/描述、草稿提示「非正式凭证」全部在；`get_print_format` 解析 ok。

#### 批发销售单（颜色版）新版——另一条线的重构版，以新名字上线

- 仓库里的重构版（含图片/色卡列开关）以 **「批发销售单（颜色版）新版」** 建进 DB（`print_format/sales_invoice_wholesale_color_v2/sales_invoice_wholesale_color_v2.json`，module=Solua Wholesale）；**旧「批发销售单（颜色版）」一字未动**，用户在打印弹窗里自行选择用哪个。
- 回读：渲染 1360 字节、总数量行 `3.5`、色卡列标题齐全、无残留 `{%`。
- 测试断言：`wholesale_print_check.py` 含 v2 文件存在、名称与 doc_type、module=Solua Wholesale、渲染含总数量行。

#### 生产踩坑：挂了不存在 Module 的打印格式会直接打不开

- 全库扫描发现旧「批发销售单（颜色版）」module=**「Solua Home 定制」**，而 Module Def 里只有 `Solua Wholesale`（modules.txt 也是）。`frappe.www.printview.get_print_format` 会 `frappe.get_cached_value("Module Def", module, "custom")` → **DoesNotExistError**，即打印时直接报错。已把该格式 module 修到 `Solua Wholesale` 并清缓存；全库仅此一条坏记录，修后五张自定义格式全部解析 ok。
- 排查提醒：**Print Format 的 module 必须指向真实存在的 Module Def**；modules.txt 只列了 `Solua` 和 `Wholesale` 两个词，实际 Module Def 名是拼接的 `Solua Wholesale`。

#### 部署与回读（2026-09-23）

- 备份 `sites/erp.solua.one/private/backups/20260923-print-formats/`（hooks.py、wholesale.py 改动前副本）。
- 上线 4 个文件：`hooks.py`（jinja methods 增 `get_pick_list_print_data`、`get_print_total_qty`）、`printing/wholesale.py`、`print_format/pick_list_color.json`、`print_format/sales_invoice_wholesale_color_v2.json`；除 hooks.py 因**换行符 CRLF/LF 差异** SHA 不同（内容一致）外其余逐一致。
- DB 写入用独立脚本（含 `frappe.db.commit()`）：upsert 两个格式 + 设默认格式；回读确认 `拣货单（颜色版）`/`批发销售单（颜色版）新版` 都在、旧版未动、`Pick List.default_print_format = 拣货单（颜色版）`。
- **进程新鲜度**：文件 14:24:05 写入，gunicorn master + 5 workers 与两个后台 worker 14:27:48 启动（晚于文件），无需再重启。
- 11 个测试全绿；手册与发布白名单同步。

### 19.22 已确认业务规则（统一摘要）

以下为仍有效的用户确认，作为搜索入口；详细实现与生产状态见本手册对应章节。Obsidian ERP 笔记仅作原始讨论参考，若与本节冲突，以较新的明确确认及生产回读为准。

- Solua Home 是批发商，从中国进口至莫桑比克，按客户订单配送到客户指定门店；一个客户可维护多个门店及各自地址、联系人和电话。
- 窗帘按条、窗帘杆按根、地板革按卷，不裁切；交易数量为整数。窗帘按颜色分别建变体并记录库存，颜色号由负责人按实物/供应商色卡手动选择，保留前导零；供应商共用包装条码用于识别款式，业务行必须指向具体颜色变体。不得把货号冒充条码或自动猜色。
- 入库成本由用户提供已计算完成的最终单位成本；不额外分摊运费、清关费。缺货时修改订购数量，不把欠货默认保留为待补送。
- 同时需要 Sales Order 订单确认单与 Delivery Note / `Guia de Remessa`。允许因车辆装载量分批交付；订单数量、本次交付数量及已交付/剩余量应语义分明。正式送货记录应保留实际客户门店地址、司机/车辆、销售订单和发票关联或后续开票安排，并提供签收及差异备注位置；客户 NUIT 仅在已知时填写。
- 支持先付款、货到付款、赊账及定金加尾款；使用 ERPNext 原生 Payment Entry/预收款/核销链路，不将订金重复记作收入。
- 首页供员工共用但按权限展示，优先呈现经营数据并保留常用操作入口；xPos 入口保留。具体页面和未完验收状态见 19.10、19.16、19.18。

### 19.23 文档来源与维护

- ERPNext / Solua Home 的开发流程、业务决定和生产核验以本手册为准，不再维护独立的首页或色卡实施计划副本。
- xPos 诊断与客户端修复按日期记在 `xpos-client/OPERATIONS_HISTORY.md`；`xpos-client/baseline-manifest.md` 仍单独保留，用于安装包基线与校验值，不和事件报告混合。
- `local-customization-audit-20260918.md` 是有独立审计证据的历史审计；`transaction-deletion-import-logic-summary.md` 描述另一项独立功能逻辑，暂保留。
- Obsidian ERP 笔记可作为需求讨论的原始来源，但内容可能过时；只把后来确认且仍有效的决定整理进本手册。Obsidian 原文件不由本次整理修改，密码、密钥等文件不引用、不复制、不上传。
- 旧首页/色卡计划、会话摘要及三份 xPos 分散报告从当前文档树移除；其已合并内容仍可在 Git 历史中查阅。

### 19.21 2026-09-23 物料批量改价：普通物料预览的 dict 属性错误

物料列表的「批量修改物料价格」支持两种目标：选择普通在售物料时只处理该 Item；选择启用模板时预览并处理其启用、可销售变体。共用计划函数 `_get_plan()` 中，模板分支的 `frappe.get_all()` 返回字典式记录，普通物料分支也手动构造普通 Python 字典。若写成 `item.name`，普通物料会在预览时触发 `AttributeError: 'dict' object has no attribute 'name'`，还没进入价格写入步骤。

#### 开发经验

- `frappe.get_doc()` 返回 Document，可按属性访问；`frappe.get_all()` 的结果及代码手动构造的记录应按 mapping 访问。混合两类来源时，统一用 `item["name"]`、`row["currency"]` 等键访问，避免只在普通物料或模板路径出错。
- 复用同一计划函数的分支都要覆盖：至少分别验证普通物料和模板变体预览；价格记录要覆盖无记录、新建计划和唯一现有记录更新计划。预览错误必须发生在任何写入之前。
- 本次修复已在生产部署，普通物料与模板路径的隔离回归检查通过。生产文件 SHA256：`5c9319bda15cb7dc17de81441d8ae4d93a12dd4835fe0fbd32e3fc1b2dc17c77`；变更前代码副本：`sites/erp.solua.one/private/code-backups/20260923-bulk-variant-price/item_price_bulk.py.v2.before-dict-fix`。只重启服务并清缓存，未跑迁移、未更改任何 Item Price 数据。
