# Host TW2K for remote Grok Bot computer-use play.
# Binds 0.0.0.0 and allows remote harness (token still required).
#
#   powershell -File scripts/run_hosted_grokbot.ps1                          # 2 Qwen + 1 external (P3) - CU playtest default
#   powershell -File scripts/run_hosted_grokbot.ps1 -ExternalSeats P3,P4,P5  # 2 Qwen + 3 external (multi-bot)
#   powershell -File scripts/run_hosted_grokbot.ps1 -Port 8031 -PublicHost "tw2k.example.com"
#
# Then expose:  powershell -File scripts/expose_hosted_bot.ps1 -Port <port> -Detach
# Then open:    {base}/bot?seat=P3  and paste the P3 token from .tw2k/external_tokens.json.
#
# Phase D (computer-use insights): a hosted match must not freeze on external seats nobody is
# driving. Two defences, both on by default here:
#   * one external seat (P3) unless you pass -ExternalSeats
#   * -IdleWaitS 8: an external seat with no harness client seen in the last 45 s auto-WAITs
#     after 8 s instead of the full -TimeoutS. Attended seats (a bot or /bot page polling) keep
#     the full timeout.

param(
  [string]$HostAddr = "0.0.0.0",
  [int]$Port = 8031,
  [string]$PublicHost = "",
  [int]$StartingCredits = 100000,
  [int]$MaxDays = 10,
  [int]$TimeoutS = 180,
  [int]$IdleWaitS = 8,
  # Turns per in-game day. Engine default is 1000; ~120 makes a day roll in minutes for playtests.
  [int]$TurnsPerDay = 120,
  [int]$Seed = 210922,
  [string]$Model = "qwen3.8:latest",
  [string]$ExternalSeats = "P3",
  [string]$QwenNames = "QwenA,QwenB",
  [string]$ExternalNames = "Commander,GrokPilot2,GrokPilot3"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TW2K_HARNESS_ALLOW_REMOTE = "1"

if (-not (Test-Path ".env")) { Write-Error "Need .env with TW2K_CUSTOM_* for Qwen seats." }

$seats = @($ExternalSeats -split "," | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ })
$qwen  = @($QwenNames -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$extN  = @($ExternalNames -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$numAgents = $qwen.Count + $seats.Count
$names = @($qwen) + @($extN[0..($seats.Count - 1)])
$namesCsv = $names -join ","
$seatsCsv = $seats -join ","

python scripts/gen_external_tokens.py --seats $seatsCsv | Out-Host
$tokFile = ".tw2k\external_tokens.json"
$tokens = Get-Content -LiteralPath $tokFile -Raw | ConvertFrom-Json

$display = if ($PublicHost) { $PublicHost } else { "THIS_MACHINE_IP" }
Write-Host ""
Write-Host "Seats: $numAgents  (Qwen: $($qwen -join ', ')  |  external: $seatsCsv)"
Write-Host "Grok Bot cockpit:  http://${display}:${Port}/bot?seat=$($seats[0])"
Write-Host "Spectator:         http://${display}:${Port}/"
Write-Host "Harness (remote):  http://${display}:${Port}/harness/v1/..."
Write-Host "TW2K_HARNESS_ALLOW_REMOTE=1   external timeout ${TimeoutS}s   idle auto-WAIT ${IdleWaitS}s   turns/day $TurnsPerDay"
Write-Host "Tokens (masked) in $tokFile - paste into /bot Connect field."
foreach ($seat in $seats) {
  $t = [string]$tokens.$seat
  $masked = if ($t.Length -gt 12) { $t.Substring(0,4) + "..." + $t.Substring($t.Length-4) } else { "?" }
  Write-Host "  $seat token $masked"
}
Write-Host ""

$serveArgs = @(
  "serve", "--host", $HostAddr, "--port", $Port, "--provider", "custom", "--model", $Model,
  "--num-agents", $numAgents, "--agent-kind", "llm", "--agent-names", $namesCsv,
  "--external", $seatsCsv, "--external-timeout-s", $TimeoutS,
  "--starting-credits", $StartingCredits, "--max-days", $MaxDays, "--seed", $Seed
)
if ($IdleWaitS -gt 0)   { $serveArgs += @("--external-idle-wait-s", $IdleWaitS) }
if ($TurnsPerDay -gt 0) { $serveArgs += @("--turns-per-day", $TurnsPerDay) }

# Prefer python -m in case Scripts not on PATH after pip --user
$tw2k = Get-Command tw2k -EA SilentlyContinue
if ($tw2k) { & tw2k @serveArgs } else { python -m tw2k.cli @serveArgs }
