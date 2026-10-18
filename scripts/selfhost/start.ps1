# Start the Galaxy War Command closed-beta lobby on 127.0.0.1:8099 (games on 8100-8119).
# -Quick also opens a Cloudflare Quick Tunnel and prints its https://...trycloudflare.com address.
param(
    [switch]$Quick,
    [int]$Port = 8099,
    [string]$GamePorts = "8100-8119",
    [string]$Python = "C:\Python313\python.exe"
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$root = Join-Path $repo "saves\selfhost"
New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null

if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
    Write-Host "Port $Port is already in use; is the lobby already running? (scripts\selfhost\status.ps1)"
    exit 1
}
$lo, $hi = $GamePorts.Split("-") | ForEach-Object { [int]$_ }
if ($lo -lt 8100 -or $hi -gt 8119 -or $hi -lt $lo) {
    Write-Host "Game ports must stay inside 8100-8119 (got $GamePorts)."
    exit 1
}
$busy = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -ge $lo -and $_.LocalPort -le $hi } | ForEach-Object { $_.LocalPort } | Sort-Object -Unique)
if ($busy.Count -gt 0) {
    Write-Host "Busy game ports (the lobby will skip them): $($busy -join ', ')"
}
$free = ($hi - $lo + 1) - $busy.Count
Write-Host "Game ports $GamePorts : $free free"

$env:PYTHONPATH = "$repo\src"
$env:PYTHONUNBUFFERED = "1"
$env:TW2K_LOBBY_PORT = "$Port"
$env:TW2K_GAME_PORTS = $GamePorts
$out = Join-Path $root "logs\lobby.console.log"
$lobby = Start-Process -FilePath $Python -ArgumentList @("-m", "tw2k.cli", "lobby") -WorkingDirectory $repo `
    -RedirectStandardOutput $out -RedirectStandardError "$out.err" -WindowStyle Hidden -PassThru
Set-Content -Path (Join-Path $root "lobby.pid") -Value $lobby.Id

$up = $false
foreach ($i in 1..60) {
    Start-Sleep -Milliseconds 500
    try {
        if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/healthz" -TimeoutSec 2).StatusCode -eq 200) { $up = $true; break }
    } catch { }
    if ($lobby.HasExited) { break }
}
if (-not $up) { Write-Host "The lobby did not come up; see $out"; exit 1 }
Write-Host "Lobby up: http://127.0.0.1:$Port/   admin: http://127.0.0.1:$Port/admin   (PID $($lobby.Id))"

& (Join-Path $PSScriptRoot "status.ps1") -Port $Port -TunnelOnly

if ($Quick) {
    $cf = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cf) { Write-Host "cloudflared not found: winget install --id Cloudflare.cloudflared"; exit 1 }
    $tlog = Join-Path $root "logs\quick-tunnel.log"
    $tunnel = Start-Process -FilePath $cf.Source -ArgumentList @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$Port") `
        -RedirectStandardOutput "$tlog.out" -RedirectStandardError $tlog -WindowStyle Hidden -PassThru
    Set-Content -Path (Join-Path $root "tunnel.pid") -Value $tunnel.Id
    foreach ($i in 1..60) {
        Start-Sleep -Seconds 1
        $hit = Select-String -Path $tlog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { Write-Host "Quick Tunnel: $($hit.Matches[0].Value)"; break }
    }
}
