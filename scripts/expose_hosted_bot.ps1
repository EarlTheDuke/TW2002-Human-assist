# Expose the hosted TW2K match on a URL a remote Grok Bot box can reach.
#
# Providers (no account, no admin for either):
#   localhostrun (default)  HTTPS via SSH reverse tunnel to localhost.run (*.lhr.life). Uses the
#                           built-in Windows OpenSSH client. Works for datacenter/computer-use
#                           browsers that Cloudflare's bot WAF rejects with 403.
#   cloudflare              Cloudflare quick tunnel (*.trycloudflare.com). cloudflared from PATH,
#                           .tw2k\bin\, or downloaded there. NOTE: CF bot-fight mode 403s many
#                           headless / datacenter browsers (curl still works). Use for humans.
#
#   powershell -File scripts/expose_hosted_bot.ps1 -Detach                       # localhost.run, return
#   powershell -File scripts/expose_hosted_bot.ps1 -Provider cloudflare -Detach
#   powershell -File scripts/expose_hosted_bot.ps1 -Stop                         # stop all tunnels
#   powershell -File scripts/expose_hosted_bot.ps1 -Tailscale                    # + tailscale serve if installed
#
# Writes (all under gitignored .tw2k\):
#   public_base_url.txt                 the URL Commander should use (last provider run)
#   public_base_url.<provider>.txt      per-provider URL
#   <provider>.log / .err.log / .pid    tunnel output + PID
# Prints /bot?seat=P3|P4|P5 URLs. Tokens are NOT printed - read .tw2k\external_tokens.json on this box.

param(
  [int]$Port = 8031,
  [string]$LocalHost = "127.0.0.1",
  [ValidateSet("localhostrun", "cloudflare")]
  [string]$Provider = "localhostrun",
  [switch]$Detach,
  [switch]$Stop,
  [switch]$Tailscale,
  [int]$UrlTimeoutS = 75,
  [string]$Seats = "P3,P4,P5"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$tw2kDir = Join-Path (Get-Location) ".tw2k"
$binDir  = Join-Path $tw2kDir "bin"
$urlFile = Join-Path $tw2kDir "public_base_url.txt"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

function PidFile($p)  { Join-Path $tw2kDir "$p.pid" }
function LogFile($p)  { Join-Path $tw2kDir "$p.log" }
function ErrFile($p)  { Join-Path $tw2kDir "$p.err.log" }
function UrlFileFor($p) { Join-Path $tw2kDir "public_base_url.$p.txt" }

function Stop-Provider($p) {
  $pf = PidFile $p
  if (Test-Path $pf) {
    $old = Get-Content $pf -ErrorAction SilentlyContinue
    if ($old) { Stop-Process -Id ([int]$old) -Force -ErrorAction SilentlyContinue; Write-Host "stopped $p pid $old" }
    Remove-Item $pf -ErrorAction SilentlyContinue
  }
  Remove-Item (UrlFileFor $p) -ErrorAction SilentlyContinue
}

if ($Stop) {
  Stop-Provider "cloudflare"; Stop-Provider "localhostrun"
  Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Remove-Item $urlFile -ErrorAction SilentlyContinue
  exit 0
}

# 1) local match must be up
$local = "http://${LocalHost}:${Port}"
try {
  $r = Invoke-WebRequest -Uri "$local/bot" -UseBasicParsing -TimeoutSec 5
  if ($r.StatusCode -ne 200) { throw "GET /bot -> $($r.StatusCode)" }
} catch {
  Write-Error "No match answering at $local/bot. Start it first: powershell -File scripts/run_hosted_grokbot.ps1 -Port $Port"
}
Write-Host "local ok: $local/bot -> 200"

# 2) start the chosen tunnel as a child process with captured output
Stop-Provider $Provider
$logFile = LogFile $Provider; $errFile = ErrFile $Provider
Remove-Item $logFile, $errFile -ErrorAction SilentlyContinue

switch ($Provider) {
  "cloudflare" {
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
    Write-Host "cloudflared: $cf ($((& $cf --version 2>&1 | Select-Object -First 1)))"
    $exe = $cf
    $argv = @("tunnel", "--no-autoupdate", "--url", $local)
    $urlRegex = 'https://[a-z0-9-]+\.trycloudflare\.com'
  }
  "localhostrun" {
    $exe = (Get-Command ssh.exe -ErrorAction SilentlyContinue).Source
    if (-not $exe) { Write-Error "ssh.exe not found (Windows OpenSSH client). Use -Provider cloudflare." }
    Write-Host "ssh: $exe -> nokey@localhost.run"
    $argv = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30",
              "-o", "ServerAliveCountMax=3", "-o", "ExitOnForwardFailure=yes", "-T",
              "-R", "80:${LocalHost}:${Port}", "nokey@localhost.run")
    $urlRegex = 'https://[a-z0-9]+\.lhr\.life'
  }
}

$proc = Start-Process -FilePath $exe -ArgumentList $argv -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $logFile -RedirectStandardError $errFile
Set-Content -Path (PidFile $Provider) -Value $proc.Id
Write-Host "$Provider pid $($proc.Id) starting..."

# 3) wait for the public URL
$base = $null
$deadline = (Get-Date).AddSeconds($UrlTimeoutS)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 2
  if ($proc.HasExited) { break }
  $text = ""
  foreach ($f in $logFile, $errFile) { if (Test-Path $f) { $text += (Get-Content $f -Raw -ErrorAction SilentlyContinue) } }
  $m = [regex]::Match($text, $urlRegex)
  if ($m.Success) { $base = $m.Value; break }
}
if (-not $base) {
  Write-Host "--- $Provider output ---"
  foreach ($f in $logFile, $errFile) { if (Test-Path $f) { Get-Content $f | Select-Object -Last 30 } }
  Stop-Provider $Provider
  Write-Error "no public URL from $Provider within ${UrlTimeoutS}s"
}
Set-Content -Path (UrlFileFor $Provider) -Value $base -NoNewline
Set-Content -Path $urlFile -Value $base -NoNewline
Write-Host ""
Write-Host "PUBLIC BASE URL ($Provider): $base   (saved to $urlFile)"

# 4) verify through the tunnel with a browser-like UA. Fresh hostnames can take a minute to
#    reach the local resolver; fall back to pinning the edge IP from 1.1.1.1 with curl --resolve.
$hostName = $base -replace '^https://', ''
$ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
$curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
$ok = $false; $how = ""
for ($i = 0; $i -lt 8 -and -not $ok; $i++) {
  if ($curl) {
    $code = & $curl -s -o NUL -w "%{http_code}" -A $ua "$base/bot"
    if ($code -eq "200") { $ok = $true; $how = "system DNS" }
    elseif ($code -eq "403") { $how = "403 - provider bot-blocks this UA; try -Provider localhostrun"; break }
    else {
      try {
        $edge = (Resolve-DnsName $hostName -Server 1.1.1.1 -Type A -ErrorAction Stop | Select-Object -First 1).IPAddress
        $code = & $curl -s -o NUL -w "%{http_code}" -A $ua --resolve "${hostName}:443:${edge}" "$base/bot"
        if ($code -eq "200") { $ok = $true; $how = "edge $edge (local DNS still catching up - normal)" }
      } catch { }
    }
  } else {
    try { if ((Invoke-WebRequest -Uri "$base/bot" -UseBasicParsing -TimeoutSec 15).StatusCode -eq 200) { $ok = $true; $how = "system DNS" } } catch { }
  }
  if (-not $ok) { Start-Sleep -Seconds 4 }
}
Write-Host ("tunnel check: GET {0}/bot -> {1}" -f $base, ($(if ($ok) { "200 via $how" } elseif ($how) { $how } else { "not verified yet; retry in a minute" })))

Write-Host ""
Write-Host "Seat URLs (paste the matching token from .tw2k\external_tokens.json into Connect):"
foreach ($seat in ($Seats -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
  Write-Host "  $seat  $base/bot?seat=$seat"
}
Write-Host "  spectator  $base/"
Write-Host ""

# 5) optional Tailscale
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
  Write-Host "$Provider tunnel left running (pid $($proc.Id)). Stop with: powershell -File scripts/expose_hosted_bot.ps1 -Stop"
  exit 0
}
Write-Host "tunnel running in foreground. Ctrl+C to stop."
try { Wait-Process -Id $proc.Id } finally { Stop-Provider $Provider; Remove-Item $urlFile -ErrorAction SilentlyContinue }
