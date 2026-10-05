#!/usr/bin/env python3
"""Find Tatoeba Persian sentences covered by the deck index.

Downloads Tatoeba dumps into .cache/tatoeba/ on first run. Writes
sentence_candidates.txt for review. Does not invent colloquial lines; many
hits are formal and need a spoken rewrite before import.
"""

from __future__ import annotations

import argparse
import bz2
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "anki_unlock.py").is_file():
            return parent
    raise SystemExit("Could not find repo root (anki_unlock.py)")


ROOT = repo_root()
DECK_INDEX = ROOT / "deck_index.txt"
SENTENCES_INDEX = ROOT / "sentences_index.txt"
CACHE = ROOT / ".cache" / "tatoeba"
OUT_DEFAULT = ROOT / "sentence_candidates.txt"
TATOEBA_PES = "https://downloads.tatoeba.org/exports/per_language/pes/"
TATOEBA_ENG = "https://downloads.tatoeba.org/exports/per_language/eng/"
UA = "AnkiCardUnlock/1.0 (local sentence candidate finder)"

ARABIC_YE = "ي"
PERS_YE = "ی"
ARABIC_KE = "ك"
PERS_KE = "ک"
DIAC = re.compile(r"[\u064b-\u065f\u0670\u0640]")
ZWNJ = "\u200c"
PUNCT = str.maketrans({c: " " for c in "؟?!.،,؛;:«»\"'()[]{}…-"})
SPOKEN_MARKERS = ("رو ", "اون ", "دیگه", "میشه", "خونه", "آره", "اره", "الان", "اگه")
SKIP_TOKENS = {"تام", "مری", "جان", "براد"}  # Tatoeba cast names / noise


def norm_fa(text: str) -> str:
    text = text.replace(ARABIC_YE, PERS_YE).replace(ARABIC_KE, PERS_KE)
    text = DIAC.sub("", text)
    return text.strip()


def tokens(text: str) -> list[str]:
    text = norm_fa(text).replace(ZWNJ, "").translate(PUNCT)
    return [w for w in text.split() if w]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp:
        dest.write_bytes(resp.read())


def ensure_tatoeba() -> tuple[Path, Path, Path]:
    pes = CACHE / "pes_sentences.tsv.bz2"
    eng = CACHE / "eng_sentences.tsv.bz2"
    links = CACHE / "pes-eng_links.tsv.bz2"
    download(TATOEBA_PES + "pes_sentences.tsv.bz2", pes)
    download(TATOEBA_PES + "pes-eng_links.tsv.bz2", links)
    download(TATOEBA_ENG + "eng_sentences.tsv.bz2", eng)
    return pes, eng, links


def load_tsv_sentences(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with bz2.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            out[parts[0]] = parts[2]
    return out


def load_links(path: Path) -> dict[str, list[str]]:
    links: dict[str, list[str]] = defaultdict(list)
    with bz2.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            links[parts[0]].append(parts[1])
    return links


def parse_index(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        sys.exit(f"Missing {path}. Run: python anki_unlock.py --export-indexes")
    rows: list[dict[str, str]] = []
    columns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# columns:"):
            columns = [c.strip() for c in line.split(":", 1)[1].split(",")]
            continue
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not columns or len(parts) < len(columns):
            continue
        rows.append(dict(zip(columns, parts)))
    return rows


def expand_lexicon(deck_rows: list[dict[str, str]]) -> dict[str, set[str]]:
    """Map normalized Persian surface -> set of vocab transliterations.

    Lemma surfaces are registered first. Conjugations may not claim a surface
    that already belongs to another note's lemma (خواندن must not own خونه).
    """
    forms: dict[str, set[str]] = defaultdict(set)
    lemma_owner: dict[str, str] = {}
    pers_end = ["م", "ی", "ه", "یم", "ید", "ن", "ین"]
    form_end = ["م", "ی", "د", "یم", "ید", "ند"]
    past_end = ["م", "ی", "", "یم", "ید", "ند"]

    def add_lemma(surface: str, key: str) -> None:
        surface = norm_fa(surface).replace(ZWNJ, "")
        if not surface:
            return
        forms[surface].add(key)
        lemma_owner.setdefault(surface, key)

    def add_conj(surface: str, key: str) -> None:
        surface = norm_fa(surface).replace(ZWNJ, "")
        if len(surface) < 2:
            return
        owner = lemma_owner.get(surface)
        if owner is not None and owner != key:
            return
        forms[surface].add(key)

    for row in deck_rows:
        tr = row.get("transliteration", "")
        sc = row.get("script", "")
        for piece in re.split(r"[~/>]", sc.replace("&gt;", ">")):
            add_lemma(piece.strip().lstrip("-"), tr)

    for row in deck_rows:
        tr = row.get("transliteration", "")
        sc = row.get("script", "")
        tags = row.get("tags", "")
        sc2 = sc.replace("&gt;", ">")
        is_verb = "Verb" in tags.split() or ">" in tr or ">" in sc2
        if not is_verb or ">" not in sc2:
            continue
        inf_part, stem_part = sc2.split(">", 1)
        stems = [s.strip() for s in stem_part.split("~") if s.strip()]
        infs = [s.strip() for s in inf_part.split("~") if s.strip()]
        for stem in stems:
            stem0 = stem.replace(ZWNJ, "").lstrip("-")
            if not stem0:
                continue
            for pref in ("می", "نمی", "ب"):
                for end in pers_end + form_end:
                    add_conj(pref + stem0 + end, tr)
            # Light verbs and داشتن-style presents often omit می-
            for end in pers_end + form_end:
                add_conj(stem0 + end, tr)
        for inf in infs:
            past = inf[:-1] if inf.endswith("ن") else inf
            past0 = past.replace(ZWNJ, "")
            if len(past0) < 2:
                continue
            for end in past_end:
                add_conj(past0 + end, tr)
                add_conj("ن" + past0 + end, tr)

    for surface, key in (("می", "mi-"), ("نمی", "n*-")):
        forms.setdefault(surface, set()).add(key)
    for base, key in (("هست", "budan"), ("نیست", "budan")):
        for end in ("", "م", "ی", "یم", "ید", "ند", "ن"):
            add_conj(base + end, key)
    return forms


def best_vocab_keys(tok: str, forms: dict[str, set[str]]) -> list[str]:
    keys = forms.get(tok, set())
    if not keys:
        return []
    content = [
        k
        for k in keys
        if not k.startswith("-")
        and k not in ("mi-", "n*-", "b*-")
        and "Ending" not in k
        and "(" not in k
    ]
    pool = content or list(keys)
    # One best key: shortest headword wins (بودن over موافق بودن for هست)
    best = min(pool, key=lambda k: (len(k), k))
    return [best]


def existing_scripts(sentences_rows: list[dict[str, str]]) -> set[str]:
    return {norm_fa(r.get("script", "")).replace(ZWNJ, "") for r in sentences_rows}


def target_rows(deck_rows: list[dict[str, str]], words: list[str]) -> list[dict[str, str]]:
    wanted = {norm_fa(w).replace(ZWNJ, "") for w in words}
    out = []
    for row in deck_rows:
        scripts = [
            norm_fa(p).replace(ZWNJ, "")
            for p in re.split(r"[~/>]", row["script"].replace("&gt;", ">"))
            if p.strip()
        ]
        translits = [
            p.strip().lower()
            for p in re.split(r"[~/>]", row["transliteration"].replace("&gt;", ">"))
            if p.strip()
        ]
        if wanted & set(scripts) or wanted & set(translits):
            out.append(row)
    return out


def score_candidate(text: str, toks: list[str], has_eng: bool) -> tuple[int, str]:
    if any(t in SKIP_TOKENS for t in toks):
        return (-100, "reject_name")
    if len(toks) < 2:
        return (-50, "too_short")
    spoken = any(m in text for m in SPOKEN_MARKERS)
    status = "spokenish" if spoken else "needs_spoken_rewrite"
    score = 0
    score += 5 if spoken else 0
    score += 3 if has_eng else 0
    score += 2 if text.rstrip().endswith(("؟", "?")) else 0
    n = len(toks)
    if 2 <= n <= 8:
        score += 4
    elif n <= 14:
        score += 2
    else:
        score -= 2
    return score, status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--words",
        nargs="+",
        required=True,
        help="Target Persian spellings or transliterations",
    )
    parser.add_argument("--limit", type=int, default=5, help="Candidates per word")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()

    deck_rows = parse_index(DECK_INDEX)
    sent_rows = parse_index(SENTENCES_INDEX) if SENTENCES_INDEX.is_file() else []
    targets = target_rows(deck_rows, args.words)
    if not targets:
        print("No target words matched deck_index.txt.")
        return 1

    forms = expand_lexicon(deck_rows)
    have = existing_scripts(sent_rows)
    pes_path, eng_path, links_path = ensure_tatoeba()
    print("Loading Tatoeba…")
    pes = load_tsv_sentences(pes_path)
    eng = load_tsv_sentences(eng_path)
    links = load_links(links_path)

    # Pre-tokenize Persian sentences once
    indexed: list[tuple[str, str, list[str]]] = []
    for sid, text in pes.items():
        toks = tokens(text)
        if len(toks) < 2:
            continue
        indexed.append((sid, text, toks))

    lines: list[str] = [
        "# sentence_candidates",
        "# source: Tatoeba (pes) filtered to deck_index surfaces",
        "# status spokenish: may be usable after light edit",
        "# status needs_spoken_rewrite: formal; rewrite in Tehrani before import",
        "# status reject_*: skip",
        "# Every content token matched an expanded deck form (conjugations included).",
        "",
    ]

    covered = 0
    uncovered = 0
    for row in targets:
        tr = row["transliteration"]
        sc = row["script"]
        surfaces = [
            norm_fa(p).replace(ZWNJ, "")
            for p in re.split(r"[~/>]", sc.replace("&gt;", ">"))
            if p.strip()
        ]
        if not surfaces:
            continue
        hits: list[tuple[int, str, str, str, str]] = []
        for sid, text, toks in indexed:
            if not any(s in toks for s in surfaces):
                continue
            unknown = [w for w in toks if w not in forms]
            if unknown:
                continue
            norm_text = norm_fa(text).replace(ZWNJ, "")
            if norm_text in have:
                continue
            eng_ids = links.get(sid, [])
            english = next((eng[i] for i in eng_ids if i in eng), "")
            score, status = score_candidate(text, toks, bool(english))
            if score < 0:
                continue
            reqs: set[str] = set()
            for tok in toks:
                for key in best_vocab_keys(tok, forms):
                    head = key.split(">")[0].split("~")[0].strip()
                    if head and head not in ("mi-", "n*-", "b*-"):
                        reqs.add(head)
            hits.append((score, status, text, english, " ".join(sorted(reqs))))
        hits.sort(key=lambda h: (-h[0], len(h[2])))
        lines.append(f"## {tr} / {sc}")
        if not hits:
            uncovered += 1
            lines.append("NO_COVERED_CANDIDATE")
            lines.append("")
            continue
        covered += 1
        for score, status, text, english, reqs in hits[: args.limit]:
            lines.append(f"- score={score} status={status}")
            lines.append(f"  fa: {text}")
            if english:
                lines.append(f"  en: {english}")
            lines.append(f"  approx_vocab: {reqs}")
        lines.append("")

    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(
        f"Targets with candidates: {covered}; without: {uncovered}; wrote {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
