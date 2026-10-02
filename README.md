# Farsi sentence deck + unlock script

Colloquial / conversational sentences for talking and texting, gated on your `Farsi` vocab deck via AnkiConnect.

## Daily / after study

```text
python anki_unlock.py
```

What it does:

| Target | Rule | Effect |
|--------|------|--------|
| Vocab script cards | Both FA↔EN cards **mature** (interval ≥ 21 days) | `ScriptUnlocked=1` |
| Sentence Read / Say / Fill | Every `req::…` vocab note has **no New cards** | `SentenceUnlocked=1` |
| Sentence Script Read / Write | Every `req::…` vocab note is **mature** (≥ 21 days) | `SentenceScriptUnlocked=1` |
| Conversation word list | Both FA↔EN cards are **not New** | `learned_vocab.txt` (`mature` when interval ≥ 21) |
| Blank front | No template would show text, or this card's front would not | Suspend that card. A fully locked note's only card is suspended too |

Same maturity bar for vocab script and sentence script. Unlock fields sync; run on desktop, then sync.

`learned_vocab.txt` is written next to `anki_unlock.py` on every run (`--vocab-out` changes the path). `learned` rows are words you have studied. `mature` rows are the ones whose script cards are unlocked. The `farsi-conversation` skill reads that file and uses only those words, in transliteration or Persian script.

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
