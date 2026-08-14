# Data layout — where the text lives

## The scenario bundle

`StreamingAssets/scenario/scenario01` holds 145 TextAssets, and the split matters:

| asset | role |
|---|---|
| Per-chapter scripts (`00_00`, `01_02`, …) | What the engine **executes**. Still Japanese. Every tag *argument* the game draws comes from here. |
| `ScenarioData` (17.3 M characters ≈ 23 MB of UTF-8, `{"target":[…]}`, 140 entries) | The translated text. `text[]` messages mapped by `loadLine[]`; `selText[]` choices mapped by `selLine[]`. |
| `LoadData` (36 M characters ≈ 36 MB, `"version":"ldb/1"`) | Save/load state database. Not script. |

Sizes are worth stating in both units: `ScenarioData` is 17.3 M *characters* but
23.3 MB on disk, because Vietnamese diacritics cost two UTF-8 bytes each (the
stock Japanese file is 22.5 MB). A note that just says "17 MB" reads as a byte
count and is wrong by a third.

Because the chapter scripts are what runs, a notice widget stays Japanese even
after `ScenarioData` is fully translated. Those live in tag arguments and must be
patched in the chapter scripts:

```
[geninfo text="…"]   [terinfo text="…"]   [select_monitor text="…"]
```

Do **not** translate `[seladd text=…]` there — choices are substituted from
`selText[]` and already display translated text.

`resources.assets` is largely untouched Japanese original that is never displayed.
The patch changes exactly three objects in it: the `SystemTextData` TextAsset, the
chapter script **`00_01`** (a second copy of it lives here, not just in
`scenario01`), and the `FOT-iroha21popuraStdN-R` font.

## The json bundle

`StreamingAssets/json/json` holds the Terminal / Dictionary / Genebark data:

| asset | contents |
|---|---|
| `TerminalRuleData` | 21 rule pages — `content[]` of `{heading, text}`, plus a `body` field |
| `TerminalHomeAlertData` | 86 notification lines |
| `TerminalProfileData` | Character profiles: `name`, `ruby`, `comment`, … |
| `DictionaryData` | 80 glossary entries: `category`, `title`, `ruby`, `text` |
| `ChapterData` | Chapter-select titles and synopses |
| `GenebarkNewsData` / `NoteData` / `ChatMainData` | In-game social-media widgets |
| `MapData`, `Q&AData`, `ConfigVolumeData`, … | Misc UI |

Values are nested per language slot: `{"title": {"jp": "..."}}`.

### `TerminalRuleData` has a trap

The screen renders `content[].heading` / `content[].text`. It does **not** render
`body`. An earlier translation pass filled `body` on 16 of 21 pages, which looked
done in the data and displayed as Japanese in game. If a page shows Japanese,
check which field you filled.

Also: `body` sometimes duplicates another page's text verbatim. Rule id 45's
`body` is a copy of id 44's, but their Japanese rules differ (2 culprits vs 1,
kill-all vs down-to-3, 8 shared skill uses vs 5). Porting `body` across would
have shipped wrong game rules. Translate from the Japanese, not from a sibling.

## The JP-slot convention

Text tables carry `JP` / `EN` / `CN` slots per entry, but the game **only ever
reads the JP slot** — the console language setting does not switch it. Ryujinx set
to `AmericanEnglish` still renders JP.

So every translation is written *into the JP slot*, leaving EN and CN untouched.
For `SystemTextData`'s 92 entries the rule was:

- if the official `EN` string is usable (non-empty, not the literal `"None"`, no CJK)
  → copy EN into JP (73 entries)
- otherwise → write a fresh translation into JP (19 entries)

This is why official English system dialogs appear alongside translated story
text. It is intentional. When adding UI text, prefer the game's own official
English wording over inventing new phrasing.

Only `_jp` asset bundles ship (`ui_jp`, `scene_jp`, `font_jp`, `sprite_jp`, …),
which is the underlying reason the JP slot is the only live one.

## Line breaks

**Real newlines (U+000A) everywhere text is displayed** — all `ScenarioData`
prose and every TextAsset in the json bundle. Audited: zero literal backslash-n
tokens in displayed text; the json bundle has none at all, and the handful left
in `scenario01` all sit inside tags (below).

Earlier in the patch's history some assets stored the two-character token and
were converted since, so any script that splits on `"\\n"` now returns one giant
line and silently reports every entry as a single line.

The **only** surviving literal backslash-n tokens are 89 occurrences: 84 **inside
`[command]` tag arguments** (`[select_monitor text="…\n…"]`, `[terinfo text="…"]`)
and 5 in `LoadData`'s `childJsons`. Those must stay literal — a real newline inside
`[...]` ends the command line and breaks parsing.

**Count them after parsing, not before.** These assets are JSON, so a real newline
is stored in the raw asset text as the two characters `\n`. Counting `"\\n"` over
the raw string returns 208,576 for `ScenarioData` — all of them ordinary newlines.
Parse first, then count; the answer is 55.

### The hard breaks were lost in translation — chat restored, prose not

Separate from the storage format: the Japanese build uses hard breaks heavily and
the translation dropped nearly all of them. Stock `text[]` has **22,208** entries
containing a real newline; the patch had **173**, all of them lines that were
never translated. The halves had been run together on one line, often with
nothing but a space at the join where the Japanese had a break.

**The Genebark chat is fixed.** All **135** messages that were two or three lines
in Japanese and one line in Vietnamese now carry the break again, placed where the
Japanese broke: `text[]` is up to **308** multi-line entries. The split point was
chosen per message — sentence boundary first, then a capitalised word (a full stop
the translation dropped), then a clause-opening conjunction (`nên`, `nhưng`,
`rồi`, `mà`, …), with the Japanese line lengths as the position prior. Twelve were
overridden by hand where Vietnamese word order diverges from Japanese, mostly the
`Unknown@73w35vq` announcements, which put the date last where Japanese puts it
first.

Two traps that showed up doing it, worth knowing before the same pass is run over
the ADV prose:

- A capital letter mid-sentence usually means a dropped full stop, but not when it
  is a **proper noun** — `hợp tác với Unlogical`, `gửi cho anh Yuri`. Splitting
  there cuts a name off its sentence. Keep an exclusion list (the romanisations in
  [05](05-protagonist-name.md), plus `Unlogical`, `Genebark`, `Stage`, `Operator`,
  `Player`, and the single-letter pronouns `T` / `C` this translation uses).
- Splitting purely by proportional position cuts inside compounds — `nơi để lại kỷ`
  / `niệm sâu sắc`. Rank candidates by grammatical strength first, distance second.

Roughly **21,900** prose entries still read as one merged line. That pass is a
much larger job and is tracked in the README.

## Measuring translation coverage

Do **not** judge coverage by counting CJK characters. Kanji character names
(涼乃, 雅火, …) appear inside fully-translated lines and inflate the count badly.

Measure per entry over body lines only, skipping `[commands]` and `【nameplates】`,
and test for **kana** rather than kanji — kana is the reliable signal for
untranslated Japanese prose.

Two more false-positive traps when detecting "is this still Japanese":

- `・` (U+30FB, katakana middle dot) sits in the katakana block but is used as a
  bullet in translated text. Excluding it changes the answer completely.
- `　` (U+3000, ideographic space) is used as the indent character throughout.

A regex of `[ぁ-ゖァ-ヺ一-鿿]` avoids both.

## Untranslated by design

`ScenarioData` scenarioIDs 0–8 (route 1, chapter 0) are developer test material
(`01_test_live2d_*`, `sample1/2/3`, `ul_test*`), including a 1,267-line script
with an unrelated cast that is never played. `NotificationData_GENEBARK` and
`_TERMINAL` are dummy placeholders (`ダミー`, `お知らせ1（簡潔）`).

## Never translate these — they are lookup keys

| field | why |
|---|---|
| `GenebarkChatMainData.charID` / `.speaker` | keys into the speaker table |
| `GenebarkChatSpeakerReplaceData.speaker` | the key; `.replace` is the display handle |
| `Q&AData.bustup.chara` / `.face` | sprite lookups |
| `AdvCharacterBustUpDatabase.characterName` / `.bustUpName` | sprite lookups |
| `chara_info` / `_chara_info` `charaname` | matched by script commands like `[涼乃 左 出 2111 M すまし]` |
| `DictionaryData.category` (あ/か/さ…) | kana grouping behind the ten dictionary tabs |
| `TerminalRuleBackgroundData.memo` | developer note, never displayed |

Roughly 1,900 Japanese strings fall into this class. Renaming any of them breaks
sprite loading, voice playback, or chat threading.
