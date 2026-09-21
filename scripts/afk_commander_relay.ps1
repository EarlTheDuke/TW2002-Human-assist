# Optional backup if the IDE agent dies while Ben is AFK.
# Preferred path: one long Fable session that Start-Sleep polls docs/COMMANDER_NEXT.md
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$Mailbox = Join-Path $Root "docs\COMMANDER_NEXT.md"
Write-Host "Watching $Mailbox — Ctrl+C to stop"
while ($true) {
  if (-not (Test-Path -LiteralPath $Mailbox)) { Start-Sleep 30; continue }
  $text = Get-Content -LiteralPath $Mailbox -Raw
  if ($text -match 'machine_state:\*\*\s*`COMPLETE`') { Write-Host "COMPLETE — exiting"; break }
  if ($text -match 'machine_state:\*\*\s*`COMMANDER_QUEUED`') {
    Write-Host "$(Get-Date -Format o) COMMANDER_QUEUED — trying agent CLI"
    $agent = Get-Command agent -ErrorAction SilentlyContinue
    if ($agent) {
      $prompt = "Read docs/COMMANDER_NEXT.md and docs/GROK_CURSOR_HANDOFF.md. Do the Active task. Update Changelog. Set machine_state to WAITING_COMMANDER when done. Never ask Ben."
      & agent -p $prompt --workspace $Root
    } else {
      Write-Host "agent CLI not on PATH — keep the IDE Fable session running"
    }
  }
  Start-Sleep -Seconds 180
}
