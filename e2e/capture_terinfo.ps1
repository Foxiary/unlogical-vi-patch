# Chụp băng-rôn [terinfo] trên máy thật.
#
#   .\capture_terinfo.ps1 -Slot 3            # dựng save trước bằng e2e\make_save.py
#   .\capture_terinfo.ps1 -Slot 3 -SkipLaunch
#
# Băng-rôn chỉ hiện ~1,5 giây ([wait time=1500] ngay sau lệnh), nên không canh một phát
# ăn ngay được. Cách làm: vào đúng block bằng save đã dựng, rồi **bắn F8 liên tục** trong
# lúc bấm A tiến thoại, sau đó lọc ảnh nào có băng-rôn.
param(
    [int]$Slot = 3,
    [switch]$SkipLaunch,
    [int]$Burst = 26,
    [int]$Advance = 6
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\input.ps1"

$ryu  = 'D:\Apps\Ryujinx\Ryujinx.exe'
$game = 'D:\Downloads\UNLOGICAL\UNLOGICAL [010068501FF9A000].xci'
$out  = Join-Path $PSScriptRoot ('out\terinfo_{0}' -f (Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'))
New-Item -ItemType Directory -Force $out | Out-Null
function Say([string]$m) { $m; Add-Content -Path (Join-Path $out 'report.txt') -Value $m }
Say "slot      : $Slot"
Say "out       : $out"

if (-not $SkipLaunch) {
    # -LiteralPath BẮT BUỘC: tên file game có `[010068501FF9A000]`, mà `[...]` với
    # Test-Path là lớp ký tự đại diện — không có -LiteralPath thì file có thật vẫn báo
    # không thấy.
    foreach ($p in @($ryu, $game)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "không thấy: $p" }
    }
    Get-Process Ryujinx -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Start-Process $ryu -ArgumentList "`"$game`""
    Say 'đã khởi động Ryujinx, chờ cửa sổ hiện ra…'
}

# Chờ CỬA SỔ trước khi gửi phím. Không có bước này thì vòng boot gọi Focus-Ryu ngay ở
# giây thứ 2 và ném 'no Ryujinx window found' — Ryujinx mất khoảng 20-40 giây mới dựng
# xong cửa sổ và nạp game.
for ($i = 1; $i -le 60; $i++) {
    if (Get-RyuWindow) { Say ("cửa sổ Ryujinx hiện sau ~{0}s" -f ($i * 2)); break }
    Start-Sleep -Seconds 2
}
if (-not (Get-RyuWindow)) { throw 'Ryujinx không dựng được cửa sổ sau 120s' }
Start-Sleep -Seconds 5

# --- đi qua boot: notice -> phim -> title ------------------------------------------------
$py = 'python'
$state = ''
for ($i = 1; $i -le 60; $i++) {
    Start-Sleep -Seconds 2
    $shot = Get-RyuShot -CopyTo (Join-Path $out ('boot_{0:d2}.png' -f $i)) -TimeoutSec 15
    if (-not $shot) { continue }
    $state = (& $py "$PSScriptRoot\checks\identify.py" $shot) 2>&1 | Select-Object -Last 1
    Say ("boot {0:d2}  state={1}" -f $i, $state)
    switch -Regex ($state) {
        'title'            { break }
        'notice'           { Send-RyuKeys -Keys @('Z'); Start-Sleep -Milliseconds 300;
                             Send-RyuKeys -Keys @('PLUS') }
        'loading|busy'     { }
        default            { Send-RyuKeys -Keys @('PLUS') }
    }
    if ($state -match 'title') { break }
}
if ($state -notmatch 'title') { Say "CẢNH BÁO: chưa tới TITLE (state=$state), vẫn thử tiếp" }

# --- TITLE -> MENU -> LOAD ---------------------------------------------------------------
Send-RyuKeys -Keys @('Z') -Gap 1200                       # vào MENU
Start-Sleep -Seconds 1
$shot = Get-RyuShot -CopyTo (Join-Path $out 'menu.png')
$cur  = (& $py "$PSScriptRoot\checks\menu_cursor.py" $shot) 2>&1 | Select-Object -Last 1
Say "con trỏ MENU: $cur"
# LOAD là mục index 1 (NEW GAME=0, LOAD=1, SECTION=2)
$idx = 0
if ($cur -match '(\d+)') { $idx = [int]$Matches[1] }
$steps = 1 - $idx
if ($steps -gt 0) { Send-RyuKeys -Keys (@('DOWN') * $steps) }
elseif ($steps -lt 0) { Send-RyuKeys -Keys (@('UP') * (-$steps)) }
Send-RyuKeys -Keys @('Z') -Gap 1500
Get-RyuShot -CopyTo (Join-Path $out 'load_list.png') | Out-Null
Say 'đã mở LOAD — chọn slot bằng tay nếu ảnh load_list.png cho thấy con trỏ sai chỗ'

# slot 3 nằm ở hàng 4 của trang 1 (0-based), đi xuống $Slot lần
Send-RyuKeys -Keys (@('DOWN') * $Slot)
Get-RyuShot -CopyTo (Join-Path $out 'load_pick.png') | Out-Null
Send-RyuKeys -Keys @('Z') -Gap 1500
Send-RyuKeys -Keys @('Z') -Gap 3000            # xác nhận "load?" nếu có
Get-RyuShot -CopyTo (Join-Path $out 'loaded.png') | Out-Null
Say 'đã nạp save, bắt đầu bắn F8'

# --- bắn F8 xen kẽ bấm A -----------------------------------------------------------------
for ($i = 1; $i -le $Burst; $i++) {
    Get-RyuShot -CopyTo (Join-Path $out ('burst_{0:d2}.png' -f $i)) -TimeoutSec 8 | Out-Null
    if ($i % 2 -eq 0) { Send-RyuKeys -Keys @('Z') -Gap 150 }
}
Say "xong — $Burst ảnh trong $out"
Say 'lọc ảnh có băng-rôn: python e2e\checks\find_terinfo.py <thư mục>'
