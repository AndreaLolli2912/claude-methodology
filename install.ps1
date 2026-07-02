# install.ps1 — deploy the working methodology into this machine's ~/.claude.
# Run from the repo root:  .\install.ps1
# Copies the bundled files into %USERPROFILE%\.claude, backing up anything it replaces.
# Location-independent: it uses its own folder ($PSScriptRoot), so you can move the repo.

$ErrorActionPreference = "Stop"                          # stop on the first real error

$repoClaude = Join-Path $PSScriptRoot "claude"           # the repo's mirror of ~/.claude
$target     = Join-Path $env:USERPROFILE ".claude"       # this machine's ~/.claude
$stamp      = Get-Date -Format "yyyyMMdd-HHmmss"         # suffix used for backup copies

# The files this bundle owns, as paths relative to ~/.claude
$files = @(
  "CLAUDE.md",
  "METHODOLOGY.md",
  "skills\init-project-docs\SKILL.md"
)

foreach ($rel in $files) {
  $from  = Join-Path $repoClaude $rel                    # source: inside the repo
  $to    = Join-Path $target $rel                        # destination: ~/.claude
  $toDir = Split-Path $to -Parent                        # its containing folder

  if (-not (Test-Path $from)) { Write-Warning "missing in bundle: $rel"; continue }
  New-Item -ItemType Directory -Force -Path $toDir | Out-Null   # ensure the folder exists

  if (Test-Path $to) {                                   # never clobber silently: back up first
    Copy-Item $to "$to.$stamp.bak" -Force
    Write-Host "backed up existing $rel  ->  $rel.$stamp.bak"
  }
  Copy-Item $from $to -Force                             # then install the bundled version
  Write-Host "installed $rel"
}

Write-Host ""
Write-Host "Done. Restart Claude Code, then check /skills lists 'init-project-docs'."
