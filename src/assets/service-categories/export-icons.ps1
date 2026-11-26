Add-Type -AssemblyName System.Drawing
$creativeNames = @('photography','videography','video-editing','graphic-design','animation-and-vfx','fashion-design','logo-and-branding-design','advertisement-production','promotional-video-production','digital-marketing','travel-video-editing','influencer-reel-editing','vfx')
$professionalNames = @('website-development','mobile-application-development','custom-software-development','portfolio-development','e-commerce-development','crm-and-erp-solutions','ai-and-automation','cloud-and-devops','software-maintenance','it-consulting','cybersecurity-services','api-development-and-integration')
$exportRoot = $PSScriptRoot
foreach ($family in @('creative','professional')) {
  $names = if ($family -eq 'creative') { $creativeNames } else { $professionalNames }
  $sheet = [System.Drawing.Bitmap]::FromFile((Join-Path $exportRoot "originals/$family-sheet-transparent.png"))
  for ($index = 0; $index -lt $names.Count; $index++) {
    $left = [int][Math]::Round(($index % 4) * $sheet.Width / 4.0)
    $top = [int][Math]::Round([Math]::Floor($index / 4.0) * $sheet.Height / 4.0)
    $right = [int][Math]::Round((($index % 4) + 1) * $sheet.Width / 4.0)
    $bottom = [int][Math]::Round(([Math]::Floor($index / 4.0) + 1) * $sheet.Height / 4.0)
    $rectangle = New-Object System.Drawing.Rectangle($left,$top,($right-$left),($bottom-$top))
    $bitmap = New-Object System.Drawing.Bitmap(256,256,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $targetRectangle = New-Object System.Drawing.Rectangle(0,0,256,256)
    $graphics.DrawImage($sheet,$targetRectangle,$rectangle,[System.Drawing.GraphicsUnit]::Pixel)
    $target = Join-Path $exportRoot ($names[$index] + '-256.png')
    if (Test-Path -LiteralPath $target) { throw "Refusing to overwrite $target" }
    $bitmap.Save($target,[System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    Write-Output $target
  }
  $sheet.Dispose()
}
