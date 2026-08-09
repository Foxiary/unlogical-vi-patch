# Repacking with UnityPy

Notes against UnityPy 1.25, Switch (Tegra) textures.

## 1. Re-encode textures through the `image` setter

```python
d.image = new_img
d.save()
```

This handles ASTC compression, the Switch block-linear **swizzle** and the
platform blob together, and preserves `m_TextureFormat`.

Calling `Texture2DConverter.image_to_texture2d` / `parse_image_data` by hand and
diffing the two gives a meaningless result (measured PSNR 8 dB) because the
swizzle/flip handling does not round-trip that way. Through the setter, the same
image round-trips at **PSNR ~68 dB, max channel delta 16** — visually lossless, so
re-encoding a whole atlas to change a small region is acceptable.

The encoder is not the weak link: UnityPy calls astc-encoder at `quality=100`. A
no-op decode→encode round trip of the Archive atlas scores 60.8 dB overall and
66–77 dB on 1px-stroke pixel-font kanji. Anti-aliased 1px strokes with black under
transparent pixels also survive at 54–59 dB, so neither anti-aliasing nor missing
colour-bleed actually breaks ASTC here.

## 2. `env.file.save()` defaults to *uncompressed*

On a 4.1 MB bundle that produced a 23.7 MB file. Pass:

```python
env.file.save(packer="lz4")
```

which writes `data_flag=194, block_info_flag=2` — the flags Unity's own LZ4HC
bundles use (check with `env.file.dataflags`). `packer="original"` reuses whatever
the source had.

`.assets` files save with plain `env.file.save()`, no `packer`.

Setting `.image` on a texture whose pixels live in a `.resS` **inlines** the data
(`m_StreamData` → empty) and grows the file — 101 KB to 4.3 MB for
`sharedassets9`. The sibling `.resS` must still be shipped alongside it, because
the other textures in that file keep their absolute offsets into it.

## 3. Atlas sprites are TIGHT-MESHED

This is the single biggest trap.

Unity's packer gives each sprite a polygon mesh hugging the **original** artwork's
ink (`m_RD.settingsRaw` meshType Tight; 9–34 triangles is typical). The game
renders only inside that mesh, so new art extending beyond the old shape is
silently **cut away** — glyphs come out with chunks missing.

**Repainting clips the sprite even if you never move anything**, because different
glyph shapes fall outside the old outline. On the stock build every sprite loses
exactly **0** opaque pixels, so any loss at all is a repaint regression. All 12
`UL_option_keycon_button_*` sprites were already losing 7–79 px from an earlier
English repaint before any mesh work.

### Detecting it

Count opaque pixels in the atlas crop versus in `sprite.image`; any shortfall is
mesh clipping.

```
atlas crop  -> did the pixels land in the right place
sprite.image -> what the game actually draws (applies the mesh)
```

**`sprite.image` is the check that matters.** Cropping the Texture2D at the
`m_RenderDataMap` rect only proves placement; it ignores the mesh and will happily
report 58–60 dB / IoU 1.000 on a sprite the game renders full of holes. During
development the atlas crop was trusted over `sprite.image`, `sprite.image` was
wrongly written off as a decoder bug, and visibly broken art shipped — the in-game
screenshot matched `sprite.image` exactly. After the mesh rebuild it reads
68–99 dB / IoU 1.000. Use both.

Note also that comparing RGBA directly is misleading on mostly-transparent images:
RGB under fully-transparent pixels is undefined and gets scrambled by ASTC,
tanking PSNR without changing anything visible. Composite over an opaque
background before measuring.

### Rebuilding as a full-rect quad

Copy the layout of a 4-vertex sprite already present in the same file
(`UL_archive_bg_acce_08` served as the template):

- `m_VertexData.m_VertexCount = 4`
- `m_DataSize` = two **streams**, not interleaved — 4×float3 positions (48 B) then
  4×float2 UVs (32 B). The UVs are **zeroed**; atlas UVs come from `uvTransform`,
  not the vertex stream.
- Vertex order TL, TR, BL, BR with `m_IndexBuffer = (0,1,2, 2,1,3)`
- `m_SubMeshes` = one entry, `indexCount 6`, `vertexCount 4`, zeroed `localAABB`

Quad corners in sprite-local units:

```
x0 = (textureRectOffset.x - m_Rect.width  * pivot.x) / m_PixelsToUnits
x1 = (textureRectOffset.x + textureRect.width  - m_Rect.width  * pivot.x) / m_PixelsToUnits
y0 = (textureRectOffset.y - m_Rect.height * pivot.y) / m_PixelsToUnits
y1 = (textureRectOffset.y + textureRect.height - m_Rect.height * pivot.y) / m_PixelsToUnits
```

Verify this against every existing tight mesh's bounding box before writing —
agreement should be ~0.001 for finely quantised vertices, ~0.02 for coarser ones.
**If a mesh does not span its rect, skip it**: a full-rect quad is not a safe
substitute, and the mismatch is the signal. One sprite (`menu_choices`) failed
that check by a full unit and was deliberately left alone.

## 4. The `uvTransform` trap

In a `SpriteAtlas` `m_RenderDataMap` entry the rect origin is stored **twice**: in
`textureRect` and again inside `uvTransform`. The runtime samples through
`uvTransform`:

```
uv_px = pos * m_PixelsToUnits + (uvTransform.y, uvTransform.w)
```

so the fields are `(scaleX, offsetX, scaleY, offsetY)`, offsets in atlas pixels
with y bottom-up.

Relocating a sprite by rewriting only `textureRect` leaves it sampling its old
slot in game. UnityPy's `sprite.image` crops by `textureRect`, so every offline
check passes while the game draws something else — combined with a full-rect mesh,
the sprite then displays whatever tight packing had interleaved into its old rect,
which looks like random glyphs appearing inside the widget.

If you move a sprite, move `uvTransform` too, and verify with a renderer that goes
through it.

## 5. Sprite rects come from the SpriteAtlas, not the sprite

For an atlased sprite, `m_RD.texture` is 0 and `m_RD.textureRect` is in
*source-texture* space — several sprites will appear to occupy the same rect. The
real atlas placement is in the `SpriteAtlas`'s `m_RenderDataMap`, keyed by the
sprite's `m_RenderDataKey`.

Convert to image coordinates with `top = atlasHeight − y − h`, then confirm the
mapping once on an **unmodified** file, where the crop and `sprite.image` should
agree pixel-for-pixel.

## 6. Alpha bleed

The stock art carries colour bleed — transparent pixels hold the glyph colours
dilated outward, rather than black. Freshly rendered art has black under every
transparent pixel. This turned out not to break ASTC here, but matching the
original convention costs nothing: dilate RGB outward into transparent regions,
leaving alpha untouched.

## Verify after any repack

- object count and the `path_id` → (type, name) map
- `(signature, version, version_engine, version_player, cab_file, dataflags)`
- untouched regions of a modified atlas, composited, should score >45 dB

UnityPy renames the internal CAB node to `CAB-UnityPy_Mod`; this game loads such
bundles fine.
