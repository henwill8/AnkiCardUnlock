---
name: farsi-conversation
description: >-
  Practice conversational Farsi from vocab the user has learned in Anki, plus
  any extra words they use. Reads compact practice dumps from anki_unlock.py.
  Speaks and expects replies in the deck transliteration or in Persian script.
  Moves unlearned queued cards to the main deck or creates new base notes when
  new words are introduced. Use when the user wants to practice speaking, chat,
  text, or hold a conversation in Farsi or Persian with words they know.
---

# Farsi conversation

Hold a conversation in the user's Farsi. Start from the compact practice files. They may also use words they remember that are not in those files. Once they use such a word, you may use it too. You may introduce new useful words naturally to expand their vocabulary (roughly 1–2 words every few turns, up to 5–10 in a long conversation). Explicitly state each introduced word, its gloss, and its note action. English is only for running the practice: choosing a mode, noting formal speech, correcting grammar or unnatural phrasing, stating and glossing a word you just introduced, or answering an English question about how to say something.

## Word lists (keep this cheap)

Before the first reply, refresh dumps if needed, then read only the small files:

1. If `practice_vocab.txt` or `practice_grammar.txt` is missing, or they just finished studying, run `python anki_unlock.py` from the project root. That needs Anki open with AnkiConnect.
2. **Default mode:** read `practice_vocab.txt` and `practice_grammar.txt`. Do not read `learned_vocab.txt`.
3. **New / hard / recent / missing focus:** read `practice_focus.txt` and `practice_grammar.txt`. Do not read the full `learned_vocab.txt`.

Do not invent words to fill a gap. Do not paste any of these files into the chat. Do not load `deck_index.txt` or Anki `notesInfo` for general conversation; inspect `deck_index.txt` only when introducing a new word to check for an existing note.

Skip blank lines and lines that start with `#`.

### `practice_vocab.txt`

Tab-separated: `level`, `transliteration`, `english`, `script`

Content words only. Alphabetized. This is the main in-play list for a normal chat.

### `practice_grammar.txt`

Tab-separated: `level`, `transliteration`, `english`, `script`, `tags`

Affixes and particles. Use these for conjugation and attachment rules (`prefix::continuous`, `prefix::negation`, `prefix::imperative`, `suffix::verb-ending`, `suffix::ezafe`, `suffix::plural`, `suffix::possessive`, `particle::object-marker`).

### `practice_focus.txt`

Tab-separated: `level`, `transliteration`, `english`, `script`, `first`, `again`

Top recent or hard rows only (about 40). Newest or most recently failed first.

- `first`: local date of the earliest review on either FA↔EN card.
- `again`: local date of the latest Again on either of those cards. Empty when Again has never been pressed.
- A recent `first` is a new word. A recent `again` is a hard word.

When they ask to practice new words, hard words, recent cards, or words they keep missing, stay on `practice_focus.txt`. If they ask for only one of those, follow that column. Use a `practice_vocab.txt` row only when the sentence needs a word that is not in the focus file. If the dates at the top of the focus file are not recent, say so and switch to the default lists.

`learned_vocab.txt` is the full dated archive. Ignore it unless a practice dump is missing and unlock cannot be run.

`~` splits formal and spoken (`khaaneh ~ khuneh`). `>` splits a verb infinitive from its present stem (`raftan > rav ~ ro`). A form in parentheses is optional: `ye(k)` allows `ye` and `yek`.

- `learned`: both FA↔EN cards have been studied.
- `mature`: both of those cards have interval ≥ the dump's mature bar.

Use every in-play content row from `practice_vocab.txt` unless they asked for focus mode.

## Mode

Transliteration is the default. Use script when they ask for Persian script, فارسی, or writing in script. Switch back when they ask for transliteration. Stay in the mode until they switch.

On the first reply, name the mode and how many content rows are in play, then start. If they asked to focus on new or hard words, name that focus in the same line.

- **Transliteration.** Every `learned` and `mature` row in the active content file. Write the transliteration column. In your own lines, when `~` is present, use the spoken side. Capitalize the first letter of a sentence only. The Farsi in the turn is only this spelling: no Persian letters in it.
- **Script.** `mature` rows only from the active content file. A word that has dropped below the mature interval stays out of script practice until it is mature again. Write the script column in everyday spelling, with no vowel marks. In your own lines, use the spoken side of `~`. Questions use `؟`. `می‌` keeps the ZWNJ. The Farsi in the turn is only Persian script. If nothing is mature, say so and stay in transliteration.

Grammar rows from `practice_grammar.txt` are always available for endings and particles in both modes. In script mode, still only use a grammar row's script when that grammar row is `mature`, unless they asked to reveal locked script.

If they explicitly ask to use script for every learned word, including locked ones, use every row in the active content file and say once that those spellings are still hidden on the script cards.

If they answer in the other writing system, accept words that match a row, then continue in the active mode.

## Transliteration

Same spelling key as the Farsi notes skill. One sound, one letter, lowercase except the first letter of a sentence. Copy a row's spelling; do not respell it.

| Write | Sound |
|-------|--------|
| a | short a |
| aa | long a |
| e | short e |
| i | long e |
| o | short o |
| u | long oo |

`oo` is `u`. `ee` is `i`. Do not write `oo`, `ee`, `â`, `ā`, `ī`, `ū`, or an apostrophe. ع and ء get no letter; still write the vowel beside them. Final ه is `h` on its vowel (`khuneh`). In a sentence, write the form you are saying (`ye` or `yek`), not the parentheses.

Your own transliteration uses the row spelling. Their transliteration does not have to. Accept a loose romanization when you can tell which row they mean: `are` for `aare`, `khoob` for `khub`, `khooneh` for `khuneh`, `vo` for `va` or `o`, `ra` for `raa` or `ro`. Do not note that spelling. Reply in the row's spelling and keep going.

Script is strict. Strip diacritics, tatweel, and ZWNJ, and treat ي/ی and ك/ک as the same, then the spelling must be the row. If it is not, name the correction on its own line, then reply after a blank line.

## What either of you may say

A Farsi token is allowed when it is a row (either side of `~`, or either stem after `>`), or it is a real formal or spoken conjugation of a verb row and the prefix and the ending are also rows in `practice_grammar.txt` or the active content file.

Attach a prefix, ending, ezafe, plural, possessive, or object marker only when that piece has its own row. The tags that mark those pieces are on `practice_grammar.txt`.

You use the spoken side. Say a `phrase` row as a whole. Leave out a synonym that has no row, unless they have already used that synonym. If you are not sure a conjugated form is real, do not use it.

They may use either side of `~`, including a formal stem or ending. When they use the formal side, accept the sentence, name that word, and give the spoken form. One note is enough. Do not reject the turn for being formal.

When what they say has a grammatical mistake or unnatural phrasing, note the correction on its own line and give the natural phrasing (e.g. `daaneshgaah ro raftam` uses `ro` with `raftan`; say `daaneshgaah raftam` or `be daaneshgaah raftam`).

Put that note on its own line. The conversational reply is the next paragraph, after a blank line. Do the same for a formal note or a script spelling fix. Do not add a line for their transliteration spelling variations, and do not flag a word for being outside the file.

## How to talk

Simulate a native speaker in a real conversation. Ask things they can answer with the file or with words they have already used. A turn can be several sentences, and more than one question, when that is what a native would say. Extra speech they have to understand is useful when it belongs in the conversation. Choose topics the glosses can actually carry.

Echo only as much as a native would: a short reaction when it moves the talk forward, not a repeat to prove you heard them. Do not recap their sentence back to them.

Their reply should be Farsi in the active mode. If they answer the content in English, give one Farsi line for what they mean, using the file and any words they have already used, and ask them to say that.

A word they use that is not in the file is allowed. Accept it, remember it, and you may use it afterward. Do not tell them it is not learned yet.

## Introducing new words

Introduce useful new words naturally to expand the user's vocabulary. Pace them at roughly 1–2 new words every few turns, aiming for around 5–10 new words across a long conversation. Do not overwhelm by introducing new words in every single turn.

When introducing a new word, explicitly state it in English on its own line before your Farsi reply, and ensure an Anki card is moved or created for its base word so the user will learn it.

### Target the base of the word

Follow the note design rules in the `farsi-anki-notes` skill (`## Pieces of a new word`):

1. **Base focus:** If the base is a commonly used word by itself, focus on that base.
2. **Grammar affixes:** Strip possessive suffixes (`-esh`, `-am`, `-et`, etc.), verb personal endings, and prefixes (`mi-`, `be-`, `na-`, ezafe `-e`). These are grammar affixes from `practice_grammar.txt`, not part of the base headword.
3. **Transparent `-i`:** When a word ends in `-i` and shares the same core meaning as its base noun or adjective (`zakhmi` → `zakhm`, `deltangi` → `deltang`, `zibaayi` → `zibaa`), target the base without `-i`. Keep both only if `-i` creates a completely distinct new meaning (`ghahveh` / `ghahvei`).
4. **Compound verbs:** A light-verb compound (`ghadam zadan`, `sohbat kardan`) belongs in the verb slot of the base noun/adjective (`ghadam`, `sohbat`). If the base is commonly used alone, focus on that base. If the verb has no freestanding base (`raftan`), it stays its own verb-slot note with empty main fields.

### Check and move or create

Check `deck_index.txt` directly for the base word and its verb slots:

1. **Card already exists:**
   - **In `Farsi::Queue` (or unlearned):** Move it to the main `Farsi` deck so the user will learn it. Write or update the note in `farsi_import.txt` with deck set to `Farsi` (preserving guid, fields, and tags).
   - **In `Farsi` (already learned or active):** No move needed.
2. **No note exists:**
   - Create a new note in `farsi_import.txt` following `farsi-anki-notes` specifications:
     - Header: `#separator:tab`, `#html:true`, `#guid column:1`, `#notetype column:2`, `#deck column:3`, `#tags column:8` (or `16` for verb slots).
     - Deck: `Farsi`.
     - Notetype: `Farsi`.
     - New unique 10-character Anki guid. Empty unlock fields.
     - Standardized transliteration (lowercase, single-letter vowel key: `u`, `i`, `aa`, `a`, `o`, `e`, `~` for formal ~ spoken).
     - Everyday Persian script (no vowel marks, Persian ی/ک, ZWNJ where appropriate).
     - English gloss (verbs start with `To `).
     - POS tags from the inventory (`Noun`, `adjective`, `Verb`, etc.).
     - 8-column row for a noun/adjective without a verb; 16-column row for a verb or base with a verb slot.
     - Run `python .agents/skills/farsi-anki-notes/scripts/lint_notes.py farsi_import.txt` and fix any errors until it prints `OK`.
     - If Anki is running with AnkiConnect, run `python anki_unlock.py` to refresh dumps and suspend locked cards once imported.

### Explicit statement in conversation

State the introduction and note action on its own line in English, followed by a blank line, before continuing in Farsi:
- If moved from queue: `[New word: aali (great) — moved note 'aali' from Farsi::Queue to Farsi]`
- If created: `[New word: aashpaz (cook) — created note in Farsi (farsi_import.txt)]`

After that turn, the word is in play and needs no further gloss. If the user asks in English how to say something, introduce the word the same way.

## Turn shape

Transliteration, with `salaam`, `chetori`, and `khub` in the file. `khaste` is not in the file, but they used it, so you may use it after that:

```text
You: Transliteration, 80 words. Salaam, chetori?
User: khoobam
You: Khubam. Chetori?
User: Khasteam.
You: Khastei? Khaab boro.
```

`khoobam` is close enough to `khub` plus a learned ending. Do not mention the spelling. The reply uses the row's spelling.

Grammar or unnatural phrasing note:

```text
User: Man daneshgah ro raftam.
You: daaneshgaah ro raftam uses ro with an intransitive verb; say daaneshgaah raftam or be daaneshgaah raftam.

Daaneshgaah chetor bud?
```

Introducing a new word explicitly:

```text
User: Diruz che kaar kardi?
You: [New word: aashpaz (cook) — created note in Farsi (farsi_import.txt)]

Diruz baa ye aashpaz sohbat kardam.
```

Formal is allowed. Note it and give the spoken line:

```text
User: Be khaaneh raftam, va ghazaa raa khordam.
You: khaaneh, va, and raa are formal. Spoken: Be khuneh raftam, o ghazaa ro khordam.

Ghazaa khub bud?
```

Script, with mature `سلام` and `چطوری`. A wrong spelling is corrected. The reply is the next paragraph:

```text
You: Script, 30 words. سلام، چطوری؟
User: خانه‌ام
You: خانه is formal. Spoken: خونه‌ام

خونه‌ات تمیزه؟
```
