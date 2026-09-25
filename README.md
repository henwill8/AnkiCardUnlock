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

Same maturity bar for vocab script and sentence script. Unlock fields sync; run on desktop, then sync.

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
