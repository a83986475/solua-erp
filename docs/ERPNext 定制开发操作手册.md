# ERPNext 定制开发操作手册

> 版本: v16 | 最后更新: 2026-08-06 | 基于真实安装经验编写

> 🔄 **2026-08-06 变更记录：App 重命名 my_custom_app → solua_home**
> - **模块名**：`my_custom_app` → `solua_home`（Python 包名规范：小写+下划线，无空格）
> - **GitHub 仓库**：`a83986475/erpnext-apps` → **`a83986475/solua-erp`**（旧 URL 自动重定向）
> - **正式元数据**：app_title=`Solua Home 定制`、publisher=`Solua Home, Lda`、email=`admin@solua.one`
> - **影响面**：代码内 42 处引用、服务器 `apps/solua_home` 目录、`apps.txt`/`apps.json`/symlink、`tabInstalled Application`、`tabDefaultValue.installed_apps`（踩坑点：漏改会导致 `No module named 'my_custom_app'`）
> - **状态**：本地示例副本 / GitHub `721e541` / 服务器三处一致，POS 扫码选色与 get_items 拦截已验证生效
> - ⚠️ 本文档后续命令/路径中的 `solua_home` 即为当前模块名（历史操作如 `bench new-app solua_home` 按新名执行即可）

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
9. [常用命令速查](#9-常用命令速查)
10. [安装问题排查](#10-安装问题排查)
11. [服务器运维问题排查](#11-服务器运维问题排查)
12. [WSL2 开发环境问题排查](#12-wsl2开发环境问题排查)
13. [自定义 App 开发问题排查](#13-自定义-app-开发问题排查)
14. [开发问题排查](#14-开发问题排查)

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

**Docker 自启状态**（实测确认，无需再动）：

| 单元 | 自启 | 说明 |
|------|------|------|
| `docker.service` | disabled | 已禁用 |
| `docker.socket` | disabled | 已禁用（否则 socket 激活会在有客户端连接时自动拉起 dockerd） |
| `containerd.service` | disabled | 已禁用 |

禁用命令（需要 root，用 `wsl -u root -e` 执行）：

```bash
wsl -u root -e systemctl disable --now docker containerd
wsl -u root -e systemctl disable --now docker.socket
```

**验证**：`wsl -e bash -lc "systemctl is-enabled docker docker.socket containerd"` 应全部输出 `disabled`；`docker ps` 报 `Cannot connect to the Docker daemon` 即为正常（无自启）。

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
> # 在服务器 bench 目录执行（确保用 Node 24，见 11.6 节）
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

> ⚠️ 若使用真实 EAN 条码，注意 `Code128` 类型可绕过校验（见 6.5.2）。新 Variant 的条码：颜色 Variant 一般不需要独立条码（条码在模板上，扫码弹窗选色），如个别颜色需要独立条码可单独加。

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

## 9. 常用命令速查

### 9.1 环境管理

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

### 9.2 Bench 命令

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

### 9.3 调试命令

```bash
bench --site dev.localhost run-tests            # 运行测试
bench --site dev.localhost run-tests --module solua_home.tests  # 运行指定测试
bench console                                    # Python shell
bench --site dev.localhost export-fixtures       # 导出 fixtures
```

### 9.4 站点管理

```bash
bench new-site site-name                    # 创建新站点
bench --site site-name reinstall            # 重新安装
bench drop-site site-name                   # 删除站点
bench --site site-name list-apps            # 列出已安装 app
bench --site site-name backup               # 备份
bench --site site-name restore 备份文件路径   # 恢复
```

---

## 10. 安装问题排查

### 10.1 pip3 install 报 `externally-managed-environment`

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

### 10.2 bench init 报 `No such file or directory: 'uv'`

**错误信息**：`FileNotFoundError: [Errno 2] No such file or directory: 'uv'`

**原因**：bench 5.x 使用 `uv` 管理虚拟环境，但系统未安装。

**解决**：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version   # 验证
```

### 10.3 bench init 报 `pkg-config is not installed`

**错误信息**：`pkg-config is not installed. Please install it before proceeding.`

**原因**：编译 frappe 的 Python 依赖时需要 `pkg-config`。Ubuntu 24.04 默认未安装。

**解决**：
```bash
sudo apt install -y pkg-config
```

### 10.4 bench init 报 `Python>=3.14,<3.15` 不满足

**错误信息**：`Because the current Python version (3.12.3) does not satisfy Python>=3.14`

**原因**：ERPNext v16 的 `version-16` 分支最新版要求 Python 3.14+。

**解决**：
```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.14 python3.14-dev python3.14-venv
# 然后 bench init 时指定 python3.14
bench init frappe-bench --frappe-branch version-16 --python python3.14
```

### 10.5 bench build 报 `Expected node >=24`

**错误信息**：`The engine "node" is incompatible with this module. Expected version ">=24"`

**原因**：ERPNext v16 最新版要求 Node 24+。

**解决**：
```bash
nvm install 24
nvm alias default 24
node --version   # 验证为 v24.x.x
```

### 10.6 使用 root 用户操作导致的权限问题

**问题**：用 `sudo bench init` 后，文件所有者变为 root，普通用户无法编辑。

**解决**：
```bash
# 退出 root
exit
# 重新以普通用户操作
# 如果已经用了 sudo bench init，需要改回权限
sudo chown -R $(whoami):$(whoami) ~/frappe-bench
```

### 10.7 安装过程中断后重试

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

## 11. 服务器运维问题排查

### 11.1 supervisor 没有加载 frappe 进程组

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

### 11.2 nginx 配置检查

```bash
# 检查 nginx 配置是否正确
sudo nginx -t

# 重新加载 nginx
sudo systemctl reload nginx
```

### 11.3 站点维护模式

```bash
# 检查站点状态
bench --site your-site doctor

# 关闭维护模式（如果站点显示维护中）
bench --site your-site set-maintenance-mode off
```

### 11.4 服务器备份与恢复

```bash
# 备份单个站点
bench --site your-site backup

# 备份所有站点
bench --site all backup

# 备份文件位置：~/frappe-bench/sites/your-site/private/backups/

# 恢复站点
bench --site your-site restore /path/to/backup/file.sql.gz
```

### 11.5 服务器中文翻译不生效

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

### 11.6 服务器 Node 版本切换

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

## 12. 开发问题排查

### 12.1 WSL2 中 supervisor 警告（正常现象）

**问题现象**：在 WSL2 开发环境中执行 `bench build` 或 `bench restart` 时，看到：
```
WARN: restarting supervisor group `frappe:` failed. Use `bench restart` to retry.
```

**原因**：这是**正常的**。WSL2 开发环境使用 `bench start` 直接启动开发服务器，不依赖 supervisor。这条警告只是因为 bench 尝试重启 supervisor 管理下的进程，但在开发环境中 supervisor 没有被配置。

**处理**：忽略即可。开发时用 `bench start` 启动服务，这个警告不影响任何功能。

### 12.2 bench build 报 "Assets for Release ... don't exist"

**问题现象**：
```
Assets for Release v16.27.0 don't exist
✔ Application Assets Linked
```

**原因**：这是**正常的**。开发模式下没有预构建的生产环境静态资源包，bench 自动将源码链接为资产。

**处理**：无需处理。生产部署时才需要构建完整的资产包。

---

## 13. 自定义 App 开发问题排查

### 13.1 手动创建 App 后 `install-app` 报 `No module named 'X'`

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

### 13.2 `setup.py` 和 `install.py` 的冲突

**问题**：Frappe App 有两个用途不同的 `setup.py`：
1. Python 打包配置（`from setuptools import setup, find_packages`）—— 在 App 根目录
2. Frappe 安装/迁移钩子（`after_install`, `add_translations`）—— 在模块内部

**如果两者重名**，Python 打包时会找不到包。**解决方案**：把 Frappe 安装函数改名为 `install.py`，并更新 `hooks.py` 引用：
```python
# hooks.py 中
after_install = "solua_home.install.after_install"   # 指向 install.py
after_migrate = "solua_home.install.after_migrate"  # 指向 install.py
```

### 13.3 Translation 字段名变更

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

### 13.4 `notification_config` 导致 migrate 失败

**问题**：migrate 时报 `ValueError: dictionary update sequence element`

**原因**：`hooks.py` 中的 `notification_config` 指向一个不存在或返回值格式错误的函数。

**解决**：如果不需要自定义通知，直接删除 hooks.py 中的 `notification_config` 行：
```python
# 删除这行
notification_config = "solua_home.config.notifications.get_notification_config"
```

### 13.5 `sites/apps.json` 注册

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

### 13.6 Redis 端口冲突：`Address already in use`

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

### 13.7 `bench start` 闪退：Scheduler 退出导致全部进程关闭

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

### 13.8 `start.sh` PATH 中 Windows 路径导致语法错误

**问题现象**：运行 `start.sh` 报 `syntax error near unexpected token ('`

**原因**：`export PATH="$HOME/.local/bin:$PATH"` 中 `$PATH` 展开后包含 Windows 路径的括号 `Program Files (x86)`，Shell 语法解析失败。

**解决**：设置干净的 PATH，不引用 `$PATH`：
```bash
export PATH=/home/yang/.local/bin:/home/yang/.nvm/versions/node/v24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### 13.9 新开 WSL 终端后 `node` 找不到

**问题现象**：新开 WSL 终端后 `bench start` 报 `node: not found`

**原因**：nvm 的配置在 `.bashrc` 中，新终端需要手动加载

**解决**：在 `start.sh` 中添加 nvm 加载：
```bash
export NVM_DIR=/home/yang/.nvm
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

## 14. 开发问题排查

### 14.1 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8000

# 换端口启动
bench start --port 8001
```

### 14.2 数据库连接失败

```bash
# 检查 MariaDB 是否在运行
sudo service mariadb status

# 启动 MariaDB
sudo service mariadb start

# 手动连接测试
sudo mysql -u root -p
```

### 14.3 缓存问题

```bash
# 开发时发现修改没生效，先清缓存
bench --site dev.localhost clear-cache

# 如果还不行，重建前端
bench build
```

### 14.4 Python 调试

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

### 14.5 JavaScript 调试

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

## 💡 最后提醒

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

> 📝 **备忘：当前环境信息**
>
> - 服务器: Ubuntu 24.04（通过 bench 直接安装，supervisor + nginx）
> - 本地开发: WSL2 (Windows 11 + Ubuntu 24.04)
> - ERPNext 版本: v16（`version-16` 分支）
> - Python: 3.14.x（通过 deadsnakes PPA 安装）
> - Node.js: 24.x（通过 nvm 管理，服务器 system node 仍为 v20）
> - bench: 5.31.0（通过 pipx 安装）
> - 自定义 App 名: `solua_home`
> - 开发站点: `dev.localhost:8000`
> - 生产站点: `erp.solua.one`
> - SSH: `ssh qq`（用户 ubuntu，sudo 免密）
> - GitHub: `https://github.com/a83986475/solua-erp.git`（原 erpnext-apps，2026-08-06 改名）
