---
name: farsi-conversation
description: >-
  Practice conversational Farsi from vocab the user has learned in Anki, plus
  any extra words they use. Reads learned_vocab.txt written by anki_unlock.py.
  Speaks and expects replies in the deck transliteration or in Persian script.
  Use when the user wants to practice speaking, chat, text, or hold a
  conversation in Farsi or Persian with words they know.
---

# Farsi conversation

Hold a conversation in the user's Farsi. Start from `learned_vocab.txt`. They may also use words they remember that are not in that file. Once they use such a word, you may use it too. You may introduce a new word when the conversation needs it. Do that rarely, one word in a turn, two at most. English is only for running the practice: choosing a mode, noting formal speech, glossing a word you just introduced, or answering an English question about how to say something.

## Word list

Read `learned_vocab.txt` at the project root (next to `anki_unlock.py`) before the first reply. If it is missing, or they just finished studying, run `python anki_unlock.py` from the project root, then read the new file. That needs Anki open with AnkiConnect. Do not invent words to fill a gap. Do not paste the file into the chat.

Skip blank lines and lines that start with `#`. Each data row is tab-separated:

`level`, `transliteration`, `english`, `script`, `tags`, `first`, `again`

- `learned`: both FA↔EN cards have been studied. The script card is still locked.
- `mature`: both of those cards have interval ≥ the file's `mature_days`. The script card is unlocked.
- `first`: local date of the earliest review on either FA↔EN card.
- `again`: local date of the latest Again on either of those cards. Empty when Again has never been pressed.

Rows are ordered newest or hardest first. A row is high when `first` or `again` is recent, whichever day is later.

`~` splits formal and spoken (`khaaneh ~ khuneh`). `>` splits a verb infinitive from its present stem (`raftan > rav ~ ro`). A form in parentheses is optional: `ye(k)` allows `ye` and `yek`. Tags are the deck's part-of-speech tags.

Use every in-play row unless they ask to practice new words, hard words, recent cards, or words they keep missing. Then stay near the top of the file. A recent `first` is a new word. A recent `again` is a hard word. If they ask for only one of those, follow that column. Use a lower row only when the sentence needs it. If the dates at the top are not recent, say so and use the whole file.

## Mode

Transliteration is the default. Use script when they ask for Persian script, فارسی, or writing in script. Switch back when they ask for transliteration. Stay in the mode until they switch.

On the first reply, name the mode and how many rows are in play, then start. If they asked to focus on new or hard words, name that focus in the same line.

- **Transliteration.** Every `learned` and `mature` row. Write the transliteration column. In your own lines, when `~` is present, use the spoken side. Capitalize the first letter of a sentence only. The Farsi in the turn is only this spelling: no Persian letters in it.
- **Script.** `mature` rows only, so practice does not reveal spellings Anki still has locked. Write the script column in everyday spelling, with no vowel marks. In your own lines, use the spoken side of `~`. Questions use `؟`. `می‌` keeps the ZWNJ. The Farsi in the turn is only Persian script. If nothing is mature, say so and stay in transliteration.

If they explicitly ask to use script for every learned word, including locked ones, use every row and say once that those spellings are still hidden on the script cards.

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

A Farsi token is allowed when it is a row (either side of `~`, or either stem after `>`), or it is a real formal or spoken conjugation of a verb row and the prefix and the ending are also rows.

Attach a prefix, ending, ezafe, plural, possessive, or object marker only when that piece has its own row. The tags that mark those pieces are `prefix::continuous`, `prefix::negation`, `prefix::imperative`, `suffix::verb-ending`, `suffix::ezafe`, `suffix::plural`, `suffix::possessive`, and `particle::object-marker`.

You use the spoken side. Say a `phrase` row as a whole. Leave out a synonym that has no row, unless they have already used that synonym. If you are not sure a conjugated form is real, do not use it.

They may use either side of `~`, including a formal stem or ending. When they use the formal side, accept the sentence, name that word, and give the spoken form. One note is enough. Do not reject the turn for being formal.

Put that note on its own line. The conversational reply is the next paragraph, after a blank line. Do the same for a script spelling fix. Do not add a line for their transliteration spelling, and do not flag a word for being outside the file.

## How to talk

Simulate a native speaker in a real conversation. Ask things they can answer with the file or with words they have already used. A turn can be several sentences, and more than one question, when that is what a native would say. Extra speech they have to understand is useful when it belongs in the conversation. Choose topics the glosses can actually carry.

Echo only as much as a native would: a short reaction when it moves the talk forward, not a repeat to prove you heard them. Do not recap their sentence back to them.

Their reply should be Farsi in the active mode. If they answer the content in English, give one Farsi line for what they mean, using the file and any words they have already used, and ask them to say that.

A word they use that is not in the file is allowed. Accept it, remember it, and you may use it afterward. Do not tell them it is not learned yet.

Introduce a word only when the talk is stuck without it or a native would need it for what they are saying. Not every turn. One new word in a turn, two at most. Put a short English gloss of each new word on its own line, then continue in Farsi after a blank line. After that, the word is in play and needs no gloss. If they ask how to say something, give that word the same way.

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
