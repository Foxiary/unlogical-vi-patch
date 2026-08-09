# Baked-art screens — UI text painted into sprites

Some UI text is **pixels, not strings**. Searching romfs and
`Managed/Metadata/global-metadata.dat` for it finds nothing, because it was never
text to begin with.

If a screen looks Japanese but a text audit reports it clean, this is why.

## Name Entry

Texture `sactx-0-2048x4096-ASTC 4x4-NameInput-f513dc0f` (path_id 10, 2048×4096,
format id 48) inside `StreamingAssets/scene/scene_jp`.

`文字入力 / 戻る / 初期化`, `なまえを いれてください`, `＋決定` and the fixed
surname `涼乃` were all painted in. Region boxes in PIL top-left coordinates —
Unity rects are bottom-left, so `top = 4096 − y − h`:

| element | box | on screen at 1080p |
|---|---|---|
| A/B/ZL prompt row + hint line | `(746, 901, 1179, 972)` | (784, 760) |
| `＋決定` button | `(1107, 1578, 1259, 1770)` | (1250, 748) |
| LAST NAME field with `涼乃` | `(735, 976, 1221, 1100)` | (679, 395) |

Translated to *Enter Text / Back / Reset*, *Please enter your name*, *OK*,
*Suzuno*. The romanisation **Suzuno** comes from the game's own asset names
(`00_suzuno_*`).

The **first-name** field is not art — it is player-entered TMP text.

## Archive page

`level9` contains **zero TMP components** — the entire screen is sprites. Assets
live in `sharedassets9.assets` (plus a 7.1 MB `.resS`), atlas
`sactx-0-2048x2048-ASTC 4x4-Archive-587e47dd`.

The category names (LIBRARY / MOVIE / MUSIC / Dictionary / Q&A / SHORT STORY /
RECOLLECTION) are drawn into the background illustration and were left alone. The
translatable pieces are the eight `moji` (文字) sprites plus the key prompt:

| sprite | was | became |
|---|---|---|
| `…_moji_01_still` | 画像閲覧 | IMAGE / GALLERY |
| `…_moji_02_movie` | 映像閲覧 | MOVIE / GALLERY |
| `…_moji_03_music` | 音楽鑑賞 | MUSIC / PLAYER |
| `…_moji_04_dictionary` | 辞書 | WORD / LIST |
| `…_moji_05_Q&A` | 一問一答 | Q&A |
| `…_moji_06_shortstory` | 掌編 | SHORT / STORY |
| `…_moji_07_recollection` | 終幕一覧 | ENDING / LIST |
| `UL_archive_key` | Ⓐ決定 Ⓑ戻る | Ⓐ Select Ⓑ Back |

Palette: white `#FFFFFF`, cyan `#A5F5EE`, pink `#FFD2D9`. The key prompt is
purple `#8650A9`, and its Ⓐ/Ⓑ circles were copied from the original rather than
redrawn.

Two design constraints worth keeping:

- The seven labels swap into the **same** screen slot as the cursor moves, so they
  need one shared glyph size. Sizing each to fill its own box makes them jump.
- `辞書`'s box is only 106 px wide, which is why it became WORD/LIST rather than
  DICTIONARY — the latter cannot fit at the shared size.

## Key-config button glyphs

`sharedassets7.assets`, atlas `Option`. Each sprite is a complete **icon + word**
image, not an icon beside a text field:

| sprite | box |
|---|---|
| `UL_option_keycon_button_Y` / `_X` / `_A` / `_B` / `_minus` / `_plus` | 132×37 |
| `_L` / `_R` / `_ZL` / `_ZR` | 134×37 |
| `_Rstick` | 173×37 |
| `_Lstick` | 176×37 |

Because the boxes were sized for Japanese, replacing `スティック` with the much
shorter `STICK` left ~55 px of dead space. The sprite is centre-anchored in its
cell, so the visible content drifted **left** and no longer lined up with the
button rows. Fixed by shifting the ink right inside the existing box (+20 px for
Rstick, +22 px for Lstick) so all twelve glyphs sit at the same offset from box
centre (−64 to −65).

## Backlog prompts

`ui_jp`, 4096×4096 atlas `g`. Two sprites:

- `UL_adv_backlog_key` (337×83) — Ⓐ音声再生 / Ⓨ巻き戻し / ⓁⓇ高速送り / Ⓑ戻る
- `UL_adv_backlog_key2` (343×83) — same minus the Ⓨ rewind option

Became *Ⓐ Play Voice / Ⓨ Rewind / ⓁⓇ Fast Forward / Ⓑ Back*, with the original
button glyphs copied across and text colour `#CFD7DD` sampled from the source.

## Fonts used for replacements

The game's own fonts render replacements convincingly — `FOT-NewRodin ProN DB`
for gothic UI text, `ULPixel` for the dot-matrix face. Extract them from the
bundles rather than substituting a lookalike.

For pixel-font work, render **without anti-aliasing** and upscale by an integer
factor with nearest-neighbour, so strokes stay hard-edged like the original art.

## The trap that matters most

Every sprite here is **tight-meshed**. Repainting the pixels is only half the
edit — see [04 — Repacking](04-repacking.md). Skipping the mesh rebuild produces
art that looks perfect in every offline check and renders full of holes in game.
