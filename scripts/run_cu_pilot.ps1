# Computer-use pilot (grokbot-player G5): Commander plays P3 by screen on /bot?mode=cu.
#
#   Lineup  P1 QwenA      LLM (provider custom, -Model; TW2K_CUSTOM_* from .env)
#           P2 SeatBrain  scripted seat_brain_v2 over the harness (control seat, 60 s deadline)
#           P3 Commander  external, computer use (600 s deadline, hold-my-slot on)
#   Match   seed 250925, 2 days, 60 turns/day, port 8032, spectator gate on, tunnel on.
#
#   powershell -File scripts/run_cu_pilot.ps1 -DryRun              # host paused (no turns), run checks, stop
#   powershell -File scripts/run_cu_pilot.ps1 -DryRun -KeepUp      # same, leave the paused host up
#   powershell -File scripts/run_cu_pilot.ps1 -Go                  # THE PILOT - only after Ben's go
#
# Never uses :8031 (the live match) and never touches the main folder. Secrets stay in .tw2k\ (gitignored):
# seat tokens, spectator token/link, seat links, public URL. Per-action log for every external seat:
# saves\<run>\external_actions.jsonl (summary: python scripts/cu_pilot_report.py --latest).

param(
  [int]$Port = 8032,
  [switch]$DryRun,
  [switch]$Go,
  [switch]$KeepUp,
  [switch]$NoTunnel,
  [ValidateSet("localhostrun", "cloudflare")]
  [string]$TunnelProvider = "localhostrun",
  [string]$Model = "qwen3.8:latest",
  [int]$Seed = 250925,
  [int]$MaxDays = 2,
  [int]$TurnsPerDay = 60,
  [int]$StartingCredits = 100000,
  [int]$CuTimeoutS = 600,
  [int]$BotTimeoutS = 60,
  [int]$IdleWaitS = 8,
  # Commander's turn_due endpoint (P3 only). Dry run without it: a local receiver checks the payload.
  [string]$WebhookUrl = $env:TW2K_GROKBOT_WEBHOOK_URL,
  [int]$ReceiverPort = 8039
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
# Start-Process joins -ArgumentList with spaces and does not quote; this checkout path has spaces.
function Quote-Args([object[]]$a) { $a | ForEach-Object { $s = [string]$_; if ($s -match '\s') { '"' + $s + '"' } else { $s } } }

if ($DryRun -eq $Go) {
  Write-Host "Pick exactly one: -DryRun (safe checks, no turns) or -Go (starts the pilot; needs Ben's go)."
  exit 2
}
if ($Port -eq 8031) { Write-Error "Port 8031 is the live match. The pilot runs on 8032+." }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { Write-Error "Port $Port is already in use." }

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
$env:TW2K_HARNESS_ALLOW_REMOTE = "1"          # tunnel clients
$tw2kDir = Join-Path (Get-Location) ".tw2k"
New-Item -ItemType Directory -Force -Path $tw2kDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $tw2kDir "cu_pilot\$stamp"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$savesRoot = if ($env:TW2K_SAVES_DIR) { $env:TW2K_SAVES_DIR } else { Join-Path (Get-Location) "saves" }

if ($Go -and -not (Test-Path ".env") -and -not $env:TW2K_CUSTOM_BASE_URL) {
  Write-Error "P1 QwenA needs TW2K_CUSTOM_BASE_URL / TW2K_CUSTOM_API_KEY (copy .env into this checkout or export them)."
}

# Seat tokens (P2, P3) + spectator gate
$tokFile = Join-Path $tw2kDir "external_tokens.json"
python scripts/gen_external_tokens.py --seats P2,P3 --file $tokFile | Out-Host
$specFile = Join-Path $tw2kDir "spectator_token.txt"
if (-not (Test-Path $specFile)) {
  $bytes = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  [IO.File]::WriteAllText($specFile, ([Convert]::ToBase64String($bytes)).TrimEnd("=").Replace("+", "-").Replace("/", "_"))
}
$env:TW2K_SPECTATOR_TOKEN = (Get-Content $specFile -Raw).Trim()
[IO.File]::WriteAllText((Join-Path $tw2kDir "spectator_link.txt"), "http://127.0.0.1:$Port/spectate?token=$($env:TW2K_SPECTATOR_TOKEN)")

# turn_due webhook for P3 only (P2 is a bot; it must not ping Commander)
Remove-Item Env:TW2K_GROKBOT_WEBHOOK_URL -ErrorAction SilentlyContinue
$receiverArgs = @()
if (-not $WebhookUrl) {
  if ($Go) { Write-Warning "No -WebhookUrl / TW2K_GROKBOT_WEBHOOK_URL: Commander gets no turn_due pings (the pilot still works by polling /bot)." }
  else { $WebhookUrl = "http://127.0.0.1:$ReceiverPort/pilot-hook"; $receiverArgs = @("--receiver-port", $ReceiverPort) }
}
if ($WebhookUrl) { $env:TW2K_GROKBOT_WEBHOOK_P3 = $WebhookUrl }

$serveArgs = @(
  "-m", "tw2k.cli", "serve", "--host", "127.0.0.1", "--port", $Port,
  "--provider", "custom", "--model", $Model, "--num-agents", 3, "--agent-kind", "llm",
  "--agent-names", "QwenA,SeatBrain,Commander", "--external", "P2,P3",
  "--external-timeout-s", $CuTimeoutS, "--external-seat-timeouts", "P2=$BotTimeoutS",
  "--external-idle-wait-s", $IdleWaitS, "--external-tokens-file", $tokFile,
  "--seed", $Seed, "--max-days", $MaxDays, "--turns-per-day", $TurnsPerDay, "--starting-credits", $StartingCredits
)
if ($DryRun) { $serveArgs += "--start-paused" }

Write-Host "Pilot host :$Port  ($(if ($DryRun) { 'DRY RUN - paused, no turns' } else { 'LIVE PILOT' }))  logs $runDir"
$server = Start-Process -FilePath "python" -ArgumentList (Quote-Args $serveArgs) -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $runDir "host.out.log") -RedirectStandardError (Join-Path $runDir "host.err.log")
[IO.File]::WriteAllText((Join-Path $runDir "host.pid"), [string]$server.Id)

$up = $false
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Milliseconds 500
  try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/bot" -TimeoutSec 5).StatusCode -eq 200) { $up = $true; break } } catch { }
  if ($server.HasExited) { break }
}
if (-not $up) { Write-Error "Host did not come up on :$Port - see $runDir\host.err.log" }
Start-Sleep -Seconds 2   # seats + seat links are written right after start

if ($DryRun) {
  python scripts/cu_pilot_check.py --base "http://127.0.0.1:$Port" --tokens-file $tokFile --spectator-token-file $specFile `
    --links-dir (Join-Path $tw2kDir "seat_links") --saves-root $savesRoot --log-dir $runDir `
    --seed $Seed --max-days $MaxDays --turns-per-day $TurnsPerDay --cu-timeout $CuTimeoutS --bot-timeout $BotTimeoutS @receiverArgs
  $rc = $LASTEXITCODE
  if ($KeepUp) { Write-Host "Host left up (paused), pid $($server.Id). Stop: Stop-Process -Id $($server.Id)" }
  else { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue; Write-Host "Dry-run host stopped." }
  exit $rc
}

# ---- LIVE PILOT (-Go) ----
$brain = Start-Process -FilePath "python" -PassThru -WindowStyle Hidden `
  -ArgumentList (Quote-Args @("scripts/seat_brain_v2.py", "--seat", "P2", "--harness", "--base-url", "http://127.0.0.1:$Port", "--tokens-file", $tokFile, "--log-dir", (Join-Path $runDir "p2_brain"))) `
  -RedirectStandardOutput (Join-Path $runDir "p2_brain.out.log") -RedirectStandardError (Join-Path $runDir "p2_brain.err.log")
[IO.File]::WriteAllText((Join-Path $runDir "p2_brain.pid"), [string]$brain.Id)
Write-Host "P2 SeatBrain (seat_brain_v2 --harness) pid $($brain.Id)"

if (-not $NoTunnel) {
  $wd = Start-Process -FilePath "powershell" -PassThru -WindowStyle Hidden `
    -ArgumentList @("-NoProfile", "-File", "scripts/tunnel_watchdog.ps1", "-Port", $Port, "-Provider", $TunnelProvider, "-IntervalS", 60)
  [IO.File]::WriteAllText((Join-Path $runDir "tunnel_watchdog.pid"), [string]$wd.Id)
  Write-Host "Tunnel watchdog pid $($wd.Id): public URL -> .tw2k\public_base_url.txt, seat links refreshed automatically"
}
Write-Host ""
Write-Host "Commander (P3): open the link in .tw2k\seat_links\P3.txt once (no token paste), then play on /bot?seat=P3&mode=cu"
Write-Host "Ben (spectator): .tw2k\spectator_link.txt (swap in the public base when opening remotely)"
Write-Host "Per-action log: $savesRoot\<run>\external_actions.jsonl   summary: python scripts/cu_pilot_report.py --latest"
Write-Host "Stop: Stop-Process -Id $($server.Id),$($brain.Id)$(if (-not $NoTunnel) { ",$($wd.Id); powershell -File scripts/expose_hosted_bot.ps1 -Stop" })"
