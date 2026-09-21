# Canonical mixed match: 2x TinyBox Qwen (custom provider) + 4x external Grok Bot seats.
#
#   P1, P2 = custom LLM  (TW2K_CUSTOM_BASE_URL / TW2K_CUSTOM_MODEL from .env; default qwen3.8:latest)
#   P3..P6 = external    (driven over /harness/v1 with per-seat bearer tokens)
#
# Usage (from repo root):
#   powershell -File scripts/run_2qwen_4external.ps1
#   powershell -File scripts/run_2qwen_4external.ps1 -Port 8000 -StartingCredits 1000000 -MaxDays 15 -TimeoutS 120
#
# Bots: see docs/GROK_BOT_PLAYER_GUIDE.md. Each bot needs TW2K_HARNESS_URL, TW2K_HARNESS_PLAYER,
# TW2K_HARNESS_TOKEN (from .tw2k/external_tokens.json — gitignored; never commit it).

param(
  [int]$Port = 8000,
  [int]$StartingCredits = 1000000,
  [int]$MaxDays = 15,
  [int]$TimeoutS = 120,
  [int]$Seed = 42,
  [string]$Model = "qwen3.8:latest",
  [string]$Names = "QwenA,QwenB,GrokBot1,GrokBot2,GrokBot3,GrokBot4"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path ".env")) {
  Write-Error "No .env file. Copy .env.example to .env and set TW2K_CUSTOM_BASE_URL / TW2K_CUSTOM_API_KEY."
}

# Make sure P3..P6 have tokens before the server boots so bots can be configured now.
python scripts/gen_external_tokens.py --seats P3,P4,P5,P6 | Out-Host

$tokFile = if ($env:TW2K_EXTERNAL_TOKENS_FILE) { $env:TW2K_EXTERNAL_TOKENS_FILE } else { ".tw2k\external_tokens.json" }
$tokens = Get-Content -LiteralPath $tokFile -Raw | ConvertFrom-Json

Write-Host ""
Write-Host "Per-seat bot env (tokens masked; full values are in $tokFile):"
foreach ($seat in "P3", "P4", "P5", "P6") {
  $t = [string]$tokens.$seat
  $masked = if ($t.Length -gt 12) { $t.Substring(0, 4) + "..." + $t.Substring($t.Length - 4) } else { "<short>" }
  Write-Host "  $seat  TW2K_HARNESS_URL=http://127.0.0.1:$Port  TW2K_HARNESS_PLAYER=$seat  TW2K_HARNESS_TOKEN=$masked"
  Write-Host "      curl -H `"Authorization: Bearer <token>`" http://127.0.0.1:$Port/harness/v1/$seat/status"
}
Write-Host ""
Write-Host "Spectator: http://127.0.0.1:$Port    Ctrl+C stops the match."
Write-Host ""

tw2k serve `
  --provider custom `
  --model $Model `
  --num-agents 6 `
  --agent-kind llm `
  --agent-names $Names `
  --external P3,P4,P5,P6 `
  --external-timeout-s $TimeoutS `
  --starting-credits $StartingCredits `
  --max-days $MaxDays `
  --seed $Seed `
  --port $Port
