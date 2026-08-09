# Technical notes

Reverse-engineering notes for the UNLOGICAL translation patch — where the text
actually lives, how the engine renders it, and the traps that cost real time.

> Tài liệu kỹ thuật viết bằng tiếng Anh vì phần lớn thuật ngữ là của Unity/UnityPy.

| | |
|---|---|
| [01 — Data layout](01-data-layout.md) | Which file holds which text, and the JP-slot rule |
| [02 — Text rendering](02-text-rendering.md) | Wrapping, overflow, auto-sizing, safe editing rules |
| [03 — Baked-art screens](03-baked-art.md) | UI text painted into sprite atlases |
| [04 — Repacking with UnityPy](04-repacking.md) | Texture re-encode, bundle packing, sprite meshes |
| [05 — Protagonist name](05-protagonist-name.md) | IL2CPP literals and save data |

## Build target

Unity **6000.0.56f1**, IL2CPP, Switch (Tegra) textures. Everything here is
verified against game version **v1.0.2**. Offsets in
`Managed/Metadata/global-metadata.dat` differ between 1.0.0 and 1.0.2, so the
metadata patch is version-specific.

## Working method

Keep a clean v1.0.2 dump beside the working copy. Almost every question in these
notes was settled by diffing the patched file against stock rather than by
reasoning about it — which file actually changed, how many pixels a sprite lost,
whether a string is display text or a lookup key.

Take a backup before every edit. The convention used during development was a
`_backup/` folder with the filename suffixed by the edit that followed it
(`json.prerulespacing`, `sharedassets9.assets.prearchive`, …), which makes it
possible to revert one step rather than all of them.
