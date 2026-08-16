"""Tiện ích chung cho các sprite "key prompt" (dải Ⓐ決定 Ⓑ戻る … ở chân màn hình).

Những dải này là **tranh vẽ**, không phải chuỗi ký tự: chúng nằm trong atlas ASTC
của từng màn hình. Module này lo phần khó — tìm ô của sprite trong atlas, cắt ra,
dán lại, và dựng lại mesh thành quad full-rect (xem [[unitypy-switch-bundle-repack]]).

Dùng:
    from keyart import Container
    c = Container("romfs/Data/sharedassets6.assets")
    s = c.sprite("UL_section_abc_com_key")
    img = s.crop()            # ảnh vùng sprite trong atlas (PIL, RGBA)
    s.paste(new_img)          # ghi đè vùng đó
    s.full_rect_mesh()        # mesh 4 đỉnh, hết bị cắt
    c.save()
"""

import json
import os
import struct

import UnityPy
from PIL import Image


def _keyid(k):
    """m_RenderDataKey -> chuỗi so sánh được."""
    return json.dumps(k, default=str, sort_keys=True)


class SpriteSlot:
    def __init__(self, container, obj):
        self.c = container
        self.obj = obj
        self.tree = obj.read_typetree()
        self.name = self.tree["m_Name"]
        self.path_id = obj.path_id
        self.rd, self.atlas_obj, self.atlas_tree, self.map_index = container._render_data(self.tree, obj.assets_file)
        self.file = obj.assets_file
        self.tex_pid = self.rd["texture"]["m_PathID"]
        self.texkey = (id(self.file), self.tex_pid)
        self.tex_obj = container.by_pid[self.texkey]

    # ---- hình học ---------------------------------------------------------
    @property
    def rect(self):
        r = self.rd["textureRect"]
        return r["x"], r["y"], r["width"], r["height"]

    def box(self):
        """Hộp cắt theo toạ độ PIL (gốc trên-trái)."""
        x, y, w, h = self.rect
        th = self.c.tex_image(self.texkey).height
        left = int(round(x))
        top = int(round(th - y - h))
        return left, top, left + int(round(w)), top + int(round(h))

    def crop(self):
        return self.c.tex_image(self.texkey).crop(self.box())

    def paste(self, img):
        box = self.box()
        want = (box[2] - box[0], box[3] - box[1])
        if img.size != want:
            raise ValueError(f"{self.name}: ảnh {img.size} != ô {want}")
        tex = self.c.tex_image(self.texkey)
        tex.paste(img, box)          # ghi đè hẳn, kể cả alpha
        self.c.dirty_tex.add(self.texkey)

    # ---- mesh -------------------------------------------------------------
    def full_rect_mesh(self):
        """Thay mesh tight bằng quad 4 đỉnh phủ kín ô — nếu không, nét mới bị xén.

        Mesh nằm ở `m_RD` của chính sprite (SpriteAtlasData trong bản Unity này
        **không** mang mesh), còn toạ độ lấy từ ô atlas."""
        rd = self.tree["m_RD"]
        p2u = self.tree["m_PixelsToUnits"]
        pv = self.tree["m_Pivot"]
        mr = self.tree["m_Rect"]
        off = self.rd["textureRectOffset"]
        _, _, w, h = self.rect

        x0 = (off["x"] - mr["width"] * pv["x"]) / p2u
        y0 = (off["y"] - mr["height"] * pv["y"]) / p2u
        x1 = x0 + w / p2u
        y1 = y0 + h / p2u

        # hai stream: 4 x float3 vị trí, rồi 4 x float2 UV (để trắng)
        pos = [(x0, y1), (x1, y1), (x0, y0), (x1, y0)]   # TL, TR, BL, BR
        data = b"".join(struct.pack("<fff", x, y, 0.0) for x, y in pos)
        data += b"\x00" * 32

        vd = rd["m_VertexData"]
        vd["m_VertexCount"] = 4
        vd["m_DataSize"] = data
        ch = vd["m_Channels"]
        for i, c in enumerate(ch):
            c["stream"] = 0
            c["offset"] = 0
            c["format"] = 0
            c["dimension"] = 0
        ch[0].update(stream=0, offset=0, format=0, dimension=3)
        ch[4].update(stream=1, offset=0, format=0, dimension=2)

        rd["m_IndexBuffer"] = [0, 0, 1, 0, 2, 0, 2, 0, 1, 0, 3, 0]
        rd["m_SubMeshes"] = [{
            "firstByte": 0, "indexCount": 6, "topology": 0, "baseVertex": 0,
            "firstVertex": 0, "vertexCount": 4,
            "localAABB": {"m_Center": {"x": 0.0, "y": 0.0, "z": 0.0},
                          "m_Extent": {"x": 0.0, "y": 0.0, "z": 0.0}},
        }]
        self.c.dirty_sprites[(id(self.file), self.path_id)] = (self.obj, self.tree)

    def vertex_count(self):
        return self.tree["m_RD"]["m_VertexData"]["m_VertexCount"]


class Container:
    def __init__(self, path):
        self.path = path
        self.env = UnityPy.load(path)
        self.objects = list(self.env.objects)
        self.by_pid = {(id(o.assets_file), o.path_id): o for o in self.objects}
        self._atlases = [(o, o.read_typetree()) for o in self.objects
                         if o.type.name == "SpriteAtlas"]
        self._imgs = {}
        self.dirty_tex = set()
        self.dirty_sprites = {}

    # ---- tra cứu ----------------------------------------------------------
    def _render_data(self, sprite_tree, afile=None):
        key = _keyid(sprite_tree["m_RenderDataKey"])
        for obj, tree in self._atlases:
            if afile is not None and obj.assets_file is not afile:
                continue
            for i, (k, v) in enumerate(tree["m_RenderDataMap"]):
                if _keyid(k) == key:
                    return v, obj, tree, i
        rd = sprite_tree["m_RD"]
        if rd["texture"]["m_PathID"]:
            return rd, None, None, None
        raise KeyError(f"{sprite_tree['m_Name']}: không tìm thấy render data")

    def sprite(self, name):
        for o in self.objects:
            if o.type.name != "Sprite":
                continue
            if o.read_typetree()["m_Name"] == name:
                return SpriteSlot(self, o)
        raise KeyError(name)

    def sprite_names(self):
        return [o.read_typetree()["m_Name"] for o in self.objects if o.type.name == "Sprite"]

    def tex_image(self, key):
        if key not in self._imgs:
            self._imgs[key] = self.by_pid[key].read().image.convert("RGBA")
        return self._imgs[key]

    # ---- ghi --------------------------------------------------------------
    def save(self, out_path, packer=None):
        """Nén lại và ghi ra `out_path`. Bundle cần packer='lz4'; .assets thì không."""
        for key in self.dirty_tex:
            d = self.by_pid[key].read()
            d.image = self._imgs[key]
            d.save()
        for obj, tree in self.dirty_sprites.values():
            obj.save_typetree(tree)
        data = self.env.file.save(packer=packer) if packer else self.env.file.save()
        with open(out_path, "wb") as f:
            f.write(data)
        return len(data)


def render_check(container_path, name):
    """Ảnh mà game thực sự vẽ (đi qua mesh + uvTransform)."""
    env = UnityPy.load(container_path)
    for o in env.objects:
        if o.type.name == "Sprite" and o.read_typetree()["m_Name"] == name:
            return o.read().image
    raise KeyError(name)
