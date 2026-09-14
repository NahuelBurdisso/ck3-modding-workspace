Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$sig = @"
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
"@
Add-Type -MemberDefinition $sig -Name Win -Namespace Native
$p = Get-Process ck3 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($p) {
  [Native.Win]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
  [Native.Win]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
  Start-Sleep -Seconds 2
}
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$bmp.Save("D:/ck3/_shot.png", [System.Drawing.Imaging.ImageFormat]::Png)

# crops: top HUD bar and bottom-left character panel
$crop = {
  param($x, $y, $w, $h, $out, $scale)
  $r = New-Object System.Drawing.Rectangle $x, $y, $w, $h
  $sub = $bmp.Clone($r, $bmp.PixelFormat)
  $big = New-Object System.Drawing.Bitmap ([int]($w * $scale)), ([int]($h * $scale))
  $gg = [System.Drawing.Graphics]::FromImage($big)
  $gg.InterpolationMode = "HighQualityBicubic"
  $gg.DrawImage($sub, 0, 0, $big.Width, $big.Height)
  $big.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
}
& $crop 0 0 2560 60 "D:/ck3/_shot_top.png" 1.0
& $crop 0 1080 700 360 "D:/ck3/_shot_char.png" 1.4
Write-Output "ok"
