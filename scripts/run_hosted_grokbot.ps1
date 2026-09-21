# Host TW2K for remote Grok Bot computer-use play.
# Binds 0.0.0.0 and allows remote harness (token still required).
#
#   powershell -File scripts/run_hosted_grokbot.ps1
#   powershell -File scripts/run_hosted_grokbot.ps1 -Port 8031 -PublicHost "tw2k.example.com"
#
# Then open:  http://<host>:<port>/bot?seat=P3
# Paste the P3 token from .tw2k/external_tokens.json into the page.

param(
  [string]$HostAddr = "0.0.0.0",
  [int]$Port = 8031,
  [string]$PublicHost = "",
  [int]$StartingCredits = 100000,
  [int]$MaxDays = 10,
  [int]$TimeoutS = 180,
  # Turns per in-game day. Default engine value is 1000; for computer-use playtests use ~120 so
  # a day rolls over in minutes even when the external seats idle out (see HOSTING_GROKBOT.md).
  [int]$TurnsPerDay = 0,
  [int]$Seed = 210922,
  [string]$Model = "qwen3.8:latest",
  [string]$Names = "QwenA,QwenB,Commander,GrokPilot2,GrokPilot3"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TW2K_HARNESS_ALLOW_REMOTE = "1"

if (-not (Test-Path ".env")) { Write-Error "Need .env with TW2K_CUSTOM_* for Qwen seats." }

python scripts/gen_external_tokens.py --seats P3,P4,P5 | Out-Host
$tokFile = ".tw2k\external_tokens.json"
$tokens = Get-Content -LiteralPath $tokFile -Raw | ConvertFrom-Json

$display = if ($PublicHost) { $PublicHost } else { "THIS_MACHINE_IP" }
Write-Host ""
Write-Host "Grok Bot cockpit:  http://${display}:${Port}/bot?seat=P3"
Write-Host "Spectator:         http://${display}:${Port}/"
Write-Host "Harness (remote):  http://${display}:${Port}/harness/v1/..."
Write-Host "TW2K_HARNESS_ALLOW_REMOTE=1"
Write-Host "Tokens (masked) in $tokFile — paste into /bot Connect field."
foreach ($seat in "P3","P4","P5") {
  $t = [string]$tokens.$seat
  $masked = if ($t.Length -gt 12) { $t.Substring(0,4) + "..." + $t.Substring($t.Length-4) } else { "?" }
  Write-Host "  $seat token $masked"
}
Write-Host ""

$serveArgs = @(
  "serve", "--host", $HostAddr, "--port", $Port, "--provider", "custom", "--model", $Model,
  "--num-agents", "5", "--agent-kind", "llm", "--agent-names", $Names,
  "--external", "P3,P4,P5", "--external-timeout-s", $TimeoutS,
  "--starting-credits", $StartingCredits, "--max-days", $MaxDays, "--seed", $Seed
)
if ($TurnsPerDay -gt 0) { $serveArgs += @("--turns-per-day", $TurnsPerDay) }

# Prefer python -m in case Scripts not on PATH after pip --user
$tw2k = Get-Command tw2k -EA SilentlyContinue
if ($tw2k) { & tw2k @serveArgs } else { python -m tw2k.cli @serveArgs }
