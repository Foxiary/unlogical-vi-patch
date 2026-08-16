# Focus the Ryujinx window, send scancode key presses, capture via Ryujinx's own F8 hotkey.
# Dot-source this file, then use Get-RyuWindow / Focus-Ryu / Send-RyuKeys / Get-RyuShot.

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class RyuInput {
    [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT {
        public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)] public struct INPUT {
        public uint type; public KEYBDINPUT ki; public int pad1; public int pad2;
    }
    [DllImport("user32.dll")] static extern uint SendInput(uint n, INPUT[] p, int size);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern void SwitchToThisWindow(IntPtr h, bool alt);
    [DllImport("user32.dll")] static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
    [DllImport("user32.dll")] static extern bool AttachThreadInput(uint from, uint to, bool attach);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }

    const uint SCANCODE = 0x0008, EXTENDED = 0x0001, KEYUP = 0x0002;

    public static void Key(ushort scan, bool ext, bool up) {
        INPUT[] i = new INPUT[1];
        i[0].type = 1;
        i[0].ki.wScan = scan;
        i[0].ki.dwFlags = SCANCODE | (ext ? EXTENDED : 0) | (up ? KEYUP : 0);
        SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }

    // Windows blocks foreground changes requested by a background process. Tap ALT, attach to
    // the target's input queue, then fall back to SwitchToThisWindow.
    //
    // The ALT tap is only for stealing focus, and it MUST NOT run when the window already has
    // it: Send-RyuKeys calls this before every key, so an unconditional ALT meant the game saw
    // ALT immediately before each press. That swallowed presses - sending DOWN,DOWN from
    // NEW GAME advanced the cursor only to LOAD, so the runner opened LOAD instead of `section`.
    public static bool Focus(IntPtr h) {
        if (GetForegroundWindow() == h) { return true; }
        ShowWindow(h, 9);                                  // SW_RESTORE
        Key(0x38, false, false); Key(0x38, false, true);    // ALT
        uint tgt = GetWindowThreadProcessId(h, IntPtr.Zero);
        uint me = GetCurrentThreadId();
        AttachThreadInput(me, tgt, true);
        SetForegroundWindow(h);
        BringWindowToTop(h);
        AttachThreadInput(me, tgt, false);
        if (GetForegroundWindow() != h) { SwitchToThisWindow(h, true); }
        System.Threading.Thread.Sleep(400);
        return GetForegroundWindow() == h;
    }
}
'@ -ErrorAction SilentlyContinue

# Set 1 scancodes. Arrow keys are extended (E0-prefixed).
$script:RyuScan = @{
    'Z' = @(0x2C, $false); 'X' = @(0x2D, $false); 'C' = @(0x2E, $false); 'V' = @(0x2F, $false)
    'W' = @(0x11, $false); 'A' = @(0x1E, $false); 'S' = @(0x1F, $false); 'D' = @(0x20, $false)
    'Q' = @(0x10, $false); 'E' = @(0x12, $false); 'U' = @(0x16, $false); 'O' = @(0x18, $false)
    'UP' = @(0x48, $true); 'DOWN' = @(0x50, $true); 'LEFT' = @(0x4B, $true); 'RIGHT' = @(0x4D, $true)
    'ENTER' = @(0x1C, $false); 'PLUS' = @(0x0D, $false); 'MINUS' = @(0x0C, $false)
    'KPPLUS' = @(0x4E, $false)   # numpad +, in case Ryujinx's "Plus" binding means this one
    'F8' = @(0x42, $false); 'F4' = @(0x3E, $false); 'F5' = @(0x3F, $false)
}

function Get-RyuWindow {
    Get-Process Ryujinx -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending | Select-Object -First 1
}

function Focus-Ryu {
    param([int]$Tries = 4)
    $p = Get-RyuWindow
    if (-not $p) { throw 'no Ryujinx window found' }
    for ($i = 1; $i -le $Tries; $i++) {
        if ([RyuInput]::Focus($p.MainWindowHandle)) { return $true }
        Start-Sleep -Milliseconds (250 * $i)
    }
    Write-Warning "could not raise the Ryujinx window after $Tries tries; keys and F8 will not land"
    $false
}

function Send-RyuKeys {
    param([string[]]$Keys, [int]$Hold = 110, [int]$Gap = 400)
    [void](Focus-Ryu)
    foreach ($name in $Keys) {
        $k = $script:RyuScan[$name.ToUpper()]
        if (-not $k) { throw "unknown key '$name'" }
        [RyuInput]::Key([uint16]$k[0], [bool]$k[1], $false)
        Start-Sleep -Milliseconds $Hold
        [RyuInput]::Key([uint16]$k[0], [bool]$k[1], $true)
        Start-Sleep -Milliseconds $Gap
    }
}

# Press F8 and return the path of the PNG Ryujinx wrote, or $null on timeout.
function Get-RyuShot {
    param([string]$CopyTo = $null, [int]$TimeoutSec = 12)
    $dir = "$env:APPDATA\Ryujinx\screenshots"
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    $before = New-Object 'System.Collections.Generic.HashSet[string]'
    Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue | ForEach-Object { [void]$before.Add($_.Name) }
    Send-RyuKeys -Keys @('F8') -Gap 200
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $new = $null
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 400
        $new = Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue |
               Where-Object { -not $before.Contains($_.Name) } |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($new) { break }
    }
    if (-not $new) { return $null }
    # wait for the file to stop growing so the PNG is complete before anything reads it
    $last = -1
    for ($i = 0; $i -lt 20; $i++) {
        $len = (Get-Item $new.FullName).Length
        if ($len -eq $last -and $len -gt 0) { break }
        $last = $len; Start-Sleep -Milliseconds 200
    }
    if ($CopyTo) { Copy-Item $new.FullName $CopyTo -Force; return $CopyTo }
    $new.FullName
}
