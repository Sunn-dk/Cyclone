param(
    [string]$Serial = '',
    [ValidateRange(10,180)][int]$Seconds = 120,
    [string]$Output = 'results/video/Cyclone-demo.mp4'
)
$ErrorActionPreference='Stop'
$command=Get-Command adb -ErrorAction SilentlyContinue
$adb=if($command){$command.Source}else{Join-Path $env:LOCALAPPDATA 'Android/Sdk/platform-tools/adb.exe'}
if(-not(Test-Path -LiteralPath $adb)){throw 'adb not found'}
if(-not $Serial){
    $devices=@(& $adb devices | Select-Object -Skip 1 | Where-Object {$_ -match '\sdevice$'} | ForEach-Object {($_ -split '\s+')[0]})
    if($devices.Count -ne 1){throw 'Pass -Serial when not exactly one device is connected'}
    $Serial=$devices[0]
}
$resolvedOutput=[IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null
$remote='/sdcard/Android/data/com.example.imageopt/files/demo/Cyclone-demo.mp4'
Write-Host 'Unlock Sony, close floating chat bubbles/notifications, open Cyclone and prepare the local image server.'
Write-Host 'This records the screen without microphone audio. Record narration separately if needed.'
Read-Host "Press Enter when ready to record for $Seconds seconds"
& $adb -s $Serial shell mkdir -p '/sdcard/Android/data/com.example.imageopt/files/demo'
& $adb -s $Serial shell screenrecord --size 720x1680 --bit-rate 4000000 --time-limit $Seconds $remote
if($LASTEXITCODE -ne 0){throw 'screenrecord failed; keep the phone unlocked and check free storage'}
& $adb -s $Serial pull $remote $resolvedOutput
if($LASTEXITCODE -ne 0){throw 'Could not pull the video'}
Write-Host "Video file: $resolvedOutput"
Write-Host 'Watch the full file before marking D8 video complete. This script does not prove the demonstration content.'
