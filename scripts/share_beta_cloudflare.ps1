# Open a free temporary Cloudflare quick tunnel to a lobby that is already running.
# This script never starts, stops, or restarts the game server. Ben runs that himself.
param(
    [int]$Port = 8099
)
$ErrorActionPreference = "Stop"

function Show-CloudflaredInstall {
    Write-Host "cloudflared is not installed."
    Write-Host ""
    Write-Host "Official install steps:"
    Write-Host "  Windows (winget):  winget install --id Cloudflare.cloudflared"
    Write-Host "  macOS (Homebrew):  brew install cloudflared"
    Write-Host "  Other systems:     https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/"
    exit 1
}

if ($env:TW2K_LOBBY_PORT -and -not $PSBoundParameters.ContainsKey("Port")) {
    $Port = [int]$env:TW2K_LOBBY_PORT
}

$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) { Show-CloudflaredInstall }

$target = "http://127.0.0.1:$Port"
Write-Host "Sharing the lobby that is already running at $target"
Write-Host "This script does not start, stop, or restart the game server."
Write-Host "Press Ctrl+C to stop the tunnel. The lobby keeps running."
Write-Host "The public link changes on every run. Old links stop working."
Write-Host ""

$script:printed = $false
& $cf.Source tunnel --no-autoupdate --url $target 2>&1 | ForEach-Object {
    $line = "$_"
    Write-Host $line
    if ($script:printed) { return }
    if ($line -match "https://[a-z0-9-]+\.trycloudflare\.com") {
        $script:printed = $true
        $pub = $Matches[0]
        Write-Host ""
        Write-Host "Public link: $pub"
        Write-Host "Lobby:       $pub/"
        Write-Host "Seat:        $pub/g/<game-id>/bot?seat=<seat>&token=<token>&layout=redesign"
        Write-Host "Send each seat link to one player. The token is the password for that seat."
        Write-Host ""
    }
}
