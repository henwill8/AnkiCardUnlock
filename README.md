# Farsi sentence deck + unlock script

Colloquial / conversational sentences for talking and texting, gated on your `Farsi` vocab deck via AnkiConnect.

## Daily / after study

```text
python anki_unlock.py
```

What it does:

| Target | Rule | Effect |
|--------|------|--------|
| Vocab script cards | Both FA↔EN cards **mature** (interval ≥ 21 days) | `ScriptUnlocked=1`. Cleared when either card drops below 21, and that script card is suspended |
| Sentence Read / Say / Fill | Every `req::…` vocab note has **no New cards** | `SentenceUnlocked=1` |
| Sentence Script Read / Write | Every `req::…` vocab note is **mature** (≥ 21 days) | `SentenceScriptUnlocked=1`. Cleared when a required word drops below 21, and those script cards are suspended |
| Conversation word list | Both FA↔EN cards are **not New** | Compact practice dumps + full `learned_vocab.txt` |
| Blank front | No template would show text, or this card's front would not | Suspend that card. A fully locked note's only card is suspended too |

Same maturity bar for vocab script and sentence script. Unlock fields sync; run on desktop, then sync.

Every unlock run writes:

| File | Contents |
|------|----------|
| `practice_vocab.txt` | Content words only: level, translit, English, script |
| `practice_grammar.txt` | Affixes/particles with tags |
| `practice_focus.txt` | Top ~40 newest/hardest rows with `first` / `again` |
| `learned_vocab.txt` | Full dated archive (`--vocab-out` changes this path) |

`learned` = studied. `mature` = script unlocked (interval ≥ 21). The `farsi-conversation` skill reads the compact practice files by default, and `practice_focus.txt` when you ask for new/hard words.

### Compact indexes + sentence candidates

Vocab notes have no example-sentence fields. Sentence practice is only in the `Farsi Sentences` deck.

```text
python anki_unlock.py --export-indexes
python .cursor/skills/farsi-anki-notes/scripts/find_sentence_candidates.py --words خونه اتاق
```

`--export-indexes` writes `deck_index.txt` and `sentences_index.txt` (guid + compact fields). The candidate script searches Tatoeba Persian for lines whose tokens are all in your deck and writes `sentence_candidates.txt`. Many hits are formal and still need a spoken Tehrani rewrite; the script does not auto-import.

`req::` tags nest under one sidebar entry. Ignore them while studying.

## Sentence card types

Once translit-unlocked (`SentenceUnlocked`):

1. **Read** — Farsi Transliteration → English  
2. **Say** — English → Farsi Transliteration (speak/text it)  
3. **Cloze / Fill** — one-word blank, only if `ClozePrompt` is filled  

Once script-unlocked later (`SentenceScriptUnlocked`):

4. **Script read** — فارسی → English  
5. **Script write** — English → type فارسی  

Difficulties: `diff::1` short, `diff::2` medium, `diff::3` longer. Themes under `theme::`.

## Style notes

- Colloquial forms (`mishe`, `aare`, `diggeh`, `alaan`, `una`, `ro` for `raa`, etc.)
- Only words from your current vocab deck
- Transliteration matches your `Farsi.txt` rules
