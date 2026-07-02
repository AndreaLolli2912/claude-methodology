# capture.ps1 — the reverse of install.ps1.
# Copies the LIVE methodology files FROM ~/.claude back INTO this repo, so you can commit
# edits you made in the live location. Run from the repo root:  .\capture.ps1

$ErrorActionPreference = "Stop"

$repoClaude = Join-Path $PSScriptRoot "claude"           # destination: inside the repo
$source     = Join-Path $env:USERPROFILE ".claude"       # source: this machine's ~/.claude

$files = @(
  "CLAUDE.md",
  "METHODOLOGY.md",
  "skills\init-project-docs\SKILL.md"
)

foreach ($rel in $files) {
  $from = Join-Path $source $rel
  $to   = Join-Path $repoClaude $rel
  if (-not (Test-Path $from)) { Write-Warning "not found in ~/.claude: $rel"; continue }
  New-Item -ItemType Directory -Force -Path (Split-Path $to -Parent) | Out-Null
  Copy-Item $from $to -Force
  Write-Host "captured $rel"
}

Write-Host ""
Write-Host "Done. Now:  git add -A;  git commit -m 'update methodology';  git push"
