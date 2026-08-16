# e2e runner: launch the patched game in Ryujinx, navigate to a screen, capture, check.
#
#   .\run.ps1 -Case section-select
#   .\run.ps1 -Case section-select -SkipLaunch -SkipNavigate     # game already on-screen
#
# Navigation never trusts a fixed sleep: after each key it captures and asks
# checks\identify.py where we are, then acts on the answer.
param(
    [ValidateSet('section-select')] [string]$Case = 'section-select',
    [switch]$SkipLaunch,
    [switch]$SkipNavigate,
    [int]$MaxSteps = 22
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$root\lib\input.ps1"

$RYUJINX = 'D:\Apps\Ryujinx\Ryujinx.exe'
$GAME    = 'D:\Downloads\UNLOGICAL\UNLOGICAL [010068501FF9A000].xci'
$ROMFS   = 'D:\Downloads\010068501ff9a000\romfs'
$PY      = 'python'

$stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$out = Join-Path $root "out\$stamp"
New-Item -ItemType Directory -Force $out | Out-Null
$report = Join-Path $out 'report.txt'
function Say([string]$m) { $m; Add-Content -Path $report -Value $m }

Say "case      : $Case"
Say "artifacts : $out"
Say ''

# ---- preconditions -----------------------------------------------------------------
if (-not (Test-Path -LiteralPath $RYUJINX)) { throw "Ryujinx not found: $RYUJINX" }
if (-not [System.IO.File]::Exists($GAME)) {
    # Ryujinx only whispers this into its log and then sits on the game list
    throw "game file not found: $GAME"
}
$mod = "$env:APPDATA\Ryujinx\mods\contents\010068501ff9a000\vn-translation\romfs"
$link = Get-Item -Force $mod -ErrorAction SilentlyContinue
if (-not $link) { throw "mod path missing: $mod" }
Say "mod link  : $($link.LinkType) -> $($link.Target)"
if ("$($link.Target)".TrimEnd('\') -ne $ROMFS.TrimEnd('\')) {
    Say "WARNING   : mod link does not point at $ROMFS"
}
Say ''

# ---- static data checks (independent of the game) ----------------------------------
$dataExit = 0
foreach ($check in @('check_chapterdata.py', 'check_scripts.py')) {
    Say "--- checks\$check ---"
    $o = & $PY "$root\checks\$check" 2>&1
    if ($LASTEXITCODE -ne 0) { $dataExit = $LASTEXITCODE }
    $o | ForEach-Object { Say "  $_" }
    Say ''
}

# ---- launch ------------------------------------------------------------------------
if (-not $SkipLaunch) {
    Say '--- launching ---'
    Get-Process Ryujinx -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 3
    Start-Process -FilePath $RYUJINX -ArgumentList "`"$GAME`"" -WorkingDirectory (Split-Path $RYUJINX)
    # wait for the guest to actually start; the log is the only reliable signal
    $logDir = Join-Path (Split-Path $RYUJINX) 'Logs'
    $booted = $false
    foreach ($i in 1..40) {
        Start-Sleep -Seconds 3
        $log = Get-ChildItem $logDir -Filter *.log -EA SilentlyContinue |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($log -and (Select-String -Path $log.FullName -Pattern 'ApplyRomFsMods|EnsureSaveData' -Quiet -EA SilentlyContinue)) {
            Say "  guest started after ~$($i*3)s (RomFS mods applied)"
            $booted = $true
            break
        }
        if ($log -and (Select-String -Path $log.FullName -Pattern "Couldn't find any application" -Quiet -EA SilentlyContinue)) {
            throw 'Ryujinx could not open the game file (see its log)'
        }
    }
    if (-not $booted) { Say '  WARNING: never saw the guest start in the log; continuing anyway' }
    Start-Sleep -Seconds 8
}

# ---- navigate ----------------------------------------------------------------------
$shot = $null
$state = 'unknown'
$notices = 0
if (-not $SkipNavigate) {
    Say ''
    Say '--- navigating to section-select ---'
    for ($step = 1; $step -le $MaxSteps; $step++) {
        $file = Join-Path $out ('step{0:d2}.png' -f $step)
        $shot = Get-RyuShot -CopyTo $file
        if (-not $shot) { Say "  step $step : F8 produced nothing (window not focused?)"; Start-Sleep -Seconds 3; continue }
        # 2>&1 can yield an ErrorRecord, which has no .Trim(); force it through [string]
        $id = & $PY "$root\checks\identify.py" $shot 2>&1
        $state = ([string]($id | Select-Object -First 1)).Trim()
        Say ("  step {0,2} : {1,-15} {2}" -f $step, $state, (Split-Path $shot -Leaf))
        if ($state -eq 'section-select') { break }
        switch ($state) {
            'title'   { Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 10 }   # -> loading -> menu
            'menu'    {
                # read the cursor instead of assuming; `section` is index 2
                $cur = & $PY "$root\checks\menu_cursor.py" $shot 2>&1
                $parts = ($cur | Select-Object -First 1).Trim() -split ' ', 2
                $idx = [int]$parts[0]
                Say ("           cursor at index {0} ({1})" -f $idx, $parts[1])
                if ($idx -lt 0) { Send-RyuKeys -Keys @('DOWN'); break }
                $delta = 2 - $idx
                if ($delta -gt 0) { Send-RyuKeys -Keys @((1..$delta | ForEach-Object { 'DOWN' })) }
                elseif ($delta -lt 0) { Send-RyuKeys -Keys @((1..(-$delta) | ForEach-Object { 'UP' })) }
                Start-Sleep -Milliseconds 600
                Send-RyuKeys -Keys @('Z')
                Start-Sleep -Seconds 8
            }
            # ATTENTION then CAUTION: one A each, exactly two in the whole boot. Plus follows
            # immediately - the OP movie starts the moment the second notice clears, and waiting
            # first means sitting through it.
            'notice'  {
                $notices++
                Send-RyuKeys -Keys @('Z','PLUS','KPPLUS') -Gap 250
                Start-Sleep -Seconds 2
            }
            'loading' { Start-Sleep -Seconds 6 }
            'busy'    { Start-Sleep -Seconds 5 }                               # black / fading; never press
            # 'other' is the OP movie, which yields to Plus (Ryujinx's binding is the main-row
            # +, numpad + as a fallback). B backs out if we opened a screen by mistake instead.
            'other'   { Send-RyuKeys -Keys @('PLUS','KPPLUS'); Start-Sleep -Seconds 4 }
            default   { Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 4 }
        }
    }
} else {
    $shot = Get-RyuShot -CopyTo (Join-Path $out 'final.png')
    $state = (& $PY "$root\checks\identify.py" $shot 2>&1 | Select-Object -First 1).Trim()
    Say "  state: $state"
}

# ---- measure -----------------------------------------------------------------------
Say ''
if ($state -eq 'section-select' -and $shot) {
    $final = Join-Path $out 'final.png'
    Copy-Item $shot $final -Force
    Say '--- checks\measure_shot.py (entry *PRO-00-01, the default cursor position) ---'
    & $PY "$root\checks\measure_shot.py" $final '*PRO-00-01' 2>&1 | ForEach-Object { Say "  $_" }
} else {
    Say "FAIL never reached section-select (last state: $state)"
}

Say ''
$verdict = if ($dataExit -eq 0 -and $state -eq 'section-select') { 'PASS' } else { 'FAIL' }
Say "verdict: $verdict   (data checks exit=$dataExit, screen=$state)"
Say "report : $report"
if ($verdict -ne 'PASS') { exit 1 }
