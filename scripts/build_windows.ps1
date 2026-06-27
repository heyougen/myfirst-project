$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonVersion = & python --version
$pyInstallerVersion = & python -m PyInstaller --version
Write-Host "Python: $pythonVersion"
Write-Host "PyInstaller: $pyInstallerVersion"

if (Test-Path -LiteralPath "build") {
    Remove-Item -LiteralPath "build" -Recurse -Force
}
if (Test-Path -LiteralPath "dist") {
    Remove-Item -LiteralPath "dist" -Recurse -Force
}

& python -m PyInstaller --noconfirm --clean "STM32GitReleaseTool.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $repoRoot "dist\STM32GitReleaseTool.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build completed without producing $exePath"
}

$exe = Get-Item -LiteralPath $exePath
if ($exe.Length -lt 1MB) {
    throw "Generated executable is unexpectedly small: $($exe.Length) bytes"
}

Write-Host "Build completed: $($exe.FullName)"
Write-Host "Size: $([math]::Round($exe.Length / 1MB, 2)) MB"
