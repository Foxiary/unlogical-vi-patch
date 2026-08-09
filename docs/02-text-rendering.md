# Text rendering — wrapping, overflow, safe edits

Vietnamese runs longer than the Japanese the layout was built for, so boxes
overflow. Two different mechanisms decide what happens, and they behave nothing
alike.

## Wrapping is per-component

TextMeshPro's field is `m_TextWrappingMode` in this Unity version — **not**
`m_enableWordWrapping`, which no longer exists. Querying the old name returns
`None` and reads as "not set", which is a silent wrong answer.

| mode | components |
|---|---|
| **NoWrap** — hard `\n` required, long lines clip | Dictionary body / title / ruby (`level22`), ChapterSelect synopsis, Terminal rule item |
| **Normal** — auto-wraps | ADV message boxes (`level10` pids 886/887), backlog, Genebark chat, news/note widgets, Terminal info/caption, profile comment |

On a NoWrap component the `\n` tokens are load-bearing: nothing re-flows at
runtime, so after editing wording you must re-wrap by hand or the line clips
mid-word.

## Known box budgets

Measured in half-width units, where a fullwidth CJK character counts 2. The
practical trick is to take the widest *original Japanese* line as the budget —
it is proven to fit by construction.

| screen | budget | notes |
|---|---|---|
| Terminal rule pages | 72 units | longest JP line was 36 fullwidth chars |
| Terminal home alerts | 61 units | derived from the already-translated alerts |
| Dictionary body | ~37 chars | box 500×476 at font 32; holds 15 lines |
| Chapter synopsis | ~41 chars / ~9 lines | box 620×474 at font 31.25 |
| Chapter title | ~28–30 chars | mask 527×58, right-aligned, NoWrap |

### Wrap to the *pixel* budget, not a character count

The chapter synopses were wrapped at 18 characters — matching the Japanese,
which used 18–19 **fullwidth** characters. Latin glyphs are about half as wide,
so each line used ~50% of the column and the text needed twice the lines: 36 of
43 entries overflowed, one reaching 31 lines in a 9-line box.

## Auto-sizing as the fix

When re-wrapping is not enough, enable TMP auto-sizing — but **always pin
`m_fontSizeMax` to the component's original `m_fontSize`**. Auto-size picks the
largest size in `[min, max]` that fits, and the stock `m_fontSizeMax` is 72,
which would blow short strings up.

| component | file | box | size | floor |
|---|---|---|---|---|
| `Message(Normal)/Text`, `Message(Highest)/Text` | `level10` (pids 886/887) | 1400×186 | 42 | 28 |
| `NewsText01` (Genebark news headline) | `ui_jp` | stretched | 32 | 16 |
| `NewsText02` (news body) | `ui_jp` | stretched | 25 | 14 |
| `NoteText01` (note widget) | `ui_jp` | stretched | 32 | 16 |

ADV overflow was measured against real geometry (box 1400×186, charSpacing 5.3,
lineSpacing −42, pointSize 58, lineHeight 116, advances from the TTF embedded in
`sharedassets7.assets`): floor 42 → 1242 messages overflow, 36 → 15, 32 → 2,
**28 → 0**.

`level10` has no embedded type trees. Borrow TMP `nodes` from any MonoBehaviour
in `ui_jp` that has `m_enableAutoSizing`, and pass them to
`read_typetree` / `save_typetree`. Bundles like `ui_jp` embed their own trees and
need no `nodes`.

## The engine appends 。 to spoken lines

No line in the data ends with one, yet every quoted line shows one on screen.
IL2CPP metadata carries `'。'` as literal 14668 (plus `'。、！？…'`, an
"already punctuated" set); blanking 14668 to a space is the lever.

## Safe editing rules

**Never do a blind global replace in `ScenarioData`.** The katakana prolong mark
`ー` appears 1180 times, but 1117 are inside `[command]` tags — character names,
dictionary terms, voice file ids — where changing it breaks sprite and dictionary
lookups. Replace only outside `[...]` and `【...】`, and skip lines starting with
either.

**Apply every edit to both `scriptText` and the `text[]` array** so they stay in
sync. A phrase typically occurs exactly twice — once in each.

**Order replacements longest-first.** Short strings are often substrings of
longer ones. Replacing `犯人を暴く` first corrupted the longer id-46 text that
contains it, so the later lookup failed. Same class of bug: rule id 11's text is a
prefix of id 12's.

**Watch for shared text.** Rule ids 20/21/22 hold byte-identical strings, so one
replace covers all three and the second lookup finds nothing. Deduplicate before
looping, or assert on the count you expect.

**Beware real newlines when building search fragments.** `text[]` values may
contain real newlines, which are escaped in the raw JSON — a fragment spanning one
matches nothing. Clip search fragments at line boundaries.

**Separators matter after romanisation.** Japanese names contain no spaces, so a
plain space between them is an unambiguous separator. Romanised names *do*
contain spaces, so wrapping can split `Masa | Isa` across lines and invent a
person. Promote the separator to `　` (U+3000) first — the convention the chapter
scripts already use (`Tarui Nagito　Yamashina Yuya`).

## Bulk edits are compressed

The bundles are LZ4-compressed, so grepping the raw files for a string finds
nothing. Search the decompressed TextAssets instead. A byte scan that comes back
empty is not evidence the string is absent.
