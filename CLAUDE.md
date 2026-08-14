# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A fan Vietnamese translation patch for the Nintendo Switch visual novel **UNLOGICAL** (Title ID `010068501ff9a000`, game version **v1.0.2**), shipped as LayeredFS mod romfs.

There is **no source code, no build system, and no test suite here**. The repo contains three things:

- `romfs/Data/**` — 19 patched Unity binaries (`.assets`, bundles, `global-metadata.dat`). These *are* the deliverable.
- `manifest.json` — path / size / MD5 for every shipped file, including the one published outside git.
- `docs/` — reverse-engineering notes, in English (the vocabulary is Unity/UnityPy). `README.md` is in Vietnamese, aimed at players.

Editing happens **outside this repo**: a clean v1.0.2 dump beside a working copy, patched with Python + UnityPy, then the resulting binaries are copied in. The tooling was never committed. Treat the repo as the publication surface, not the workshop.

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
- `romfs/Data/**/*.resS` — byte-identical to stock, supplied by the base game. But note `sharedassets9.assets` *depends* on its sibling `.resS` still being present in the player's install, because untouched textures there keep absolute offsets into it.

Take a backup before every binary edit. The development convention was a gitignored `_backup/` folder with the filename suffixed by the edit that followed it (`json.prerulespacing`, `sharedassets9.assets.prearchive`), so a single step can be reverted rather than all of them.

## Architecture: where the text actually lives

Read [`docs/`](docs/) before touching data — the notes exist because these facts cost real debugging time. The load-bearing points:

**Text is spread across four unrelated storage mechanisms**, and finding a Japanese string means knowing which one you are in:

| kind | lives in | notes |
|---|---|---|
| Story prose, choices | `scenario01` → `ScenarioData` TextAsset | ~17 MB JSON; `text[]`/`selText[]` mapped by `loadLine[]`/`selLine[]` |
| Executed script (tag arguments) | `scenario01` → per-chapter scripts | Still Japanese by design; `[geninfo]`/`[terinfo]`/`[select_monitor]` arguments render on screen and must be patched *here*, not in `ScenarioData` |
| Terminal / Dictionary / widgets | `json` bundle | `TerminalRuleData`, `TerminalHomeAlertData`, `DictionaryData`, … |
| Two protagonist-name defaults | `Managed/Metadata/global-metadata.dat` | IL2CPP string literals, overwritten in place within their 6-byte slots |
| UI words that are **pixels, not strings** | sprite atlases in `scene_jp`, `sharedassets7/9`, `ui_jp` | A text audit reporting a Japanese-looking screen as clean means it is baked art |

**The JP-slot rule.** Text tables carry JP/EN/CN slots but the engine only ever reads **JP** — the console language setting does not switch it, because only `_jp` bundles ship. Every translation is written into the JP slot, EN and CN untouched. This is why official English system dialogs sit alongside Vietnamese story text: for `SystemTextData`, usable official EN strings were copied into JP. When adding UI text, prefer the game's own official English wording over inventing phrasing.

**~1,900 Japanese strings are lookup keys, not display text** — `charaname`, `charID`/`speaker`, bustup `chara`/`face`, `DictionaryData.category`. Renaming any breaks sprite loading, voice playback, or chat threading. `docs/01-data-layout.md` has the full list.

## Traps that produce silently wrong results

These all pass offline checks and fail in game, or fail in a way that looks like the opposite problem:

- **Bundles are LZ4-compressed.** Grepping the raw file for a string finds nothing. An empty byte scan is not evidence the string is absent — search decompressed TextAssets.
- **Atlas sprites are tight-meshed.** Repainting pixels without rebuilding the mesh ships art full of holes. `sprite.image` is the check that matters; cropping the Texture2D at its rect only proves placement and will report a perfect score on broken art.
- **`uvTransform` stores the rect origin a second time.** Move a sprite via `textureRect` alone and the game samples the old slot while every offline check passes.
- **`env.file.save()` defaults to uncompressed** — pass `packer="lz4"` for bundles (a 4.1 MB bundle became 23.7 MB without it). `.assets` files save with no `packer`.
- **TextMeshPro's wrap field is `m_TextWrappingMode` in Unity 6000.0.56f1.** The old `m_enableWordWrapping` no longer exists; querying it returns `None`, which reads as "not set".
- **Real newlines (U+000A) everywhere text is displayed.** The only literal backslash-n tokens left are 89 occurrences *inside* `[command]` arguments, where they must stay literal — a real newline there ends the command line. Scripts that split on `"\\n"` return one giant line and report everything as single-line.
- **Never blind-global-replace in `ScenarioData`.** Skip `[...]` and `【...】`, order replacements longest-first (short strings are substrings of longer ones), deduplicate shared text, and apply every edit to both `scriptText` and `text[]`.
- **Do not measure translation coverage by counting CJK.** Kanji character names appear inside fully translated lines. Test for kana per entry over body lines: `[ぁ-ゖァ-ヺ一-鿿]`, which also avoids the `・` bullet and `　` indent false positives.

## Version coupling

The patch is built against **v1.0.2** only. `global-metadata.dat` offsets differ between 1.0.0 and 1.0.2, so applying the metadata patch to another version crashes or garbles text. Confirm the emulator has update `v131072` selected before shipping anything that touches metadata. Reverting the name patch is just deleting that one file from the mod romfs.

Build target for reference: Unity **6000.0.56f1**, IL2CPP, Switch (Tegra) ASTC textures, UnityPy 1.25.

## Conventions

- Almost every question in `docs/` was settled by **diffing the patched file against a stock dump**, not by reasoning. Keep doing that.
- Established romanisations are taken from the game's own asset names and already-translated widget text, never invented; story convention is surname-first. The list is in `docs/05-protagonist-name.md` — reuse it rather than transliterating afresh.
- Markdown and JSON keep LF endings (`.gitattributes`).
- Known-outstanding Japanese items are tracked in the README's "Các phần tồn đọng đã biết" section; update it when one is closed.
