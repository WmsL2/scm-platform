param(
    [string]$TaskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
)

$samples = Join-Path $TaskRoot '.codex-assets/official-ppt/samples/v5/catalog-minimal'
$runRoot = Join-Path $samples ('wps-export-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$wps = New-Object -ComObject KWPP.Application
$version = $wps.Version
$exports = [System.Collections.Generic.List[object]]::new()
try {
    Get-ChildItem -LiteralPath $samples -Filter '*.pptx' | ForEach-Object {
        $case = $_
        $renderDir = Join-Path $runRoot $case.BaseName
        New-Item -ItemType Directory -Path $renderDir -Force | Out-Null
        $presentation = $wps.Presentations.Open($case.FullName, $true, $false, $false)
        try {
            $presentation.Export($renderDir, 'PNG', 1600, 900)
            $exports.Add([pscustomobject]@{
                Source = $case.FullName
                Slides = $presentation.Slides.Count
                Output = $renderDir
            })
        }
        finally {
            $presentation.Close()
        }
    }
}
finally {
    $wps.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wps) | Out-Null
}

[pscustomobject]@{
    WPS = $version
    Exports = $exports.ToArray()
    Acceptance = 'Fictional file-level visual QA; customer final acceptance remains external'
} | ConvertTo-Json -Depth 5
