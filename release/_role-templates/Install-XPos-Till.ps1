param(
    [string]$HubIp,
    [string]$InstallPath = "C:\xpos"
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "请以管理员身份运行此脚本。"
    }
}

function New-RandomHex {
    param([int]$Bytes = 24)
    $buffer = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($buffer)).Replace("-", "").ToLowerInvariant()
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutMs = 3000
    )
    $client = New-Object Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait($TimeoutMs)) { return $false }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Wait-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$Seconds = 60
    )
    for ($i = 0; $i -lt ($Seconds * 2); $i++) {
        if (Test-TcpPort -HostName $HostName -Port $Port -TimeoutMs 1000) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Assert-IPv4 {
    param([Parameter(Mandatory = $true)][string]$Value)
    $address = $null
    if (-not [Net.IPAddress]::TryParse($Value, [ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
        throw "Hub IP 必须是 IPv4 地址。"
    }
    return $address.ToString()
}

function Test-Hub {
    param([Parameter(Mandatory = $true)][string]$Ip)
    $uri = "http://${Ip}:6789/api/health"
    if (-not (Test-TcpPort -HostName $Ip -Port 6789 -TimeoutMs 5000)) {
        throw "Hub ${Ip}:6789 不可达；未写入 Till 配置。"
    }
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 5
        $body = $response.Content | ConvertFrom-Json
        if ($response.StatusCode -ne 200 -or $body.status -ne "ok" -or $body.role -ne "hub") { throw "health check failed" }
    } catch {
        throw "Hub ${Ip}:6789 不是可用的 xPos Hub；未写入 Till 配置。"
    }
}

function Find-MySqlClient {
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "MariaDB 11.4\bin\mysql.exe"),
        (Join-Path ${env:ProgramFiles} "MariaDB 11.4\bin\mariadb.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "MariaDB 11.4\bin\mysql.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "MariaDB 11.4\bin\mariadb.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    foreach ($name in @("mysql.exe", "mariadb.exe")) {
        try {
            $command = Get-Command $name -ErrorAction Stop
            if ($command.Source) { return $command.Source }
        } catch {}
    }
    throw "未找到 MariaDB 客户端。"
}

function Protect-LocalSecret {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value -like "enc:v1:*") { return $Value }
    try {
        Add-Type -AssemblyName System.Security
        $plain = [Text.Encoding]::UTF8.GetBytes($Value)
        $cipher = [Security.Cryptography.ProtectedData]::Protect($plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        return "enc:v1:" + [Convert]::ToBase64String($cipher)
    } catch {
        return $Value
    }
}

function Unprotect-LocalSecret {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value -or $Value -notlike "enc:v1:*") { return $Value }
    try {
        Add-Type -AssemblyName System.Security
        $cipher = [Convert]::FromBase64String($Value.Substring(7))
        $plain = [Security.Cryptography.ProtectedData]::Unprotect($cipher, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        return [Text.Encoding]::UTF8.GetString($plain)
    } catch {
        return $null
    }
}

function Invoke-MySql {
    param(
        [Parameter(Mandatory = $true)][string]$MysqlPath,
        [Parameter(Mandatory = $true)][string]$User,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Password,
        [Parameter(Mandatory = $true)][string]$Sql,
        [string]$Database
    )
    $defaults = Join-Path $env:TEMP ("xpos-mariadb-" + [guid]::NewGuid().ToString("N") + ".cnf")
    $content = "[client]`r`nuser=$User`r`npassword=$Password`r`nhost=127.0.0.1`r`nport=3307`r`nprotocol=tcp`r`nskip-ssl`r`n"
    [IO.File]::WriteAllText($defaults, $content)
    try {
        $arguments = "--defaults-extra-file=`"$defaults`" --batch --skip-column-names"
        if ($Database) { $arguments += " --database=$Database" }
        $startInfo = New-Object Diagnostics.ProcessStartInfo
        $startInfo.FileName = $MysqlPath
        $startInfo.Arguments = $arguments
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardInput = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $process = New-Object Diagnostics.Process
        $process.StartInfo = $startInfo
        [void]$process.Start()
        $process.StandardInput.Write($Sql)
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) { throw "MariaDB 操作失败（代码 $($process.ExitCode)）。" }
        return $stdout
    } finally {
        Remove-Item -LiteralPath $defaults -Force -ErrorAction SilentlyContinue
    }
}

function Get-ExistingDbConfig {
    $paths = @(
        (Join-Path $env:APPDATA "X POS\db-config.json"),
        (Join-Path $env:APPDATA "xpos-frontend\db-config.json")
    )
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        try {
            $config = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
            if ($config.host -eq "127.0.0.1" -and [int]$config.port -eq 3307 -and $config.user -and $config.database -eq "xpos_local") {
                return $config
            }
        } catch {}
    }
    return $null
}

function Ensure-MariaDb {
    param([Parameter(Mandatory = $true)][string]$MsiPath)
    $service = Get-Service -Name MariaDB -ErrorAction SilentlyContinue
    $fresh = $false
    $rootPassword = $null
    if (-not $service) {
        if (Test-TcpPort -HostName "127.0.0.1" -Port 3307) {
            throw "端口 3307 已被占用，但未找到 MariaDB 服务。"
        }
        if (-not (Test-Path -LiteralPath $MsiPath)) { throw "安装包内缺少 MariaDB 安装文件。" }
        $rootPassword = New-RandomHex -Bytes 24
        $msiArgs = @(
            "/i", ('"{0}"' -f $MsiPath), "/qn", "/norestart",
            "PASSWORD=$rootPassword", "PORT=3307", "SERVICENAME=MariaDB",
            "ALLOWREMOTEROOTACCESS=0", "UTF8=1"
        )
        $result = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -ArgumentList $msiArgs -Wait -PassThru -WindowStyle Hidden
        if ($result.ExitCode -notin @(0, 3010)) { throw "MariaDB 安装失败（代码 $($result.ExitCode)）。" }
        $fresh = $true
        $service = Get-Service -Name MariaDB -ErrorAction SilentlyContinue
    }
    if (-not $service) { throw "MariaDB 服务未创建。" }
    if ($service.Status -ne "Running") { Start-Service -Name MariaDB }
    if (-not (Wait-TcpPort -HostName "127.0.0.1" -Port 3307)) { throw "MariaDB 未能在端口 3307 启动。" }
    return [pscustomobject]@{ Fresh = $fresh; RootPassword = $rootPassword; Mysql = (Find-MySqlClient) }
}

function Sql-Literal {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) { return "NULL" }
    return "'" + $Value.Replace("\", "\\").Replace("'", "''") + "'"
}

function Protect-ConfigFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @("S-1-5-32-544", "S-1-5-18")) {
        $identity = New-Object Security.Principal.SecurityIdentifier($sid)
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity, "FullControl", "Allow")
        $acl.AddAccessRule($rule)
    }
    $userRule = New-Object Security.AccessControl.FileSystemAccessRule([Security.Principal.WindowsIdentity]::GetCurrent().User, "FullControl", "Allow")
    $acl.AddAccessRule($userRule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Write-DbConfig {
    param([Parameter(Mandatory = $true)][string]$Password)
    $config = [ordered]@{
        host = "127.0.0.1"
        port = 3307
        user = "xpos"
        password = Protect-LocalSecret -Value $Password
        database = "xpos_local"
    }
    $json = $config | ConvertTo-Json
    foreach ($path in @(
        (Join-Path $env:APPDATA "X POS\db-config.json"),
        (Join-Path $env:APPDATA "xpos-frontend\db-config.json")
    )) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force | Out-Null
        [IO.File]::WriteAllText($path, $json)
        Protect-ConfigFile -Path $path
    }
}

function Backup-ExistingInstall {
    param([Parameter(Mandatory = $true)][string]$Path)
    $existingConfigs = @(
        (Join-Path $env:APPDATA "X POS\db-config.json"),
        (Join-Path $env:APPDATA "xpos-frontend\db-config.json")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    if (Get-Process -Name "X POS" -ErrorAction SilentlyContinue) { throw "请先退出正在运行的 X POS。" }
    $backup = "$Path.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    while (Test-Path -LiteralPath $backup) { $backup += "-1" }
    Move-Item -LiteralPath $Path -Destination $backup
    if ($existingConfigs) {
        $configDir = Join-Path $backup "user-data"
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        foreach ($config in $existingConfigs) { Copy-Item -LiteralPath $config -Destination $configDir -Force }
    }
    return $backup
}

function Install-AppFiles {
    param([Parameter(Mandatory = $true)][string]$Path)
    $source = Join-Path $PSScriptRoot "app"
    if (-not (Test-Path -LiteralPath (Join-Path $source "X POS.exe"))) { throw "安装包内缺少 X POS.exe。" }
    Copy-Item -LiteralPath $source -Destination $Path -Recurse
    if (-not (Test-Path -LiteralPath (Join-Path $Path "resources\app.asar"))) { throw "X POS 程序文件校验失败。" }
}

function New-DesktopShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $desktop ($Name + ".lnk")))
    $shortcut.TargetPath = Join-Path $Path "X POS.exe"
    $shortcut.WorkingDirectory = $Path
    $shortcut.IconLocation = "$($shortcut.TargetPath),0"
    $shortcut.Save()
}

function Seed-TillDatabase {
    param(
        [Parameter(Mandatory = $true)]$MariaDb,
        [Parameter(Mandatory = $true)]$Seed,
        [Parameter(Mandatory = $true)][string]$HubUrl,
        [Parameter(Mandatory = $true)][string]$TillId,
        [Parameter(Mandatory = $true)][string]$SchemaPath
    )
    $existing = Get-ExistingDbConfig
    $seedLines = @(
        "INSERT INTO ``sync_meta`` (``key``,``value``,``updated_at``) VALUES (" + (Sql-Literal "node_role") + "," + (Sql-Literal "till") + ",NOW()) ON DUPLICATE KEY UPDATE ``value``=VALUES(``value``),``updated_at``=NOW();",
        "INSERT INTO ``sync_meta`` (``key``,``value``,``updated_at``) VALUES (" + (Sql-Literal "hub_url") + "," + (Sql-Literal $HubUrl) + ",NOW()) ON DUPLICATE KEY UPDATE ``value``=VALUES(``value``),``updated_at``=NOW();",
        "INSERT INTO ``sync_meta`` (``key``,``value``,``updated_at``) VALUES (" + (Sql-Literal "till_id") + "," + (Sql-Literal $TillId) + ",NOW()) ON DUPLICATE KEY UPDATE ``value``=VALUES(``value``),``updated_at``=NOW();",
        "INSERT INTO ``sync_meta`` (``key``,``value``,``updated_at``) VALUES (" + (Sql-Literal "hub_api_secret") + "," + (Sql-Literal ([string]$Seed.hub_access_token)) + ",NOW()) ON DUPLICATE KEY UPDATE ``value``=VALUES(``value``),``updated_at``=NOW();"
    )
    $schema = (Get-Content -Raw -LiteralPath $SchemaPath).TrimEnd()
    if (-not $schema.EndsWith(";")) { $schema += ";" }
    $sql = $schema + [Environment]::NewLine + ($seedLines -join [Environment]::NewLine)

    if ($MariaDb.Fresh) {
        $dbPassword = New-RandomHex -Bytes 24
        $provision = "CREATE DATABASE IF NOT EXISTS ``xpos_local`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`r`n" +
            "CREATE USER IF NOT EXISTS 'xpos'@'127.0.0.1' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "CREATE USER IF NOT EXISTS 'xpos'@'localhost' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "ALTER USER 'xpos'@'127.0.0.1' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "ALTER USER 'xpos'@'localhost' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "GRANT ALL PRIVILEGES ON ``xpos_local``.* TO 'xpos'@'127.0.0.1';`r`n" +
            "GRANT ALL PRIVILEGES ON ``xpos_local``.* TO 'xpos'@'localhost';`r`nFLUSH PRIVILEGES;"
        Invoke-MySql -MysqlPath $MariaDb.Mysql -User "root" -Password $MariaDb.RootPassword -Sql $provision | Out-Null
        Invoke-MySql -MysqlPath $MariaDb.Mysql -User "root" -Password $MariaDb.RootPassword -Database "xpos_local" -Sql $sql | Out-Null
        Write-DbConfig -Password $dbPassword
        return $true
    }

    $existingPassword = if ($existing -and $existing.password) { Unprotect-LocalSecret -Value ([string]$existing.password) } else { $null }
    if ($existing -and $existingPassword) {
        try {
            Invoke-MySql -MysqlPath $MariaDb.Mysql -User ([string]$existing.user) -Password $existingPassword -Database "xpos_local" -Sql $sql | Out-Null
            Write-DbConfig -Password $existingPassword
            return $true
        } catch {}
    }

    try {
        Invoke-MySql -MysqlPath $MariaDb.Mysql -User "root" -Password "" -Sql "SELECT 1" | Out-Null
        $dbPassword = New-RandomHex -Bytes 24
        $provision = "CREATE DATABASE IF NOT EXISTS ``xpos_local`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`r`n" +
            "CREATE USER IF NOT EXISTS 'xpos'@'127.0.0.1' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "CREATE USER IF NOT EXISTS 'xpos'@'localhost' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "ALTER USER 'xpos'@'127.0.0.1' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "ALTER USER 'xpos'@'localhost' IDENTIFIED BY " + (Sql-Literal $dbPassword) + ";`r`n" +
            "GRANT ALL PRIVILEGES ON ``xpos_local``.* TO 'xpos'@'127.0.0.1';`r`n" +
            "GRANT ALL PRIVILEGES ON ``xpos_local``.* TO 'xpos'@'localhost';`r`nFLUSH PRIVILEGES;"
        Invoke-MySql -MysqlPath $MariaDb.Mysql -User "root" -Password "" -Sql $provision | Out-Null
        Invoke-MySql -MysqlPath $MariaDb.Mysql -User "root" -Password "" -Database "xpos_local" -Sql $sql | Out-Null
        Write-DbConfig -Password $dbPassword
        return $true
    } catch {}

    if ($existing) {
        Write-Host "检测到已有 xPos 数据库配置，已保留其受保护配置；未覆盖已有数据库。"
        return $false
    }
    throw "MariaDB 已存在但无法安全取得管理员连接；未写入 xPos 配置。"
}

Assert-Administrator
if ([string]::IsNullOrWhiteSpace($HubIp)) { $HubIp = Read-Host "请输入 Hub 主机 IPv4 地址" }
$HubIp = Assert-IPv4 -Value $HubIp
Test-Hub -Ip $HubIp
$hubUrl = "http://${HubIp}:6789"
$computer = if ($env:COMPUTERNAME) { $env:COMPUTERNAME.ToUpperInvariant() } else { "PC" }
$computer = [regex]::Replace($computer, "[^A-Z0-9_-]", "-")
if ($computer.Length -gt 60) { $computer = $computer.Substring(0, 60) }
$tillId = "TILL-$computer"
$seedPath = Join-Path $PSScriptRoot "bootstrap\till-seed.json"
$schemaPath = Join-Path $PSScriptRoot "app\resources\schema.sql"
$mariadbPath = Join-Path $PSScriptRoot "dependencies\mariadb-11.4.13-winx64.msi"
if (-not (Test-Path -LiteralPath $seedPath)) { throw "安装包内缺少 Till bootstrap 文件。" }
$seed = Get-Content -Raw -LiteralPath $seedPath | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$seed.hub_access_token)) { throw "Till bootstrap 文件不是有效配置。" }
$backup = Backup-ExistingInstall -Path $InstallPath
$mariadb = Ensure-MariaDb -MsiPath $mariadbPath
$seeded = Seed-TillDatabase -MariaDb $mariadb -Seed $seed -HubUrl $hubUrl -TillId $tillId -SchemaPath $schemaPath
if (-not $seeded -and -not (Test-Path -LiteralPath (Join-Path $env:APPDATA "X POS\db-config.json"))) {
    throw "未能建立 xPos 数据库配置。"
}
Install-AppFiles -Path $InstallPath
New-DesktopShortcut -Path $InstallPath -Name "X POS Till"
Write-Host "xPos Till 已安装到 $InstallPath。"
Write-Host "已验证 Hub：${hubUrl}；Till ID：$tillId。"
if ($backup) { Write-Host "原有安装已备份到 $backup。" }
Write-Host "首次启动将直接进入 xPos 登录页；本包不含 ERPNext API 凭据。"
