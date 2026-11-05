---
name: farsi-anki-notes
description: >-
  Fill and normalize live Farsi Anki vocab notes through AnkiConnect: formal
  and spoken forms, Persian script, part-of-speech tags, and transliteration
  (u for long oo, aa for long a, i for long e, a for short a, o for short o,
  e for short e). Write note changes to an import file the user reviews in
  Anki. Suspend cards on a note that has no available template, so Anki does not
  show a blank front. Use when the user adds incomplete Farsi notes, asks to fix
  note formatting or transliteration, or wants words from a Persian vocabulary
  or frequency list.
---

# Farsi Anki notes

Normalize the user's live Farsi notes, then add any word list they supply. Match notes already in Anki. Read [reference.md](reference.md) for spoken alternations and tags. Read [examples.md](examples.md) before rewriting a row.

Vocab notes do not carry example sentences.

## Decks

```text
Farsi            ← main deck; new vocab goes here
└── Queue        ← paced backlog
```

Study and browse `Farsi`. `anki_unlock.py` searches `deck:"Farsi"`, which includes `Farsi::Queue`.

| Note | Deck |
|------|------|
| New vocab from this skill / import | `Farsi` |
| Existing vocab being fixed | Keep that note's deck. Never move a note between `Farsi` and `Farsi::Queue`. |

Script **cards** (not notes) on a note whose `ScriptUnlocked` is `1` are moved to `Farsi::Queue` at the card level via AnkiConnect `changeDeck`. The note itself stays in whatever deck it is in. See [Script card placement](#script-card-placement).

## Source

Anki is open with AnkiConnect at `http://127.0.0.1:8765`. If AnkiConnect does not answer, stop.

Do **not** load full `notesInfo` JSON into context. That dump is tens of thousands of tokens. Use the compact indexes instead:

1. Run `python anki_unlock.py --export-indexes` when `deck_index.txt` is missing or stale.
2. Read `deck_index.txt` for vocab (guid, deck, transliteration, english, script, ScriptUnlocked, tags).
3. Read `learned_vocab.txt` for learned words.

Fetch a single note with AnkiConnect only when the index row is not enough. Never pull the whole deck through `notesInfo`.

Guids are in the index files. Copy the guid already on that note. Do not invent a guid for a note that already exists, or the import will add a duplicate.

Do not write notes with `updateNoteFields` or `addNote`. Write an import file the user imports, so Anki's import screen shows every change. One notetype per file. Put vocab changes in `farsi_import.txt` in the repo. An existing note keeps its guid, so the import updates that note. A new note gets a new guid.

Copy guid, deck, ScriptUnlocked, English, script, transliteration, and tags from the index (or Anki) unless that field is one you are fixing. Never set or clear ScriptUnlocked. Never change an existing note's deck.

## Script card placement

When a note has `ScriptUnlocked` = `1`, its script cards (the card templates whose front shows the Farsi script) must live in `Farsi::Queue`, even if the note itself is in `Farsi`. The import file cannot do this; use AnkiConnect `changeDeck` after the notes are in Anki.

Steps:

1. Find the card ids of script cards on `ScriptUnlocked` notes in `Farsi` (not already in `Farsi::Queue`):
   ```json
   {"action": "findCards", "version": 6,
    "params": {"query": "deck:Farsi ScriptUnlocked:1"}}
   ```
   Filter that list to cards whose template front references the script field (template name contains `Script` or `FA Script`).
2. Move those card ids:
   ```json
   {"action": "changeDeck", "version": 6,
    "params": {"cards": [<ids>], "deck": "Farsi::Queue"}}
   ```

Do this after every import that unlocks script cards, and after `python anki_unlock.py --suspend-locked` (so suspended script cards are already excluded from study before the deck move). Do not move script cards that are already in `Farsi::Queue`.

## Blank fronts

Anki builds a card when that template's front would show text. If every template is locked, it still keeps one card, and the front is blank. Suspend those cards or they show up in study.

A front shows text when, after `{{#Field}}` / `{{^Field}}` and replacements (`{{Field}}`, `{{type:Field}}`, `{{hint:Field}}`), some text remains. A field is empty when it has no text. `ScriptUnlocked`, `VerbScriptUnlocked`, and `Verb2ScriptUnlocked` count only when the value is `1`.

If no template on a note would show text, that note has no available card. Suspend every card on it. Also suspend a card whose own front would show no text, even when another card on the same note is available. Vocab FA↔EN stays available while script is locked, so do not suspend those cards.

The import file cannot suspend. For notes already in Anki, suspend their card ids with AnkiConnect action `suspend`. Do not unsuspend. Do not set or clear an unlock field to do this. `anki_unlock.py` suspends the same cards on every run. `python anki_unlock.py --suspend-locked` suspends them and does not change unlock fields. Run that after the notes are in Anki, including after the user imports.

## File

The import uses this header:

```text
#separator:tab
#html:true
#guid column:1
#notetype column:2
#deck column:3
#tags column:8
```

Eight tab-separated fields when the note has no verb. Anki maps columns 4–7 onto the first four fields of the note type. The live script field is named `Farsi Script`. A row that fills a verb slot on an existing base note is sixteen fields, with `#tags column:16`, and keeps the base guid, deck, and `ScriptUnlocked`. For a standalone verb with no base noun (e.g. `maandan ~ mundan > maan ~ mun`, `raftan > rav ~ ro`): Anki GUI text import strictly requires that the first mapped field (`Farsi Transliteration`, Column 4) is not blank. Write the verb into the main fields (Columns 4, 5, 6), leave the verb columns empty, and tag `Verb`. After importing, run `python anki_unlock.py --verb-slots --apply` to move it into the verb slot. Do not mix 8-column and 16-column rows in one file.

| # | Field | Rule |
|---|-------|------|
| 1 | guid | Keep existing. New notes get a new 10-character Anki guid. |
| 2 | notetype | `Farsi` |
| 3 | deck | New notes use `Farsi`. Existing notes keep their deck. Never change a note's deck in the import file. |
| 4 | Farsi Transliteration | Lowercase spelling key. See below. |
| 5 | English | Short gloss. Keep wording that is already right. |
| 6 | Farsi Script | Normal Persian spelling, no vowel marks. |
| 7 | ScriptUnlocked | `1` or empty. Never set or clear this. |
| 8 | tags | Space-separated, on an 8-column row. Every note needs at least one. |
| 8 | Verb Transliteration | On a 16-column row. Same spelling rules as the noun. |
| 9 | Verb English | Short gloss. Verbs start with `To `. |
| 10 | Verb Script | Persian spelling of that verb. |
| 11 | VerbScriptUnlocked | `1` or empty. Copy it when a verb note already has a value. Never set or clear it otherwise. |
| 12 | Verb2 Transliteration | Second verb, or empty. |
| 13 | Verb2 English | |
| 14 | Verb2 Script | |
| 15 | Verb2ScriptUnlocked | `1` or empty. Same rule as the first verb unlock. |
| 16 | tags | On a 16-column row. |

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
- Two different words for one meaning stay one note. Do not split them and do not drop one. The delimiter is in [Same meaning](#same-meaning).

Verbs: `infinitive &gt; present-stem`. Present stem is the stem after `mi-` / `be-`, not the past stem. When the infinitive and the stem both change: `formal-infinitive ~ spoken-infinitive &gt; formal-stem ~ spoken-stem`, and the script mirrors only the spelling changes. `aamadan ~ umadan &gt; aa ~ u` / `آمدن ~ اومدن &gt; آ ~ او`.

Before inventing a stem, copy the stem already on that verb's note in the deck. Compound notes use that stem: `fekr kardan &gt; kon` because `kardan &gt; kon` is the deck's stem. Add a spoken stem only when it is standard Tehrani. If you are not sure it differs, leave one form.

## Same meaning

One meaning, one note. Match the meaning, not only the spelling.

Two different words for that meaning go on the one note, with spaces around the delimiter. Both the transliteration and the script use it.

- Neither word is more formal or more colloquial: `/`. `esm / naam` / `اسم / نام`. `dobaareh / baaz` / `دوباره / باز`. `jadid / taazeh` / `جدید / تازه`.
- One word is more formal and the other is more colloquial: `~`, formal side first. `pedar ~ baabaa`. `mamnun ~ mersi`. `khorshid ~ aaftaab` (خورشید is formal, آفتاب is everyday). A pronunciation pair such as `khaaneh ~ khuneh` uses this same `~`.

Same spelling, different meaning: two notes. `baaz` / Open stays its own note. Again is `dobaareh / baaz`. Do not merge those meanings, and do not write `dobaareh ~ baaz`.

A new note that only repeats a meaning already in the deck: add its word to the older note with `/` or `~`, and keep the older guid and deck. Leave the new note out of the import. If its cards are still new, delete it with AnkiConnect `deleteNotes`. Do not delete the older note.

Do not sweep the deck for older pairs unless the user asks. If you notice one while matching, name it in the report.

## Pieces of a new word

When a new note is added, also add colloquially used pieces that are not already notes. A piece counts when people say it as its own word or prefix, not only inside the longer word.

- Subword: `biparvaa` also adds `parvaa` (پروا). From دلتنگی enter `deltang`, and also add `tang`, because people say تنگ. دل is already a note, so it is not added again.
- New prefix or suffix: add it once, in the tag inventory's shape (`bi-`, `be-`). Do not add a second note if that prefix is already there.
- Compound verb, or a plain verb of the same root and the same idea: write it onto the base note's verb slot. The base stays the noun or adjective. `ghadam zadan` goes on `ghadam`. `baaridan` goes on `baaraan`, because rain and to rain are the same idea. Keep the base guid, deck, and `ScriptUnlocked`. A second verb on that word uses the Verb2 fields. A third verb stays its own note, written into the main fields with tag `Verb`.
- A verb with no base stays its own note. In `farsi_import.txt`, write it into the main fields with tag `Verb` so Anki's text import does not fail with an "empty first field" error. Then `python anki_unlock.py --verb-slots --apply` moves it into its own verb slot. `raftan` and `maandan` are that shape. `bar daashtan` does not join the preposition `bar`, so it stays a standalone verb note too. `charkh` (wheel) does not join `charkhidan`. `baar` (time or turn) does not join `baaridan`. `sakht` and `doshvaar` stay the pair they already are. `ghahveh` does not join `ghahvei`.
- When the new word is a noun or adjective, check for a verb people actually use with it: a light-verb compound, or the same root and the same idea (`baaraan` / `baaridan`). If that verb is already a note, it belongs in this note's verb slot. If people use the verb and it is not a note yet, write it in the verb slot of this note. Do not give it a second guid.
- When the new word is a verb, check for a base people actually say. If that base is already a note, write the verb into its verb slot. If the base is missing and people say it, the note's main fields are the base and the verb goes in the verb slot (`tark` / `tark kardan`). If there is no base, write the verb in the main fields with tag `Verb`, and explicitly remind the user to run `python anki_unlock.py --verb-slots --apply` after importing.
- Ending `-i`, or another ending just as transparent: keep one note when the two words are the same idea. A noun and the adjective for that same thing, or the reverse, is one note, even when people say both often. Keep the form without `-i`. `zakhmi` is wounded, the same idea as `zakhm` (wound), so the note is `zakhm` / زخم. `bedehkaari` is debt, the same idea as `bedehkaar` (in debt), so the note is `bedehkaar` / بدهکار. `zibaayi` is the noun from `zibaa`, so the note is `zibaa`. `deltangi` is the noun from `deltang`, so the note is `deltang`. If the word being added is that same-idea form, enter the base instead. If the deck already has that form and not the base, rewrite the note to the base. If the base is already a note, do not add the derived form.
- Keep both when the derived word is a new meaning, not the same idea in another part of speech. `ghahveh` is coffee and `ghahvei` is brown. `khaakestar` is ash and `khaakestari` is grey. `zendaan` is prison and `zendaani` is prisoner. Add the missing one. Do not rewrite the derived note into the base. A verb of the same idea and the same root is the verb-slot case above, not this one.

Do not add a conjugated form of a verb the deck already has. `bardaar` (بردار) is `be-` plus the stem `daar` on `bar daashtan > daar`. `bogzaar` (بگذار) is `be-` plus `gozaar` on `gozaashtan > gozaar ~ zaar`; the spoken command is بذار from the stem `zaar` already on that note. Do not add a bound fragment nobody says alone.

## What to fix

Run [scripts/lint_notes.py](scripts/lint_notes.py) on the import file. Fix every error. Then run it again and stop only when it prints `OK`.

On each bad note:

1. Lowercase the transliteration and apply the vowel table. `khooneh` → `khuneh`, `oon` → `un`, `oomadan` → `umadan`, `doonestan` → `dunestan`, `Ruye` → `ruy`, `Vaali` → `vali`, `anha` (آنها) → `anhaa`.
2. Add the missing formal or spoken side when the shift is real. See [reference.md](reference.md).
3. Make the script match those spellings. Persian ی and ک, not Arabic ي and ك. No extra spaces.
4. Fill tags from the inventory in [reference.md](reference.md). A light-verb compound is `Verb`.
5. Keep the English gloss. Extend it only when a second form makes the old gloss wrong. First letter capital. Verbs start with `To `. No trailing space.
6. Write an eight-field row when the note has no verb. A verb uses the sixteen-field row. Keep the base guid when the verb joins that note. A verb with no base keeps its own guid and is written into the main fields with tag `Verb` (to avoid Anki's empty-first-field error). Preserve deck and ScriptUnlocked. Do not move a note between `Farsi` and `Farsi::Queue`.

Do not delete a note the deck already had. Delete only a newly added note whose meaning is already covered, as in [Same meaning](#same-meaning). Do not reorder existing notes. Do not change a gloss that is already accurate. Do not set `ScriptUnlocked`. Do not put example sentences on vocab notes.

Fix the vocab spelling and list any old → new transliterations in the summary.

## Adding a word list

When the user also gives a list or a URL:

1. Collect each word's Persian spelling and English meaning. Convert any source romanization into this transliteration. Do not paste `â` or apostrophes through.
2. Match notes already in Anki before adding. Match Persian spelling after unifying ی/ي and ک/ك and stripping diacritics, tatweel, and ZWNJ. Also match transliteration keys split on `~`, `/`, and `>`. A different word with the same meaning is not a new note: fold it onto the existing note with `/` or `~`. See [Same meaning](#same-meaning). Same spelling with a different meaning is a separate note.
3. If the list only adds the spoken side of a note that is already there, update that note in the import. Do not add a duplicate.
4. New notes go in the import, in list order. Deck `Farsi`. Empty `ScriptUnlocked`. New guid, unique among the import and the notes already in Anki. A noun or adjective with no verb is eight fields. A verb, or a word that has a verb slot, is sixteen fields.
5. A verb that is the same idea and the same root is written onto the base note's verb slot, light verb or not. Keep the base guid. Before adding a noun or adjective, check for a verb people use with that word. Before adding a verb, check for a base people say. A missing base that people say becomes the main fields, with the verb in the verb slot. A verb with no base keeps its own guid, is written into the main fields with tag `Verb`, and requires running `python anki_unlock.py --verb-slots --apply` after import. A different idea or a different root stays apart. Do not invent an unrelated compound. Do add colloquially used subwords and new prefixes. If a listed word is only `-i`, or another ending just as transparent, and it is the same idea as the base, enter the base instead. If that word is a new meaning, keep it and add the base when people say the base. See [Pieces of a new word](#pieces-of-a-new-word).

## Report

Tell the user the import path, how many notes you fixed, how many you added, and how many list words were already present. Say which same-meaning words were folded onto an existing note, whether the delimiter was `/` or `~`, and which new notes were deleted. Say which subwords or prefixes you added with the new words, which derived `-i` forms you rewrote to the base because they are the same idea, which you did not add for that reason, and which you kept because the derived word is a new meaning, and which surface forms you did not add because they are only a conjugation of a verb already in the deck. Name any older same-meaning pair you noticed and did not change. Give a few before → after examples. Mention transliterations that changed. Say how many fully locked cards you suspended. If new notes are not in Anki yet, say those cards get a blank front until they are suspended after import. Do not paste the deck. The user imports the file; do not import it for them.

**MANDATORY USER REMINDER:** Whenever any standalone verb is written to `farsi_import.txt`, you MUST explicitly remind the user to run `python anki_unlock.py --verb-slots --apply` after importing into Anki, followed by `python anki_unlock.py --suspend-locked`.
