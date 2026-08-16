# Ad-hoc: reach an ADV line and capture the nameplate, to check the speaker-name driven colour.
# Boots, clears the notices, opens LOAD, takes the first slot that has data, then advances.
param([int]$Advance = 6)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$root\lib\input.ps1"
$PY = 'python'
$out = Join-Path $root ('out\plate_' + (Get-Date -Format 'HH-mm-ss'))
New-Item -ItemType Directory -Force $out | Out-Null

function State($shot) { ([string]((& $PY "$root\checks\identify.py" $shot 2>&1) | Select-Object -First 1)).Trim() }

# --- get to the main menu using the same state machine as run.ps1
$state = ''
for ($i = 1; $i -le 16; $i++) {
    $shot = Get-RyuShot -CopyTo (Join-Path $out ('boot{0:d2}.png' -f $i))
    if (-not $shot) { Start-Sleep -Seconds 3; continue }
    $state = State $shot
    "boot $i : $state"
    if ($state -eq 'menu') { break }
    switch ($state) {
        'title'   { Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 10 }
        'notice'  { Send-RyuKeys -Keys @('Z','PLUS','KPPLUS') -Gap 250; Start-Sleep -Seconds 2 }
        'loading' { Start-Sleep -Seconds 6 }
        'busy'    { Start-Sleep -Seconds 5 }
        default   { Send-RyuKeys -Keys @('PLUS','KPPLUS'); Start-Sleep -Seconds 4 }
    }
}
if ($state -ne 'menu') { "never reached the menu (last: $state)"; exit 1 }

# --- LOAD is index 1
$cur = & $PY "$root\checks\menu_cursor.py" (Get-RyuShot -CopyTo (Join-Path $out 'menu.png')) 2>&1
$idx = [int](([string]($cur | Select-Object -First 1)).Trim() -split ' ')[0]
"menu cursor at $idx, moving to LOAD (1)"
$d = 1 - $idx
if ($d -gt 0) { Send-RyuKeys -Keys @((1..$d | ForEach-Object { 'DOWN' })) }
elseif ($d -lt 0) { Send-RyuKeys -Keys @((1..(-$d) | ForEach-Object { 'UP' })) }
Start-Sleep -Milliseconds 600
Send-RyuKeys -Keys @('Z')
Start-Sleep -Seconds 5
[void](Get-RyuShot -CopyTo (Join-Path $out 'load_screen.png'))

# --- confirm the highlighted slot, then confirm the "load this?" prompt
Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 2
[void](Get-RyuShot -CopyTo (Join-Path $out 'load_prompt.png'))
Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 12
[void](Get-RyuShot -CopyTo (Join-Path $out 'loaded.png'))

# --- advance a few lines and capture each, so at least one lands on a character nameplate
for ($i = 1; $i -le $Advance; $i++) {
    Send-RyuKeys -Keys @('Z'); Start-Sleep -Seconds 2
    [void](Get-RyuShot -CopyTo (Join-Path $out ('adv{0:d2}.png' -f $i)))
}
"artifacts: $out"
