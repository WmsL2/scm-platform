# Read-only WPS visual QA. Never quit an existing user WPS process or save a deck.
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$samples = Join-Path $taskRoot '.codex-assets/official-ppt/samples/v5/jd-festive-red-two-page'
$original = Join-Path $taskRoot '.codex-assets/official-ppt/originals/模版2.pptx'
$wps = New-Object -ComObject KWPP.Application
$version = $wps.Version
$opened = [System.Collections.Generic.List[object]]::new()
$exports = [System.Collections.Generic.List[object]]::new()
$temporaryOriginal = Join-Path $samples ('source-readonly-' + [guid]::NewGuid().ToString('N') + '.pptx')
try {
    # Export a uniquely named copy, leaving any source already open by the user alone.
    Copy-Item -LiteralPath $original -Destination $temporaryOriginal
    $cases = @(Get-ChildItem -LiteralPath $samples -File -Filter 'JD_FESTIVE_RED-v5-two-page-*.pptx')
    $cases += Get-Item -LiteralPath $temporaryOriginal
    foreach ($case in $cases) {
        $name = if ($case.FullName -eq $temporaryOriginal) { 'source' } else { $case.BaseName }
        $renderDir = Join-Path $samples ('rendered/' + $name)
        New-Item -ItemType Directory -Path $renderDir -Force | Out-Null
        $presentation = $wps.Presentations.Open($case.FullName, $true, $false, $false)
        $opened.Add($presentation)
        $count = $presentation.Slides.Count
        if ($count -lt 2) { throw ('WPS did not open the deck: ' + $case.FullName) }
        $presentation.Export($renderDir, 'PNG', 1600, 900)
        $exports.Add([pscustomobject]@{Deck=$name;Slides=$count;RenderDirectory=$renderDir})
        Write-Output ($name + ': ' + $count + ' slides exported')
    }
} finally {
    foreach ($presentation in $opened) {
        try { $presentation.Close() } catch { Write-Warning $_.Exception.Message }
    }
    # Only this unique temporary copy is removed; no recursive deletion.
    if (Test-Path -LiteralPath $temporaryOriginal) {
        Remove-Item -LiteralPath $temporaryOriginal
    }
}
[pscustomobject]@{
    Renderer='WPS KWPP.Application'
    Version=$version
    Exports=$exports.ToArray()
    Acceptance='Customer final visual acceptance, approved font and real-subject image QA pending'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $samples 'WPS-export-manifest.json') -Encoding utf8
