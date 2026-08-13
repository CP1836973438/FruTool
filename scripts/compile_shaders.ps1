# Compile FruTool GLSL fragment shaders to Qt .qsb binaries.
# Requires Qt 6 qsb (qtshadertools). Uses .qt/ from aqtinstall or QT_QSB env.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ShaderDir = Join-Path $Root "frutool\qml\FruTool\shaders"

function Find-Qsb {
    if ($env:QT_QSB -and (Test-Path $env:QT_QSB)) { return $env:QT_QSB }
    $candidates = @(
        (Join-Path $Root ".qt\6.8.2\mingw_64\bin\qsb.exe"),
        (Join-Path $Root ".qt\6.7.2\mingw_64\bin\qsb.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    $found = Get-Command qsb -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    throw "qsb not found. Install Qt qtshadertools or set QT_QSB to qsb.exe path."
}

$qsb = Find-Qsb
Write-Host "Using qsb: $qsb"

Get-ChildItem -Path $ShaderDir -Filter "*.frag" | ForEach-Object {
    $out = Join-Path $ShaderDir ($_.Name + ".qsb")
    Write-Host "Compiling $($_.Name) -> $($_.Name).qsb"
    & $qsb --glsl "100 es,120,150" --hlsl 50 --msl 12 -o $out -b $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "qsb failed for $($_.Name)" }
}

Write-Host "Done."
