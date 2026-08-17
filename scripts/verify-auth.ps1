<#
.SYNOPSIS
    Verify the WS-A trust boundary end to end: backend auth tests + frontend typecheck.

.DESCRIPTION
    Idempotent. Creates the shared virtualenv and installs dependencies only if
    they are missing, then runs the auth enforcement suite and `tsc --noEmit`.

    The venv is deliberately shared across the parallel worktrees
    (vaf-ws-a / vaf-ws-b / vaf-ws-c) — torch, faiss and ultralytics are several
    gigabytes and there is no reason to hold three copies.

.EXAMPLE
    pwsh scripts/verify-auth.ps1
    pwsh scripts/verify-auth.ps1 -SkipInstall
#>
[CmdletBinding()]
param(
    [string] $VenvPath = "$PSScriptRoot\..\..\vaf-venv",
    [switch] $SkipInstall
)

$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
$failed = @()

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# 1. Shared virtualenv
# ---------------------------------------------------------------------------
$python = Join-Path $VenvPath 'Scripts\python.exe'

if (-not $SkipInstall) {
    if (-not (Test-Path $python)) {
        Write-Step "Creating shared virtualenv at $VenvPath"
        $py312 = (py -0p | Select-String '3\.12').ToString().Split()[-1]
        if (-not $py312) { throw "Python 3.12 not found. Install it or pass -VenvPath." }
        & $py312 -m venv $VenvPath
    }
    else {
        Write-Host "Shared virtualenv already present — reusing it." -ForegroundColor DarkGray
    }

    # fastapi is the cheapest proxy for "requirements are installed".
    & $python -c "import fastapi" 2>$null
    if (-not $?) {
        Write-Step "Installing backend requirements (multi-GB, one time)"
        & $python -m pip install --upgrade pip
        & $python -m pip install -r (Join-Path $repo 'backend\requirements-local.txt')
    }
    else {
        Write-Host "Backend requirements already installed — skipping." -ForegroundColor DarkGray
    }
}

if (-not (Test-Path $python)) { throw "No interpreter at $python. Re-run without -SkipInstall." }

# ---------------------------------------------------------------------------
# 2. Backend — the trust boundary tests
# ---------------------------------------------------------------------------
Write-Step 'Backend: auth enforcement suite'
Push-Location (Join-Path $repo 'backend')
try {
    & $python -m pytest `
        tests/test_auth_enforcement.py `
        tests/test_auth.py `
        tests/test_auth_wiring.py `
        -q --no-header -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { $failed += 'backend auth tests' }
}
finally { Pop-Location }

# ---------------------------------------------------------------------------
# 3. Frontend — typecheck
# ---------------------------------------------------------------------------
Write-Step 'Frontend: npx tsc --noEmit'
Push-Location (Join-Path $repo 'frontend')
try {
    if (-not (Test-Path 'node_modules')) {
        Write-Host 'Installing node modules...' -ForegroundColor DarkGray
        npm ci --no-audit --no-fund
    }

    $tsc = & npx tsc --noEmit 2>&1
    $tsc | Write-Host

    # ~39 errors pre-date this workstream and belong to WS-C. Only fail on
    # errors in files WS-A owns.
    $owned = @(
        'src/middleware.ts', 'src/lib/session.ts', 'src/stores/auth.ts',
        'src/lib/api.ts', 'src/app/(dashboard)/layout.tsx',
        'src/app/login/page.tsx', 'src/app/register/page.tsx'
    )
    $mine = $tsc | Where-Object {
        $line = $_.ToString().Replace('\', '/')
        $line -match 'error TS' -and ($owned | Where-Object { $line.StartsWith($_) })
    }
    if ($mine) {
        Write-Host "Type errors in WS-A files:" -ForegroundColor Red
        $mine | Write-Host
        $failed += 'frontend typecheck'
    }
    else {
        Write-Host 'No type errors in WS-A files.' -ForegroundColor Green
    }
}
finally { Pop-Location }

# ---------------------------------------------------------------------------
Write-Host ''
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host 'All WS-A checks passed.' -ForegroundColor Green
