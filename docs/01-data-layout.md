# Data layout — where the text lives

## The scenario bundle

`StreamingAssets/scenario/scenario01` holds 145 TextAssets, and the split matters:

| asset | role |
|---|---|
| Per-chapter scripts (`00_00`, `01_02`, …) | What the engine **executes**. Still Japanese. Every tag *argument* the game draws comes from here. |
| `ScenarioData` (~17 MB JSON, `{"target":[…]}`, 140 entries) | The translated text. `text[]` messages mapped by `loadLine[]`; `selText[]` choices mapped by `selLine[]`. |
| `LoadData` (~36 MB, `"version":"ldb/1"`) | Save/load state database. Not script. |

Because the chapter scripts are what runs, a notice widget stays Japanese even
after `ScenarioData` is fully translated. Those live in tag arguments and must be
patched in the chapter scripts:

```
[geninfo text="…"]   [terinfo text="…"]   [select_monitor text="…"]
```

Do **not** translate `[seladd text=…]` there — choices are substituted from
`selText[]` and already display translated text.

`resources.assets` is largely untouched Japanese original that is never displayed,
with the exception of `SystemTextData` and one chapter script.

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
prose and every TextAsset in the json bundle. Audited: zero literal
backslash-n tokens in any of them.

Earlier in the patch's history some assets stored the two-character token and
were converted since, so any script that splits on `"\\n"` now returns one giant
line and silently reports every entry as a single line.

The **only** surviving literal backslash-n tokens are 89 occurrences **inside
`[command]` tag arguments** (`[select_monitor text="…\n…"]`, `[terinfo text="…"]`,
and `LoadData`'s `childJsons`). Those must stay literal — a real newline inside
`[...]` ends the command line and breaks parsing.

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
