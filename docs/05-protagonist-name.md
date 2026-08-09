# Protagonist name — metadata literals and save data

The ADV nameplate is driven by the token **`【player】`** in `ScenarioData`
(29,483 occurrences). The engine substitutes the protagonist's full name: a fixed
surname plus the player-entered given name. Dialogue also uses an inline
**`[主人公]`** token (2,488 occurrences) for the given name mid-sentence.

## The two defaults are IL2CPP string literals

Both live in `Managed/Metadata/global-metadata.dat`, each appearing exactly once
and each 6 UTF-8 bytes:

| literal idx | was | now | offset (v1.0.2) |
|---|---|---|---|
| 15053 | `涼乃` (fixed surname) | `Suzuno` | 496921 |
| 15063 | `環無` (default given name) | `Tamamu` | 497033 |

Because the replacements are also 6 bytes they were overwritten **in place** — the
string-literal table at offset 256 and every metadata offset stay untouched, so no
rebuild is needed. Header layout (v31): pair 0 = stringLiteral table, pair 1 =
stringLiteralData, at file offsets 8 and 16.

The metadata differs between 1.0.0 and 1.0.2, so **this patch is
version-specific**. Confirm the emulator has update `v131072` (= 1.0.2) selected
before shipping a metadata patch. Reverting is just deleting the file from the
mod romfs.

## Do not romanise the lookup keys

`charaname` values in `chara_info` / `_chara_info` (`resources.assets`) are
*lookup keys* that scenario commands match against, e.g.:

```
[涼乃 左 出 2111 M すまし]
```

Renaming them breaks sprite loading.

## The given name is save data, not game data

Patching literal 15063 only changes the default offered at name entry — it cannot
alter a name already confirmed. The live value is in the save file:

```
%APPDATA%\Ryujinx\bis\user\save\0000000000000001\{0,1}\auto_data
```

Two journal slots; keep them identical. Format: a 524288-byte file holding a gzip
stream followed by zero padding. The gzip payload is a fixed 8192-byte buffer —
a .NET `BinaryWriter` 7-bit-encoded length prefix, then UTF-8 JSON, then zero
padding.

Relevant fields: `m_PlayerName`, `m_LanguagePlayerName[10]`,
`m_LanguageNickName[10]`, `m_CurrentLanguage` (0 = Japanese).

The emulator must be closed before editing, or it overwrites on exit.

## Incidental findings

Slot 1 of the language arrays holds the game's **official English default given
name, `Hina`** (also metadata literal 4747). There is no `Suzuno` literal in stock
metadata.

`m_CurrentLanguage` and the per-language arrays show the engine supports 10
languages, but only `_jp` asset bundles ship — which is why everything is patched
into the JP slots rather than switching language. See
[01 — Data layout](01-data-layout.md).

The name-entry keyboard has **英 / 数 / 記** tabs, so a player can type a Latin
given name directly; the literal only supplies the default.

## Established romanisations

Taken from the game's own already-translated widget text and story nameplates
rather than invented. Story convention is **surname first**:

`Nagamori Ran` · `Yasaka Soichi` · `Munakata Kai` · `Kogasaki Shiori` ·
`Oshino Mitsuki` · `Himejima Kyousuke` · `Toudou Itsuki` · `Arisawa Zadkiel` ·
`Shinjo Ryo` · `Masa Isa` · `Kasuya Yuzuha` · `Aihara Shoru` · `Naruse Rento` ·
`Hinode Ryoku` · `Yoshino Ibuki` · `Yuuki Soma` · `Tarui Nagito` ·
`Yamashina Yuya` · `Jito Eiko` · `Akagawa Kanon` · `Kozumi Shota` ·
`Yoshitani Naoki` · `Suzuno`

Spirits: `Hotaru` · `Shinju` · `Ruri` · `Menou` · `Kohaku`

Two of these were contested in the data and resolved toward the story spelling,
which outnumbers the alternative by thousands of occurrences: 姫嶋恭介 is
`Himejima Kyousuke` (not `Kyosuke`), 東堂伊槻 is `Toudou Itsuki` (not `Todo`).
`TerminalProfileData.ruby` originally used given-name-first order for all nine
full names and was flipped to match.
