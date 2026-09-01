# -*- coding: utf-8 -*-
"""Phần dùng chung cho các bản vá marquee (`fix_*_marquee.py`).

Game có sẵn `AutoScrollText` (Assets/Scripts/Auto/AutoScrollText.cs) nhưng không gắn vào
đâu; xem docstring `fix_music_title_marquee.py` cho hành vi đọc từ disassembly. Thư viện
này lo phần "thêm component chưa từng có trong file":

- file **không** nhúng type tree (`level*`, `sharedassets*`): MonoScript nằm ở
  `globalgamemanagers.assets` (external), chỉ cần type entry với hai hash —
  `script_id = MD4(className + namespace + assemblyName)`, `old_type_hash = MonoScript.m_PropertiesHash`
  (đối chiếu khớp 23/23 entry sẵn có của level13).
- bundle **có** type tree (`ui_jp`): MonoScript nằm ngay trong CAB và type entry phải kèm node.
  Thêm một MonoScript object (chép từ một MonoScript sẵn có, đổi tên/hash) và dựng node bằng cách
  ghép các node sẵn có (header của ContentSizeFitter, `PPtr<$TextMeshProUGUI>` của
  EventTriggerButton.textMeshPro, ...).

Bố cục byte các component (sau header 32 byte: GO PPtr, m_Enabled+pad, Script PPtr, m_Name rỗng):
    RectMask2D        m_Padding 4f · m_Softness 2i                                  = 56
    AutoScrollText    targetText PPtr · scrollMode i · startDelay speed pauseDuration f = 60
    ContentSizeFitter m_HorizontalFit i · m_VerticalFit i                            = 40
    LayoutElement     m_IgnoreLayout u8+pad · minW minH prefW prefH flexW flexH f · m_LayoutPriority i = 64
"""
import copy
import os
import struct

import UnityPy

GGM = r"D:\Downloads\UNLOGICAL_v2\Data\globalgamemanagers.assets"
MS_RECTMASK2D, MS_AUTOSCROLL, MS_CSF, MS_LE = 407, 1187, 399, 385   # pid MonoScript trong globalgamemanagers
MODES = {"loop": 0, "restart": 1}
CSF_PREFERRED, CSF_NONE = 2, 0
TMP_LEFT, TMP_CENTER = 1, 2


def md4(data):
    """MD4 thuần Python — OpenSSL 3 không còn bật md4."""
    def f(x, y, z): return (x & y) | (~x & z)
    def g(x, y, z): return (x & y) | (x & z) | (y & z)
    def h(x, y, z): return x ^ y ^ z
    def rol(x, n): return ((x << n) | (x >> (32 - n))) & 0xffffffff
    msg = bytearray(data) + b"\x80"
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", len(data) * 8)
    a0, b0, c0, d0 = 0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476
    for i in range(0, len(msg), 64):
        x = struct.unpack("<16I", msg[i:i + 64])
        a, b, c, d = a0, b0, c0, d0
        for j in range(16):
            a, b, c, d = d, rol((a + f(b, c, d) + x[j]) & 0xffffffff, (3, 7, 11, 19)[j % 4]), b, c
        for j in range(16):
            k = (j % 4) * 4 + j // 4
            a, b, c, d = d, rol((a + g(b, c, d) + x[k] + 0x5a827999) & 0xffffffff, (3, 5, 9, 13)[j % 4]), b, c
        for j, k in enumerate((0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15)):
            a, b, c, d = d, rol((a + h(b, c, d) + x[k] + 0x6ed9eba1) & 0xffffffff, (3, 9, 11, 15)[j % 4]), b, c
        a0, b0, c0, d0 = [(u + v) & 0xffffffff for u, v in ((a0, a), (b0, b), (c0, c), (d0, d))]
    return struct.pack("<4I", a0, b0, c0, d0)


def hash128(h):
    """Hash128 của UnityPy (object có bytes_N_) hoặc dict {'bytes[N]': v} -> 16 byte."""
    if isinstance(h, dict):
        return bytes(h["bytes[%d]" % i] for i in range(16))
    return bytes(getattr(h, "bytes_%d_" % i) for i in range(16))


def script_id_of(class_name, namespace, assembly):
    return md4((class_name + namespace + assembly).encode())


def pptr(fid, pid):
    return struct.pack("<iq", fid, pid)


def mb_head(go_pid, script_fid, script_pid):
    """m_GameObject + m_Enabled(+pad) + m_Script + m_Name rỗng = 32 byte."""
    return pptr(0, go_pid) + struct.pack("<B3x", 1) + pptr(script_fid, script_pid) + struct.pack("<i", 0)


def rectmask2d_data(go_pid, script_fid, script_pid, softness_x=0):
    d = mb_head(go_pid, script_fid, script_pid) + struct.pack("<4f", 0, 0, 0, 0) + struct.pack("<2i", softness_x, 0)
    assert len(d) == 56
    return d


def autoscroll_data(go_pid, script_fid, script_pid, target_fid, target_pid, mode, delay, speed, pause):
    d = mb_head(go_pid, script_fid, script_pid) + pptr(target_fid, target_pid) + struct.pack("<i3f", MODES[mode], delay, speed, pause)
    assert len(d) == 60
    return d


def csf_data(go_pid, script_fid, script_pid, horizontal=CSF_PREFERRED, vertical=CSF_NONE):
    d = mb_head(go_pid, script_fid, script_pid) + struct.pack("<2i", horizontal, vertical)
    assert len(d) == 40
    return d


def layoutelement_data(go_pid, script_fid, script_pid, min_width, priority=1):
    d = mb_head(go_pid, script_fid, script_pid) + struct.pack("<i", 0) + struct.pack("<6f", min_width, -1, -1, -1, -1, -1) + struct.pack("<i", priority)
    assert len(d) == 64
    return d


def load_ggm_scripts():
    """pid -> MonoScript (đọc được m_ClassName/m_Namespace/m_AssemblyName/m_PropertiesHash)."""
    return {o.path_id: o.read() for o in UnityPy.load(GGM).objects if o.type.name == "MonoScript"}


def find_script_type(sf, file_index, script_pid):
    for i, t in enumerate(sf.types):
        if t.class_id == 114:
            st = sf.script_types[t.script_type_index]
            if st.local_serialized_file_index == file_index and st.local_identifier_in_file == script_pid:
                return i, t
    return None, None


def add_script_type(sf, file_index, script_pid, class_name, namespace, assembly, properties_hash, node=None):
    """Thêm script_types entry + SerializedType (class 114). `node` bắt buộc khi file nhúng type tree."""
    assert find_script_type(sf, file_index, script_pid)[0] is None, "script %d đã có type entry" % script_pid
    proto = next(t for t in sf.types if t.class_id == 114)
    st = copy.copy(sf.script_types[0])
    st.local_serialized_file_index = file_index
    st.local_identifier_in_file = script_pid
    sf.script_types.append(st)
    t = copy.copy(proto)
    t.class_id = 114
    t.is_stripped_type = False
    t.script_type_index = len(sf.script_types) - 1
    t.script_id = script_id_of(class_name, namespace, assembly)
    t.old_type_hash = properties_hash
    if sf._enable_type_tree:
        assert node is not None, "file nhúng type tree — cần node"
        t.node = node
        t.type_dependencies = tuple(proto.type_dependencies or ())
    sf.types.append(t)
    return len(sf.types) - 1, t


def check_hashes(sf, scripts_by_pid, file_index):
    """Đối chiếu công thức hash với các entry MonoBehaviour sẵn có trỏ vào `file_index`."""
    n = 0
    for t in sf.types:
        if t.class_id != 114:
            continue
        st = sf.script_types[t.script_type_index]
        if st.local_serialized_file_index != file_index:
            continue
        ms = scripts_by_pid.get(st.local_identifier_in_file)
        if ms is None:
            continue
        cls, ns, asm, ph = ms
        assert t.script_id == script_id_of(cls, ns, asm), "script_id lệch ở %s" % cls
        assert t.old_type_hash == ph, "old_type_hash lệch ở %s" % cls
        n += 1
    return n


def new_object(sf, proto_pid, pid, data, type_id=None, stype=None):
    """Object mới chép khung từ `proto_pid` (cùng class), dữ liệu thô `data`."""
    o = copy.copy(sf.objects[proto_pid])
    o.path_id = pid
    o.byte_start = 0
    o.byte_size = len(data)
    o.data = bytes(data)
    if type_id is not None:
        o.type_id, o.serialized_type = type_id, stype
    assert pid not in sf.objects, pid
    sf.objects[pid] = o
    return o


# ---------------------------------------------------------------- node (bundle có type tree)
def clone_node(n):
    """TypeTreeNode của UnityPy không pickle/deepcopy được — dựng lại từ to_dict()."""
    from UnityPy.helpers.TypeTreeNode import TypeTreeNode
    d = n.to_dict()
    d.pop("m_Children", None)
    return TypeTreeNode(**d, m_Children=[clone_node(c) for c in n.m_Children])


def _leaf(proto, name, m_type=None, size=None, meta=None, level=1):
    n = clone_node(proto)
    n.m_Name = name
    if m_type is not None:
        n.m_Type = m_type
    if size is not None:
        n.m_ByteSize = size
    if meta is not None:
        n.m_MetaFlag = meta
    n.m_Level = level
    for c in n.m_Children:
        c.m_Level = level + 1
    return n


def _renumber(root):
    for i, n in enumerate(root.traverse()):
        n.m_Index = i
    return root


def header_nodes(csf_node):
    """4 node đầu (m_GameObject, m_Enabled, m_Script, m_Name) chép từ type ContentSizeFitter."""
    root = clone_node(csf_node)
    root.m_Children = root.m_Children[:4]
    assert [c.m_Name for c in root.m_Children] == ["m_GameObject", "m_Enabled", "m_Script", "m_Name"]
    return root


def build_autoscroll_node(csf_node, pptr_tmp_node):
    """MonoBehaviour: header · PPtr<$TextMeshProUGUI> targetText · int scrollMode · float ×3."""
    root = header_nodes(csf_node)
    int_proto = csf_node.m_Children[4]          # int m_HorizontalFit
    assert int_proto.m_Type == "int"
    root.m_Children.append(_leaf(pptr_tmp_node, "targetText", "PPtr<$TextMeshProUGUI>", 12))
    root.m_Children.append(_leaf(int_proto, "scrollMode"))
    for nm in ("startDelay", "speed", "pauseDuration"):
        root.m_Children.append(_leaf(int_proto, nm, "float", 4, 0))
    return _renumber(root)


def build_layoutelement_node(csf_node, bool_node):
    """MonoBehaviour: header · UInt8 m_IgnoreLayout · float ×6 · int m_LayoutPriority."""
    root = header_nodes(csf_node)
    int_proto = csf_node.m_Children[4]
    root.m_Children.append(_leaf(bool_node, "m_IgnoreLayout", "UInt8", 1, 0x4100))
    for nm in ("m_MinWidth", "m_MinHeight", "m_PreferredWidth", "m_PreferredHeight", "m_FlexibleWidth", "m_FlexibleHeight"):
        root.m_Children.append(_leaf(int_proto, nm, "float", 4, 0))
    root.m_Children.append(_leaf(int_proto, "m_LayoutPriority"))
    return _renumber(root)


def verify_untouched(orig_raw, chk, changed, new_pids):
    assert len(chk.objects) == len(orig_raw) + len(new_pids), (len(chk.objects), len(orig_raw), len(new_pids))
    bad = [pid for pid, raw in orig_raw.items() if pid not in changed and chk.objects[pid].get_raw_data() != raw]
    if bad:
        raise SystemExit("save làm lệch %d object ngoài dự kiến: %s" % (len(bad), bad[:20]))
    for pid in new_pids:
        assert pid in chk.objects, pid


def changed_fields(a, b):
    """Các ô 4 byte khác nhau giữa hai blob cùng độ dài."""
    assert len(a) == len(b), (len(a), len(b))
    return sorted({i // 4 * 4 for i in range(len(a)) if a[i] != b[i]})


def borrowed_tmp_nodes(ui_path):
    """File không nhúng type tree: mượn node TextMeshProUGUI từ bundle ui_jp."""
    for o in UnityPy.load(ui_path).objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if isinstance(t, dict) and "m_enableAutoSizing" in t:
            return o.serialized_type.node
    raise SystemExit("không mượn được type tree TMP từ " + ui_path)


def backup_once(src, backup):
    import shutil
    if not os.path.exists(backup):
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(src, backup)
        print("backup ->", backup)
