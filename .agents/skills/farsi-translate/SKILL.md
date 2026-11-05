---
name: farsi-translate
description: >-
  Translate English sentences into natural colloquial Farsi or Farsi messages
  (texts, replies) to English, break down grammar and vocabulary, and automatically
  add or move any unknown words into Anki via farsi_import.txt following the
  farsi-anki-notes rules. Use when translating between English and Farsi or
  processing Farsi messages to learn new words.
---

# Farsi Translate & Card Creation

## Interaction Modes

Determine which mode applies before doing anything else:

| Input | Mode | Action |
|---|---|---|
| **"Quoted English"** | English → Farsi | Translate into colloquial Tehrani Farsi, break down grammar, add unknown words to Anki |
| **Plain English** | Conversation | Answer the question or comment directly — no translation or Anki update needed |
| **Farsi script or transliteration (unquoted)** | Farsi → English | Translate into natural English (treat as a message from the user's girlfriend), break down grammar, add unknown words to Anki |

---

In translation modes (quoted English or incoming Farsi), break down the grammar, identify any words or affixes the user does not yet know, and ensure all unknown base words, missing subwords, and active compound verbs are moved or added to their Anki deck via `farsi_import.txt`.

## Workflow Overview

1. **Translate the sentence:** Translate into natural spoken Tehrani Farsi (or English if given Farsi).
2. **Break down the components:** Deconstruct each word, particle, and affix.
3. **Check knowledge against Anki:** Check `learned_vocab.txt`, `practice_grammar.txt`, and `deck_index.txt`.
4. **Add or move unknown words:** Follow the exact note design and import procedures from `farsi-anki-notes`.
5. **Lint and verify:** Run `lint_notes.py` on `farsi_import.txt`.
6. **Report:** Output the translation, linguistic breakdown, note actions, and next steps.

---

## 1. Translation Standards

* **English to Farsi:** Translate into everyday, colloquial Tehrani Persian unless the user explicitly requests formal/written style.
* **Farsi to English:** Translate incoming Persian script or latin transliteration into natural, fluent English, explaining any colloquial idioms, contractions, or tone nuances.
* Use colloquial sound shifts and words: `un` (for `aan`), `ro` (for `raa`), `alaan` / `haalaa`, `khuneh`, `mishe`, `digeh`, `ageh`.
* Use colloquial verb contractions and spoken endings: `-e` for 3rd person singular present/copula, `-in` for 2nd person plural, `-an` for 3rd person plural, spoken stems (`beram`, `begam`, `bedam`, `mikhuaam`).
* Script must use normal Persian spelling (no short vowel diacritics, Persian `ی` and `ک`, ZWNJ with `می‌` and compound affixes).
* Transliteration must strictly follow the deck's single-sound key:
  * `aa` for long a, `a` for short a
  * `u` for long oo, `o` for short o
  * `i` for long ee, `e` for short e
  * `v` for consonantal و, `y` for consonantal ی
  * All lowercase except the first letter of the sentence.
  * No `oo`, `ee`, `â`, `ā`, `ī`, `ū`, or apostrophes. `ع` and `ء` get no letter (write the adjacent vowel).

---

## 2. Checking Unknown Words & Deck Status

Inspect the local index and practice dumps directly on disk (do not query AnkiConnect over the network):
* `learned_vocab.txt`: Words the user has already learned or matured in Anki.
* `practice_grammar.txt`: Grammar affixes and particles the user has studied.
* `deck_index.txt`: All notes across `Farsi` and `Farsi::Queue`.

Always inspect these local text files directly so checks run automatically without requiring confirmation prompts.

For every content word in the translation:
1. **Already Learned (`learned` / `mature` in `learned_vocab.txt`):** The user knows it.
2. **In `Farsi::Queue` (in `deck_index.txt`):** Move it to `Farsi` by writing/updating the note in `farsi_import.txt` with deck set to `Farsi`.
3. **Not in `deck_index.txt`:** Create a new note in `farsi_import.txt` following `farsi-anki-notes` specifications.

---

## 3. Note Design Rules (Matching `farsi-anki-notes`)

Follow the rules in `farsi-anki-notes` (`SKILL.md` and `reference.md`):

### Target the base word
* **Base focus:** Target the freestanding root word (noun or adjective) rather than inflected forms.
* **Strip affixes:** Strip possessive suffixes (`-am`, `-et`, `-esh`, `-emun`, `-etun`, `-eshun`), verb endings, prefixes (`mi-`, `be-`, `na-`), and ezafe (`-e`). These are grammar affixes, not separate headwords.
* **Transparent `-i`:** When a derived word ends in transparent `-i` and shares the same core idea as its base noun/adjective (`zakhmi` → `zakhm`, `deltangi` → `deltang`), enter the base without `-i`. Keep both only if `-i` creates a completely distinct meaning (`ghahveh` / `ghahvei`).
* **Compound verbs in verb slots:** Light-verb compounds (`ghadam zadan`, `sohbat kardan`, `ehtemaal daashtan`) belong in the verb slot of the base noun or adjective (`ghadam`, `sohbat`, `ehtemaal`).
  * If the base is freestanding, the base is the main field and the verb goes in Verb 1 / Verb 2.
  * If the verb has no freestanding base (`raftan`), the main fields stay empty and the verb fills the verb slot.
* **Add subwords / pieces:** When adding a new compound or word, also add any colloquially used subwords or components that are not yet in the deck.

### Note format in `farsi_import.txt`
* Always match the file header (typically 16 columns):
  ```text
  #separator:tab
  #html:true
  #guid column:1
  #notetype column:2
  #deck column:3
  #tags column:16
  ```
* Columns:
  1. `guid`: New unique 10-character Anki guid (using digits, letters, and Anki punctuation: `!#$%&*+-.:;=?@[]^_`{|}~`).
  2. `notetype`: `Farsi`
  3. `deck`: `Farsi`
  4. `Farsi Transliteration`: Lowercase, standardized key (`u`, `i`, `aa`, `a`, `o`, `e`, `~` for formal ~ spoken).
  5. `English`: Short gloss, capitalized first letter (`To ` for verbs).
  6. `Farsi Script`: Everyday Persian spelling (no vowel marks, Persian `ی` and `ک`).
  7. `ScriptUnlocked`: Empty string `""`.
  8. `Verb Transliteration`: Verb infinitive &gt; stem (`kardan &gt; kon`), or empty.
  9. `Verb English`: Short gloss starting with `To `, or empty.
  10. `Verb Script`: Persian script for the verb (`کردن > کن`), or empty.
  11. `VerbScriptUnlocked`: Empty string `""`.
  12. `Verb2 Transliteration`: Second verb, or empty.
  13. `Verb2 English`: Second verb English, or empty.
  14. `Verb2 Script`: Second verb script, or empty.
  15. `Verb2ScriptUnlocked`: Empty string `""`.
  16. `tags`: Valid tags from `reference.md` (`Noun`, `Verb`, `adjective`, `adverb`, `preposition`, `pronoun`, `phrase`, etc.).

* Verb Rules & Method 2 for Standalone Verbs:
  - If a base noun/adjective exists in the deck (e.g. `ghabul` exists and adding `ghabul daashtan`), update the existing base note row in `farsi_import.txt` by populating its `Verb Transliteration` / `Verb English` / `Verb Script` fields (or Verb 2).
  - If the verb is a standalone verb with NO base noun (e.g. `maandan ~ mundan > maan ~ mun`, `raftan > rav ~ ro`): write it into the main fields (`Farsi Transliteration`, `English`, `Farsi Script`), leave verb columns empty, and tag `Verb`. Anki GUI import strictly requires that the first mapped field (`Farsi Transliteration`) cannot be blank.
  - **MANDATORY USER REMINDER:** Whenever a standalone verb is emitted into `farsi_import.txt`, you MUST explicitly remind the user to run `python anki_unlock.py --verb-slots --apply` after importing into Anki, which moves the verb into its proper verb slot and clears the main fields.

---

## 4. Linting and Validation

After writing to `farsi_import.txt`:
```powershell
python .agents/skills/farsi-anki-notes/scripts/lint_notes.py farsi_import.txt
```
Fix any formatting, width, tag, or transliteration errors until the linter prints `OK`.

---

## 5. Output Format

Present the response clearly with the following sections:

1. **Translation:**
   * **Persian Script:** Spoken sentence with correct spacing and ZWNJ.
   * **Transliteration:** Deck phonetic spelling.
   * **English:** The translated meaning.
2. **Sentence Breakdown:**
   * Table or bullet list mapping each token to its meaning, grammatical role (stem, affix, particle), and knowledge status (*Known / In Queue / New*).
3. **Deck Updates (`farsi_import.txt`):**
   * List any notes added or moved from `Farsi::Queue` to `Farsi`, showing transliteration, English gloss, Persian script, verb slots, and tags.
4. **Next Steps:**
   * Reminder to import `farsi_import.txt` into Anki.
   * If any standalone verbs were added (verbs with no base noun), explicitly include the command:
     ```powershell
     python anki_unlock.py --verb-slots --apply
     ```
   * Command to suspend locked cards:
     ```powershell
     python anki_unlock.py --suspend-locked
     ```

