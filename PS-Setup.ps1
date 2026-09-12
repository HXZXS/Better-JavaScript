$AppName     = 'Better-JavaScript-DataRelay'
$ProcessName = 'Better JavaScript DataRelay'
$InstallerName = 'BJS_Setup.exe'
$InstallDir  = 'C:\Program Files\Better-JavaScript-DataRelay'
$ExeName     = 'Better JavaScript DataRelay.exe'
$LaunchAfterInstall = $true

$DownloadUrls = @(
    'https://gh-proxy.com/https://github.com/HXZXS/Better-JavaScript/releases/download/releases/AUTO-Setup.exe'
    'https://gh.927223.xyz/https://github.com/HXZXS/Better-JavaScript/releases/download/releases/AUTO-Setup.exe'
    'https://tvv.tw/https://github.com/HXZXS/Better-JavaScript/releases/download/releases/AUTO-Setup.exe'
    'https://ghf.无名氏.top/https://github.com/HXZXS/Better-JavaScript/releases/download/releases/AUTO-Setup.exe'
)
$ExpectedHash = '5979DCA97216CA11EC2B6A9ABA7225F7DCA4E845E14849BF6C108FFBD253BE2F'
$UserAgent    = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

$ErrorActionPreference = 'Stop'

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}


if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $newProcess = Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -PassThru
    Start-Sleep -Milliseconds 100
    Stop-Process -Id $PID -Force
    exit
}

$Host.UI.RawUI.WindowTitle = "$AppName Automatic Installer"

try {
    $Host.UI.RawUI.BackgroundColor = 'Black'
    $Host.UI.RawUI.ForegroundColor = 'White'
    Clear-Host
} catch {}

$E = [char]27
$RainbowColors = @(196,202,208,214,220,226,190,154,118,82,46,51,45,39,33,27,21,57,93,129,165,201,207)

function Get-DisplayWidth {
    param([string]$Text)
    $w = 0
    foreach ($ch in $Text.ToCharArray()) {
        $code = [int][char]$ch
        if (($code -ge 0x1100 -and $code -le 0x115F) -or
            ($code -ge 0x2E80 -and $code -le 0x303E) -or
            ($code -ge 0x3041 -and $code -le 0x33FF) -or
            ($code -ge 0x3400 -and $code -le 0x4DBF) -or
            ($code -ge 0x4E00 -and $code -le 0x9FFF) -or
            ($code -ge 0xA000 -and $code -le 0xA4CF) -or
            ($code -ge 0xAC00 -and $code -le 0xD7A3) -or
            ($code -ge 0xF900 -and $code -le 0xFAFF) -or
            ($code -ge 0xFE30 -and $code -le 0xFE4F) -or
            ($code -ge 0xFF00 -and $code -le 0xFF60) -or
            ($code -ge 0xFFE0 -and $code -le 0xFFE6)) {
            $w += 2
        } else {
            $w += 1
        }
    }
    return $w
}

function Write-Rainbow {
    param([string]$Text, [switch]$Bold)
    $i = 0
    foreach ($ch in $Text.ToCharArray()) {
        $c = $RainbowColors[$i % $RainbowColors.Count]
        if ($Bold) {
            Write-Host "${E}[1;38;5;${c}m$ch" -NoNewline
        } else {
            Write-Host "${E}[38;5;${c}m$ch" -NoNewline
        }
        $i++
    }
    Write-Host "${E}[0m"
}

function Write-Tag {
    param([string]$Tag, [string]$Text, [int]$TagColor = 51)
    Write-Host "  ${E}[48;5;${TagColor}m${E}[30m $Tag ${E}[0m ${E}[97m$Text${E}[0m"
}
function Write-Ok   { param([string]$T) Write-Host "  ${E}[48;5;46m${E}[30m  OK  ${E}[0m ${E}[92m$T${E}[0m" }
function Write-Warn { param([string]$T) Write-Host "  ${E}[48;5;226m${E}[30m WARN ${E}[0m ${E}[93m$T${E}[0m" }
function Write-Err  { param([string]$T) Write-Host "  ${E}[48;5;196m${E}[97m FAIL ${E}[0m ${E}[91m$T${E}[0m" }
function Write-Info { param([string]$T) Write-Host "  ${E}[48;5;39m${E}[97m INFO ${E}[0m ${E}[96m$T${E}[0m" }
function Write-Step { param([string]$T) Write-Host ''; Write-Host "  ${E}[1;38;5;213m>> $T${E}[0m" }

function Show-Progress {
    param([double]$Percent)
    $width = 100
    $filled = [int][math]::Round($Percent)
    if ($filled -gt $width) { $filled = $width }
    if ($filled -lt 0) { $filled = 0 }

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append("${E}[2K`r")
    [void]$sb.Append('  ')

    for ($i = 0; $i -lt $width; $i++) {
        if ($i -lt $filled) {
            $c = $RainbowColors[$i % $RainbowColors.Count]
            [void]$sb.Append("${E}[38;5;${c}m=")
        } else {
            [void]$sb.Append("${E}[38;5;238m-")
        }
    }

    [void]$sb.Append("${E}[0m ")
    [void]$sb.Append("${E}[1;38;5;226m")
    [void]$sb.Append($Percent.ToString('F1'))
    [void]$sb.Append("${E}[0m${E}[97m/100${E}[0m")

    [Console]::Write($sb.ToString())
}

function Clear-ProgressLine { [Console]::Write("${E}[2K`r") }

function Show-Banner {
    param([string]$Title, [string]$Subtitle, [string]$BorderColor = '17')

    $innerWidth = 58
    $bannerBg = "48;5;${BorderColor}"
    $blank = ' ' * $innerWidth

    Write-Host "  ${E}[${bannerBg}m$blank${E}[0m"

    $titleWidth = Get-DisplayWidth $Title
    $padLeft = [int](($innerWidth - $titleWidth) / 2)
    $padRight = $innerWidth - $padLeft - $titleWidth

    Write-Host "  ${E}[${bannerBg}m$(' ' * $padLeft)${E}[0m" -NoNewline
    $i = 0
    foreach ($ch in $Title.ToCharArray()) {
        $c = $RainbowColors[$i % $RainbowColors.Count]
        Write-Host "${E}[1;${bannerBg};38;5;${c}m$ch" -NoNewline
        $i++
    }
    Write-Host "${E}[${bannerBg}m$(' ' * $padRight)${E}[0m"

    $subWidth = Get-DisplayWidth $Subtitle
    $padSubLeft = [int](($innerWidth - $subWidth) / 2)
    $padSubRight = $innerWidth - $padSubLeft - $subWidth

    Write-Host "  ${E}[${bannerBg}m$(' ' * $padSubLeft)${E}[38;5;250m$Subtitle${E}[${bannerBg}m$(' ' * $padSubRight)${E}[0m"
    Write-Host "  ${E}[${bannerBg}m$blank${E}[0m"
}

Clear-Host
Write-Host ''
Show-Banner -Title $AppName -Subtitle 'Automatic Installer  /  自动安装程序'
Write-Host ''

# ---- Step 1: 进程检查 ----
Write-Step 'Step 1/4  Checking running processes  /  检查运行中的程序'

$targets = @(Get-Process -Name $ProcessName -ErrorAction SilentlyContinue)
if ($targets.Count -eq 0) {
    $alt = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path -like "*Better-JavaScript*"
    }
    $targets = @($alt)
}

if ($targets.Count -gt 0) {
    Write-Warn "Found $($targets.Count) running process(es) / 发现 $($targets.Count) 个运行中的进程"
    foreach ($p in $targets) {
        Write-Host "         PID $($p.Id)  $($p.ProcessName)" -ForegroundColor DarkGray
    }
    foreach ($p in $targets) {
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction Stop
            Write-Ok "Stopped PID $($p.Id) / 已结束进程 PID $($p.Id)"
        } catch {
            Write-Err "Failed to stop PID $($p.Id) / 结束失败：$($_.Exception.Message)"
        }
    }
    Start-Sleep -Milliseconds 800
    $left = @(Get-Process -Name $ProcessName -ErrorAction SilentlyContinue)
    if ($left.Count -gt 0) {
        Write-Err 'Process still running, aborting / 进程仍然存在，已中止'
        Read-Host 'Press Enter to exit / 按回车退出'
        exit 1
    }
} else {
    Write-Ok 'No running process / 没有运行中的程序'
}

# ---- Step 2: 下载 ----
Write-Step 'Step 2/4  Downloading installer  /  下载安装包'

$tmpPath = Join-Path $env:TEMP $InstallerName
$downloaded = $false
$total = $DownloadUrls.Count
$index = 0

foreach ($url in $DownloadUrls) {
    $index++
    try {
        Write-Info "[$index/$total] Source / 来源: $url"

        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.UserAgent = $UserAgent
        $req.Timeout = 30000
        $req.ReadWriteTimeout = 60000
        $req.AllowAutoRedirect = $true

        $resp = $req.GetResponse()
        $totalBytes = $resp.ContentLength
        $inStream = $resp.GetResponseStream()
        $outStream = [System.IO.File]::Create($tmpPath)

        $buffer = New-Object byte[] 81920
        $received = 0
        $lastPercent = -1.0

        while (($read = $inStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $outStream.Write($buffer, 0, $read)
            $received += $read
            if ($totalBytes -gt 0) {
                $percent = [math]::Round(($received / $totalBytes) * 100, 1)
                if ($percent -ne $lastPercent) {
                    Show-Progress -Percent $percent
                    $lastPercent = $percent
                }
            }
        }
        $outStream.Close(); $inStream.Close(); $resp.Close()
        Clear-ProgressLine

        $hash = (Get-FileHash -Path $tmpPath -Algorithm SHA256).Hash
        if ($hash -eq $ExpectedHash) {
            $downloaded = $true
            Write-Ok 'Hash verified / 哈希校验通过'
            break
        } else {
            Write-Warn "Hash mismatch / 哈希不匹配: $hash"
            Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Clear-ProgressLine
        Write-Warn "Failed / 失败: $($_.Exception.Message)"
        Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue
    }
}

if (-not $downloaded) {
    Write-Err 'All download sources failed / 所有下载源均失败'
    Read-Host 'Press Enter to exit / 按回车退出'
    exit 1
}

$sizeMB = [math]::Round((Get-Item $tmpPath).Length / 1MB, 2)
Write-Ok "Downloaded / 下载完成: $tmpPath ($sizeMB MB)"

# ---- Step 3: 安装 ----
Write-Step 'Step 3/4  Installing  /  正在安装'

try {
    $installArgs = @('/SILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$InstallDir`"")
    $proc = Start-Process -FilePath $tmpPath -ArgumentList $installArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Installer returned non-zero exit code: $($proc.ExitCode) / 安装程序返回非零退出码：$($proc.ExitCode)"
    }
    Write-Ok 'Installation complete / 安装完成'
}
catch {
    Write-Err "Installation failed / 安装失败: $($_.Exception.Message)"
    Read-Host 'Press Enter to exit / 按回车退出'
    exit 1
}
finally {
    if (Test-Path $tmpPath) { Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue }
}

# ---- Step 4: 验证 ----
Write-Step 'Step 4/4  Verifying & finalizing  /  验证与收尾'

$exePath = Join-Path $InstallDir $ExeName
if (Test-Path $exePath) {
    Write-Ok "Main executable found / 已找到主程序: $exePath"
} else {
    Write-Warn "Main executable not found / 未找到主程序: $exePath"
}

if ($LaunchAfterInstall -and (Test-Path $exePath)) {
    Write-Info 'Launching application / 正在启动程序'
    Start-Process -FilePath $exePath
}

Write-Host ''
Show-Banner -Title 'All done!' -Subtitle 'Installation completed  /  安装全部完成'
Write-Host ''

Read-Host 'Press Enter to exit / 按回车退出'
