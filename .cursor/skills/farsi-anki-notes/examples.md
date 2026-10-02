# Examples

Incomplete rows from the export, in the shape to write back. `ScriptUnlocked` stays empty. Guids stay. `&gt;` is the stem separator in the file.

## Case and tags only

```text
Bar / Up, on, or upon / بر
→ bar / Up, on, or upon / بر / preposition

Jadid ~ Taazeh / New / جدید ~ تازه
→ jadid ~ taazeh / New / جدید ~ تازه / adjective

Yaa / Or / یا
→ yaa / Or / یا / particle particle::connector

Hameh / All or everyone / همه
→ hameh / All or everyone / همه / pronoun

Khod / Self / خود
→ khod / Self / خود / pronoun

Fekr / Thought or idea / فکر
→ fekr / Thought or idea / فکر / Noun
```

`hich` was missing a field break and had a trailing space: `Hich` / `None or nothing` / `هیچ` → `hich` / `None or nothing` / `هیچ` / `pronoun`.

## Vowel is the spelling

`Vaali` used `aa` for ی. ی is `i`.

```text
Amaa / Vaali / But / اما / ولی
→ amaa ~ vali / But / اما ~ ولی / particle particle::connector
```

`Ruye` added an e the spelling does not have. روی is `ruy`; spoken رو is `ru`.

```text
Ruye ~ ru / On or on top of /  روی ~ رو
→ ruy ~ ru / On or on top of / روی ~ رو / preposition
```

## Verb compound

```text
Fekr Kardan > Kon / To think / فکر کردن > کن
→ fekr kardan &gt; kon / To think / فکر کردن &gt; کن / Verb
```

## Spoken form was missing

مخ is the spoken spelling of مغز.

```text
Mokh / Mind / مخ
→ maghz ~ mokh / Brain or mind / مغز ~ مخ / Noun
```

## Long oo is u

Do this anywhere in the file, not only on new rows.

```text
khaaneh ~ khooneh / خانه ~ خونه → khaaneh ~ khuneh / خانه ~ خونه
aamadan ~ oomadan &gt; aa ~ oo → aamadan ~ umadan &gt; aa ~ u
aan ~ oon → aan ~ un
daanestan ~ doonestan &gt; daan ~ doon → daanestan ~ dunestan &gt; daan ~ dun
```

Script stays `خونه`, `اومدن`, `او`, `اون`, `دونستن` — only the transliteration letter changes. `anha` for آنها becomes `anhaa` because the final ا is long a.

## Same spelling, two sounds

```text
raftan &gt; rav ~ ro / رفتن &gt; رو
shodan &gt; shav ~ sho / شدن &gt; شو
```

Do not write `رو ~ رو`.

## Sentence for a new word

`otaagh` is not something you say alone. Put it in a line you would actually text, using other deck words. Spoken `ro`, `un`, `mishe`. First letter capitalized. Unlock fields empty.

```text
Mishe fardaa berim un otaagh?
Can we go to that room tomorrow?
میشه فردا بریم اون اتاق؟
ClozePrompt: Mishe fardaa berim un ____?
tags: diff::3 req::fardaa req::mishe req::otaagh req::raftan req::un theme::plans
```

`Salaam, chetori?` is short and people say it constantly, so it is allowed (`diff::1`). A longer line people say all the time is also allowed; tag it `diff::2` or `diff::3` for its length. `Otaagh bozorge.` is short and not something people say, so it is not allowed.

## Already done — leave the pattern

```text
pedar ~ baabaa / پدر ~ بابا / Noun
mamnun ~ mersi / ممنون ~ مرسی / interjection
ye(k) / یک / یه / Number
budan &gt; hast/bash / بودن &gt; هست/باش / Verb
```
