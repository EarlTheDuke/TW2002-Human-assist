# Mixed match: 2x TinyBox Qwen (custom provider) + 3x external Grok Bot seats.
#
#   P1, P2 = custom LLM  (TW2K_CUSTOM_BASE_URL / TW2K_CUSTOM_MODEL from .env; default qwen3.8:latest)
#   P3..P5 = external    (driven over /harness/v1 with per-seat bearer tokens)
#
# Usage (from repo root):
#   powershell -File scripts/run_2qwen_3external.ps1
#   powershell -File scripts/run_2qwen_3external.ps1 -Port 8030 -StartingCredits 1000000 -MaxDays 10 -TimeoutS 180 -Seed 20260921
#
# Pair with: python scripts/playtest_commander_3seat.py
# Spectator: http://127.0.0.1:<Port>

param(
  [int]$Port = 8030,
  [int]$StartingCredits = 1000000,
  [int]$MaxDays = 10,
  [int]$TimeoutS = 180,
  [int]$Seed = 20260921,
  [string]$Model = "qwen3.8:latest",
  [string]$Names = "QwenA,QwenB,Commander,GrokPilot2,GrokPilot3"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path ".env")) {
  Write-Error "No .env file. Copy .env.example to .env and set TW2K_CUSTOM_BASE_URL / TW2K_CUSTOM_API_KEY."
}

# Mint / refresh tokens for the three external seats before the server boots.
python scripts/gen_external_tokens.py --seats P3,P4,P5 | Out-Host

$tokFile = if ($env:TW2K_EXTERNAL_TOKENS_FILE) { $env:TW2K_EXTERNAL_TOKENS_FILE } else { ".tw2k\external_tokens.json" }
$tokens = Get-Content -LiteralPath $tokFile -Raw | ConvertFrom-Json

Write-Host ""
Write-Host "Per-seat bot env (tokens masked; full values are in $tokFile):"
foreach ($seat in "P3", "P4", "P5") {
  $t = [string]$tokens.$seat
  $masked = if ($t.Length -gt 12) { $t.Substring(0, 4) + "..." + $t.Substring($t.Length - 4) } else { "<short>" }
  Write-Host "  $seat  TW2K_HARNESS_URL=http://127.0.0.1:$Port  TW2K_HARNESS_PLAYER=$seat  TW2K_HARNESS_TOKEN=$masked"
  Write-Host "      curl -H `"Authorization: Bearer <token>`" http://127.0.0.1:$Port/harness/v1/$seat/status"
}
Write-Host ""
Write-Host "Spectator: http://127.0.0.1:$Port"
Write-Host "Playtest driver: python scripts/playtest_commander_3seat.py --base-url http://127.0.0.1:$Port"
Write-Host "Ctrl+C stops the match."
Write-Host ""

tw2k serve `
  --provider custom `
  --model $Model `
  --num-agents 5 `
  --agent-kind llm `
  --agent-names $Names `
  --external P3,P4,P5 `
  --external-timeout-s $TimeoutS `
  --starting-credits $StartingCredits `
  --max-days $MaxDays `
  --seed $Seed `
  --port $Port
