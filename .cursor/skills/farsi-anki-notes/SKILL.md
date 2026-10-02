---
name: farsi-anki-notes
description: >-
  Fill and normalize Farsi Anki vocab notes in a tab-separated deck export
  (Farsi.txt): formal and spoken forms, Persian script, part-of-speech tags,
  and transliteration (u for long oo, aa for long a, i for long e, a for short
  a, o for short o, e for short e). Also add Farsi Sentence notes for newly
  added words. Commonly spoken lines can be any length. A short sentence
  must be commonly spoken; otherwise use a longer line with several deck
  words. Use when the user adds incomplete Farsi notes, asks to
  fix note formatting or transliteration, wants words from a Persian vocabulary
  or frequency list, or wants sentences for new vocab.
---

# Farsi Anki notes

Normalize notes in the user's Farsi vocab export, then add any word list they supply. Match notes already in the file. Read [reference.md](reference.md) for spoken alternations and tags. Read [examples.md](examples.md) before rewriting a row.

## File

The export is an Anki notes file, usually named `Farsi.txt`. Use the path the user gives. If they say it is exported and do not give a path, find `Farsi.txt` (Downloads is the usual place). Do not create a second copy.

Keep the header:

```text
#separator:tab
#html:true
#guid column:1
#notetype column:2
#deck column:3
#tags column:8
```

Eight tab-separated fields:

| # | Field | Rule |
|---|-------|------|
| 1 | guid | Keep existing. New notes get a new 10-character Anki guid. |
| 2 | notetype | `Farsi` |
| 3 | deck | `Farsi` |
| 4 | Farsi Transliteration | Lowercase spelling key. See below. |
| 5 | English | Short gloss. Keep wording that is already right. |
| 6 | Farsi | Normal Persian spelling, no vowel marks. |
| 7 | ScriptUnlocked | `1` or empty. Never set or clear this. |
| 8 | tags | Space-separated. Every note needs at least one. |

`#html:true` means a field that contains `"` is wrapped in quotes and internal quotes are doubled. Edit rows in place. Do not re-serialize the whole file. Quote a new field only when it contains a tab, a newline, or `"`.

In this file the verb-stem separator is `>` or `&gt;`. Both import as `>`. When you rewrite a verb field, write `&gt;`. Leave untouched rows as they are.

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

Run [scripts/lint_notes.py](scripts/lint_notes.py) on the file. Fix every error. Then run it again and stop only when it prints `OK`.

On each bad note:

1. Lowercase the transliteration and apply the vowel table. `khooneh` → `khuneh`, `oon` → `un`, `oomadan` → `umadan`, `doonestan` → `dunestan`, `Ruye` → `ruy`, `Vaali` → `vali`, `anha` (آنها) → `anhaa`.
2. Add the missing formal or spoken side when the shift is real. See [reference.md](reference.md).
3. Make the script match those spellings. Persian ی and ک, not Arabic ي and ك. No extra spaces.
4. Fill tags from the inventory in [reference.md](reference.md). A light-verb compound is `Verb`.
5. Keep the English gloss. Extend it only when a second form makes the old gloss wrong. First letter capital. Verbs start with `To `. No trailing space.
6. Repair the row so it has eight fields. Preserve guid and ScriptUnlocked.

Do not delete notes. Do not reorder existing notes. Do not change a gloss that is already accurate. Do not set `ScriptUnlocked`.

Changing a transliteration changes the slug sentence notes use in `req::` tags (`khooneh` becomes `khuneh`). If a sentence export is in the same task, update those tags. If it is not, still fix the vocab spelling and list the old → new slugs in the summary.

## Adding a word list

When the user also gives a list or a URL:

1. Collect each word's Persian spelling and English meaning. Convert any source romanization into this transliteration. Do not paste `â` or apostrophes through.
2. Skip a word already in the deck. Match Persian spelling after unifying ی/ي and ک/ك and stripping diacritics, tatweel, and ZWNJ. Also match transliteration keys split on `~`, `/`, and `>`.
3. If the list only adds the spoken side of a note that is already there, update that note. Do not append a duplicate.
4. Append truly new notes at the end, in list order. Empty `ScriptUnlocked`. New guid, unique in the file. Same shapes as the other notes.
5. Add the listed compounds even if the noun and the light verb are already notes. Do not add compounds the list did not ask for.
6. Add sentences for the words you just added. Follow [Sentences](#sentences).

## Sentences

After new vocab is in the file, add sentence notes that use those words. Append them to the sentence export if one is open (`Farsi_Sentences.txt`, or the file the user names). If none exists, create that file next to the vocab export. Do not put sentences in `Farsi.txt`.

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

Leave both unlock fields empty. New guid. Do not duplicate a sentence already in the file or, if Anki is open, already in `note:"Farsi Sentence"`.

Use a sentence people actually say. Length does not decide that. A common line can be short or long.

A short sentence is allowed only when people say that line all the time. `Salaam, chetori?` and `Khasteam.` count. `Otaagh bozorge` does not. If the new word is not part of a common short line, put it in a longer sentence that uses several other words from the deck.

Tag length, not commonness: `diff::1` short, `diff::2` medium, `diff::3` longer. A long line people say every day is still `diff::3`.

Prefer a few dense sentences that cover the new words over one thin sentence per word. Every new content word still has to appear in at least one sentence.

Write colloquial Tehrani, the way the sentence deck already does: `mishe`, `aare`, `digeh`, `alaan`, `un`, `ro`, `ageh`, `khuneh`, spoken endings. Every content word must already be a vocab note. If a natural sentence needs a word that is not in the deck, write a different sentence.

Transliteration uses the same spelling key as the vocab notes. Capitalize the first letter of the sentence only. Script is the same spoken sentence in normal spelling, including `می‌` with ZWNJ.

`req::` tags use the vocab key of each word in the sentence. Slug = lowercase, spaces removed, then drop every character except `a-z`, `0-9`, `*`, and `-`. Split the vocab headword on `~`, `/`, and `>` first, and tag the piece that appears. `mishe` → `req::mishe`. `sohbat mikonam` → `req::sohbatkardan`. `to-ro` → `req::to` and `req::raa`. Also tag `diff::` and a `theme::` (`greeting`, `daily`, `plans`, `feelings`, `questions`, `affection`, or a short new one).

ClozePrompt is the transliteration with one blank on the new word, and only when the rest of the line is still a sentence. Leave it empty on a fixed phrase. Hint is a few words or empty.

## Report

Tell the user the file path, how many notes you fixed, how many you added, and how many list words were already present. Say how many sentences you added and which new words they cover. Give a few before → after examples. Mention transliteration slugs that changed. Do not paste the deck.
