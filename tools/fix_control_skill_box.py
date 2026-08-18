# -*- coding: utf-8 -*-
"""Bật auto-size cho hai ô chữ của màn Terminal → CONTROL (danh sách kỹ năng).

Yêu cầu 18/08: `TerminalControlSkillData` để caption **một dòng phẳng là cố ý**, cho
TMP tự ngắt — vì bám theo chỗ ngắt của bản Nhật thì tiếng Việt bị cắt giữa cụm
(`…đã bị loại để⏎hồi sinh.`). Nhưng hai component này đang `m_enableAutoSizing = 0`,
nên chữ không co được: wrap ra bao nhiêu dòng thì tràn bấy nhiêu, không có đường lùi.

    CaptionText (TMP) (1) < Caption < Caption_Mask < TerminalBgBase < Terminal_Control
    RequestText (TMP)     < Request < Request_Mask < TerminalBgBase < Terminal_Control

Cả hai đều `wrap=1, autosize=0, size=31, min=18, max=72`.

**Ghim `m_fontSizeMax` về đúng `m_fontSize` gốc (31), không để 72.** Bật auto-size mà
để max 72 thì mục NGẮN bị phóng to — cùng cái bẫy đã ghi trong `fix_synopsis_box.py`.
Sau khi vá, chữ chỉ có thể co xuống (sàn 18), không bao giờ nở ra.

    python tools\\fix_control_skill_box.py           # chạy thử
    python tools\\fix_control_skill_box.py --apply
    python tools\\fix_control_skill_box.py --check   # chốt, lỗi -> exit 1
"""
import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import UnityPy   # noqa: E402

BUNDLE = os.path.join(ROOT, "romfs", "Data", "StreamingAssets", "ui", "ui_jp")
BACKUP = os.path.join(ROOT, "_backup", "ui_jp.controlskill")
APPLY = "--apply" in sys.argv
CHECK = "--check" in sys.argv

TARGETS = {"CaptionText (TMP) (1)", "RequestText (TMP)"}
PARENT = "Terminal_Control"


def backup_path(base):
    """Không bỏ qua backup vì tên đã tồn tại — xem bẫy trong memory merge."""
    if not os.path.exists(base):
        return base
    i = 2
    while os.path.exists("%s-%d" % (base, i)):
        i += 1
    return "%s-%d" % (base, i)


def ancestors(go, depth=8):
    out, cur = [], go
    for _ in range(depth):
        out.append(cur.m_Name)
        tr = None
        for c in cur.m_Components:
            cc = c.read()
            if cc.object_reader.type.name in ("RectTransform", "Transform"):
                tr = cc
                break
        # Transform gốc có `m_Father` là PPtr RỖNG (m_PathID == 0), không phải None —
        # gọi .read() lên nó thì UnityPy raise "PPtr can't deref with m_PathID == 0".
        if tr is None or tr.m_Father is None or getattr(tr.m_Father, "m_PathID", 0) == 0:
            break
        p = tr.m_Father.read()
        if p is None:
            break
        cur = p.m_GameObject.read()
    return out


def collect(env):
    """[(object_reader, tên GameObject, typetree)] cho đúng hai ô của Terminal_Control."""
    found = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if not isinstance(t, dict) or "m_enableAutoSizing" not in t:
            continue
        try:
            go = o.read().m_GameObject.read()
        except Exception:
            continue
        if go.m_Name not in TARGETS:
            continue
        if PARENT not in ancestors(go):
            continue
        found.append((o, go.m_Name, t))
    return found


def main():
    env = UnityPy.load(BUNDLE)
    found = collect(env)
    if len(found) != 2:
        raise SystemExit("chờ 2 component dưới %s, thấy %d" % (PARENT, len(found)))

    for _, name, t in found:
        print("  %-22s size=%-5s autosize=%s min=%s max=%s wrap=%s"
              % (name, t["m_fontSize"], t["m_enableAutoSizing"],
                 t["m_fontSizeMin"], t["m_fontSizeMax"], t["m_TextWrappingMode"]))

    bad = [n for _, n, t in found
           if t["m_enableAutoSizing"] != 1 or t["m_fontSizeMax"] != t["m_fontSize"]]
    if CHECK:
        if bad:
            print("\nFAIL chưa bật auto-size / max chưa ghim: %s" % ", ".join(bad))
            print("chạy `python tools\\fix_control_skill_box.py --apply`")
            raise SystemExit(1)
        print("\nPASS cả 2 ô đã auto-size, max ghim đúng cỡ gốc")
        return
    if not bad:
        print("\nkhông có gì để sửa")
        return

    plan = []
    for o, name, t in found:
        new = dict(t)
        new["m_enableAutoSizing"] = 1
        new["m_fontSizeMax"] = t["m_fontSize"]      # ghim, không để 72
        plan.append((o, name, t, new))
        print("\n-> %s" % name)
        print("     autosize %s -> %s" % (t["m_enableAutoSizing"], new["m_enableAutoSizing"]))
        print("     fontSizeMax %s -> %s   (sàn giữ %s)"
              % (t["m_fontSizeMax"], new["m_fontSizeMax"], t["m_fontSizeMin"]))
        for k in ("m_fontSize", "m_TextWrappingMode", "m_fontSizeMin", "m_margin"):
            assert new.get(k) == t.get(k), "%s đổi ngoài dự kiến" % k

    if not APPLY:
        print("\nCHẠY THỬ — thêm --apply để ghi")
        return

    bak = backup_path(BACKUP)
    shutil.copy2(BUNDLE, bak)
    print("\nbackup ->", bak)
    for o, name, _old, new in plan:
        o.save_typetree(new)
    with open(BUNDLE, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print("đã ghi", BUNDLE, os.path.getsize(BUNDLE))

    again = collect(UnityPy.load(BUNDLE))
    assert len(again) == 2, "đọc lại chỉ thấy %d component" % len(again)
    for _, name, t in again:
        assert t["m_enableAutoSizing"] == 1, "%s: auto-size chưa bật" % name
        assert t["m_fontSizeMax"] == t["m_fontSize"], "%s: max chưa ghim" % name
        print("  đọc lại %-22s autosize=%s min=%s max=%s"
              % (name, t["m_enableAutoSizing"], t["m_fontSizeMin"], t["m_fontSizeMax"]))


main()
