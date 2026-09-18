param(
    [string]$SourceRootPassword,
    [string]$HubKeyOutput,
    [string]$HubKeyInputPath
)

$ErrorActionPreference = "Stop"
$release = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$common = Join-Path $release "xpos-windows"
$hubDir = Join-Path $release "XPos-Hub-Setup"
$tillDir = Join-Path $release "XPos-Till-Setup"
$hubZip = Join-Path $release "XPos-Hub-Setup.zip"
$tillZip = Join-Path $release "XPos-Till-Setup.zip"
$hubKeyOutputPath = $HubKeyOutput
if (-not [string]::IsNullOrWhiteSpace($hubKeyOutputPath) -and $hubKeyOutputPath -match "^[A-Za-z]:$") { $hubKeyOutputPath += "\" }
$hubKeyBase = if ([string]::IsNullOrWhiteSpace($hubKeyOutputPath)) { Join-Path $release "XPos-Hub-Key" } else { [IO.Path]::GetFullPath($hubKeyOutputPath) }
$hubKeyFile = if ([IO.Path]::GetExtension($hubKeyBase) -ieq ".json") { $hubKeyBase } else { Join-Path $hubKeyBase "XPOS-HUB-KEY.json" }
$msi = "E:\IDM\Compressed\mariadb-11.4.13-winx64.msi"

if (-not (Test-Path -LiteralPath (Join-Path $common "app\resources\app.asar"))) { throw "通用 app.asar 不存在。" }
if (-not (Test-Path -LiteralPath $msi)) { throw "MariaDB MSI 不存在。" }

if ([string]::IsNullOrWhiteSpace($HubKeyInputPath) -and [string]::IsNullOrWhiteSpace($SourceRootPassword)) {
    $context = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $release "..\chatgpt-context.md")
    $match = [regex]::Match($context, "MariaDB\s*根密码\s*[:：]\s*(\S+)")
    if (-not $match.Success) { throw "无法读取本机 MariaDB 管理连接。" }
    $SourceRootPassword = $match.Groups[1].Value
}

function Find-NodeClient {
    $candidates = @()
    try {
        $command = Get-Command node.exe -ErrorAction Stop
        if ($command.Source) { $candidates += $command.Source }
    } catch {}
    $candidates += @(
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe"
    )
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    throw "构建机缺少 Node.js，无法读取 Electron 本地受保护配置。"
}

function Unprotect-DpapiBytes {
    param([Parameter(Mandatory = $true)][byte[]]$Cipher)
    Add-Type -AssemblyName System.Security
    return [Security.Cryptography.ProtectedData]::Unprotect($Cipher, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
}

function Get-ElectronSafeStorageKey {
    $paths = @(
        (Join-Path $env:APPDATA "xpos-frontend\Local State"),
        (Join-Path $env:APPDATA "X POS\Local State")
    )
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        try {
            $state = Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
            $encoded = [string]$state.os_crypt.encrypted_key
            if ([string]::IsNullOrWhiteSpace($encoded)) { continue }
            $wrapped = [Convert]::FromBase64String($encoded)
            if ($wrapped.Length -le 5 -or [Text.Encoding]::ASCII.GetString($wrapped, 0, 5) -ne "DPAPI") { continue }
            $cipher = New-Object byte[] ($wrapped.Length - 5)
            [Array]::Copy($wrapped, 5, $cipher, 0, $cipher.Length)
            $key = Unprotect-DpapiBytes -Cipher $cipher
            if ($key.Length -eq 32) { return $key }
        } catch {}
    }
    throw "无法在当前 Windows 用户下读取 Electron 本地加密密钥；请使用创建原 xPos 配置的同一 Windows 用户运行。"
}

function Unprotect-SourceSecret {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][byte[]]$SafeStorageKey,
        [Parameter(Mandatory = $true)][string]$NodePath
    )
    if ($Value -notlike "enc:v1:*") { return $Value }
    try {
        $raw = [Convert]::FromBase64String($Value.Substring(7))
        $version = if ($raw.Length -ge 3) { [Text.Encoding]::ASCII.GetString($raw, 0, 3) } else { "" }
        if ($version -notin @("v10", "v11")) {
            return [Text.Encoding]::UTF8.GetString((Unprotect-DpapiBytes -Cipher $raw))
        }
        $payload = [ordered]@{
            key = [Convert]::ToBase64String($SafeStorageKey)
            value = [Convert]::ToBase64String($raw)
        } | ConvertTo-Json -Compress
        $nodeScript = @'
const crypto = require("crypto");
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const raw = Buffer.from(input.value, "base64");
const key = Buffer.from(input.key, "base64");
if (raw.length < 3 + 12 + 16 || key.length !== 32) process.exit(2);
const nonce = raw.subarray(3, 15);
const body = raw.subarray(15);
const tag = body.subarray(body.length - 16);
const ciphertext = body.subarray(0, body.length - 16);
const decipher = crypto.createDecipheriv("aes-256-gcm", key, nonce);
decipher.setAuthTag(tag);
process.stdout.write(Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString("base64"));
'@
        $nodeFile = Join-Path $env:TEMP ("xpos-safe-storage-" + [guid]::NewGuid().ToString("N") + ".js")
        [IO.File]::WriteAllText($nodeFile, $nodeScript, (New-Object Text.UTF8Encoding($false)))
        try {
            $encodedPlain = (@($payload | & $NodePath $nodeFile 2>$null) -join "").Trim()
            if ($LASTEXITCODE -ne 0) { throw "safeStorage decrypt failed" }
            return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encodedPlain))
        } finally {
            Remove-Item -LiteralPath $nodeFile -Force -ErrorAction SilentlyContinue
        }
    } catch {
        throw "无法在当前 Windows 用户下读取本机受保护同步配置。"
    }
}

function Read-HubKeyFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    try { $key = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json } catch { throw "无法读取 Hub U 盘配置文件。" }
    if ([int]$key.format -ne 1) { throw "Hub U 盘配置文件格式不受支持。" }
    foreach ($name in @("server_url", "api_key", "api_secret")) {
        if ([string]::IsNullOrWhiteSpace([string]$key.$name)) { throw "Hub U 盘配置文件缺少必要配置。" }
        if ([string]$key.$name -match "[\r\n]") { throw "Hub U 盘配置文件内容无效。" }
    }
    if ([string]$key.server_url -notmatch "^https?://") { throw "Hub U 盘配置文件中的服务器地址无效。" }
    if ([string]$key.api_key -like "enc:v1:*" -or [string]$key.api_secret -like "enc:v1:*") { throw "Hub U 盘配置文件必须是可移植凭据。" }
    return $key
}

if (-not [string]::IsNullOrWhiteSpace($HubKeyInputPath)) {
    $hubKey = Read-HubKeyFile -Path ([IO.Path]::GetFullPath($HubKeyInputPath))
} else {
    $mysql = "C:\Program Files\MariaDB 11.4\bin\mysql.exe"
    if (-not (Test-Path -LiteralPath $mysql)) { throw "本机 MariaDB 客户端不存在。" }
    $query = 'SELECT `key`,`value` FROM `sync_meta` WHERE `key` IN (''server_url'',''api_key'',''api_secret'')'
    $rows = & $mysql "--protocol=TCP" "--host=127.0.0.1" "--port=3307" "--user=root" "--password=$SourceRootPassword" "--skip-ssl" "--database=xpos_local" "--batch" "--skip-column-names" "--raw" "--execute=$query" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "无法读取本机 xPos 受保护同步配置。" }
    $meta = @{}
    foreach ($row in $rows) {
        $parts = [string]$row -split [char]9, 3
        if ($parts.Count -ge 2) { $meta[$parts[0]] = $parts[1] }
    }
    foreach ($key in @("server_url", "api_key", "api_secret")) {
        if ([string]::IsNullOrWhiteSpace([string]$meta[$key])) { throw "本机同步配置缺少 $key。" }
    }
    $storedApiKey = [string]$meta["api_key"]
    $storedApiSecret = [string]$meta["api_secret"]
    $portable = $false
    if ($storedApiKey -notlike "enc:v1:*" -and $storedApiSecret -notlike "enc:v1:*") {
        $apiKey = $storedApiKey
        $apiSecret = $storedApiSecret
        $portable = $true
    } else {
        try {
            $node = Find-NodeClient
            $safeStorageKey = Get-ElectronSafeStorageKey
            $apiKey = Unprotect-SourceSecret -Value $storedApiKey -SafeStorageKey $safeStorageKey -NodePath $node
            $apiSecret = Unprotect-SourceSecret -Value $storedApiSecret -SafeStorageKey $safeStorageKey -NodePath $node
            $portable = -not [string]::IsNullOrWhiteSpace($apiKey) -and -not [string]::IsNullOrWhiteSpace($apiSecret)
        } catch {}
    }
    if ($portable) {
        $hubKey = [ordered]@{
            format = 1
            server_url = [string]$meta["server_url"]
            api_key = $apiKey
            api_secret = $apiSecret
        }
    } elseif ($storedApiKey -like "enc:v1:*" -and $storedApiSecret -like "enc:v1:*") {
        $hubKey = [ordered]@{
            format = 2
            mode = "inherit-local"
            server_url = [string]$meta["server_url"]
            api_key = $storedApiKey
            api_secret = $storedApiSecret
        }
        Write-Host "无法导出可移植凭据，已生成同机继承模式 Hub 配置文件。"
    } else {
        throw "本机同步配置无法转换为 Hub U 盘配置。"
    }
}
New-Item -ItemType Directory -Path (Split-Path -Parent $hubKeyFile) -Force | Out-Null
[IO.File]::WriteAllText($hubKeyFile, ($hubKey | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
$hubKeyReadme = Join-Path (Split-Path -Parent $hubKeyFile) "README.txt"
if ([string]::IsNullOrWhiteSpace($HubKeyOutput)) {
    [IO.File]::WriteAllText($hubKeyReadme, "将 XPOS-HUB-KEY.json 复制到 U 盘根目录。Hub 安装时插入该 U 盘；不要把它放入安装 ZIP。`r`n", (New-Object Text.UTF8Encoding($false)))
}

foreach ($path in @($hubDir, $tillDir, $hubZip, $tillZip)) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
}
New-Item -ItemType Directory -Path $hubDir, $tillDir -Force | Out-Null
foreach ($dir in @($hubDir, $tillDir)) {
    Copy-Item -LiteralPath (Join-Path $common "app") -Destination $dir -Recurse
    New-Item -ItemType Directory -Path (Join-Path $dir "dependencies"), (Join-Path $dir "bootstrap") -Force | Out-Null
    Copy-Item -LiteralPath $msi -Destination (Join-Path $dir "dependencies\mariadb-11.4.13-winx64.msi")
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Install-XPos-Hub.ps1") -Destination $hubDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README-Hub.txt") -Destination (Join-Path $hubDir "README.txt")
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Install-XPos-Till.ps1") -Destination $tillDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README-Till.txt") -Destination (Join-Path $tillDir "README.txt")

$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
$hubAccessToken = ([BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
$hubSeed = [ordered]@{
    format = 2
    hub_access_token = $hubAccessToken
}
$tillSeed = [ordered]@{
    format = 1
    hub_access_token = $hubAccessToken
}
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $hubDir "bootstrap\hub-seed.json"), ($hubSeed | ConvertTo-Json), $utf8)
[IO.File]::WriteAllText((Join-Path $tillDir "bootstrap\till-seed.json"), ($tillSeed | ConvertTo-Json), $utf8)
Write-Host "Hub U 盘配置文件已生成：$hubKeyFile"

function Write-Manifest {
    param([string]$Directory)
    $lines = @()
    foreach ($file in (Get-ChildItem -LiteralPath $Directory -Recurse -File | Sort-Object FullName)) {
        $relative = $file.FullName.Substring($Directory.Length + 1).Replace("\", "/")
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $lines += "$hash  $relative"
    }
    [IO.File]::WriteAllLines((Join-Path $Directory "SHA256SUMS.txt"), $lines, (New-Object Text.UTF8Encoding($false)))
}
Write-Manifest -Directory $hubDir
Write-Manifest -Directory $tillDir

Compress-Archive -Path (Join-Path $hubDir "*") -DestinationPath $hubZip -CompressionLevel Optimal
Compress-Archive -Path (Join-Path $tillDir "*") -DestinationPath $tillZip -CompressionLevel Optimal
Get-FileHash -LiteralPath $hubZip -Algorithm SHA256
Get-FileHash -LiteralPath $tillZip -Algorithm SHA256
