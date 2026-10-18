# Stop the closed-beta lobby gracefully: every game is snapshotted, then the workers and the lobby exit.
# Running games come back from their snapshots on the next start.ps1. Also stops a Quick Tunnel started by start.ps1.
param([int]$Port = 8099)
$ErrorActionPreference = "Continue"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$root = Join-Path $repo "saves\selfhost"
$keyFile = Join-Path $root "lobby.shutdown.key"
$pidFile = Join-Path $root "lobby.pid"

if (Test-Path $keyFile) {
    $key = (Get-Content $keyFile -Raw).Trim()
    try {
        Invoke-WebRequest -UseBasicParsing -Method Post "http://127.0.0.1:$Port/admin/shutdown" `
            -Headers @{ "x-lobby-shutdown" = $key } -TimeoutSec 10 | Out-Null
        Write-Host "Shutdown requested; waiting for the games to save..."
    } catch { Write-Host "The lobby did not answer on port $Port." }
}

if (Test-Path $pidFile) {
    $lobbyPid = [int](Get-Content $pidFile -Raw).Trim()
    $p = Get-Process -Id $lobbyPid -ErrorAction SilentlyContinue
    if ($p) {
        if (-not $p.WaitForExit(60000)) {
            Write-Host "The lobby did not exit in 60 s; ending it (its game workers end with it)."
            taskkill /T /F /PID $lobbyPid | Out-Null
        }
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

$tunnelPid = Join-Path $root "tunnel.pid"
if (Test-Path $tunnelPid) {
    $tp = [int](Get-Content $tunnelPid -Raw).Trim()
    $proc = Get-Process -Id $tp -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -like "cloudflared*") { Stop-Process -Id $tp }
    Remove-Item $tunnelPid -ErrorAction SilentlyContinue
}
Write-Host "Stopped."
