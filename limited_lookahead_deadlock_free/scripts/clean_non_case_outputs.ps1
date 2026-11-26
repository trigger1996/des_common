param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath $Manifest -Raw -Encoding utf8 | ConvertFrom-Json
$workspacePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$outputsPath = (Resolve-Path -LiteralPath (Join-Path $workspacePath 'outputs')).Path
if ($outputsPath -ne $plan.outputs) { throw 'Output root does not match the inspected workspace.' }
$boundary = $outputsPath.TrimEnd('\') + '\'
foreach ($entry in $plan.targets) {
    $targetPath = (Resolve-Path -LiteralPath $entry.path).Path
    if (-not $targetPath.StartsWith($boundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing an out-of-workspace target: $targetPath"
    }
    $item = Get-Item -LiteralPath $targetPath -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Refusing a linked target: $targetPath"
    }
}
foreach ($entry in $plan.targets) {
    Remove-Item -LiteralPath $entry.path -Recurse -Force
}
