# Keep the hosted /bot tunnel alive. localhost.run drops idle SSH sessions (and the forward dies if
# the origin restarts); this loop re-runs expose_hosted_bot.ps1 -Detach whenever the tunnel process
# is gone or {base}/bot stops answering 200. The public URL changes on every re-expose, so
# consumers must re-read .tw2k\public_base_url.txt (that is the contract; do not cache the URL).
#
#   powershell -File scripts/tunnel_watchdog.ps1                 # foreground loop, Ctrl+C to stop
#   powershell -File scripts/tunnel_watchdog.ps1 -Port 8031 -IntervalS 60 -Provider localhostrun
#
# Log: .tw2k\tunnel_watchdog.log (gitignored). Stop the tunnel itself with expose_hosted_bot.ps1 -Stop.

param(
  [int]$Port = 8031,
  [int]$IntervalS = 60,
  [ValidateSet("localhostrun", "cloudflare")]
  [string]$Provider = "localhostrun"
)

$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
$tw2k = Join-Path (Get-Location) ".tw2k"
$logFile = Join-Path $tw2k "tunnel_watchdog.log"
$pidFile = Join-Path $tw2k "$Provider.pid"
$urlFile = Join-Path $tw2k "public_base_url.txt"
$ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

function Log($msg) {
  $line = "{0} {1}" -f (Get-Date -Format o), $msg
  Add-Content -Path $logFile -Value $line
  Write-Host $line
}

function Tunnel-Healthy {
  if (-not (Test-Path $pidFile)) { return "no pid file" }
  $tunnelPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $tunnelPid -or -not (Get-Process -Id $tunnelPid -ErrorAction SilentlyContinue)) { return "process gone" }
  if (-not (Test-Path $urlFile)) { return "no url file" }
  $base = (Get-Content $urlFile -Raw).Trim()
  if (-not $base) { return "empty url" }
  $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
  if (-not $curl) { return $null }  # cannot probe; trust the process
  $code = & $curl.Source -s -o NUL -w "%{http_code}" -m 20 -A $ua "$base/bot"
  if ($code -ne "200") { return "GET /bot -> $code" }
  return $null
}

Log "watchdog start port=$Port provider=$Provider interval=${IntervalS}s"
while ($true) {
  # Origin must be up; otherwise re-exposing is pointless.
  $originUp = [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  if (-not $originUp) {
    Log "origin :$Port not listening - waiting"
  } else {
    $why = Tunnel-Healthy
    if ($why) {
      Log "tunnel unhealthy ($why) - re-exposing"
      $out = powershell -NoProfile -File scripts/expose_hosted_bot.ps1 -Port $Port -Provider $Provider -Detach 2>&1
      $urlLine = ($out | Select-String -Pattern "PUBLIC BASE URL" | Select-Object -First 1)
      if ($urlLine) { Log "re-exposed: " + ($urlLine.Line -replace 'https://[a-z0-9.-]+', 'https://<new-host>') }
      else { Log "re-expose failed: " + (($out | Select-Object -Last 3) -join " | ") }
    }
  }
  Start-Sleep -Seconds $IntervalS
}
