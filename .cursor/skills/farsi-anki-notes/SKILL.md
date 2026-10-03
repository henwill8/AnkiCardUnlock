---
name: farsi-anki-notes
description: >-
  Fill and normalize live Farsi Anki vocab notes through AnkiConnect: formal
  and spoken forms, Persian script, part-of-speech tags, and transliteration
  (u for long oo, aa for long a, i for long e, a for short a, o for short o,
  e for short e). Also add a spoken example sentence on each vocab note, and
  Farsi Sentence notes for newly added words. Commonly spoken lines can be any
  length. A short sentence must be commonly spoken; otherwise use a longer line
  with several deck words. Write note changes to an import file the user
  reviews in Anki. Suspend cards on a note that has no available template, so
  Anki does not show a blank front. Use when the user adds incomplete Farsi
  notes, asks to fix note formatting or transliteration, wants words from a
  Persian vocabulary or frequency list, or wants sentences for new vocab.
---

# Farsi Anki notes

Normalize the user's live Farsi notes, then add any word list they supply. Match notes already in Anki. Read [reference.md](reference.md) for spoken alternations and tags. Read [examples.md](examples.md) before rewriting a row.

## Source

Anki is open with AnkiConnect at `http://127.0.0.1:8765`. Read vocab with `note:"Farsi"`. Read sentence notes with `note:"Farsi Sentence"`. Do not search for a deck export and do not edit one.

If AnkiConnect does not answer, stop.

`notesInfo` does not include the guid. Copy the guid Anki already has for that note. Do not invent a guid for a note that already exists, or the import will add a duplicate.

Do not write notes with `updateNoteFields` or `addNote`. Write an import file the user imports, so Anki's import screen shows every change. One notetype per file. Put vocab changes in `farsi_import.txt` in the repo. Put sentence-note changes in `farsi_sentences_import.txt`. An existing note keeps its guid, so the import updates that note. A new note gets a new guid.

Copy guid, deck, ScriptUnlocked, English, script, transliteration, and tags from Anki unless that field is one you are fixing. Never set or clear ScriptUnlocked.

If `Example` or `Example Blank` is missing from the model, stop and say so. An import cannot create those fields.

## Blank fronts

Anki builds a card when that template's front would show text. If every template is locked, it still keeps one card, and the front is blank. Suspend those cards or they show up in study.

A front shows text when, after `{{#Field}}` / `{{^Field}}` and replacements (`{{Field}}`, `{{type:Field}}`, `{{hint:Field}}`), some text remains. A field is empty when it has no text. `ScriptUnlocked`, `SentenceUnlocked`, and `SentenceScriptUnlocked` count only when the value is `1`.

If no template on a note would show text, that note has no available card. Suspend every card on it. Also suspend a card whose own front would show no text, even when another card on the same note is available. Vocab FA↔EN stays available while script is locked, so do not suspend those cards. A new sentence note leaves both unlock fields empty, so none of its cards are available.

The import file cannot suspend. For notes already in Anki, suspend their card ids with AnkiConnect action `suspend`. Do not unsuspend. Do not set or clear an unlock field to do this. `anki_unlock.py` suspends the same cards on every run. `python anki_unlock.py --suspend-locked` suspends them and does not change unlock fields. Run that after the notes are in Anki, including after the user imports.

## File

The import uses this header:

```text
#separator:tab
#html:true
#guid column:1
#notetype column:2
#deck column:3
#tags column:10
```

Ten tab-separated fields. Anki maps columns 4–9 onto the note type in this order. The live script field is named `Farsi Script`.

| # | Field | Rule |
|---|-------|------|
| 1 | guid | Keep existing. New notes get a new 10-character Anki guid. |
| 2 | notetype | `Farsi` |
| 3 | deck | Keep the note's deck. New notes use `Farsi`. |
| 4 | Farsi Transliteration | Lowercase spelling key. See below. |
| 5 | English | Short gloss. Keep wording that is already right. |
| 6 | Farsi Script | Normal Persian spelling, no vowel marks. |
| 7 | Example | Spoken sentence in Persian script. See [Example sentence](#example-sentence). |
| 8 | Example Blank | That same sentence in Persian script, with this note's word replaced by `____` and a right-to-left mark (U+200F) on each side of the underlines. |
| 9 | ScriptUnlocked | `1` or empty. Never set or clear this. |
| 10 | tags | Space-separated. Every note needs at least one. |

`#html:true` means a field that contains `"` is wrapped in quotes and internal quotes are doubled. Quote a field only when it contains a tab, a newline, or `"`. Include only notes you are changing, plus new notes.

In a verb field the stem separator is `>` or `&gt;`. Both import as `>`. When you rewrite a verb field, write `&gt;`. Copy a verb field you are not rewriting as Anki stored it.

## Transliteration

This spelling is supposed to be standardized so the user can go from the transliteration to the spelling. One sound, one letter. All lowercase.

| Write | Sound | Spells as |
|-------|--------|-----------|
| a | short a | fathe, or initial ا for a word that starts with that vowel |
| aa | long a | آ, or ا when ا is the long vowel |
| e | short e | kasre |
| i | long e | ی as a vowel, ای |
| o | short o | zamme, or و when و is the short vowel (تو `to`) |
| u | long oo | و when و is the long vowel (خوب `khub`, خونه `khuneh`) |
| v | consonantal و | و |
| y | consonantal ی | ی |

Do not write `oo`, `ee`, `â`, `ā`, `ī`, `ū`, or an apostrophe. `oo` is `u`. `ee` is `i`. ع and ء get no letter; still write the vowel beside them (`aashegh`, `saat`). Do not mark tashdid. Final ه is `h` on its vowel (`khaaneh`, `hafteh`). A letter that is written but often unsaid goes in parentheses: `ye(k)`, `u(n)`, `sob(h)`.

The script field is everyday spelling, not a letter-by-letter copy of the short vowels. `bad` is `بد`, not `بَد`.

## Formal and spoken

`formal ~ spoken`, with spaces around `~`. Use this when Tehrani speech actually differs. One form when it does not.

- Different spelling: both fields carry both sides. `khaaneh ~ khuneh` / `خانه ~ خونه`.
- Same spelling, different sound: both sounds in the transliteration, one spelling in script. `raftan &gt; rav ~ ro` / `رفتن &gt; رو`.
- Two words the user already paired (جدید / تازه, ممنون / مرسی) stay one note. Do not split them and do not drop one.

Verbs: `infinitive &gt; present-stem`. Present stem is the stem after `mi-` / `be-`, not the past stem. When the infinitive and the stem both change: `formal-infinitive ~ spoken-infinitive &gt; formal-stem ~ spoken-stem`, and the script mirrors only the spelling changes. `aamadan ~ umadan &gt; aa ~ u` / `آمدن ~ اومدن &gt; آ ~ او`.

Before inventing a stem, copy the stem already on that verb's note in the deck. Compound notes use that stem: `fekr kardan &gt; kon` because `kardan &gt; kon` is the deck's stem. Add a spoken stem only when it is standard Tehrani. If you are not sure it differs, leave one form.

## What to fix

Run [scripts/lint_notes.py](scripts/lint_notes.py) on the import file. Fix every error. Then run it again and stop only when it prints `OK`.

On each bad note:

1. Lowercase the transliteration and apply the vowel table. `khooneh` → `khuneh`, `oon` → `un`, `oomadan` → `umadan`, `doonestan` → `dunestan`, `Ruye` → `ruy`, `Vaali` → `vali`, `anha` (آنها) → `anhaa`.
2. Add the missing formal or spoken side when the shift is real. See [reference.md](reference.md).
3. Make the script match those spellings. Persian ی and ک, not Arabic ي and ك. No extra spaces.
4. Fill tags from the inventory in [reference.md](reference.md). A light-verb compound is `Verb`.
5. Keep the English gloss. Extend it only when a second form makes the old gloss wrong. First letter capital. Verbs start with `To `. No trailing space.
6. Write the row with ten fields. Preserve guid, deck, and ScriptUnlocked.
7. Fill Example and Example Blank when either is empty, or when covering the word leaves a blank you cannot guess. Follow [Example sentence](#example-sentence).

Do not delete notes. Do not reorder existing notes. Do not change a gloss that is already accurate. Do not set `ScriptUnlocked`. Leave an example that already makes the covered word obvious.

Changing a transliteration changes the slug sentence notes use in `req::` tags (`khooneh` becomes `khuneh`). If you are also writing sentence notes, update those tags. If you are not, still fix the vocab spelling and list the old → new slugs in the summary.

## Adding a word list

When the user also gives a list or a URL:

1. Collect each word's Persian spelling and English meaning. Convert any source romanization into this transliteration. Do not paste `â` or apostrophes through.
2. Skip a word already in Anki. Match Persian spelling after unifying ی/ي and ک/ك and stripping diacritics, tatweel, and ZWNJ. Also match transliteration keys split on `~`, `/`, and `>`.
3. If the list only adds the spoken side of a note that is already there, update that note in the import. Do not add a duplicate.
4. New notes go in the import, in list order. Deck `Farsi`. Empty `ScriptUnlocked`. New guid, unique among the import and the notes already in Anki. Same shapes as the other notes, including Example and Example Blank.
5. Add the listed compounds even if the noun and the light verb are already notes. Do not add compounds the list did not ask for.
6. Add sentences for the words you just added. Follow [Sentences](#sentences).

## Example sentence

Every vocab note carries one spoken sentence that uses that word. Write it in the same pass as the other fixes and the Farsi Sentence notes. It stays on the vocab row. It is not a `Farsi Sentence` note.

Read `learned_vocab.txt` next to `anki_unlock.py` when that file exists. Prefer words listed there (`learned` and `mature`). You may use words that are not in it, including words that are not in the deck, when the line needs them. Prefer a known word over an unknown one.

The line is a memory cue, as short as it can be. Colloquial Tehrani: `mishe`, `aare`, `digeh`, `alaan`, `un`, `ro`, `ageh`, `khuneh`, spoken endings. Use the spoken side of this note, conjugated when it is a verb. No `~`. No vowel marks.

Covering this note's word has to still point at the meaning. Pick the other words for that, then stop. A line that is only the word (`نمی‌دونم.`) leaves a blank card. A leftover that is only `خیلی`, or only a pronoun, does not point at the meaning. Two words is enough when the other word already makes the blank obvious (`غذا می‌خورم`). Add one word when it does not (`نمی‌دونم کجاست`, `از حرفش ناراحتم`). Do not add a second clause.

Example is that line in normal spelling, including `می‌` with ZWNJ. Questions use `؟`.

An ASCII period is a left-to-right character. Put a right-to-left mark (U+200F) on each side of it, the same way as the underlines, in both Example and Example Blank. Otherwise it jumps to the right of the line. `؟` is already right-to-left and does not need the marks.

Example Blank is that same line in Persian script. Replace the form of this note that appears in the line with `____`, and put a right-to-left mark (U+200F) on each side of those underlines. One blank. The marks keep the underlines in the word's place. If this note is a prefix or suffix written onto another word, replace that whole word. `خونه` in `فردا می‌رم خونه.` becomes `فردا می‌رم ‏____‏.` A verb shows up conjugated: `می‌رم` in that line becomes `فردا ‏____‏ خونه.` The period in that line is stored `‏.‏`.

## Sentences

After new vocab is in the import, add sentence notes that use those words. Write them to `farsi_sentences_import.txt`. Do not put `Farsi Sentence` notes in `farsi_import.txt`. The example on a vocab note is a field of that note, not one of these rows.

Match an existing sentence file's header. A new file is:

```text
#separator:tab
#html:true
#guid column:1
#notetype column:2
#deck column:3
#tags column:11
```

Columns: guid, `Farsi Sentence`, `Farsi Sentences`, Farsi Transliteration, English, Farsi Script, ClozePrompt, SentenceUnlocked, SentenceScriptUnlocked, Hint, tags.

Leave both unlock fields empty. That note has no available card, so its cards must be suspended once they exist in Anki. See [Blank fronts](#blank-fronts). New guid. Do not duplicate a sentence already in `note:"Farsi Sentence"`.

Use a sentence people actually say. Length does not decide that. A common line can be short or long.

A short sentence is allowed only when people say that line all the time. `Salaam, chetori?` and `Khasteam.` count. `Otaagh bozorge` does not. If the new word is not part of a common short line, put it in a longer sentence that uses several other words from the deck.

Tag length, not commonness: `diff::1` short, `diff::2` medium, `diff::3` longer. A long line people say every day is still `diff::3`.

Prefer a few dense sentences that cover the new words over one thin sentence per word. Every new content word still has to appear in at least one sentence.

Write colloquial Tehrani, the way the sentence deck already does: `mishe`, `aare`, `digeh`, `alaan`, `un`, `ro`, `ageh`, `khuneh`, spoken endings. Every content word must already be a vocab note. If a natural sentence needs a word that is not in the deck, write a different sentence.

Transliteration uses the same spelling key as the vocab notes. Capitalize the first letter of the sentence only. Script is the same spoken sentence in normal spelling, including `می‌` with ZWNJ.

`req::` tags use the vocab key of each word in the sentence. Slug = lowercase, spaces removed, then drop every character except `a-z`, `0-9`, `*`, and `-`. Split the vocab headword on `~`, `/`, and `>` first, and tag the piece that appears. `mishe` → `req::mishe`. `sohbat mikonam` → `req::sohbatkardan`. `to-ro` → `req::to` and `req::raa`. Also tag `diff::` and a `theme::` (`greeting`, `daily`, `plans`, `feelings`, `questions`, `affection`, or a short new one).

ClozePrompt is the transliteration with one blank on the new word, and only when the rest of the line is still a sentence. Leave it empty on a fixed phrase. Hint is a few words or empty.

## Report

Tell the user the import path, how many notes you fixed, how many you added, and how many list words were already present. Say how many example sentences you added and how many Farsi Sentence notes you added, and which new words those sentence notes cover. Give a few before → after examples. Mention transliteration slugs that changed. Say how many fully locked cards you suspended. If new notes are not in Anki yet, say those cards get a blank front until they are suspended after import. Do not paste the deck. The user imports the file; do not import it for them.
