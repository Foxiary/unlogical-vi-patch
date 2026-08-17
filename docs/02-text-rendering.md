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
| **NoWrap** — hard `\n` required, long lines clip | Dictionary title / ruby (`level22`), ChapterSelect synopsis, Terminal rule item |
| **Normal** — auto-wraps | ADV message boxes (`level10` pids 886/887), backlog, Genebark chat, news/note widgets, Terminal info/caption, profile comment |

On a NoWrap component the `\n` tokens are load-bearing: nothing re-flows at
runtime, so after editing wording you must re-wrap by hand or the line clips
mid-word.

**Two components were switched out of NoWrap by this patch**, so the table above
describes stock, not what ships:

| component | file | change |
|---|---|---|
| `MainText (TMP)` — dictionary body | `level22` pid 331 | `m_TextWrappingMode` 0 → 1 |
| `MainText (TMP)` — in-ADV dictionary popup | `level10` pid 895 | `m_TextWrappingMode` 0 → 1 |

Both now re-flow at runtime, which is why their hard wrapping is no longer
load-bearing. Check the shipped value before hand-wrapping anything.

## Known box budgets

Measured in half-width units, where a fullwidth CJK character counts 2. The
practical trick is to take the widest *original Japanese* line as the budget —
it is proven to fit by construction.

| screen | budget | notes |
|---|---|---|
| Terminal rule pages | 72 units | longest JP line was 36 fullwidth chars |
| Terminal home alerts | 61 units | derived from the already-translated alerts |
| Dictionary body — ARCHIVE | 497 px a line, **8 lines a page** | `level22` pid 331, box 500×476 at font 32, charSpacing 3.5 |
| Dictionary body — ADV popup | **586 px a line, 11 lines a page** | `level10` pid 895, box 586×758 at font 40, charSpacing 5 — the tighter of the two, wrap for this one |
| ADV message | **1280 px a line, 3 lines** | `level10` pid 886/887, rect narrowed from 1400 (below), font 42 auto-sizing down to 28 |
| Novel mode | 1400 px a line, ~11 lines | `level10` pid 894, box 1400×720 at font 42, charSpacing 6 |
| Chapter synopsis | ~41 chars / ~9 lines | box 620×474 at font 31.25 |
| Chapter title | ~28–30 chars | mask 527×58, right-aligned, NoWrap |

### The width formula, and the two things it must not count

`characterSpacing` does **not** share the glyph advance's scale factor. TMP scales
the advance by `fontSize / pointSize` (58 here) and characterSpacing by
`fontSize / 100`, and the wrap test measures to the last glyph's right edge, so the
spacing after the final character never counts:

```
W = Σ advance × fontSize/58  +  (n−1) × characterSpacing × fontSize/100
```

At font 42 the older `(advance + spacing) × fontSize/pointSize` form — still used by
`tools/adv_layout.py` — runs 1.4 px per character wide, 7% on a full line. Two more
corrections that only a real capture could give: the ADV box **does not draw `「」`**
(measured against a 1280×720 screenshot: line 1 of a quoted message is 1362 px, which
the model reproduces only with the brackets excluded), and accumulating word widths
one at a time silently drops the space's own characterSpacing (~4.5 px per word).

### Wrap to the *pixel* budget, not a character count

The chapter synopses were wrapped at 18 characters — matching the Japanese,
which used 18–19 **fullwidth** characters. Latin glyphs are about half as wide,
so each line used ~50% of the column and the text needed twice the lines: 36 of
43 entries overflowed, one reaching 31 lines in a 9-line box.

### On an auto-wrapping component, do not hand-wrap at all

The Genebark news widget had the opposite failure. `GenebarkNewsData` kept the
Japanese line breaks — 3 lines of 8–14 fullwidth glyphs — but the Vietnamese
lines under them run 29–35 characters against a box built for 8 fullwidth
glyphs, so **every hard line wrapped a second time** and left orphan words on
their own line:

```
"Công nghệ tương lai" do AI      <- hard line 1, wrapped
kiến                             <- its orphan
tạo: Niềm hy vọng mang đến       <- hard line 2, wrapped
cho                              <- its orphan
nhân loại                        <- hard line 3
```

Rendered that way the 61 headlines took 6–10 lines each in a three-line box.
`NewsText01`/`NewsText02` are `m_TextWrappingMode` 1 with auto-sizing on and
`overflowMode` Overflow, so they wrap and shrink perfectly well on their own:
removing all 299 breaks brings the headlines to 4–5 lines at a chosen size of
19–24. The rule is per component — hand-wrap only where the wrap mode is NoWrap,
and never on top of a component that already wraps.

### …unless the engine counts the data's newlines, or the art is narrower than the rect

Two boxes break that rule, both discovered from photographs of the running game.

**The dictionary/note boxes paginate on the data's `\n`, not on what TMP drew.**
`MyUICompornentBase.BuildNoteLines` (RVA 0x19B3490) is `raw.Replace(…).Split('\n')`,
`CalcStartIndex_PageUnit` returns `notePageNo × NOTE_TEXT_LINE`, and the constant is
11 for the ADV dictionary popup (RVA 0x1A17880), 8 for the terminal ARCHIVE page and
7 for the chapter synopsis. `DictionaryBase.DefaultMaxCharsPerLine` is 0, so the code
inserts no breaks of its own — the data's `\n` are the *only* source of lines. Proof
from two photos of entry 112 when its data held 16 lines: page 1 ended exactly at data
line 11 and page 2 started exactly at data line 6 = 16 − 11, while the tail that TMP
had wrapped fell outside the window and never appeared. So on these boxes each `\n`
must equal one rendered line: hard-wrap to the pixel budget, and re-run the wrap after
any wording change (`tools/fix_dictionary_wrap.py`, `--only=NN` for a single entry).

**Novel mode indents every data line by one em, and lines TMP wrapped by nothing.**
Measured 41 canvas px ≈ 0.98 em between two adjacent lines of the same paragraph. That
is why the Japanese hard-wraps every numbered rule *and* prefixes the continuations
with two fullwidth spaces — 1 em from the engine plus 2 em from the data puts the body
of every line on one column. Dropping those indents leaves an over-long data line's
tail jutting one em to the left of everything else (`tools/fix_novel_list_wrap.py`).

**The ADV message box's rect is wider than the art.** The box is cut diagonally at the
bottom right, so measured from the text's left edge the art only allows 1430 px on line
1, 1364 on line 2, **1301 on line 3** — while the rect gave TMP 1400. Any line that
filled the rect ran onto the dark diagonal and its tail stopped being readable: 3 992
of 37 951 messages (10.5%) were in that state, 356 of them by more than 80 px. Fixed by
narrowing the rect itself to 1280 (`m_Pivot.x = 0`, so `m_SizeDelta.x` alone pins the
left edge and pulls the right edge in — one float per component). Hard-wrapping the data
instead would have cost 936 shrunken messages against this fix's 665, plus a re-run
after every sheet merge. `tools/fix_adv_wrap.py --check` is the gate; it reads the rect
width live from `level10` rather than hardcoding it.

### One typographic rule lives in the data: `... ...` breaks the line

A sentence that trails off and is answered by one that opens the same way reads as two
utterances, so the space between the two ellipses becomes a newline (33 places).
`tools/fix_ellipsis_break.py`, re-runnable, `--check` in the gate list.

## Auto-sizing as the fix

When re-wrapping is not enough, enable TMP auto-sizing — but **always pin
`m_fontSizeMax` to the component's original `m_fontSize`**. Auto-size picks the
largest size in `[min, max]` that fits, and the stock `m_fontSizeMax` is 72,
which would blow short strings up.

Every component the shipped patch touches, verified by diffing against stock —
`m_enableAutoSizing` goes 0 → 1 and the stock `[18, 72]` range is replaced by
`[floor, original m_fontSize]`:

| component | file | box | size | floor |
|---|---|---|---|---|
| `Message(Normal)/Text`, `Message(Highest)/Text` | `level10` (pids 886/887) | 1400×186 | 42 | 28 |
| `ChapterTitle (TMP)` — save/load slot | `level19` (pid 187) | — | 27 | 16 |
| `ChapterTitle (TMP)` — save/load slot | `level20` (pid 195) | — | 27 | 16 |
| `NewsText01` (Genebark news headline) | `ui_jp` | stretched | 32 | 16 |
| `NewsText02` (news body) | `ui_jp` | stretched | 25 | 14 |
| `NoteText01` (note widget) | `ui_jp` | stretched | 32 | 16 |

`level22` pid 331 also had `m_fontSizeMax` pulled 72 → 32, but its
`m_enableAutoSizing` is still **0**, so that value is inert — the change that
actually does something there is the wrap-mode flip above. Setting a size range
without the flag is a silent no-op; assert on `m_enableAutoSizing` after writing.

`level10` pid 895 is `MainText (TMP)`, the in-ADV dictionary popup — wrap-mode
only, no size change.

`level19` and `level20` are the **save/load slot screens** (`Date_yyyy`,
`PlayTime`, `dataNo`, `Chapter (TMP)`, and in `level19` also `ADVLoadBG`), not
chapter select. The chapter-title budget in the table above belongs to a
different screen; do not apply it here.

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
