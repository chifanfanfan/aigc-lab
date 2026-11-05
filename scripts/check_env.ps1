# 环境自检：确认这台机器能不能跑 ComfyUI / 训 LoRA
# 用法：powershell -ExecutionPolicy Bypass -File scripts\check_env.ps1
# 说明：nvidia-smi 在普通权限下可能失败，脚本会退回注册表读显卡信息

$ok = $true

Write-Host "== 1. 显卡 ==" -ForegroundColor Cyan
$gpuName = $null
$vramMB = 0
$smiOk = $false

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    try {
        $line = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
        if ($LASTEXITCODE -eq 0 -and $line) {
            Write-Host "  $line"
            $vramMB = [int](($line -split ',')[1] -replace '\D', '')
            $gpuName = ($line -split ',')[0].Trim()
            $smiOk = $true
        }
    } catch { }
}

if (-not $smiOk) {
    $base = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}'
    Get-ChildItem $base -ErrorAction SilentlyContinue | ForEach-Object {
        $p = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($p.DriverDesc -and $p.DriverDesc -match 'NVIDIA') {
            $bytes = $p.'HardwareInformation.qwMemorySize'
            if ($bytes) { $vramMB = [int]($bytes / 1MB) }
            $gpuName = $p.DriverDesc
            Write-Host "  $($p.DriverDesc)  显存 $([math]::Round($vramMB/1024,1)) GB（注册表读取）"
        }
    }
}

if (-not $gpuName) {
    Write-Host "  未找到 NVIDIA 显卡" -ForegroundColor Red
    $ok = $false
} elseif ($vramMB -ge 12000) {
    Write-Host "  → SDXL / 视频 / LoRA 训练都能本地跑" -ForegroundColor Green
} elseif ($vramMB -ge 8000) {
    Write-Host "  → SD1.5 + LoRA 训练可本地跑；SDXL 要 lowvram；视频勉强" -ForegroundColor Green
} elseif ($vramMB -ge 6000) {
    Write-Host "  → SD1.5 出图没问题；LoRA 训练用 network_dim=8 / batch=1" -ForegroundColor Yellow
} else {
    Write-Host "  → 4~6 GB：出图能跑（512x512）；LoRA 训练很勉强，建议上云；视频基本别想" -ForegroundColor Yellow
}

Write-Host "`n== 2. Python ==" -ForegroundColor Cyan
if (Get-Command python -ErrorAction SilentlyContinue) {
    python --version
} else {
    Write-Host "  未找到 python" -ForegroundColor Red
    $ok = $false
}

Write-Host "`n== 3. 磁盘空间 ==" -ForegroundColor Cyan
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -in 'C','D','E' } |
    ForEach-Object { "  {0}: 可用 {1:N1} GB" -f $_.Name, ($_.Free / 1GB) }
Write-Host "  提示：ComfyUI + SD1.5 约 8~10 GB"

Write-Host "`n== 4. git ==" -ForegroundColor Cyan
if (Get-Command git -ErrorAction SilentlyContinue) { git --version } else { Write-Host "  未装 git" -ForegroundColor Yellow }

Write-Host "`n============================================" -ForegroundColor Green
if ($ok) { Write-Host " 结论：可以开始" -ForegroundColor Green }
else { Write-Host " 结论：先解决上面标红的问题" -ForegroundColor Red }
