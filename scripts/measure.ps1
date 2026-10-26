param(
    [Parameter(Mandatory=$true)][ValidateSet('A','B','C','D','E')][string]$Config,
    [Parameter(Mandatory=$true)][ValidatePattern('^TC0[1-8][ab]?$')][string]$Tc,
    [ValidateSet(100,500,1000)][int]$Count = 100,
    [ValidateSet('Load','AutoScroll')][string]$Scenario = 'AutoScroll',
    [string]$Serial = '',
    [string]$SourceNote = '',
    [switch]$Clear,
    [switch]$WarmProcess
)
$ErrorActionPreference = 'Stop'
if ($Clear -and $WarmProcess) { throw '-Clear and -WarmProcess cannot be used together.' }

$adbCommand = Get-Command adb -ErrorAction SilentlyContinue
if ($adbCommand) {
    $adbPath = $adbCommand.Source
} else {
    $adbPath = Join-Path $env:LOCALAPPDATA 'Android/Sdk/platform-tools/adb.exe'
    if (-not (Test-Path -LiteralPath $adbPath)) {
        throw 'adb not found. Add Android SDK platform-tools to PATH, then reopen PowerShell.'
    }
}
function Invoke-Adb {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$AdbArgs)
    $prefix = @()
    if ($script:selectedSerial) { $prefix = @('-s', $script:selectedSerial) }
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $result = & $adbPath @prefix @AdbArgs 2>&1
        $adbExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($adbExit -ne 0) { throw "adb failed: $($AdbArgs -join ' ')`n$($result -join [Environment]::NewLine)" }
    $result
}

$script:selectedSerial = ''
$inventory = @(Invoke-Adb devices -l)
$devices = @($inventory | ForEach-Object {
    if ($_ -match '^(\S+)\s+(device|unauthorized|offline)(?:\s|$)') {
        [PSCustomObject]@{ Serial=$Matches[1]; State=$Matches[2] }
    }
})
if ($Serial) {
    $chosen = $devices | Where-Object { $_.Serial -eq $Serial }
    if (-not $chosen -or $chosen.State -ne 'device') {
        throw "Device '$Serial' is not ready. Unlock Sony, enable USB debugging and accept its RSA prompt. Run adb devices -l."
    }
    $script:selectedSerial = $Serial
} else {
    $ready = @($devices | Where-Object { $_.State -eq 'device' })
    if ($ready.Count -ne 1) {
        throw "Need exactly one ready device, or pass -Serial SERIAL. Found $($ready.Count). Unlock Sony and accept USB debugging; disconnect emulator if necessary.`n$($inventory -join [Environment]::NewLine)"
    }
    $script:selectedSerial = $ready[0].Serial
}

$pkg = 'com.example.imageopt'
$startedAt = (Get-Date).ToString('o')
$folder = Join-Path $PSScriptRoot "../results/${Config}_${Tc}_${Count}_${Scenario}_$(Get-Date -Format yyyyMMdd_HHmmss_fff)"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$apkPaths = @(Invoke-Adb shell pm path $pkg)
if (($apkPaths -join '') -notmatch 'package:') { throw 'ImageOpt is not installed. Install the benchmark APK before measuring.' }
$apkPaths | Out-File "$folder/apk-path.txt" -Encoding utf8
Invoke-Adb shell dumpsys package $pkg | Out-File "$folder/package.txt" -Encoding utf8
$deviceModel = (Invoke-Adb shell getprop ro.product.model | Out-String).Trim()
$androidSdk = (Invoke-Adb shell getprop ro.build.version.sdk | Out-String).Trim()
$androidVersion = (Invoke-Adb shell getprop ro.build.version.release | Out-String).Trim()
Write-Host "Device: $deviceModel | Android $androidVersion (SDK $androidSdk) | $script:selectedSerial"
Write-Host 'Use the benchmark APK for measurements. Keep source, count, battery/temperature, orientation and network conditions consistent.'

if ($Clear) {
    Write-Warning '-Clear erases ImageOpt settings, caches and previous exported files. Copy any needed exports before continuing.'
    Read-Host 'Press Enter to perform the requested app-data clear, or Ctrl+C to cancel'
    $clearResult = Invoke-Adb shell pm clear $pkg
    if (($clearResult -join '') -notmatch 'Success') { throw "App-data clear did not report Success: $clearResult" }
} elseif (-not $WarmProcess) {
    Invoke-Adb shell am force-stop $pkg | Out-Null
}
if (-not $WarmProcess) {
    Invoke-Adb shell am start -W -n "$pkg/.MainActivity" --es config $Config --ei count $Count |
        Out-File "$folder/start.txt" -Encoding utf8
    Write-Host 'Process restarted; disk cache is retained unless -Clear was used. Set the desired source again after -Clear.'
} else {
    Write-Host 'WarmProcess: app was NOT stopped or relaunched. Confirm the app is already open and uses the requested config/count.'
}

if (-not $SourceNote) {
    $SourceNote = Read-Host 'Enter source URL, format, URL version, delay_ms, error toggle and network condition shown in the app'
}
$cacheCondition = Read-Host 'Enter intended cache condition: cold / disk-warm / memory-warm (and preparation steps)'
Write-Host 'Prepare the app now. Cold cache: Experiment > clear RAM + disk. Disk-warm: keep disk, clear RAM only. Memory-warm: preserve process and RAM.'
Write-Host "Verify actual config=$Config and count=$Count. Do not change settings after preparation; settings changes may clear RAM."
if ($Scenario -eq 'Load') {
    Write-Host 'LOAD scenario: stay in Experiment before Start measurement, or stay on the list before Reload. Do not tap either yet.'
    Write-Host 'Start measurement returns to the list. Reload starts a new run. Auto-scroll also starts a NEW run, so do not use it during this Load trial.'
} else {
    Write-Host 'AUTOSCROLL scenario: return to the list and let it settle. Do not tap Auto-scroll yet. Auto-scroll itself begins a new run.'
}
Read-Host 'When source/cache/config/count preparation is complete, press Enter BEFORE starting the selected scenario'
Invoke-Adb shell dumpsys meminfo $pkg | Out-File "$folder/memory-before.txt" -Encoding utf8
Invoke-Adb shell dumpsys gfxinfo $pkg reset | Out-Null
$windowStartedAt = (Get-Date).ToString('o')
if ($Scenario -eq 'Load') {
    Read-Host 'Now tap Start measurement (Experiment) OR Reload (list), wait for images, open Experiment to stop, then press Enter here. Do not tap Auto-scroll'
} else {
    Read-Host 'Now tap Auto-scroll ONCE; wait until the app reports stopped (about 8 seconds), remain on the list, then press Enter here'
}
$windowEndedAt = (Get-Date).ToString('o')
Invoke-Adb shell dumpsys gfxinfo $pkg | Out-File "$folder/gfxinfo.txt" -Encoding utf8
Invoke-Adb shell dumpsys gfxinfo $pkg framestats | Out-File "$folder/framestats.txt" -Encoding utf8
Invoke-Adb shell dumpsys meminfo $pkg | Out-File "$folder/memory-after.txt" -Encoding utf8
Read-Host 'Open Experiment, confirm the run is stopped, export its ZIP (Share results) and/or CSV. Wait for export success, then press Enter'
Invoke-Adb logcat -d -v threadtime -s 'IMG_BENCH:I' | Out-File "$folder/logcat.txt" -Encoding utf8
$remoteFiles = "/sdcard/Android/data/$pkg/files"
$exportStatus = 'not copied'
try {
    New-Item -ItemType Directory -Force -Path "$folder/exports" | Out-Null
    Invoke-Adb pull "$remoteFiles/." "$folder/exports" | Out-File "$folder/pull.txt" -Encoding utf8
    $exportStatus = 'copied; may include older runs, match runId and timestamp in summary.json'
} catch {
    $exportStatus = $_.Exception.Message
    Write-Warning "Could not pull exports. Use the app Share results button to save/send the ZIP yourself. $exportStatus"
}
[ordered]@{
    ScriptStartedAt=$startedAt
    MeasurementWindowStartedAt=$windowStartedAt
    MeasurementWindowEndedAt=$windowEndedAt
    Serial=$script:selectedSerial
    DeviceModel=$deviceModel
    AndroidVersion=$androidVersion
    AndroidSdk=$androidSdk
    RequestedConfig=$Config
    RequestedCount=$Count
    Tc=$Tc
    Scenario=$Scenario
    ClearAppData=[bool]$Clear
    KeepWarmProcess=[bool]$WarmProcess
    UserReportedSourceAndConditions=$SourceNote
    UserReportedCachePreparation=$cacheCondition
    ExportStatus=$exportStatus
    Notes=@(
        'Config/count/source/cache fields are requested or user-reported; verify against the exported summary.json and requests.csv.',
        'memory-before/after are PSS snapshots, not peak memory. Sampled peak is in the app ZIP.',
        'dumpsys gfxinfo spans the manual window and may include navigation. It differs from the app finite-session FrameMetrics.',
        'App frame-over-display-period is not Android official jank. Retain both definitions when reporting.',
        'Logcat may contain previous runs; select matching RUN_START/RUN_STOP and runId.',
        'exports may include prior CSV/ZIP files; each summary.json records build type, device, count, source and run ID.',
        'The script does not change network, battery or other phone settings.'
    )
} | ConvertTo-Json -Depth 4 | Out-File "$folder/run.json" -Encoding utf8
Write-Host "Saved: $folder"
Write-Host 'Repeat the same scenario at least 3 times per configuration; record actual results, including errors and incomplete requests.'

