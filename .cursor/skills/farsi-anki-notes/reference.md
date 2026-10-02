# Deck conventions

## Tags already in the deck

Use these strings. Do not invent a new hierarchy.

| Kind | Tags |
|------|------|
| Noun | `Noun` |
| Verb, including light-verb compounds | `Verb` |
| Adjective | `adjective` |
| Adverb | `adverb` |
| Pronoun | `pronoun` |
| Preposition | `preposition` |
| Number | `Number` |
| Set phrase | `phrase` |
| Greeting | `greeting` or `greeting phrase` |
| Interjection | `interjection` |
| Conjunction (و، اما، ولی، یا) | `particle particle::connector` |
| Object marker را | `grammar particle particle::object-marker` |
| Subordinator که | `grammar particle particle::connector` |
| Ezafe | `grammar suffix suffix::ezafe` |
| Plural | `grammar suffix suffix::plural` |
| Possessive ending | `grammar suffix suffix::possessive` |
| Person ending | `grammar suffix suffix::verb-ending Verb` |
| Negation نـ | `grammar prefix::negation Verb` |
| می‌ـ | `grammar prefix::continuous Verb` |
| Imperative / subjunctive بـ | `grammar prefix::imperative` |
| باـ / بی‌ـ | `grammar prefix::attributive` plus `preposition` when it is also a preposition |

A note can carry more than one tag, space-separated, the way `phrase Verb` and `greeting phrase` already do.

## Consonants

| Write | Letters |
|-------|---------|
| b p d r f k g l m n | ب پ د ر ف ک گ ل م ن |
| t | ت ط |
| s | س ص ث |
| z | ز ذ ض ظ |
| j | ج |
| ch | چ |
| h | ه ح |
| kh | خ |
| sh | ش |
| zh | ژ |
| gh | غ ق |
| v | consonantal و |
| y | consonantal ی |

Words already in the deck are the spelling authority when they conflict with a general rule. `mostaghim` stays `gh` for ق. `shodan &gt; shav` is the stored stem until that note is the one being filled out.

## Spoken shifts to apply

Use `~` only for these kinds of real differences.

| Formal | Spoken | Example |
|--------|--------|---------|
| aan, word-final or in آن | un | `aan ~ un`, `javaan ~ javun`, `aasaan ~ aasun`, `mehrabaan ~ mehrabun` |
| aandan infinitive | undan | `khaandan ~ khundan &gt; khaan ~ khun` |
| aamadan | umadan, stem aa ~ u | `aamadan ~ umadan &gt; aa ~ u` |
| khaaneh | khuneh | `khaaneh ~ khuneh` |
| daanestan | dunestan, stem daan ~ dun | `daanestan ~ dunestan &gt; daan ~ dun` |
| tavaanestan | tunestan | `tavaanestan ~ tunestan &gt; tavaan ~ tun` |
| raa | ro | object marker |
| ast / -ad | -e | copula and he/she present |
| -id | -in | you-plural present |
| -and | -an | they present |
| -ash | -esh | his/her |
| -etaan | -tun | your (plural) |
| -eshaan | -shun | their |
| yek | ye | `ye(k)` when it is one note for both |
| chahaar | chaar | h dropped in speech |
| digar | digeh | |
| agar | ageh | |
| goftan stem gu (گو) | g (گ) | `goftan &gt; gu ~ g` |
| khaastan stem khaah (خواه) | khaa (خوا) | `khaastan &gt; khaah ~ khaa` |
| daadan stem dah (ده) | d (د) | `daadan &gt; dah ~ d` |
| raftan stem rav | ro | same spelling رو |
| shodan stem shav | sho | same spelling شو |
| small set -ak | -ik | `kuchak ~ kuchik` |
| maghz | mokh | brain; only when the note is that word |

آنها is `anhaa ~ unaa` / `آنها ~ اونا`. The long a at the end is `aa`.

Leave one form when the spoken word uses the same spelling and the same sound. Do not pair a synonym just to fill the slot. جدید and تازه are two words, not a sound shift; keep both only because the note already lists both.

## Stems the deck already uses

Reuse these on compounds. Do not replace them with a dictionary stem.

| Infinitive | Stem on the note |
|------------|------------------|
| budan | hast/bash |
| raftan | rav ~ ro |
| didan | bin |
| kharidan | khar |
| khordan | khor |
| kardan | kon |
| neveshtan | nevis |
| daashtan | daar |
| busidan | bus |
| bastan | band |
| shostan | shu |
| forukhtan | forush |
| aamadan ~ umadan | aa ~ u |
| khaandan ~ khundan | khaan ~ khun |
| saakhtan | saaz |
| jostan | ju |
| gereftan | gir |
| daadan | dah |
| farmudan | farmaay |
| zadan | zan |
| shodan | shav |
| neshastan | neshin |
| khaastan | khaah |
| khaabidan | khaab |
| dozdidan | dozd |
| koshtan | kosh |
| tavaanestan ~ tunestan | tavaan ~ tun |
| goftan | gu |
| daanestan ~ dunestan | daan ~ dun |
| bakhshidan | bakhsh |

When a full fix updates `goftan`, `daadan`, `khaastan`, or `shodan` to include the spoken stem, use that updated stem on compounds of those verbs too.

## New guids

10 characters from the alphabet already used by guids in the file: digits, letters, and Anki punctuation. No space, quote, backslash, or tab. Must not repeat a guid already in the file.

## List sources

A frequency or textbook list is a set of words to add, not a transliteration to copy. Convert its romanization into this file's spelling. Skip words whose script or transliteration key is already a note.
