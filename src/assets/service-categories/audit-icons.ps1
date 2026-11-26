Add-Type -AssemblyName System.Drawing
$names = @('photography','videography','video-editing','graphic-design','animation-and-vfx','fashion-design','logo-and-branding-design','advertisement-production','promotional-video-production','digital-marketing','travel-video-editing','influencer-reel-editing','vfx','website-development','mobile-application-development','custom-software-development','portfolio-development','e-commerce-development','crm-and-erp-solutions','ai-and-automation','cloud-and-devops','software-maintenance','it-consulting','cybersecurity-services','api-development-and-integration')
foreach ($size in @(128,64)) {
  $canvas = New-Object System.Drawing.Bitmap(640,640)
  $graphics = [System.Drawing.Graphics]::FromImage($canvas)
  $graphics.Clear([System.Drawing.Color]::White)
  $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  for ($index = 0; $index -lt $names.Count; $index++) {
    $image = [System.Drawing.Image]::FromFile((Join-Path $PSScriptRoot ($names[$index] + '-256.png')))
    $left = ($index % 5) * 128 + (128-$size)/2
    $top = [int][Math]::Floor($index/5)*128 + (128-$size)/2
    $graphics.DrawImage($image,$left,$top,$size,$size)
    $image.Dispose()
  }
  $canvas.Save((Join-Path $PSScriptRoot "originals/audit-white-$size.png"),[System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $canvas.Dispose()
}
Write-Output 'White composites complete: 25 icons at128 and64 pixels.'
