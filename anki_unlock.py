#!/usr/bin/env python3
"""Unlock Farsi script cards + sentence cards via AnkiConnect.

Also writes conversation dumps: learned_vocab.txt (full dated list),
practice_vocab.txt (compact content words), practice_grammar.txt (affixes),
and practice_focus.txt (top recent/hard rows).

Suspends a gated card unless its unlock field is exactly 1, and suspends any
blank front. When every template on a note is locked, Anki still keeps one
card with a blank front; that card is suspended too. Once a vocab script
card is unlocked it stays unlocked, even if that note later drops below the
mature interval. Sentence script unlock is cleared when a required word
drops below the mature interval, and those cards stay suspended until it is
mature again. New script cards are spaced evenly through the cards still in
the new queue, including buried siblings. Non-script siblings of a note stay
together at the earliest sibling's place, so a card shifted by a merge comes
back beside the one that stayed. A note that already has a learned card
moves to the front of that queue. Script cards are placed after that order
is set, in the gaps through the whole queue, not inside a sibling group.
Siblings that shared one new-card number get separate numbers, and the cards
inside each block are shuffled.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

ANKI_URL = "http://127.0.0.1:8765"
VOCAB_MODEL = "Farsi"
SENTENCE_MODEL = "Farsi Sentence"
VOCAB_DECK = "Farsi"
SENTENCE_DECK = "Farsi Sentences"
SCRIPT_FIELD = "ScriptUnlocked"
SENTENCE_FIELD = "SentenceUnlocked"
SENTENCE_SCRIPT_FIELD = "SentenceScriptUnlocked"
VERB_SCRIPT_FIELD = "VerbScriptUnlocked"
VERB2_SCRIPT_FIELD = "Verb2ScriptUnlocked"
SCRIPT_CARD_FIELDS = {
    SCRIPT_FIELD,
    VERB_SCRIPT_FIELD,
    VERB2_SCRIPT_FIELD,
    SENTENCE_SCRIPT_FIELD,
}
LIGHT_VERBS = {
    "kardan",
    "shodan",
    "zadan",
    "daadan",
    "daashtan",
    "gereftan",
    "khordan",
    "keshidan",
    "goftan",
}
# Same root, different idea. The verb stays its own note.
PLAIN_VERB_DENY = {
    ("charkh", "charkhidan"),
    ("baar", "baaridan"),
}
VERB_SLOTS = (
    (
        "Verb Transliteration",
        "Verb English",
        "Verb Script",
        VERB_SCRIPT_FIELD,
        {0: 3, 1: 4, 2: 5},
    ),
    (
        "Verb2 Transliteration",
        "Verb2 English",
        "Verb2 Script",
        VERB2_SCRIPT_FIELD,
        {0: 6, 1: 7, 2: 8},
    ),
)
MATURE_INTERVAL_DEFAULT = 21
MISSING_REPORT_LIMIT = 8
AGAIN_EASE = 1
REVIEW_BATCH = 200
SLUG_RE = re.compile(r"[^a-z0-9*\-]+")
ROOT = Path(__file__).resolve().parent
VOCAB_OUT = ROOT / "learned_vocab.txt"
PRACTICE_VOCAB_OUT = ROOT / "practice_vocab.txt"
PRACTICE_GRAMMAR_OUT = ROOT / "practice_grammar.txt"
PRACTICE_FOCUS_OUT = ROOT / "practice_focus.txt"
DECK_INDEX_OUT = ROOT / "deck_index.txt"
SENTENCES_INDEX_OUT = ROOT / "sentences_index.txt"
CACHE_DIR = ROOT / ".cache"
REPOSITION_ADDON = "anki_unlock_reposition"
FOCUS_LIMIT = 40
GRAMMAR_TAG_MARKERS = (
    "grammar",
    "prefix::",
    "suffix::",
    "particle::",
)


def invoke(action: str, timeout: int = 30, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(
        ANKI_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        sys.exit(
            f"Cannot reach AnkiConnect at {ANKI_URL}.\n"
            f"Open Anki desktop with AnkiConnect installed.\n{exc}"
        )
    if result.get("error"):
        raise RuntimeError(f"{action}: {result['error']}")
    return result.get("result")


def invoke_multi(actions: list[dict]) -> list:
    """Run many AnkiConnect actions in one HTTP round-trip."""
    if not actions:
        return []
    return invoke("multi", actions=actions) or []


def slug(s: str) -> str:
    return SLUG_RE.sub("", s.replace(" ", "").strip().lower())


def normalize_key(field1: str) -> list[str]:
    """Keys a vocab transliteration field can be referenced by in req:: tags."""
    # AnkiConnect may return HTML entities (&gt; for > in "goftan > gu(y)")
    raw = html.unescape(field1).strip().lower()
    raw = re.sub(r"<[^>]+>", "", raw)
    # Expand optional letters: sob(h) → sob / sobh, ye(k) → ye / yek, aa(y) → aa / aay
    variants = {raw}
    for match in re.finditer(r"\(([^)]+)\)", raw):
        inner = match.group(1)
        with_opt = raw[: match.start()] + inner + raw[match.end() :]
        without_opt = raw[: match.start()] + raw[match.end() :]
        variants.add(with_opt)
        variants.add(without_opt)

    keys: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        base = variant.split("(")[0]
        for part in re.split(r"[/>~]", base):
            key = slug(part)
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def parse_req_tags(tags: list[str]) -> list[str]:
    return [
        slug(t.split("::", 1)[1])
        for t in tags
        if t.lower().startswith("req::") and "::" in t
    ]


def field_map(note: dict) -> dict[str, str]:
    return {
        k: html.unescape(v.get("value", "") or "")
        for k, v in note["fields"].items()
    }


def fetch_notes(query: str) -> list[dict]:
    ids = invoke("findNotes", query=query)
    return invoke("notesInfo", notes=ids) if ids else []


def fetch_cards_by_id(card_ids: list[int]) -> dict[int, dict]:
    cards_by_id: dict[int, dict] = {}
    for i in range(0, len(card_ids), 1000):
        for card in invoke("cardsInfo", cards=card_ids[i : i + 1000]) or []:
            cards_by_id[card["cardId"]] = card
    return cards_by_id


def study_marks(reviews_by_card: dict) -> dict[int, tuple[int, int]]:
    """card id -> (earliest review ms, latest Again ms)."""
    marks: dict[int, tuple[int, int]] = {}
    for key, entries in reviews_by_card.items():
        first = 0
        again = 0
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            reviewed = int(entry.get("id") or 0)
            if reviewed <= 0:
                continue
            if first == 0 or reviewed < first:
                first = reviewed
            if int(entry.get("ease") or 0) == AGAIN_EASE and reviewed > again:
                again = reviewed
        marks[int(key)] = (first, again)
    return marks


def fetch_review_marks(card_ids: list[int]) -> dict[int, tuple[int, int]]:
    if not card_ids:
        return {}
    reviews: dict = {}
    for i in range(0, len(card_ids), REVIEW_BATCH):
        chunk = card_ids[i : i + REVIEW_BATCH]
        reviews.update(invoke("getReviewsOfCards", cards=chunk) or {})
    return study_marks(reviews)


def note_study_ms(card_ids: list[int], marks: dict[int, tuple[int, int]]) -> tuple[int, int]:
    """Earliest review and latest Again across a note's FA↔EN cards."""
    first_ms = 0
    again_ms = 0
    for cid in card_ids:
        first, again = marks.get(int(cid), (0, 0))
        if first and (first_ms == 0 or first < first_ms):
            first_ms = first
        if again > again_ms:
            again_ms = again
    return first_ms, again_ms


def review_day(ms: int) -> str:
    if ms <= 0:
        return ""
    return datetime.fromtimestamp(ms / 1000).date().isoformat()


_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _field_nonempty(fields: dict[str, str], name: str) -> bool:
    value = re.sub(r"<[^>]+>", "", fields.get(name, "") or "")
    return bool(value.replace("\xa0", " ").strip())


def _take_conditional(text: str, i: int, name: str) -> tuple[str, int]:
    depth = 1
    start = i
    while i < len(text):
        open_br = text.find("{{", i)
        if open_br < 0:
            return text[start:], len(text)
        end_br = text.find("}}", open_br)
        if end_br < 0:
            return text[start:], len(text)
        token = text[open_br + 2 : end_br].strip()
        token_name = token[1:].strip() if token[:1] in "#^/" else ""
        if (token.startswith("#") or token.startswith("^")) and token_name == name:
            depth += 1
        elif token.startswith("/") and token_name == name:
            depth -= 1
            if depth == 0:
                return text[start:open_br], end_br + 2
        i = end_br + 2
    return text[start:], len(text)


def _expand(text: str, fields: dict[str, str]) -> str:
    text = _COMMENT_RE.sub("", text)
    parts: list[str] = []
    i = 0
    while i < len(text):
        start = text.find("{{", i)
        if start < 0:
            parts.append(text[i:])
            break
        parts.append(text[i:start])
        end = text.find("}}", start)
        if end < 0:
            parts.append(text[start:])
            break
        token = text[start + 2 : end].strip()
        i = end + 2
        if token.startswith("#") or token.startswith("^"):
            name = token[1:].strip()
            inner, i = _take_conditional(text, i, name)
            show = _field_nonempty(fields, name)
            if token.startswith("^"):
                show = not show
            if show:
                parts.append(_expand(inner, fields))
        elif token.startswith("/") or token.startswith("!"):
            continue
        else:
            name = token.split(":", 1)[-1].strip() if ":" in token else token
            parts.append(fields.get(name, "") or "")
    return "".join(parts)


def front_text(front: str, fields: dict[str, str]) -> str:
    """Visible text a template front would show for these field values."""
    text = _expand(front, fields)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_FRONT_RE = re.compile(r"the front of this card is blank", re.IGNORECASE)


def rendered_front_blank(question: str) -> bool:
    """True when Anki's rendered question has no card content."""
    text = _STYLE_RE.sub(" ", question or "")
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text or _BLANK_FRONT_RE.search(text):
        return True
    return False


def showing_ords(fronts: list[str], fields: dict[str, str]) -> set[int]:
    return {i for i, front in enumerate(fronts) if front_text(front, fields)}


def template_gate_field(model: str, name: str, html_sides: str) -> str | None:
    lowered = name.lower()
    if model == VOCAB_MODEL:
        if VERB2_SCRIPT_FIELD in html_sides:
            return VERB2_SCRIPT_FIELD
        if VERB_SCRIPT_FIELD in html_sides:
            return VERB_SCRIPT_FIELD
        if SCRIPT_FIELD in html_sides or "script" in lowered:
            return SCRIPT_FIELD
        return None
    if model == SENTENCE_MODEL:
        if SENTENCE_SCRIPT_FIELD in html_sides or "script" in lowered:
            return SENTENCE_SCRIPT_FIELD
        return SENTENCE_FIELD
    return None


def load_template_info(
    models: list[str],
) -> dict[str, tuple[dict[int, str], list[str]]]:
    """Per model: card ordinal -> unlock field, and front templates in ord order."""
    info: dict[str, tuple[dict[int, str], list[str]]] = {}
    for model in (VOCAB_MODEL, SENTENCE_MODEL):
        if model not in models:
            continue
        templates = invoke("modelTemplates", modelName=model) or {}
        ord_gates: dict[int, str] = {}
        fronts: list[str] = []
        for ord_, (name, sides) in enumerate(templates.items()):
            front = sides.get("Front", "") or ""
            field = template_gate_field(model, name, front + (sides.get("Back", "") or ""))
            if field:
                ord_gates[ord_] = field
            fronts.append(front)
        info[model] = (ord_gates, fronts)
    return info


def apply_visibility(
    notes: list[dict],
    cards_by_id: dict[int, dict],
    ord_gates: dict[int, str],
    fronts: list[str],
    *,
    unsuspend: bool = True,
) -> tuple[int, int, int, list[int], list[int]]:
    """Suspend locked/blank fronts.

    Return (suspended, unsuspended, fully locked, unsuspended ids, suspended ids).

    A gated card (script / sentence unlock field) stays suspended unless that
    field is exactly 1 on the note. Blank fronts are suspended too. When no
    template would show text, every card on the note is suspended.
    """
    to_suspend: list[int] = []
    to_unsuspend: list[int] = []
    fully_locked = 0
    for note in notes:
        fmap = field_map(note)
        showing = showing_ords(fronts, fmap) if fronts else set()
        note_cards = [
            cid for cid in (note.get("cards") or []) if cid in cards_by_id
        ]
        if fronts and not showing and note_cards:
            fully_locked += 1
        for cid in note_cards:
            card = cards_by_id[cid]
            ord_ = card.get("ord", 0)
            suspended = card.get("queue") == -1
            field = ord_gates.get(ord_)
            template_blank = bool(fronts) and ord_ not in showing
            live_blank = rendered_front_blank(card.get("question") or "")
            if field and fmap.get(field, "") != "1":
                if not suspended:
                    to_suspend.append(cid)
                continue
            if template_blank or live_blank:
                if not suspended:
                    to_suspend.append(cid)
                continue
            if field and unsuspend and suspended:
                to_unsuspend.append(cid)

    actions: list[dict] = []
    for i in range(0, len(to_suspend), 500):
        actions.append(
            {"action": "suspend", "params": {"cards": to_suspend[i : i + 500]}}
        )
    for i in range(0, len(to_unsuspend), 500):
        actions.append(
            {
                "action": "unsuspend",
                "params": {"cards": to_unsuspend[i : i + 500]},
            }
        )
    invoke_multi(actions)
    return len(to_suspend), len(to_unsuspend), fully_locked, to_unsuspend, to_suspend


def new_script_card_ids(
    notes: list[dict],
    cards_by_id: dict[int, dict],
    ord_gates: dict[int, str],
    unsuspended: set[int],
    suspended: set[int],
) -> list[int]:
    """New script cards already in the queue, plus ones unsuspended this run."""
    found: list[int] = []
    for note in notes:
        for cid in note.get("cards") or []:
            card = cards_by_id.get(cid)
            if not card or cid in suspended:
                continue
            if ord_gates.get(card.get("ord", 0)) not in SCRIPT_CARD_FIELDS:
                continue
            if card.get("type") != 0:
                continue
            if card.get("queue") == 0 or cid in unsuspended:
                found.append(cid)
    return found


def _queue_cards(card_ids: list[int]) -> list[dict]:
    records = []
    for i in range(0, len(card_ids), 1000):
        chunk = card_ids[i : i + 1000]
        info = invoke(
            "cardsInfo",
            cards=chunk,
            fields=["due", "ord", "type", "queue", "note", "deckName"],
        ) or []
        for cid, card in zip(chunk, info):
            if not card or card.get("type") != 0:
                continue
            queue = card.get("queue")
            if queue not in (0, -2, -3):
                continue
            records.append(
                {
                    "id": cid,
                    "due": int(card.get("due") or 0),
                    "ord": int(card.get("ord") or 0),
                    "note": int(card.get("note") or 0),
                    "deck": card.get("deckName") or "",
                    "queue": queue,
                }
            )
    return records


def _cluster_note_blocks(cards: list[dict]) -> list[list[dict]]:
    """Pull every card of a note to that note's earliest queue position."""
    cards = sorted(cards, key=lambda card: (card["due"], card["ord"], card["id"]))
    blocks: list[list[dict]] = []
    index_by_note: dict[int, int] = {}
    for card in cards:
        slot = index_by_note.get(card["note"])
        if slot is None:
            index_by_note[card["note"]] = len(blocks)
            blocks.append([card])
        else:
            blocks[slot].append(card)
    return blocks


def _script_blocks(cards: list[dict]) -> list[list[dict]]:
    by_note: dict[int, list[dict]] = {}
    for card in cards:
        by_note.setdefault(card["note"], []).append(card)
    blocks = []
    for group in by_note.values():
        random.shuffle(group)
        blocks.append(group)
    random.shuffle(blocks)
    return blocks


def _place_script_blocks(fixed: list[list[dict]], scripts: list[dict]) -> list[dict]:
    """Space script-card groups through the gaps of an ordered card list.

    ``fixed`` is already in queue order, one block per note. Script cards of
    one note stay together in a gap, outside that note's block.
    """
    inserted = _script_blocks(scripts)
    if not inserted:
        return [card for block in fixed for card in block]
    if not fixed:
        return [card for block in inserted for card in block]
    cards_before = [0]
    for block in fixed:
        cards_before.append(cards_before[-1] + len(block))
    n_cards = cards_before[-1]
    at_gap: dict[int, list[list[dict]]] = {i: [] for i in range(len(cards_before))}
    for index, block in enumerate(inserted):
        target = (index + 0.5) * n_cards / len(inserted)
        gap = min(
            range(len(cards_before)),
            key=lambda candidate: (abs(cards_before[candidate] - target), candidate),
        )
        at_gap[gap].append(block)
    sequence: list[dict] = []
    for gap, block in enumerate(fixed):
        for script_block in at_gap[gap]:
            sequence.extend(script_block)
        sequence.extend(block)
    for script_block in at_gap[len(fixed)]:
        sequence.extend(script_block)
    return sequence


def _position_group(deck: str) -> str:
    """Farsi and Farsi::Queue share one new-card position list.

    That deck gathers new cards by ascending position, so a low position in
    either deck is the same queue. Other decks keep their own positions.
    """
    if deck == VOCAB_DECK or deck.startswith(VOCAB_DECK + "::"):
        return VOCAB_DECK
    return deck


def _notes_with_learned_card(note_ids: list[int]) -> set[int]:
    """Notes that already have a card past the new queue."""
    learned: set[int] = set()
    unique = list(dict.fromkeys(note_ids))
    for start in range(0, len(unique), 50):
        chunk = unique[start : start + 50]
        query = "(" + " OR ".join(f"nid:{note_id}" for note_id in chunk) + ") -is:new"
        found = invoke("findCards", query=query) or []
        for index in range(0, len(found), 1000):
            ids = found[index : index + 1000]
            info = invoke("cardsInfo", cards=ids, fields=["note", "type"]) or []
            for card in info:
                if card and card.get("type") != 0:
                    learned.add(int(card.get("note") or 0))
    learned.discard(0)
    return learned


def _script_ords_by_model() -> dict[str, set[int]]:
    info = load_template_info(invoke("modelNames") or [])
    return {
        model: {ord_ for ord_, field in gates.items() if field in SCRIPT_CARD_FIELDS}
        for model, (gates, _fronts) in info.items()
    }


def _card_is_script(card: dict, script_ords: dict[str, set[int]]) -> bool:
    if card["deck"] == SENTENCE_DECK or card["deck"].startswith(SENTENCE_DECK + "::"):
        model = SENTENCE_MODEL
    else:
        model = VOCAB_MODEL
    return card["ord"] in script_ords.get(model, set())


def scatter_new_script_cards(card_ids: list[int] | None = None) -> int:
    """Put non-script siblings together and space script cards through the gaps.

    A note's non-script new cards, including buried ones, gather at that
    note's earliest position. Notes that already have a learned card go to
    the front, in the order those notes already had. Script cards are placed
    after that order is set, spaced through the gaps of the whole queue, so
    they are not inside a sibling group. Each card then gets its own
    new-card number, and the cards inside each block are shuffled.
    """
    moving = set(dict.fromkeys(card_ids or []))
    script_ords = _script_ords_by_model()
    found = invoke(
        "findCards",
        query=(
            f'(deck:"{VOCAB_DECK}" OR deck:"{SENTENCE_DECK}") '
            "(is:new OR is:buried)"
        ),
    ) or []
    records = _queue_cards(list(dict.fromkeys([*found, *moving])))
    learned = _notes_with_learned_card([card["note"] for card in records])
    by_group: dict[str, list[dict]] = {}
    for card in records:
        by_group.setdefault(_position_group(card["deck"]), []).append(card)
    repositioned = 0
    for cards in by_group.values():
        others = [card for card in cards if not _card_is_script(card, script_ords)]
        scripts = [card for card in cards if _card_is_script(card, script_ords)]
        if not scripts and not others:
            continue
        front = [card for card in others if card["note"] in learned]
        rest = [card for card in others if card["note"] not in learned]
        fixed = _cluster_note_blocks(front) + _cluster_note_blocks(rest)
        for block in fixed:
            random.shuffle(block)
        sequence = _place_script_blocks(fixed, scripts)
        ordered = [card["id"] for card in sequence]
        if not ordered:
            continue
        invoke(
            "repositionNewCards",
            cards=ordered,
            positions=list(range(len(ordered))),
        )
        repositioned += len(ordered)
    return repositioned


def ensure_reposition_addon() -> None:
    """Install the addon AnkiConnect needs in order to reorder new cards."""
    base = os.environ.get("ANKI_BASE")
    if base:
        addons = Path(base) / "addons21"
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return
        addons = Path(appdata) / "Anki2" / "addons21"
    src = ROOT / "anki_addon" / REPOSITION_ADDON / "__init__.py"
    if not addons.is_dir() or not src.is_file():
        return
    dest = addons / REPOSITION_ADDON
    dest.mkdir(exist_ok=True)
    data = src.read_bytes()
    target = dest / "__init__.py"
    if not target.is_file() or target.read_bytes() != data:
        target.write_bytes(data)
    meta = dest / "meta.json"
    if not meta.is_file():
        meta.write_text(
            '{"name": "Anki Unlock: reposition new cards", "disabled": false}\n',
            encoding="utf-8",
        )


def sync_card_visibility(
    models: list[str],
    *,
    unsuspend: bool = True,
) -> None:
    templates = load_template_info(models)
    vocab_raw = fetch_notes(f'deck:"{VOCAB_DECK}" note:"{VOCAB_MODEL}"')
    sentences: list[dict] = []
    if SENTENCE_MODEL in models:
        sentences = fetch_notes(f'note:"{SENTENCE_MODEL}"')
    all_card_ids = [
        cid
        for note in vocab_raw + sentences
        for cid in (note.get("cards") or [])
    ]
    cards_by_id = fetch_cards_by_id(all_card_ids)
    suspended = unsuspended = fully_locked = 0
    just_unsuspended: set[int] = set()
    just_suspended: set[int] = set()
    script_new: list[int] = []
    for model, notes in ((VOCAB_MODEL, vocab_raw), (SENTENCE_MODEL, sentences)):
        if not notes or model not in templates:
            continue
        gates, fronts = templates[model]
        (
            suspended_n,
            unsuspended_n,
            locked_n,
            unsuspended_ids,
            suspended_ids,
        ) = apply_visibility(
            notes,
            cards_by_id,
            gates,
            fronts,
            unsuspend=unsuspend,
        )
        suspended += suspended_n
        unsuspended += unsuspended_n
        fully_locked += locked_n
        just_unsuspended.update(unsuspended_ids)
        just_suspended.update(suspended_ids)
        if unsuspend:
            script_new.extend(
                new_script_card_ids(
                    notes, cards_by_id, gates, just_unsuspended, just_suspended
                )
            )
    print(
        f"Visibility: suspended={suspended}; unsuspended={unsuspended}; "
        f"fully locked notes={fully_locked}"
    )
    if unsuspend:
        ensure_reposition_addon()
        try:
            moved = scatter_new_script_cards(script_new)
        except RuntimeError as exc:
            if "unsupported action" not in str(exc).lower():
                raise
            print(
                "New cards were not repositioned. "
                "AnkiConnect has no reposition action, so the "
                "anki_unlock_reposition addon was installed. "
                "Restart Anki once so it loads, then run this script again."
            )
        else:
            print(f"New queue repositioned: {moved}")


def ensure_field(model: str, field: str, existing: list[str] | None = None) -> list[str]:
    names = existing if existing is not None else invoke("modelFieldNames", modelName=model)
    if field not in names:
        invoke("modelFieldAdd", modelName=model, fieldName=field, index=None)
        print(f"Added field {field!r} to model {model!r}")
        names = list(names) + [field]
    return names


def _conditional_card(outer: str, front: str, back: str) -> dict[str, str]:
    return {
        "Front": "{{#" + outer + "}}\n" + front + "{{/" + outer + "}}",
        "Back": "{{#" + outer + "}}\n" + back + "{{/" + outer + "}}",
    }


def _verb_template_sides(
    translit: str, english: str, script: str
) -> list[tuple[str, dict[str, str]]]:
    fa_name = "Verb2 FA -> EN" if translit.startswith("Verb2") else "Verb FA -> EN"
    en_name = "Verb2 EN -> FA" if translit.startswith("Verb2") else "Verb EN -> FA"
    script_name = (
        "Verb2 Script Writing" if translit.startswith("Verb2") else "Verb Script Writing"
    )
    fa_body = (
        "{{#" + script + "}}\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        '  <span class="text">\n'
        '    <span dir="rtl" class="farsi-script">{{' + script + "}}</span>\n"
        '    <div class="hints">\n'
        "      <div>{{hint:" + translit + "}}</div>\n"
        "    </div>\n"
        "  </span>\n"
        "</div>\n"
        "{{/" + script + "}}\n"
        "{{^" + script + "}}\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        '  <span class="text">\n'
        '    <span class="farsi-script">{{' + translit + "}}</span>\n"
        "  </span>\n"
        "</div>\n"
        "{{/" + script + "}}"
    )
    en_line = (
        '<div class="en"><span class="label">EN</span>'
        '<span class="text">{{' + english + "}}</span></div>\n"
    )
    fa_back = (
        "{{FrontSide}}\n<hr id=answer>\n" + en_line
    )
    en_front = en_line
    en_back = (
        "{{FrontSide}}\n<hr id=answer>\n"
        "{{#" + script + "}}\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        '  <span class="text">\n'
        '    <span dir="rtl" class="farsi-script">{{' + script + "}}</span>\n"
        "    <br><br>\n"
        "    {{hint:" + translit + "}}\n"
        "  </span>\n"
        "</div>\n"
        "{{/" + script + "}}\n"
        "{{^" + script + "}}\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        '  <span class="text">\n'
        '    <span class="farsi-script">{{' + translit + "}}</span>\n"
        "  </span>\n"
        "</div>\n"
        "{{/" + script + "}}"
    )
    script_front = (
        en_line
        + '<div class="prompt">Type the Farsi script</div>\n'
        + "{{type:" + script + "}}"
    )
    script_back = (
        "{{FrontSide}}\n<hr id=answer>\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        '  <span class="text">\n'
        '    <span class="farsi-script" dir="rtl">{{' + script + "}}</span>\n"
        "  </span>\n"
        "</div>\n"
        '<div class="fa">\n'
        '  <span class="label">FA</span>\n'
        "  <span class=\"text\">{{" + translit + "}}</span>\n"
        "</div>\n"
    )
    unlock = VERB2_SCRIPT_FIELD if translit.startswith("Verb2") else VERB_SCRIPT_FIELD
    return [
        (fa_name, _conditional_card(translit, fa_body, fa_back)),
        (en_name, _conditional_card(english, en_front, en_back)),
        (script_name, _conditional_card(unlock, script_front, script_back)),
    ]


def ensure_verb_model() -> None:
    """Append two verb slots. Empty slots add no cards."""
    names = invoke("modelFieldNames", modelName=VOCAB_MODEL) or []
    wanted = [name for slot in VERB_SLOTS for name in slot[:4]]
    if names[:4] != [
        "Farsi Transliteration",
        "English",
        "Farsi Script",
        SCRIPT_FIELD,
    ]:
        raise RuntimeError(f"Unexpected Farsi fields: {names}")
    for name in wanted:
        names = ensure_field(VOCAB_MODEL, name, names)
    if names != [
        "Farsi Transliteration",
        "English",
        "Farsi Script",
        SCRIPT_FIELD,
        *wanted,
    ]:
        raise RuntimeError(f"Verb fields are not at the end: {names}")
    existing = set((invoke("modelTemplates", modelName=VOCAB_MODEL) or {}))
    sides = _verb_template_sides(*VERB_SLOTS[0][:3]) + _verb_template_sides(
        *VERB_SLOTS[1][:3]
    )
    for name, card in sides:
        if name in existing:
            continue
        invoke(
            "modelTemplateAdd",
            timeout=120,
            modelName=VOCAB_MODEL,
            template={"Name": name, "Front": card["Front"], "Back": card["Back"]},
        )
        print(f"Added template {name!r}")


def ensure_unlock_fields(models: list[str] | None = None) -> list[str]:
    models = models if models is not None else invoke("modelNames")
    ensure_field(VOCAB_MODEL, SCRIPT_FIELD)
    ensure_verb_model()
    if SENTENCE_MODEL in models:
        sentence_fields = invoke("modelFieldNames", modelName=SENTENCE_MODEL)
        sentence_fields = ensure_field(SENTENCE_MODEL, SENTENCE_FIELD, sentence_fields)
        ensure_field(SENTENCE_MODEL, SENTENCE_SCRIPT_FIELD, sentence_fields)
    return models


def persian_field_name(fmap: dict) -> str:
    for candidate in (
        "Farsi Transliteration",
        "Field1",
        "Persian",
        "Front",
        "Text",
    ):
        if candidate in fmap:
            return candidate
    skip = {
        SCRIPT_FIELD,
        SENTENCE_FIELD,
        SENTENCE_SCRIPT_FIELD,
        VERB_SCRIPT_FIELD,
        VERB2_SCRIPT_FIELD,
        "Farsi Script",
        "Verb Script",
        "Verb2 Script",
        "Verb English",
        "Verb2 English",
        "Verb Transliteration",
        "Verb2 Transliteration",
    }
    for k in fmap:
        if k not in skip:
            return k
    raise KeyError(f"No Persian field in {list(fmap)}")


def build_vocab_index(mature_days: int) -> tuple[dict[str, dict], list[dict]]:
    """Return (key -> note info, unique note infos)."""
    notes = fetch_notes(f'deck:"{VOCAB_DECK}" note:"{VOCAB_MODEL}"')
    if not notes:
        print(f"No notes found for deck {VOCAB_DECK!r} model {VOCAB_MODEL!r}")
        return {}, []

    all_card_ids: list[int] = []
    for note in notes:
        all_card_ids.extend(note.get("cards") or [])

    cards_by_id = fetch_cards_by_id(all_card_ids)

    index: dict[str, dict] = {}
    unique: dict[tuple[int, str], dict] = {}

    def add_slot(
        note: dict,
        fmap: dict,
        cards: list[dict],
        ords: tuple[int, int],
        translit_field: str,
        english_field: str,
        script_field: str,
        unlock_field: str,
    ) -> None:
        translit = fmap.get(translit_field, "")
        if not plain_field(translit):
            return
        main_cards = [c for c in cards if c.get("ord", 0) in ords]
        if not main_cards:
            return
        info = {
            "noteId": note["noteId"],
            "ready": all(c.get("type", 0) != 0 for c in main_cards),
            "mature": len(main_cards) >= 2
            and all(c.get("interval", 0) >= mature_days for c in main_cards),
            "fields": fmap,
            "tags": note.get("tags") or [],
            "mainCardIds": [c["cardId"] for c in main_cards],
            "first_ms": 0,
            "again_ms": 0,
            "unlock_field": unlock_field,
            "source_fields": (translit_field, english_field, script_field),
        }
        unique[(note["noteId"], unlock_field)] = info
        for k in normalize_key(translit):
            if k not in index or (not index[k]["ready"] and info["ready"]):
                index[k] = info

    for note in notes:
        fmap = field_map(note)
        cards = [cards_by_id[cid] for cid in (note.get("cards") or []) if cid in cards_by_id]
        add_slot(
            note,
            fmap,
            cards,
            (0, 1),
            "Farsi Transliteration",
            "English",
            "Farsi Script",
            SCRIPT_FIELD,
        )
        add_slot(
            note,
            fmap,
            cards,
            (3, 4),
            "Verb Transliteration",
            "Verb English",
            "Verb Script",
            VERB_SCRIPT_FIELD,
        )
        add_slot(
            note,
            fmap,
            cards,
            (6, 7),
            "Verb2 Transliteration",
            "Verb2 English",
            "Verb2 Script",
            VERB2_SCRIPT_FIELD,
        )

    ready_ids = [
        cid
        for info in unique.values()
        if info["ready"]
        for cid in info["mainCardIds"]
    ]
    marks = fetch_review_marks(ready_ids)
    for info in unique.values():
        if not info["ready"]:
            continue
        info["first_ms"], info["again_ms"] = note_study_ms(info["mainCardIds"], marks)

    return index, list(unique.values())


def plain_field(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&amp;", "&")
    )
    return re.sub(r" {2,}", " ", text.replace("\t", " ").replace("\n", " ")).strip()


def learned_row(info: dict) -> tuple[str, str, str, str, str, str, str, int] | None:
    """One dump row when both FA-EN cards have been studied.

    The last item is the sort key (later of first review and last Again), not a column.
    """
    if not info.get("ready"):
        return None
    fmap = info["fields"]
    translit_field, english_field, script_field = info.get("source_fields") or (
        persian_field_name(fmap),
        "English",
        "Farsi Script",
    )
    translit = plain_field(fmap.get(translit_field, ""))
    if not translit:
        return None
    english = plain_field(fmap.get(english_field, ""))
    script = plain_field(fmap.get(script_field, ""))
    tags = " ".join(t.strip() for t in info.get("tags") or [] if t.strip())
    level = "mature" if info.get("mature") else "learned"
    first_ms = int(info.get("first_ms") or 0)
    again_ms = int(info.get("again_ms") or 0)
    return (
        level,
        translit,
        english,
        script,
        tags.replace("\t", " "),
        review_day(first_ms),
        review_day(again_ms),
        max(first_ms, again_ms),
    )


def sorted_learned_rows(vocab_notes: list[dict]) -> list[tuple]:
    rows = [row for info in vocab_notes if (row := learned_row(info))]
    rows.sort(key=lambda row: (-row[7], row[1].casefold(), row[2].casefold(), row[3]))
    return rows


def render_learned_vocab(rows: list[tuple], mature_days: int) -> str:
    ready = len(rows)
    mature = sum(1 for row in rows if row[0] == "mature")
    header = (
        "# learned_vocab\n"
        "# source: anki_unlock.py\n"
        f"# mature_days: {mature_days}\n"
        f"# ready: {ready}\n"
        f"# mature: {mature}\n"
        "# columns: level, transliteration, english, script, tags, first, again\n"
        "# level mature: both FA-EN cards interval >= mature_days\n"
        "# level learned: both FA-EN cards are not new\n"
        "# first: local date of the earliest review on either FA-EN card\n"
        "# again: local date of the latest Again on either FA-EN card; empty if none\n"
        "# order: newest or most recently failed first (later of first and again)\n"
        "# ~ separates formal and spoken; > separates infinitive and present stem\n"
    )
    body = "".join("\t".join(row[:7]) + "\n" for row in rows)
    return header + body


def is_grammar_row(tags: str) -> bool:
    lowered = tags.lower()
    return any(marker in lowered for marker in GRAMMAR_TAG_MARKERS)


def render_practice_vocab(rows: list[tuple]) -> str:
    content = [row for row in rows if not is_grammar_row(row[4])]
    content.sort(key=lambda row: (row[1].casefold(), row[2].casefold(), row[3]))
    header = (
        "# practice_vocab\n"
        "# source: anki_unlock.py\n"
        f"# notes: {len(content)}\n"
        "# columns: level, transliteration, english, script\n"
        "# Content words only (no grammar affixes). For farsi-conversation default mode.\n"
        "# ~ separates formal and spoken; > separates infinitive and present stem\n"
    )
    body = "".join("\t".join(row[:4]) + "\n" for row in content)
    return header + body


def render_practice_grammar(rows: list[tuple]) -> str:
    grammar = [row for row in rows if is_grammar_row(row[4])]
    grammar.sort(key=lambda row: (row[1].casefold(), row[2].casefold(), row[3]))
    header = (
        "# practice_grammar\n"
        "# source: anki_unlock.py\n"
        f"# notes: {len(grammar)}\n"
        "# columns: level, transliteration, english, script, tags\n"
        "# Affixes and particles for conjugation / attachment rules.\n"
    )
    body = "".join("\t".join(row[:5]) + "\n" for row in grammar)
    return header + body


def render_practice_focus(rows: list[tuple], limit: int = FOCUS_LIMIT) -> str:
    focus = rows[:limit]
    header = (
        "# practice_focus\n"
        "# source: anki_unlock.py\n"
        f"# notes: {len(focus)}\n"
        f"# limit: {limit}\n"
        "# columns: level, transliteration, english, script, first, again\n"
        "# Newest or most recently failed first. For new/hard conversation focus.\n"
        "# first: earliest FA-EN review day; again: latest Again day (empty if none)\n"
    )
    body = "".join(
        "\t".join((row[0], row[1], row[2], row[3], row[5], row[6])) + "\n"
        for row in focus
    )
    return header + body


def write_learned_vocab(
    vocab_notes: list[dict], path: Path, mature_days: int
) -> tuple[int, int]:
    rows = sorted_learned_rows(vocab_notes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_learned_vocab(rows, mature_days), encoding="utf-8", newline="\n"
    )
    PRACTICE_VOCAB_OUT.write_text(
        render_practice_vocab(rows), encoding="utf-8", newline="\n"
    )
    PRACTICE_GRAMMAR_OUT.write_text(
        render_practice_grammar(rows), encoding="utf-8", newline="\n"
    )
    PRACTICE_FOCUS_OUT.write_text(
        render_practice_focus(rows), encoding="utf-8", newline="\n"
    )
    ready = len(rows)
    mature = sum(1 for row in rows if row[0] == "mature")
    return ready, mature


def export_deck_package(deck: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    ok = invoke("exportPackage", deck=deck, path=str(path), includeSched=False)
    if not ok or not path.is_file():
        raise RuntimeError(f"exportPackage failed for deck {deck!r} -> {path}")


def read_notes_from_apkg(path: Path) -> list[tuple[str, list[str], str, str, str]]:
    """Return (guid, fields, tags, model_name, deck_name) rows from an exported package."""
    with zipfile.ZipFile(path) as zf:
        name = (
            "collection.anki21"
            if "collection.anki21" in zf.namelist()
            else "collection.anki2"
        )
        raw = zf.read(name)
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "collection.anki2"
        db_path.write_bytes(raw)
        con = sqlite3.connect(db_path)
        models = json.loads(con.execute("SELECT models FROM col").fetchone()[0])
        model_name = {int(mid): m["name"] for mid, m in models.items()}
        decks = json.loads(con.execute("SELECT decks FROM col").fetchone()[0])
        deck_name = {int(did): d["name"] for did, d in decks.items()}
        note_deck: dict[int, str] = {}
        for nid, did in con.execute("SELECT nid, did FROM cards"):
            if nid not in note_deck:
                note_deck[int(nid)] = deck_name.get(int(did), "")
        rows: list[tuple[str, list[str], str, str, str]] = []
        for nid, mid, guid, flds, tags in con.execute(
            "SELECT id, mid, guid, flds, tags FROM notes"
        ):
            rows.append(
                (
                    guid,
                    flds.split("\x1f"),
                    (tags or "").strip(),
                    model_name.get(int(mid), ""),
                    note_deck.get(int(nid), ""),
                )
            )
        con.close()
    return rows


def render_deck_index(rows: list[tuple[str, list[str], str, str, str]]) -> str:
    body_lines: list[str] = []
    for guid, fields, tags, model, deck in rows:
        if model != VOCAB_MODEL:
            continue
        translit = plain_field(fields[0]) if fields else ""
        english = plain_field(fields[1]) if len(fields) > 1 else ""
        script = plain_field(fields[2]) if len(fields) > 2 else ""
        unlocked = plain_field(fields[3]) if len(fields) > 3 else ""
        if unlocked not in ("", "1"):
            unlocked = ""
        verb = [plain_field(fields[i]) if len(fields) > i else "" for i in range(4, 12)]
        tag_s = " ".join(tags.split())
        body_lines.append(
            "\t".join([guid, deck, translit, english, script, unlocked, *verb, tag_s])
        )

    def sort_key(line: str) -> str:
        parts = line.split("\t")
        return (parts[2] or (parts[6] if len(parts) > 6 else "")).casefold()

    body_lines.sort(key=sort_key)
    header = (
        "# deck_index\n"
        "# source: anki_unlock.py --export-indexes\n"
        f"# notes: {len(body_lines)}\n"
        "# columns: guid, deck, transliteration, english, script, ScriptUnlocked, "
        "verb_transliteration, verb_english, verb_script, VerbScriptUnlocked, "
        "verb2_transliteration, verb2_english, verb2_script, Verb2ScriptUnlocked, tags\n"
        "# Prefer this file over AnkiConnect notesInfo for sentence generation.\n"
    )
    return header + "".join(line + "\n" for line in body_lines)


def render_sentences_index(rows: list[tuple[str, list[str], str, str, str]]) -> str:
    body_lines: list[str] = []
    for guid, fields, tags, model, _deck in rows:
        if model != SENTENCE_MODEL:
            continue
        translit = plain_field(fields[0]) if fields else ""
        english = plain_field(fields[1]) if len(fields) > 1 else ""
        script = plain_field(fields[2]) if len(fields) > 2 else ""
        tag_s = " ".join(tags.split())
        body_lines.append("\t".join([guid, translit, english, script, tag_s]))
    body_lines.sort(key=lambda line: line.split("\t", 2)[1].casefold())
    header = (
        "# sentences_index\n"
        "# source: anki_unlock.py --export-indexes\n"
        f"# notes: {len(body_lines)}\n"
        "# columns: guid, transliteration, english, script, tags\n"
        "# Prefer this file over AnkiConnect notesInfo when adding sentences.\n"
    )
    return header + "".join(line + "\n" for line in body_lines)


def export_indexes(
    deck_out: Path | None = None,
    sentences_out: Path | None = None,
) -> tuple[int, int]:
    """Write compact vocab/sentence indexes with guids (via deck package export)."""
    cache = CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    vocab_pkg = cache / "_export_farsi.apkg"
    sent_pkg = cache / "_export_farsi_sentences.apkg"
    export_deck_package(VOCAB_DECK, vocab_pkg)
    vocab_rows = read_notes_from_apkg(vocab_pkg)
    deck_text = render_deck_index(vocab_rows)
    deck_path = deck_out or DECK_INDEX_OUT
    deck_path.write_text(deck_text, encoding="utf-8", newline="\n")
    vocab_n = sum(1 for line in deck_text.splitlines() if line and not line.startswith("#"))

    sent_n = 0
    models = invoke("modelNames") or []
    sent_path = sentences_out or SENTENCES_INDEX_OUT
    if SENTENCE_MODEL in models:
        export_deck_package(SENTENCE_DECK, sent_pkg)
        sent_rows = read_notes_from_apkg(sent_pkg)
        sent_text = render_sentences_index(sent_rows)
        sent_path.write_text(sent_text, encoding="utf-8", newline="\n")
        sent_n = sum(
            1 for line in sent_text.splitlines() if line and not line.startswith("#")
        )
    else:
        sent_path.write_text(
            "# sentences_index\n# sentence model not found\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Deck index: {vocab_n} notes -> {deck_path}")
    print(f"Sentences index: {sent_n} notes -> {sent_path}")
    return vocab_n, sent_n


def flush_updates(updates: list[dict]) -> None:
    """Collapse per-note field patches, then send via multi."""
    if not updates:
        return
    merged: dict[int, dict] = {}
    for action in updates:
        note = action["params"]["note"]
        nid = note["id"]
        merged.setdefault(nid, {}).update(note["fields"])
    invoke_multi(
        [
            {"action": "updateNoteFields", "params": {"note": {"id": nid, "fields": fields}}}
            for nid, fields in merged.items()
        ]
    )


def eval_reqs(reqs: list[str], index: dict[str, dict]) -> tuple[bool, bool, list[str]]:
    missing: list[str] = []
    ready_ok = True
    mature_ok = True
    for key in reqs:
        info = index.get(key)
        if not info:
            missing.append(key)
            ready_ok = False
            mature_ok = False
            continue
        if not info["ready"]:
            ready_ok = False
        if not info["mature"]:
            mature_ok = False
    return ready_ok, mature_ok, missing


def unlock(
    mature_days: int = MATURE_INTERVAL_DEFAULT,
    vocab_out: str | Path | None = None,
    suspend_only: bool = False,
) -> None:
    if suspend_only:
        sync_card_visibility(invoke("modelNames"), unsuspend=False)
        print("Done.")
        return

    models = ensure_unlock_fields()
    index, vocab_notes = build_vocab_index(mature_days)
    print(f"Indexed {len(index)} vocab keys ({len(vocab_notes)} notes) from {VOCAB_DECK!r}")

    updates: list[dict] = []
    script_on = 0
    for info in vocab_notes:
        fmap = info["fields"]
        unlock_field = info.get("unlock_field") or SCRIPT_FIELD
        if unlock_field not in fmap or not info["mature"]:
            continue
        if fmap.get(unlock_field, "") == "1":
            continue
        script_on += 1
        updates.append(
            {
                "action": "updateNoteFields",
                "params": {"note": {"id": info["noteId"], "fields": {unlock_field: "1"}}},
            }
        )

    print(f"ScriptUnlocked newly set: {script_on}")

    sentences: list[dict] = []
    unlocked = script_unlocked = script_relocked = locked = skipped = 0
    missing_report: list[tuple[str, list[str]]] = []

    if SENTENCE_MODEL not in models:
        print("Sentence model not found; run with --setup and import Farsi_Sentences.txt")
    else:
        sentences = fetch_notes(f'note:"{SENTENCE_MODEL}"')
        for note in sentences:
            reqs = parse_req_tags(note.get("tags") or [])
            fmap = field_map(note)
            if not reqs:
                skipped += 1
                continue

            ready_ok, mature_ok, missing = eval_reqs(reqs, index)
            if missing and len(missing_report) < MISSING_REPORT_LIMIT:
                missing_report.append((fmap.get("Farsi Transliteration", "")[:40], missing))

            pending: dict[str, str] = {}
            if not ready_ok:
                locked += 1
            elif SENTENCE_FIELD in fmap and fmap.get(SENTENCE_FIELD, "") != "1":
                pending[SENTENCE_FIELD] = "1"
                unlocked += 1
            if SENTENCE_SCRIPT_FIELD in fmap:
                current = fmap.get(SENTENCE_SCRIPT_FIELD, "")
                if mature_ok and current != "1":
                    pending[SENTENCE_SCRIPT_FIELD] = "1"
                    script_unlocked += 1
                elif not mature_ok and current == "1":
                    pending[SENTENCE_SCRIPT_FIELD] = ""
                    script_relocked += 1
            if pending:
                updates.append(
                    {
                        "action": "updateNoteFields",
                        "params": {"note": {"id": note["noteId"], "fields": pending}},
                    }
                )

    flush_updates(updates)

    if SENTENCE_MODEL in models:
        print(
            f"Sentences: translit newly unlocked={unlocked}; "
            f"script newly unlocked={script_unlocked}; script relocked={script_relocked}; "
            f"still locked={locked}; no req tags={skipped}"
        )
        if missing_report:
            print("Examples with unknown req:: keys (fix tags if needed):")
            for persian, miss in missing_report:
                print(f"  {persian!r} → missing {miss}")

    sync_card_visibility(models)

    out = Path(vocab_out) if vocab_out else VOCAB_OUT
    ready_n, mature_n = write_learned_vocab(vocab_notes, out, mature_days)
    print(f"Learned vocab: {ready_n} ready ({mature_n} mature) -> {out}")
    print(
        f"Practice dumps: {PRACTICE_VOCAB_OUT.name}, "
        f"{PRACTICE_GRAMMAR_OUT.name}, {PRACTICE_FOCUS_OUT.name}"
    )

    print("Done. Sync Anki when ready so mobile/web get unlock fields.")


CONTENT_POS = {"noun", "adjective"}


def _say(line: str) -> None:
    sys.stdout.buffer.write((line + "\n").encode("utf-8", "replace"))


def _pos(tags: list[str]) -> set[str]:
    return {tag.split("::", 1)[0].casefold() for tag in tags}


def _first_piece(text: str) -> str:
    raw = html.unescape(text or "").strip().lower()
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.split(r"[~>]", raw, maxsplit=1)[0]
    raw = re.sub(r"\([^)]*\)", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _base_heads(text: str) -> list[str]:
    raw = html.unescape(text or "").strip().lower()
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.split(r">", raw, maxsplit=1)[0]
    heads: list[str] = []
    for alt in raw.split("~"):
        alt = re.sub(r"\([^)]*\)", " ", alt)
        alt = re.sub(r"\s+", " ", alt).strip()
        if not alt or " " in alt or "/" in alt:
            continue
        head = alt.split(" ")[0]
        if head and head not in heads:
            heads.append(head)
    return heads


def _present_stem(text: str) -> str:
    raw = html.unescape(text or "").strip().lower()
    raw = re.sub(r"<[^>]+>", "", raw)
    if ">" not in raw:
        return ""
    stem = re.split(r"[~/]", raw.split(">", 1)[1], maxsplit=1)[0]
    stem = re.sub(r"\([^)]*\)", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.split(" ")[0] if stem else ""


def _brief(note: dict) -> str:
    return f"{note['tr']} [{note['en']}]"


def _choose_base(
    head: str, grouped: dict[str, list[dict]], skip_id: int
) -> tuple[dict | None, list[dict], bool]:
    notes = [note for note in grouped.get(head, []) if note["id"] != skip_id]
    content = [note for note in notes if _pos(note["tags"]) & CONTENT_POS]
    if not content:
        return None, notes, False

    def rank(note: dict) -> int:
        return 0 if "noun" in _pos(note["tags"]) else 1

    content.sort(key=lambda note: (rank(note), note["id"]))
    best = rank(content[0])
    tied = [note for note in content if rank(note) == best]
    if len(tied) > 1:
        return None, notes, True
    chosen = content[0]
    left = [note for note in notes if note["id"] != chosen["id"]]
    return chosen, left, False


def _load_vocab_records() -> list[dict]:
    notes = fetch_notes(f'deck:"{VOCAB_DECK}" note:"{VOCAB_MODEL}"')
    card_ids = [cid for note in notes for cid in (note.get("cards") or [])]
    cards_by_id = fetch_cards_by_id(card_ids)
    records = []
    for note in notes:
        fmap = field_map(note)
        tr = plain_field(fmap.get("Farsi Transliteration", ""))
        records.append(
            {
                "id": int(note["noteId"]),
                "tr": tr,
                "en": plain_field(fmap.get("English", "")),
                "script": plain_field(fmap.get("Farsi Script", "")),
                "unlock": plain_field(fmap.get(SCRIPT_FIELD, "")),
                "tags": list(note.get("tags") or []),
                "fields": fmap,
                "cards": [
                    cards_by_id[cid]
                    for cid in (note.get("cards") or [])
                    if cid in cards_by_id
                ],
                "head": (_base_heads(tr) or [""])[0],
                "heads": _base_heads(tr),
                "piece": _first_piece(tr),
            }
        )
    return records


def plan_verb_merges() -> dict:
    """Pair a verb with the noun or adjective of the same root and the same idea."""
    records = _load_vocab_records()
    grouped: dict[str, list[dict]] = {}
    for note in records:
        for head in note["heads"]:
            bucket = grouped.setdefault(head, [])
            if note not in bucket:
                bucket.append(note)

    pending: dict[int, list[dict]] = {}
    lines: list[str] = []

    def take(verb: dict, chosen: dict, left: list[dict], why: str) -> None:
        pending.setdefault(chosen["id"], []).append(
            {"verb": verb, "left": left, "why": why}
        )

    for verb in records:
        if "verb" not in _pos(verb["tags"]):
            continue
        tokens = verb["piece"].split(" ") if verb["piece"] else []
        if len(tokens) >= 2:
            head = tokens[0]
            chosen, left, ambiguous = _choose_base(head, grouped, verb["id"])
            if (
                chosen is None
                and not ambiguous
                and not left
                and head.endswith("i")
                and len(head) > 2
            ):
                chosen, left, ambiguous = _choose_base(head[:-1], grouped, verb["id"])
            if ambiguous:
                names = ", ".join(_brief(note) for note in left)
                lines.append(f"SKIP\t{verb['tr']}\tambiguous base {tokens[0]}: {names}")
                continue
            if chosen is None:
                if left:
                    names = ", ".join(_brief(note) for note in left)
                    lines.append(
                        f"SKIP\t{verb['tr']}\tfunction word is not the base ({names})"
                    )
                else:
                    lines.append(f"SKIP\t{verb['tr']}\tno paired note")
                continue
            if left:
                names = ", ".join(_brief(note) for note in left)
                lines.append(f"CHOICE\t{verb['tr']}\t{_brief(chosen)}\talso {names}")
            take(verb, chosen, left, "light")
            continue
        if len(tokens) != 1 or tokens[0] in LIGHT_VERBS:
            continue
        infinitive = tokens[0]
        stem = _present_stem(verb["tr"])
        found: list[tuple[dict, list[dict]]] = []
        denied: list[str] = []
        blocked = False
        for head in grouped:
            suffix = infinitive in (head + "idan", head + "dan")
            from_stem = bool(stem) and head in (stem + "aan", stem + "un")
            if not suffix and not from_stem:
                continue
            if (head, infinitive) in PLAIN_VERB_DENY:
                denied.append(head)
                continue
            chosen, left, ambiguous = _choose_base(head, grouped, verb["id"])
            if ambiguous:
                names = ", ".join(_brief(note) for note in left)
                lines.append(f"SKIP\t{verb['tr']}\tambiguous base {head}: {names}")
                blocked = True
                break
            if chosen is not None:
                found.append((chosen, left))
        if blocked:
            continue
        if not found:
            if denied:
                lines.append(
                    f"SKIP\t{verb['tr']}\tsame root, different idea ({', '.join(denied)})"
                )
            continue
        chosen_ids = {note["id"] for note, _left in found}
        if len(chosen_ids) != 1:
            names = ", ".join(_brief(note) for note, _left in found)
            lines.append(f"SKIP\t{verb['tr']}\tmore than one base ({names})")
            continue
        chosen, left = found[0]
        extra = list(left)
        for head in denied:
            extra.extend(
                note for note in grouped.get(head, []) if note["id"] != verb["id"]
            )
        if extra:
            names = ", ".join(_brief(note) for note in extra)
            lines.append(f"CHOICE\t{verb['tr']}\t{_brief(chosen)}\talso {names}")
        take(verb, chosen, extra, "plain")

    by_id = {note["id"]: note for note in records}
    merges = []
    moves = []
    delete_ids = []
    for base_id, items in sorted(pending.items()):
        base = by_id[base_id]
        items.sort(key=lambda item: item["verb"]["id"])
        occupied = {card.get("ord") for card in base["cards"]}
        for slot_i, (tr_name, en_name, script_name, unlock_name, ord_map) in enumerate(
            VERB_SLOTS, start=1
        ):
            if plain_field(base["fields"].get(tr_name, "")):
                continue
            if not items:
                break
            item = items[0]
            verb = item["verb"]
            unknown = [card for card in verb["cards"] if card.get("ord") not in ord_map]
            if unknown:
                ords = ", ".join(str(card.get("ord")) for card in unknown)
                lines.append(f"SKIP\t{verb['tr']}\tunexpected card ord {ords}")
                items.pop(0)
                continue
            targets = [ord_map[card.get("ord")] for card in verb["cards"]]
            if any(target in occupied for target in targets):
                lines.append(f"SKIP\t{verb['tr']}\ttarget card already exists")
                items.pop(0)
                continue
            items.pop(0)
            occupied.update(targets)
            slot_fields = {
                tr_name: verb["fields"].get("Farsi Transliteration", ""),
                en_name: verb["fields"].get("English", ""),
                script_name: verb["fields"].get("Farsi Script", ""),
                unlock_name: verb["fields"].get(SCRIPT_FIELD, ""),
            }
            for card in verb["cards"]:
                new_ord = ord_map[card.get("ord")]
                moves.append(
                    {"card": card["cardId"], "note": base_id, "ord": new_ord}
                )
                lines.append(
                    "MERGE\t"
                    f"slot {slot_i}\t{base['tr']}\t<=\t{verb['tr']}\t"
                    f"card {card['cardId']} ord {card.get('ord')}->{new_ord} "
                    f"ivl {card.get('interval')} due {card.get('due')}"
                )
            merges.append(
                {
                    "base": base_id,
                    "verb": verb["id"],
                    "slot": slot_i,
                    "fields": slot_fields,
                    "tags": verb["tags"],
                    "cards": [
                        (card["cardId"], card.get("interval"), card.get("due"), ord_map[card.get("ord")])
                        for card in verb["cards"]
                    ],
                }
            )
            delete_ids.append(verb["id"])
        for item in items:
            lines.append(
                f"SKIP\t{item['verb']['tr']}\tthird verb on {base['tr']} stays its own note"
            )

    edits: dict[int, dict] = {}
    for merge in merges:
        edit = edits.setdefault(
            merge["base"], {"id": merge["base"], "fields": {}, "tags": []}
        )
        edit["fields"].update(merge["fields"])
        for tag in merge["tags"]:
            if tag not in edit["tags"]:
                edit["tags"].append(tag)
    note_edits = list(edits.values())
    return {
        "lines": lines,
        "moves": moves,
        "notes": note_edits,
        "delete": delete_ids,
        "checks": merges,
    }


def merge_related_verbs(apply: bool) -> None:
    if apply:
        ensure_verb_model()
        ensure_reposition_addon()
    plan = plan_verb_merges()
    for line in plan["lines"]:
        _say(line)
    _say(
        f"{len(plan['checks'])} verbs, {len(plan['moves'])} cards, "
        f"{len(plan['delete'])} notes"
    )
    if not apply:
        _say("Dry run. Nothing written.")
        return
    if not plan["moves"]:
        _say("Nothing to merge.")
        return
    result = invoke(
        "mergeRelatedVerbs",
        timeout=120,
        moves=plan["moves"],
        edits=plan["notes"],
        delete=plan["delete"],
    )
    _say(f"Merged {result}")
    cards = fetch_cards_by_id([move["card"] for move in plan["moves"]])
    problems = []
    for merge in plan["checks"]:
        for card_id, interval, due, new_ord in merge["cards"]:
            card = cards.get(card_id)
            if card is None:
                problems.append(f"missing card {card_id}")
                continue
            if int(card.get("note") or 0) != merge["base"] or card.get("ord") != new_ord:
                problems.append(
                    f"card {card_id} note {card.get('note')} ord {card.get('ord')}"
                )
            if card.get("interval") != interval or card.get("due") != due:
                problems.append(
                    f"card {card_id} history changed ivl {interval}->{card.get('interval')} "
                    f"due {due}->{card.get('due')}"
                )
    gone = invoke("notesInfo", notes=plan["delete"]) or []
    still = [note for note in gone if note.get("noteId")]
    if still:
        problems.append(f"{len(still)} verb notes still exist")
    if problems:
        for problem in problems:
            _say("PROBLEM\t" + problem)
        raise RuntimeError("merge verification failed")
    _say("Verified card ids, note, template, interval, and due.")


MISSING_VERB_BASES = {
    "tark": ("tark", "Quitting or abandonment", "ترک", "Noun"),
}


def gate_main_templates() -> None:
    """An empty main field must not grow a card. Verb-only notes use the verb slot."""
    templates = invoke("modelTemplates", modelName=VOCAB_MODEL) or {}
    fa = templates.get("FA -> EN") or {}
    front = fa.get("Front") or ""
    inverse = "{{^Farsi Script}}\n"
    if inverse in front and "{{^Farsi Script}}\n{{#Farsi Transliteration}}" not in front:
        start = front.find(inverse)
        close = front.find("{{/Farsi Script}}", start)
        if close == -1:
            raise RuntimeError("Farsi front has no empty-script close")
        front = (
            front[: start + len(inverse)]
            + "{{#Farsi Transliteration}}\n"
            + front[start + len(inverse) : close]
            + "{{/Farsi Transliteration}}\n"
            + front[close:]
        )
        invoke(
            "modelTemplateAdd",
            timeout=120,
            modelName=VOCAB_MODEL,
            template={"Name": "FA -> EN", "Front": front, "Back": fa.get("Back") or ""},
        )
        print("Gated the Farsi front on the transliteration")
    en = templates.get("EN -> FA") or {}
    en_front = en.get("Front") or ""
    if en_front and not en_front.lstrip().startswith("{{#English}}"):
        en_front = "{{#English}}\n" + en_front.rstrip() + "\n{{/English}}\n"
        invoke(
            "modelTemplateAdd",
            timeout=120,
            modelName=VOCAB_MODEL,
            template={
                "Name": "EN -> FA",
                "Front": en_front,
                "Back": en.get("Back") or "",
            },
        )
        print("Gated the English front on the English field")


def plan_own_verb_slots() -> dict:
    """Move a verb that has no base into the verb slot of its own note."""
    merging = {item["verb"] for item in plan_verb_merges()["checks"]}
    records = _load_vocab_records()
    lines: list[str] = []
    moves = []
    edits = []
    checks = []
    ord_map = VERB_SLOTS[0][4]
    for note in records:
        pos = _pos(note["tags"])
        if "verb" not in pos or pos & {"grammar", "prefix", "suffix"}:
            continue
        if note["tr"].startswith("-") or note["tr"].startswith("n*-"):
            continue
        if plain_field(note["fields"].get("Verb Transliteration", "")):
            continue
        if note["id"] in merging:
            continue
        if not note["piece"]:
            continue
        unknown = [card for card in note["cards"] if card.get("ord") not in ord_map]
        if unknown:
            lines.append(f"SKIP\t{note['tr']}\tunexpected card ord")
            continue
        targets = [ord_map[card.get("ord")] for card in note["cards"]]
        occupied = {card.get("ord") for card in note["cards"]}
        if any(target in occupied for target in targets):
            lines.append(f"SKIP\t{note['tr']}\ttarget card already exists")
            continue
        head = note["piece"].split(" ")[0]
        base = MISSING_VERB_BASES.get(head) if len(note["piece"].split(" ")) >= 2 else None
        fields = {
            "Verb Transliteration": note["fields"].get("Farsi Transliteration", ""),
            "Verb English": note["fields"].get("English", ""),
            "Verb Script": note["fields"].get("Farsi Script", ""),
            VERB_SCRIPT_FIELD: note["fields"].get(SCRIPT_FIELD, ""),
            "Farsi Transliteration": base[0] if base else "",
            "English": base[1] if base else "",
            "Farsi Script": base[2] if base else "",
            SCRIPT_FIELD: "",
        }
        tags = list(note["tags"])
        if base and base[3] not in tags:
            tags.append(base[3])
        for card in note["cards"]:
            new_ord = ord_map[card.get("ord")]
            moves.append({"card": card["cardId"], "note": note["id"], "ord": new_ord})
            lines.append(
                "SLOT\t"
                f"{note['tr']}\t"
                + (f"base {base[0]}\t" if base else "no base\t")
                + f"card {card['cardId']} ord {card.get('ord')}->{new_ord} "
                f"ivl {card.get('interval')} due {card.get('due')}"
            )
        edits.append({"id": note["id"], "fields": fields, "tags": tags})
        checks.append(
            {
                "note": note["id"],
                "tr": note["tr"],
                "base": base[0] if base else "",
                "cards": [
                    (
                        card["cardId"],
                        card.get("interval"),
                        card.get("due"),
                        ord_map[card.get("ord")],
                    )
                    for card in note["cards"]
                ],
            }
        )
    return {"lines": lines, "moves": moves, "notes": edits, "delete": [], "checks": checks}


def place_own_verbs(apply: bool) -> None:
    if apply:
        ensure_verb_model()
        before = len(invoke("findCards", query=f'note:"{VOCAB_MODEL}"') or [])
        gate_main_templates()
        after = len(invoke("findCards", query=f'note:"{VOCAB_MODEL}"') or [])
        if before != after:
            raise RuntimeError(f"template gate changed the card count {before} -> {after}")
        ensure_reposition_addon()
    plan = plan_own_verb_slots()
    for line in plan["lines"]:
        _say(line)
    _say(f"{len(plan['checks'])} verbs, {len(plan['moves'])} cards")
    if not apply:
        _say("Dry run. Nothing written.")
        return
    if not plan["moves"]:
        _say("Nothing to move.")
        return
    result = invoke(
        "mergeRelatedVerbs",
        timeout=120,
        moves=plan["moves"],
        edits=plan["notes"],
        delete=[],
        undo="Move verbs into their verb slots",
    )
    _say(f"Moved {result}")
    cards = fetch_cards_by_id([move["card"] for move in plan["moves"]])
    problems = []
    for item in plan["checks"]:
        for card_id, interval, due, new_ord in item["cards"]:
            card = cards.get(card_id)
            if card is None:
                problems.append(f"missing card {card_id}")
                continue
            if int(card.get("note") or 0) != item["note"] or card.get("ord") != new_ord:
                problems.append(
                    f"card {card_id} note {card.get('note')} ord {card.get('ord')}"
                )
            if card.get("interval") != interval or card.get("due") != due:
                problems.append(f"card {card_id} history changed")
    if problems:
        for problem in problems:
            _say("PROBLEM\t" + problem)
        raise RuntimeError("verb slot verification failed")
    _say("Verified card ids, template, interval, and due.")


def main():
    parser = argparse.ArgumentParser(description="Farsi Anki unlock via AnkiConnect")
    parser.add_argument("--mature-days", type=int, default=MATURE_INTERVAL_DEFAULT)
    parser.add_argument(
        "--suspend-locked",
        action="store_true",
        help="Suspend blank and fully locked cards without changing unlock fields",
    )
    parser.add_argument(
        "--export-indexes",
        action="store_true",
        help="Write compact deck_index.txt and sentences_index.txt, then exit",
    )
    parser.add_argument(
        "--vocab-out",
        default=str(VOCAB_OUT),
        help="Learned-vocab dump for conversation practice",
    )
    parser.add_argument(
        "--deck-index-out",
        default=str(DECK_INDEX_OUT),
        help="Compact vocab index path (with --export-indexes)",
    )
    parser.add_argument(
        "--sentences-index-out",
        default=str(SENTENCES_INDEX_OUT),
        help="Compact sentence index path (with --export-indexes)",
    )
    parser.add_argument(
        "--merge-verbs",
        action="store_true",
        help="Print same-root verb merges. With --apply, move the cards and keep their history",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="With --merge-verbs or --verb-slots, write the change. Without this flag it is a dry run",
    )
    parser.add_argument(
        "--verb-slots",
        action="store_true",
        help="Move verbs that are their own note into the verb slot. With --apply, keep their history",
    )
    args = parser.parse_args()
    if args.merge_verbs:
        merge_related_verbs(apply=args.apply)
        return
    if args.verb_slots:
        place_own_verbs(apply=args.apply)
        return
    if args.export_indexes:
        export_indexes(
            deck_out=Path(args.deck_index_out),
            sentences_out=Path(args.sentences_index_out),
        )
        return
    unlock(
        mature_days=args.mature_days,
        vocab_out=args.vocab_out,
        suspend_only=args.suspend_locked,
    )


if __name__ == "__main__":
    main()
