# Show whether the closed-beta lobby is up, what it is running, and whether a Cloudflare tunnel is running.
param([int]$Port = 8099, [switch]$TunnelOnly)
if (-not $TunnelOnly) {
    try {
        $s = Invoke-RestMethod "http://127.0.0.1:$Port/status" -TimeoutSec 3
        Write-Host "Lobby online: $($s.games_running) game(s) running, $($s.open_seats) open seat(s), full=$($s.full), closed=$($s.closed)"
        Write-Host "Admin page: http://127.0.0.1:$Port/admin"
    } catch {
        Write-Host "Lobby is not answering on 127.0.0.1:$Port"
    }
}
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) {
    Write-Host "Tunnel: cloudflared is not installed (winget install --id Cloudflare.cloudflared)"
    return
}
$svc = Get-Service -Name cloudflared -ErrorAction SilentlyContinue
if ($svc) { Write-Host "Tunnel service: $($svc.Status)" } else { Write-Host "Tunnel service: not installed" }
$procs = @(Get-Process -Name cloudflared -ErrorAction SilentlyContinue)
Write-Host "cloudflared processes running: $($procs.Count)"
