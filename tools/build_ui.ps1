<#
.SYNOPSIS
    Compile hotkey/ui/forms/*.ui into hotkey/ui/generated/ui_*.py.

.DESCRIPTION
    Run this after editing any .ui file. Generated modules are committed to git
    so the app runs without Qt Designer installed. The test suite runs this
    script with -Check to detect drift between .ui sources and generated code.

.PARAMETER Check
    Verify only. Exits with code 1 when a generated file is missing or stale.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\build_ui.ps1
    powershell -ExecutionPolicy Bypass -File tools\build_ui.ps1 -Check
#>
[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$formsDir = Join-Path $repoRoot 'hotkey\ui\forms'
$generatedDir = Join-Path $repoRoot 'hotkey\ui\generated'

if (-not (Test-Path -LiteralPath $formsDir)) {
    throw "Forms directory not found: $formsDir"
}

$candidates = @(
    (Join-Path $repoRoot '.venv\Scripts\pyside6-uic.exe'),
    (Join-Path $repoRoot '.venv\Scripts\pyside6-uic.bat')
)
$uic = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $uic) {
    $command = Get-Command pyside6-uic -ErrorAction SilentlyContinue
    if ($command) {
        $uic = $command.Source
    }
    else {
        throw 'pyside6-uic not found. Install dependencies first: pip install -r requirements-dev.txt'
    }
}

New-Item -ItemType Directory -Force -Path $generatedDir | Out-Null

$forms = @(Get-ChildItem -LiteralPath $formsDir -Filter '*.ui' | Sort-Object Name)
if ($forms.Count -eq 0) {
    throw "No .ui files found in: $formsDir"
}

function Normalize-Text([string]$text) {
    if ($null -eq $text) { return '' }
    return ($text -replace "`r`n", "`n").TrimEnd("`n")
}

$stale = New-Object System.Collections.Generic.List[string]

foreach ($form in $forms) {
    $targetName = 'ui_{0}.py' -f $form.BaseName
    $target = Join-Path $generatedDir $targetName

    if ($Check) {
        # Keep the scratch file inside the repo: on locked-down hosts the system
        # temp directory may not be writable from Python child processes.
        $temp = Join-Path $generatedDir (".uic-check-{0}.py" -f [guid]::NewGuid().ToString('N'))
        try {
            & $uic $form.FullName -o $temp
            if ($LASTEXITCODE -ne 0) {
                throw "pyside6-uic failed: $($form.Name)"
            }

            if (-not (Test-Path -LiteralPath $target)) {
                $stale.Add("$targetName (missing)")
            }
            elseif ((Normalize-Text (Get-Content -LiteralPath $temp -Raw)) -ne
                    (Normalize-Text (Get-Content -LiteralPath $target -Raw))) {
                $stale.Add("$targetName (stale)")
            }
        }
        finally {
            if (Test-Path -LiteralPath $temp) {
                Remove-Item -LiteralPath $temp -Force
            }
        }
    }
    else {
        & $uic $form.FullName -o $target
        if ($LASTEXITCODE -ne 0) {
            throw "pyside6-uic failed: $($form.Name)"
        }
        Write-Host ("Generated {0} -> {1}" -f $form.Name, $targetName)
    }
}

if ($Check) {
    if ($stale.Count -gt 0) {
        [Console]::Error.WriteLine(
            'Generated files out of date, run tools\build_ui.ps1: ' + ($stale -join ', ')
        )
        exit 1
    }
    Write-Host 'Generated files are up to date.'
}
