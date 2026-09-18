xPos Till Windows 安装包

安装前提
- Windows 10/11 64 位，并使用管理员账户。
- 先完成 Hub 安装并确认 Hub 主机的 6789 端口可达。
- 本包固定使用 MariaDB 11.4.13、3307 端口，以及 Hub 6789 端口。

安装
1. 解压 ZIP 到临时目录。
2. 右键 Install-XPos-Till.ps1，选择“使用 PowerShell 运行”，并确认管理员权限。
3. 脚本只会要求输入 Hub 主机 IPv4 地址；它会先测试 http://Hub-IP:6789/api/health。
4. 验证成功后，脚本才会写入 Hub 配置并安装本机 Till。
5. 安装完成后，从桌面的“X POS Till”启动。

安装程序会在发现 C:\xpos 时先移动为 C:\xpos.backup-时间戳，不会直接删除。若安装中断，可从该备份恢复旧程序；已有用户数据库配置也会复制到备份目录的 user-data 子目录。

首次启动
- Till 自动使用本机 MariaDB 作为缓存和离线队列。
- Till 自动生成本机 Till ID。
- 首次启动直接显示 xPos 登录页，不进入 Setup Wizard。
- 本包不包含 ERPNext API Key 或 API Secret。

注意
- 关闭正在运行的 X POS 后再重新安装。
- Hub IP 变更后，需要重新运行 Till 安装脚本以更新本机 Hub 地址。
- 本包不包含测试订单或测试收银员账户。
