# Expose the hosted TW2K match on a URL a remote Grok Bot box can reach.
#
# Preferred: Cloudflare quick tunnel (no account, no admin). cloudflared is taken from PATH,
# or from .tw2k\bin\cloudflared.exe, or downloaded there (portable, user-writable, gitignored).
# Optional: Tailscale Serve if `tailscale` is on PATH and -Tailscale is passed.
#
#   powershell -File scripts/expose_hosted_bot.ps1                 # foreground; Ctrl+C stops tunnel
#   powershell -File scripts/expose_hosted_bot.ps1 -Detach         # leave tunnel running, return
#   powershell -File scripts/expose_hosted_bot.ps1 -Stop           # stop a detached tunnel
#   powershell -File scripts/expose_hosted_bot.ps1 -Tailscale      # also `tailscale serve` the port
#
# Writes (all under gitignored .tw2k\):
#   public_base_url.txt   https://xxxx.trycloudflare.com
#   cloudflared.log       tunnel output
#   cloudflared.pid       detached tunnel PID
# Prints /bot?seat=P3|P4|P5 URLs. Tokens are NOT printed — read .tw2k\external_tokens.json on this box.

param(
  [int]$Port = 8031,
  [string]$LocalHost = "127.0.0.1",
  [switch]$Detach,
  [switch]$Stop,
  [switch]$Tailscale,
  [int]$UrlTimeoutS = 75,
  [string]$Seats = "P3,P4,P5"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$tw2kDir  = Join-Path (Get-Location) ".tw2k"
$binDir   = Join-Path $tw2kDir "bin"
$urlFile  = Join-Path $tw2kDir "public_base_url.txt"
$logFile  = Join-Path $tw2kDir "cloudflared.log"
$errFile  = Join-Path $tw2kDir "cloudflared.err.log"
$pidFile  = Join-Path $tw2kDir "cloudflared.pid"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

function Stop-Tunnel {
  if (Test-Path $pidFile) {
    $old = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($old) {
      Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue
      Write-Host "stopped cloudflared pid $old"
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
  }
  Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

if ($Stop) { Stop-Tunnel; Remove-Item $urlFile -ErrorAction SilentlyContinue; exit 0 }

# 1) local match must be up
$local = "http://${LocalHost}:${Port}"
try {
  $r = Invoke-WebRequest -Uri "$local/bot" -UseBasicParsing -TimeoutSec 5
  if ($r.StatusCode -ne 200) { throw "GET /bot -> $($r.StatusCode)" }
} catch {
  Write-Error "No match answering at $local/bot. Start it first: powershell -File scripts/run_hosted_grokbot.ps1 -Port $Port"
}
Write-Host "local ok: $local/bot -> 200"

# 2) resolve cloudflared (PATH -> .tw2k\bin -> download portable)
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
  $cf = Join-Path $binDir "cloudflared.exe"
  if (-not (Test-Path $cf)) {
    $dl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    Write-Host "downloading portable cloudflared -> $cf"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $dl -OutFile $cf -UseBasicParsing
  }
}
$ver = (& $cf --version 2>&1 | Select-Object -First 1)
Write-Host "cloudflared: $cf ($ver)"

# 3) start quick tunnel (always as a child process so we can parse its log)
Stop-Tunnel
Remove-Item $logFile, $errFile, $urlFile -ErrorAction SilentlyContinue
$args = @("tunnel", "--no-autoupdate", "--url", $local)
$proc = Start-Process -FilePath $cf -ArgumentList $args -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $logFile -RedirectStandardError $errFile
Set-Content -Path $pidFile -Value $proc.Id
Write-Host "cloudflared pid $($proc.Id) starting..."

# 4) wait for the *.trycloudflare.com URL
$base = $null
$deadline = (Get-Date).AddSeconds($UrlTimeoutS)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 2
  if ($proc.HasExited) { break }
  $text = ""
  foreach ($f in $logFile, $errFile) { if (Test-Path $f) { $text += (Get-Content $f -Raw -ErrorAction SilentlyContinue) } }
  $m = [regex]::Match($text, 'https://[a-z0-9-]+\.trycloudflare\.com')
  if ($m.Success) { $base = $m.Value; break }
}
if (-not $base) {
  Write-Host "--- cloudflared output ---"
  foreach ($f in $logFile, $errFile) { if (Test-Path $f) { Get-Content $f | Select-Object -Last 30 } }
  Stop-Tunnel
  Write-Error "no trycloudflare URL within ${UrlTimeoutS}s"
}
Set-Content -Path $urlFile -Value $base -NoNewline
Write-Host ""
Write-Host "PUBLIC BASE URL: $base   (saved to $urlFile)"

# 5) verify through the tunnel. Fresh trycloudflare hostnames can take a minute to
#    reach the local resolver (negative DNS cache); fall back to pinning the edge IP
#    from 1.1.1.1 with curl --resolve so the check proves the tunnel, not local DNS.
$hostName = $base -replace '^https://', ''
$ok = $false
$how = ""
for ($i = 0; $i -lt 8 -and -not $ok; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "$base/bot" -UseBasicParsing -TimeoutSec 15
    if ($r.StatusCode -eq 200) { $ok = $true; $how = "system DNS" }
  } catch {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
      try {
        $edge = (Resolve-DnsName $hostName -Server 1.1.1.1 -Type A -ErrorAction Stop | Select-Object -First 1).IPAddress
        $code = & $curl.Source -s -o NUL -w "%{http_code}" --resolve "${hostName}:443:${edge}" "$base/bot"
        if ($code -eq "200") { $ok = $true; $how = "edge $edge (local DNS still catching up - normal)" }
      } catch { }
    }
    if (-not $ok) { Start-Sleep -Seconds 4 }
  }
}
Write-Host ("tunnel check: GET {0}/bot -> {1}" -f $base, ($(if ($ok) { "200 via $how" } else { "not verified yet; tunnel is registered, retry in a minute" })))

Write-Host ""
Write-Host "Seat URLs (paste the matching token from .tw2k\external_tokens.json into Connect):"
foreach ($seat in ($Seats -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
  Write-Host "  $seat  $base/bot?seat=$seat"
}
Write-Host "  spectator  $base/"
Write-Host ""

# 6) optional Tailscale
$ts = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if ($ts) {
  try {
    $ip = (& $ts ip -4 2>$null | Select-Object -First 1)
    $st = (& $ts status --json 2>$null | ConvertFrom-Json)
    $dns = $st.Self.DNSName.TrimEnd(".")
    Write-Host "Tailscale: http://${ip}:${Port}/bot?seat=P3   (MagicDNS: http://${dns}:${Port}/bot?seat=P3)"
    if ($Tailscale) {
      & $ts serve --bg "http://${LocalHost}:${Port}" | Out-Host
      Write-Host "tailscale serve enabled (https://${dns}/bot?seat=P3 inside the tailnet)"
    }
  } catch { Write-Host "Tailscale present but not logged in / no status." }
} else {
  Write-Host "Tailscale: not installed (optional). winget install tailscale.tailscale  (needs admin)"
}

if ($Detach) {
  Write-Host "tunnel left running (pid $($proc.Id)). Stop with: powershell -File scripts/expose_hosted_bot.ps1 -Stop"
  exit 0
}
Write-Host "tunnel running in foreground. Ctrl+C to stop."
try { Wait-Process -Id $proc.Id } finally { Stop-Tunnel; Remove-Item $urlFile -ErrorAction SilentlyContinue }
