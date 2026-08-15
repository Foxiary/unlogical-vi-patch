# Protagonist name — metadata literals and save data

The ADV nameplate is driven by the token **`【player】`** in `ScenarioData`
(29,483 occurrences). The engine substitutes the protagonist's full name: a fixed
surname plus the player-entered given name. Dialogue also uses an inline
**`[主人公]`** token (2,490 occurrences) for the given name mid-sentence.

## The two defaults are IL2CPP string literals

Both live in `Managed/Metadata/global-metadata.dat` and each appears exactly once.
They are two of the **four** literals this patch edits — see
[the full list](#every-metadata-literal-this-patch-edits) below, because reverting
the file reverts all four.

| literal idx | was | now | bytes written | offset (v1.0.2) |
|---|---|---|---|---|
| 15053 | `涼乃` (fixed surname) | `Suzuno` | `Suzuno` — fills the 6-byte slot | 496921 |
| 15063 | `環無` (default given name) | `Kanna` | `Kanna` — 5 bytes, length shortened | 497033 |

## Every metadata literal this patch edits

Verified by diffing the shipped file against a stock v1.0.2 dump — four literals
in the data blob, three length fields in the table:

| idx | was | now | slot | table entry | data offset |
|---|---|---|---|---|---|
| 14668 | `。` | `' '` (one space) | 3 → **1** B | 117600 | 491803 |
| 14991 | `共通・` | `Chung - ` | 9 → **8** B | 120184 | 496109 |
| 15053 | `涼乃` | `Suzuno` | 6 → 6 B | 120680 | 496921 |
| 15063 | `環無` | `Kanna` | 6 → **5** B | 120760 | 497033 |

Literal 14668 is the sentence period the engine appends to every spoken line —
see [02 — Text rendering](02-text-rendering.md), "The engine appends 。 to spoken
lines".

**A replacement does not have to fit the original slot exactly.** Bytes are
written in place at the literal's existing data offset, and if the new string is
shorter the **length field** in the string-literal table is decremented — which is
what happened to 14668, 14991 and 15063. The `dataIndex` half of each entry, and
therefore every other literal's offset, stays untouched, so no rebuild is needed.
A *longer* replacement has no room and would need one.

Header layout (v31): pair 0 = stringLiteral table (offset **256**, 15,224 entries
of 8 bytes: `length` then `dataIndex`), pair 1 = stringLiteralData (offset
**122,048**), at file offsets 8 and 16.

`Kanna` is the reading used throughout the translated script (120 occurrences in
`ScenarioData`), so the default offered at name entry matches the dialogue.

The metadata differs between 1.0.0 and 1.0.2, so **this patch is
version-specific**. Confirm the emulator has update `v131072` (= 1.0.2) selected
before shipping a metadata patch. Reverting is just deleting the file from the
mod romfs.

## The ADV nameplate comes from `talkName[]`

`ScenarioData.talkName[]` is parallel to `text[]` and is what the nameplate draws.
The patch translated 14,739 of its 39,803 values; the nameplates inside
`scriptText_Line` stay Japanese and are never displayed. Two forms:

| form | meaning |
|---|---|
| `【Yuri】` | drawn as-is |
| `【神楽 侑莉/Yuri】` | **true identity / what is drawn** — only the half after the slash reaches the screen |

The slash form is how the game hides an identity, so a Japanese-looking value is
usually not a translation gap. Audited: of 38,074 nameplates in real content,
**0** have Japanese in the displayed half, while 3,777 carry Japanese in the
hidden half. Test the half after the slash, never the whole string.

`player` inside a nameplate expands to surname + given name — `Suzuno Kanna`.

### Shared nameplates drop the surname

Eleven lines are spoken by two characters at once, and `Suzuno Kanna＆Ran` is
473 units wide against a design budget of ~336 (the placeholder in `level10` pids
890/892 is `汎用汎用汎用汎用`, 8 fullwidth glyphs at font 42), so it wrapped onto two
lines. They now name the protagonist by given name only:

| was | now | count | width |
|---|---|---|---|
| `【player＆Kai】` | `【Kanna＆Kai】` | 7 | 263 |
| `【Kai＆player】` | `【Kai＆Kanna】` | 2 | 263 |
| `【player＆Ran】` | `【Kanna＆Ran】` | 2 | 282 |

This matches the Japanese, where the same plates read `涼乃環無＆戒` at roughly the
same width. `【player/？？？】` (23 lines) is **not** touched — that is the
protagonist speaking while unidentified, and the drawn half is `？？？`.

The given name is written literally rather than as a token because **the engine
offers no verified token for it inside a nameplate**. Metadata carries four:
`[主人公]` (given name), `[主人公愛称]` (nickname), `[主人公氏名]` (full name),
`[主人公苗字]` (surname) — but only `[主人公]` is ever used by the shipped data, and
**no nameplate in the game uses a token at all**, so whether the nameplate path
runs the token pass is untested. If someone verifies that a nameplate does expand
`[主人公]`, switching them to `【[主人公]＆Kai】` is the remaining improvement.

## Every named line exists twice — do not tokenise the default variant

`ScenarioData` carries two boolean arrays parallel to `text[]`:

| flag | what the line holds | when it is shown |
|---|---|---|
| `isDefaultNameAdjust` | the **literal** default name, `環無` / `Kanna` | the player kept the default name |
| `isCustomNameAdjust` | the **`[主人公]` token** | the player entered their own |
| neither | the token | always |

The split is exact — in the Japanese, 601 lines are default+literal, 592 are
custom+token, 243 are unflagged+token, and **not one line breaks the pattern**.
The same sentence therefore appears twice, once in each form:

```
「あとでＵＲＬ送るよ。\n　環無はダメな匂いってある？」        <- isDefaultNameAdjust
「あとでＵＲＬ送るよ。\n　[主人公]はダメな匂いってある？」    <- isCustomNameAdjust
```

**A default-name line is drawn verbatim.** Writing `[主人公]` into one does not
substitute — it prints the token on screen, and it does so for exactly the players
who kept the default name, i.e. most of them. This patch made that mistake once,
converting all 618 literal `Kanna` in `text[]`; 601 of them were default-name
lines and the token showed raw in the short stories. Reverted.

What ships now: the 601 default-name lines keep the literal name, and **12** lines
are tokenised — the ones where the Japanese has `[主人公]` and the translation had
flattened it to a literal. `text[]` holds 828 tokens and 605 literal `Kanna`.

So the surname/given-name rule is not "always use the token". It is:

- **Never** touch a line flagged `isDefaultNameAdjust` — it is meant to be literal.
- A literal on a line flagged `isCustomNameAdjust`, or on an unflagged line whose
  Japanese uses the token, **is** a bug; those are the 12.
- The **surname** is never tokenised anywhere: it is fixed in metadata and Name
  Entry cannot change it. 375 literal `Suzuno` in `text[]` are all correct.

One more precedent worth keeping: `涼乃さん` (surname + honorific) is rendered as a
bare **`Suzuno`** — 195 of its 213 occurrences, and 82 of 89 when Yasaka Soichi is
the speaker. The one line that had rendered it as `Kanna` (scenarioID 117,
`text[616]`, 「……涼乃さん」) was brought into line.

Japanese honorifics are dropped throughout. Two lines had kept a `san` because the
Japanese breaks the honorific apart mid-word as the speaker falters — they now
carry the halt without it:

| | Japanese | now |
|---|---|---|
| 105 / 843 | 「……っ、ぐ……涼乃、さ……」 | 「...Hự... Suzu... no...」 |
| 109 / 356 | 「弥坂、さん……　ここから、離れて……ください」 | 「Anh Yasaka... Làm ơn... hãy rời khỏi đây đi.」 |

`弥坂さん` is `anh Yasaka` in 464 of 764 lines against 258 bare `Yasaka`, and she
calls him `anh` two lines later in that same scene, so the address form is the
convention rather than a fresh choice.

Two `-kun` remain on purpose: `Kai-kun` (105/246) and the coded `K-kun` signature
(106/314). `Kyapi-kun` is a mascot's name, not an honorific.

**When auditing for honorifics, do not grep `\bsan\b`.** Vietnamese is written
syllable-by-syllable, so that pattern hits ordinary words — `san sát`, `san sẻ`,
`tập san`, `tuần san`, `màu san hô`. Seven of nine hits in this script were
Vietnamese, not residue.

Worth knowing before assuming this was a translation bug: **the Japanese original
hardcodes 環無 too — 606 times**, in the same 60 scenarios where it also uses the
token, mostly in dialogue that addresses the protagonist directly (`環無ちゃん`,
`環無さん`, `環無サマ`). Only **12** of the 618 were places where the Japanese had a
token and the translation flattened it. So this pass fixes 12 real regressions and
then goes further than the original for the other 606.

The surname is **not** tokenised and does not need to be: it is fixed in metadata
(literal 15053) and the Name Entry screen cannot change it — the LAST NAME field
there is baked art, only the given name is player-entered. All 375 literal
`Suzuno` in `text[]` stay as they are, and `Suzuno Kanna` became
`Suzuno [主人公]`, which is exactly the Japanese convention `涼乃[主人公]`.

One possibility this does not rule out: the engine may already substitute the
default-name literal at runtime, in which case the 606 lines were never broken and
this pass is a harmless no-op. Nothing in the shipped data settles it. The test is
a new game with a different given name, then any early line where someone says the
protagonist's name.

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
