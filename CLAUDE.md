# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A fan Vietnamese translation patch for the Nintendo Switch visual novel **UNLOGICAL** (Title ID `010068501ff9a000`, game version **v1.0.2**), shipped as LayeredFS mod romfs.

There is **no source code, no build system, and no test suite here**. The repo contains three things:

- `romfs/Data/**` — the patched Unity binaries (`.assets`, bundles, `global-metadata.dat`). These *are* the deliverable. **20 files ship; 19 are tracked in git** — `font_jp` is gitignored and published as a release asset instead.
- `manifest.json` — path / size / MD5 for all 20, each tagged `"where": "repo"` or `"release"`.
- `docs/` — reverse-engineering notes, in English (the vocabulary is Unity/UnityPy). `README.md` is in Vietnamese, aimed at players.

Editing happens **outside this repo**: a clean v1.0.2 dump beside a working copy, patched with Python + UnityPy, then the resulting binaries are copied in. The tooling was never committed. Treat the repo as the publication surface, not the workshop.

The workshop this repo was published from:

| | |
|---|---|
| working copy | `D:\Downloads\010068501ff9a000\romfs` |
| clean v1.0.2 dump | `D:\Downloads\UNLOGICAL_v2\Data` (v1.0.0 at `D:\Downloads\UNLOGICAL\Data`) |
| live install | `%APPDATA%\Ryujinx\mods\contents\010068501ff9a000\vn-translation\romfs` — an NTFS **junction** to the working copy, so editing in place *is* installing |

Bash `find`/`ls` cannot traverse that junction and reports the folder empty; that is not a broken install. Check it with PowerShell `Get-Item -Force` and read `LinkType` / `Target`.

## Working with the binaries

Every file under `romfs/` is binary and marked as such in `.gitattributes` — `git diff` tells you nothing. Verify by hash instead:

```powershell
# Check every in-repo file against manifest.json
Get-Content manifest.json -Raw | ConvertFrom-Json | Where-Object { $_.where -eq 'repo' } | ForEach-Object {
  $h = (Get-FileHash -Algorithm MD5 $_.path).Hash.ToLower()
  "{0}  {1}" -f $(if ($h -eq $_.md5) { 'OK  ' } else { 'FAIL' }), $_.path
}
```

**If a binary under `romfs/` changes, `manifest.json` must be updated in the same commit** — bytes and MD5 both. Nothing enforces this automatically.

Two paths are deliberately absent from git and must stay that way:

- `StreamingAssets/font/font_jp` (270 MB) — published as a GitHub release asset; `manifest.json` marks it `"where": "release"`.
- `romfs/Data/**/*.resS` — byte-identical to stock, supplied by the base game. But **six shipped `.assets` files still name their sibling `.resS`** and depend on it being present in the player's install, because untouched textures in them keep absolute offsets into it: `resources.assets`, `sharedassets9`, `sharedassets10`, `sharedassets13`, `sharedassets19`, `sharedassets22`. (`sharedassets7` and `sharedassets16` reference none — every texture in them was inlined.) LayeredFS resolves the `.resS` from the base game, so this works as long as the patched `.assets` is built from the *same* v1.0.2 dump.

Take a backup before every binary edit. The development convention was a gitignored `_backup/` folder with the filename suffixed by the edit that followed it (`json.prerulespacing`, `sharedassets9.assets.prearchive`), so a single step can be reverted rather than all of them.

## Architecture: where the text actually lives

Read [`docs/`](docs/) before touching data — the notes exist because these facts cost real debugging time. The load-bearing points:

**Text is spread across five unrelated storage mechanisms**, and finding a Japanese string means knowing which one you are in:

| kind | lives in | notes |
|---|---|---|
| Story prose, choices | `scenario01` → `ScenarioData` TextAsset | 17.3 M characters ≈ 23 MB of UTF-8; `text[]`/`selText[]` mapped by `loadLine[]`/`selLine[]` |
| Executed script (tag arguments) | `scenario01` → per-chapter scripts | Still Japanese by design; `[geninfo]`/`[terinfo]`/`[select_monitor]` arguments render on screen and must be patched *here*, not in `ScenarioData` |
| Terminal / Dictionary / widgets | `json` bundle | `TerminalRuleData`, `TerminalHomeAlertData`, `DictionaryData`, … |
| Four IL2CPP string literals | `Managed/Metadata/global-metadata.dat` | `涼乃`→`Suzuno`, `環無`→`Kanna`, `共通・`→`Chung - `, and `。`→a space (the period the engine appends to every spoken line). Written in place; a shorter replacement also decrements the length field in the literal table. See [`docs/05`](docs/05-protagonist-name.md) |
| UI words that are **pixels, not strings** | sprite atlases in `scene_jp`, `ui_jp`, `sharedassets7/9/16/19/22` | A text audit reporting a Japanese-looking screen as clean means it is baked art |

**Never write the protagonist's given name literally.** The player types it at Name Entry, so body text uses the `[主人公]` token — 1,434 uses in `text[]`, and no literal `Kanna` outside eleven nameplates. The **surname** is the opposite: fixed in metadata, not player-editable, and correctly literal (`Suzuno`, 375 uses). The Japanese original is not a reliable guide here — it hardcodes 環無 606 times itself. See [`docs/05`](docs/05-protagonist-name.md).

**The JP-slot rule.** Text tables carry JP/EN/CN slots but the engine only ever reads **JP** — the console language setting does not switch it, because only `_jp` bundles ship. Every translation is written into the JP slot, EN and CN untouched. This is why official English system dialogs sit alongside Vietnamese story text: for `SystemTextData`, usable official EN strings were copied into JP. When adding UI text, prefer the game's own official English wording over inventing phrasing.

### What each shipped binary actually holds

Derived by diffing every shipped file against the stock v1.0.2 dump, object by object. Nothing else in these files was touched, and no shipped file is byte-identical to stock.

| file | MB | what the patch changed |
|---|---|---|
| `StreamingAssets/scenario/scenario01` | 8.7 | 23 of 145 TextAssets: `ScenarioData` (story) + 22 chapter scripts (tag arguments) |
| `StreamingAssets/json/json` | 0.1 | 16 of 36 TextAssets — Terminal / Dictionary / Genebark tables |
| `StreamingAssets/ui/ui_jp` | 48.3 | 5 fonts · 3 TMP components (`NewsText01/02`, `NoteText01`) · backlog + section key sprites · `g` and `Section` atlases |
| `StreamingAssets/scene/scene_jp` | 4.2 | Name-Entry atlas · 1 font |
| `StreamingAssets/anim/anim01` | 28.3 | **font only** (`FOT-NewRodinProN-M`) — no animation data |
| `StreamingAssets/movie/movie_jp_02` | 104.6 | the `prologue` clip, replaced wholesale — see below |
| `StreamingAssets/font/font_jp` | 269.6 | the dynamic-font bundle (release asset) |
| `Managed/Metadata/global-metadata.dat` | 9.3 | the four IL2CPP literals above |
| `resources.assets` | 13.4 | `SystemTextData` · chapter script `00_01` · 1 font |
| `sharedassets7.assets` | 8.3 | `Option` atlas — 46 of 76 sprites · 1 font |
| `sharedassets9.assets` | 4.3 | `Archive` atlas — 8 sprites |
| `sharedassets16.assets` | 2.1 | `PassWord` atlas — the whole password screen, in Vietnamese |
| `sharedassets19.assets` | 4.3 | `SaveLoad` atlas — `UL_salo_key` only |
| `sharedassets22.assets` | 0.6 | `DIC` atlas — `UL_dictionary_key` only |
| `sharedassets10.assets` / `sharedassets13.assets` | 10.6 / 0.5 | **fonts only** |
| `level10` | 0.2 | 3 TMP components (ADV message ×2, dictionary popup) |
| `level19` / `level20` | 0.04 | the save/load slot screens — `ChapterTitle (TMP)` auto-sizing, one component each |
| `level22` | 0.1 | dictionary `MainText (TMP)` wrap mode |

**Six font assets carry the added glyphs, and four of them are duplicated across files.** `FOT-NewRodinProN-DB` lives in `sharedassets7`, `scene_jp` *and* `ui_jp`; `FOT-DNPShueiMGoStd-B`/`-L` in `sharedassets10` and `ui_jp`; `FOT-DotGothic12Std-M` in `sharedassets13` and `ui_jp`; `FOT-iroha21popuraStdN-R` in `resources.assets` and `ui_jp`; `FOT-NewRodinProN-M` only in `anim01`. Patching one copy and not its twin leaves tofu on whichever screens load the other file — that is why `anim01`, `sharedassets10` and `sharedassets13` ship at all.

**`movie_jp_02` is the one change with no recorded reason.** The `prologue` clip was replaced with a full re-encode: 116.1 MB → 104.6 MB, 2546 → 2545 frames, same 1920×1080 and 30 fps, every byte different. The new file came out of a MainConcept encoder (Adobe) with `moov` moved to the front; the stock file has `moov` at the end. It carries **no subtitle track** — video and audio only — so any translated text in it is burned into the picture. Re-derive before touching it.

**~1,900 Japanese strings are lookup keys, not display text** — `charaname`, `charID`/`speaker`, bustup `chara`/`face`, `DictionaryData.category`. Renaming any breaks sprite loading, voice playback, or chat threading. `docs/01-data-layout.md` has the full list.

## Traps that produce silently wrong results

These all pass offline checks and fail in game, or fail in a way that looks like the opposite problem:

- **Bundles are LZ4-compressed.** Grepping the raw file for a string finds nothing. An empty byte scan is not evidence the string is absent — search decompressed TextAssets.
- **Atlas sprites are tight-meshed.** Repainting pixels without rebuilding the mesh ships art full of holes. `sprite.image` is the check that matters; cropping the Texture2D at its rect only proves placement and will report a perfect score on broken art.
- **`uvTransform` stores the rect origin a second time.** Move a sprite via `textureRect` alone and the game samples the old slot while every offline check passes.
- **`env.file.save()` defaults to uncompressed** — pass `packer="lz4"` for bundles (a 4.1 MB bundle became 23.7 MB without it). `.assets` files save with no `packer`.
- **TextMeshPro's wrap field is `m_TextWrappingMode` in Unity 6000.0.56f1.** The old `m_enableWordWrapping` no longer exists; querying it returns `None`, which reads as "not set".
- **Real newlines (U+000A) everywhere text is displayed.** The only literal backslash-n tokens left are 89 occurrences *inside* `[command]` arguments (84) and `LoadData`'s `childJsons` (5), where they must stay literal — a real newline there ends the command line. Scripts that split on `"\\n"` return one giant line and report everything as single-line. Beware the inverse when counting: these files *are* JSON, so a real newline is stored as the two characters `\n` in the raw asset text. Parse the JSON before counting, or every entry looks like a literal token.
- **Hard line breaks were lost in translation, and the data cannot tell you so.** Stock `text[]` has 22,208 entries containing a real newline; the translation left 173, all of them leftover Japanese. The Genebark chat has since been repaired — 135 messages, `text[]` now at 308 — but roughly 21,900 prose entries are still merged into one line. Nothing is corrupt, the components auto-wrap; "the file has newlines everywhere" just describes the *format*, not this build. See [`docs/01`](docs/01-data-layout.md) for the split heuristic and its two traps (proper nouns, compound words).
- **Never blind-global-replace in `ScenarioData`.** Skip `[...]` and `【...】`, order replacements longest-first (short strings are substrings of longer ones), deduplicate shared text, and apply every edit to both `scriptText` and `text[]`.
- **Do not measure translation coverage by counting CJK.** Kanji character names appear inside fully translated lines. Test for kana per entry over body lines: `[ぁ-ゖァ-ヺ一-鿿]`, which also avoids the `・` bullet and `　` indent false positives.

## Version coupling

The patch is built against **v1.0.2** only. `global-metadata.dat` offsets differ between 1.0.0 and 1.0.2, so applying the metadata patch to another version crashes or garbles text. Confirm the emulator has update `v131072` selected before shipping anything that touches metadata.

Reverting is just deleting that one file from the mod romfs — but it reverts **all four** literals at once, not only the name. Dropping it brings back the `。` the engine appends to every spoken line, and `共通・` in place of `Chung - `.

Build target for reference: Unity **6000.0.56f1**, IL2CPP, Switch (Tegra) ASTC textures, UnityPy 1.25.

## Conventions

- Almost every question in `docs/` was settled by **diffing the patched file against a stock dump**, not by reasoning. Keep doing that.
- Established romanisations are taken from the game's own asset names and already-translated widget text, never invented; story convention is surname-first. The list is in `docs/05-protagonist-name.md` — reuse it rather than transliterating afresh.
- Markdown and JSON keep LF endings (`.gitattributes`).
- Known-outstanding Japanese items are tracked in the README's "Các phần tồn đọng đã biết" section; update it when one is closed.
