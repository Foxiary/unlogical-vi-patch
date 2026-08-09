# UNLOGICAL — Vietnamese Translation Patch

A fan translation patch for the Nintendo Switch visual novel **UNLOGICAL**
(title ID `010068501ff9a000`).

- **Story, dialogue and choices** — Vietnamese
- **UI, menus and system text** — English

This repository contains **only the game files the translation modifies**. It is
not a copy of the game. You must already own UNLOGICAL and supply your own dump.

---

## Requirements

| | |
|---|---|
| Game version | **v1.0.2** |
| Title ID | `010068501ff9a000` |
| Tested on | Ryujinx (also works on hardware via Atmosphère LayeredFS) |

The patch is built against v1.0.2. Applying it to a different game version may
crash or display corrupted text.

---

## Installation

### 1. Get the large font file

`StreamingAssets/font/font_jp` (270 MB) is too large for a Git repository and is
published as a **release asset** instead. Download it from the
[Releases](../../releases) page.

### 2. Assemble the mod folder

Place the files so the layout is exactly:

```
<mods>/contents/010068501ff9a000/vn-translation/romfs/Data/
    Managed/Metadata/global-metadata.dat
    StreamingAssets/anim/anim01
    StreamingAssets/font/font_jp          <- from Releases
    StreamingAssets/json/json
    StreamingAssets/movie/movie_jp_02
    StreamingAssets/scenario/scenario01
    StreamingAssets/scene/scene_jp
    StreamingAssets/ui/ui_jp
    level10  level19  level20  level22
    resources.assets
    sharedassets7.assets   sharedassets9.assets   sharedassets10.assets
    sharedassets13.assets  sharedassets16.assets  sharedassets19.assets
    sharedassets22.assets
```

### 3. Ryujinx

The mods folder is:

```
%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\
```

Right-click the game → **Open Mods Directory** if you are unsure. Launch the
game; no toggle is needed — LayeredFS picks the files up automatically.

> **Note:** `sharedassets9.assets.resS` and `sharedassets19.assets.resS` are
> deliberately **not** included. They are byte-identical to the stock game, and
> the base game's copies are used. Do not copy them from anywhere else.

---

## What is translated

**Story**
- 132 of 140 scenario scripts (all dialogue, narration and choices)
- The 8 untranslated scripts are developer test material that is never played

**Terminal**
- All 21 Rule pages (clear conditions, game content, operator roles)
- All 86 Home notification alerts
- Profile name romanisations

**Dictionary / Archive**
- All 80 dictionary entries
- Archive category labels (baked artwork)

**Artwork with text painted into it**
- Name Entry screen
- Archive page labels and button prompt
- Key-config button glyphs
- Backlog button prompts

## Known gaps

These are still Japanese and are tracked as remaining work:

- 21 character names on the Profile screen (`TerminalProfileData.name`)
- 17 per-character voice-volume labels in Sound options
- 5 spirit names in the Amity list
- 3 story lines containing a stray `っ`

---

## Verifying your files

`manifest.json` lists every shipped file with its size and MD5. To check a copy:

```powershell
Get-FileHash -Algorithm MD5 romfs\Data\StreamingAssets\json\json
```

---

## Legal

This is an unofficial, non-commercial fan translation. It ships modified game
data files and is useless without a legally obtained copy of UNLOGICAL. All
rights to the original game, its script and its artwork belong to their
respective owners. No affiliation with or endorsement by the publisher is
implied. If the rights holder objects, this repository will be taken down.
