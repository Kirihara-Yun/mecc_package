param(
    [Parameter(Mandatory=$true)][string]$PresentationPath,
    [Parameter(Mandatory=$true)][string]$PdfPath
)
$ErrorActionPreference = 'Stop'
$pptWasRunning = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$pptTaskApp = $null
$pptTaskDeck = $null
try {
    $pptTaskApp = New-Object -ComObject PowerPoint.Application
    # Open the specific generated deck without creating a presentation window.
    $pptTaskDeck = $pptTaskApp.Presentations.Open($PresentationPath, -1, 0, 0)
    $pptTaskDeck.SaveAs($PdfPath, 32)
    Write-Output ('Exported ' + $pptTaskDeck.Slides.Count + ' slides to ' + $PdfPath)
}
finally {
    if ($null -ne $pptTaskDeck) {
        $pptTaskDeck.Close()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($pptTaskDeck) | Out-Null
    }
    if ($null -ne $pptTaskApp) {
        if (-not $pptWasRunning) { $pptTaskApp.Quit() }
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($pptTaskApp) | Out-Null
    }
}
