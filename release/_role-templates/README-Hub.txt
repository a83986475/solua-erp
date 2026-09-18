xPos Hub Windows 安装包

安装前提
- Windows 10/11 64 位，并使用管理员账户。
- Hub 主机应连接到门店局域网；安装程序会自动选择可用局域网 IPv4。
- 本包固定使用 MariaDB 11.4.13、3307 端口，以及 Hub 6789 端口。

安装
1. 解压 ZIP 到临时目录。
2. 将外置提供的 XPOS-HUB-KEY.json 复制到 U 盘根目录；安装时必须插入该 U 盘。若需从已有 xPos 主机生成此文件，请在原 xPos Windows 用户下运行 release\_role-templates\Build-XPos-RolePackages.ps1，脚本会生成 release\XPos-Hub-Key\XPOS-HUB-KEY.json；不要把它放入安装 ZIP。
3. 右键 Install-XPos-Hub.ps1，选择“使用 PowerShell 运行”，并确认管理员权限。
4. 安装完成后，从桌面的“X POS Hub”启动。

安装程序会在发现 C:\xpos 时先移动为 C:\xpos.backup-时间戳，不会直接删除。若安装中断，可从该备份恢复旧程序；已有用户数据库配置也会复制到备份目录的 user-data 子目录。

首次启动
- Hub 端口固定为 6789，不需要填写端口。
- 本机数据库和所需表会自动创建。
- 首次启动直接显示 xPos 登录页，不进入 Setup Wizard。
- 安装器从已插入的 Hub 配置 U 盘读取现有同步凭据，并在目标主机本地受保护保存；脚本、README、日志和界面不会显示凭据。
- 若生成器提示“同机继承模式”，说明 U 盘文件保留的是原 xPos 的 Electron 本地密文；该模式不含明文密钥，只能在原 Windows 主机和原 Windows 用户下安装 Hub。

局域网使用
- 安装完成后可查看 C:\xpos\Hub-Address.txt 获取当前 Hub 地址。
- Till 安装时只需输入该文件中的 IPv4 地址；端口仍固定为 6789。
- Hub 主机和 Till 主机应位于同一可互通的局域网，Windows 网络配置建议设为“专用”。

注意
- 关闭正在运行的 X POS 后再重新安装。
- XPOS-HUB-KEY.json 不在安装 ZIP 内；安装 Hub 时必须插入包含该文件的 U 盘。
- 安装完成后可以拔出 U 盘；Hub 日常运行不需要 U 盘。
- 本包不包含测试订单或测试收银员账户。
