param(
    [string]$Version = "1.2.0"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $repoRoot "release_assets\v$Version"
$standardExe = Join-Path $repoRoot "dist\STM32GitReleaseTool.exe"
$win7Exe = Join-Path $repoRoot "STM32GitReleaseTool-Win7.exe"
$buildKit = Join-Path $repoRoot "STM32GitReleaseTool-Win7-BuildKit.zip"

if (-not (Test-Path -LiteralPath $standardExe)) {
    throw "Standard executable not found: $standardExe"
}
if (-not (Test-Path -LiteralPath $buildKit)) {
    throw "Windows 7 build kit not found: $buildKit"
}

if (Test-Path -LiteralPath $releaseRoot) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseRoot | Out-Null

$standardName = "STM32GitReleaseTool-v$Version-Win10-Win11-x64.exe"
$buildKitName = "STM32GitReleaseTool-v$Version-Win7-BuildKit.zip"
Copy-Item -LiteralPath $standardExe -Destination (Join-Path $releaseRoot $standardName)
Copy-Item -LiteralPath $buildKit -Destination (Join-Path $releaseRoot $buildKitName)

if (Test-Path -LiteralPath $win7Exe) {
    Copy-Item -LiteralPath $win7Exe -Destination (
        Join-Path $releaseRoot "STM32GitReleaseTool-v$Version-Win7-x64.exe"
    )
} else {
    Write-Warning "Win7 executable not found. Copy it beside this repository script and run again to include it."
}

Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $releaseRoot
Copy-Item -LiteralPath (Join-Path $repoRoot "CHANGELOG.md") -Destination $releaseRoot
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $releaseRoot

$checksumLines = Get-ChildItem -LiteralPath $releaseRoot -File |
    Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
    Sort-Object Name |
    ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        "$hash  $($_.Name)"
    }
$checksumLines | Set-Content -LiteralPath (Join-Path $releaseRoot "SHA256SUMS.txt") -Encoding ASCII

Write-Host "Release assets prepared: $releaseRoot"
Get-ChildItem -LiteralPath $releaseRoot -File | Select-Object Name, Length
