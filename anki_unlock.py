#!/usr/bin/env python3
"""Unlock Farsi script cards + sentence cards via AnkiConnect."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

ANKI_URL = "http://127.0.0.1:8765"
VOCAB_MODEL = "Farsi"
SENTENCE_MODEL = "Farsi Sentence"
VOCAB_DECK = "Farsi"
SENTENCE_DECK = "Farsi Sentences"
SCRIPT_FIELD = "ScriptUnlocked"
SENTENCE_FIELD = "SentenceUnlocked"
SENTENCE_SCRIPT_FIELD = "SentenceScriptUnlocked"
MATURE_INTERVAL_DEFAULT = 21
MISSING_REPORT_LIMIT = 8
SLUG_RE = re.compile(r"[^a-z0-9*\-]+")


def invoke(action: str, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(
        ANKI_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
    raw = field1.strip().lower()
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
    return {k: v.get("value", "") for k, v in note["fields"].items()}


def fetch_notes(query: str) -> list[dict]:
    ids = invoke("findNotes", query=query)
    return invoke("notesInfo", notes=ids) if ids else []


def ensure_field(model: str, field: str, existing: list[str] | None = None) -> list[str]:
    names = existing if existing is not None else invoke("modelFieldNames", modelName=model)
    if field not in names:
        invoke("modelFieldAdd", modelName=model, fieldName=field)
        print(f"Added field {field!r} to model {model!r}")
        names = list(names) + [field]
    return names


def ensure_unlock_fields(models: list[str] | None = None) -> list[str]:
    models = models if models is not None else invoke("modelNames")
    ensure_field(VOCAB_MODEL, SCRIPT_FIELD)
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
    skip = {SCRIPT_FIELD, SENTENCE_FIELD, SENTENCE_SCRIPT_FIELD, "Farsi Script"}
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

    cards_by_id: dict[int, dict] = {}
    if all_card_ids:
        for card in invoke("cardsInfo", cards=all_card_ids) or []:
            cards_by_id[card["cardId"]] = card

    index: dict[str, dict] = {}
    unique: dict[int, dict] = {}

    for note in notes:
        nid = note["noteId"]
        fmap = field_map(note)
        keys = normalize_key(fmap.get(persian_field_name(fmap), ""))

        cards = [cards_by_id[cid] for cid in (note.get("cards") or []) if cid in cards_by_id]
        # FA↔EN are ord 0/1; ignore later script cards for readiness/maturity
        main_cards = [c for c in cards if c.get("ord", 0) in (0, 1)]
        if not main_cards:
            continue

        info = {
            "noteId": nid,
            "ready": all(c.get("type", 0) != 0 for c in main_cards),
            "mature": len(main_cards) >= 2
            and all(c.get("interval", 0) >= mature_days for c in main_cards),
            "fields": fmap,
        }
        unique[nid] = info
        for k in keys:
            # First key wins unless replacing a not-yet-ready entry with a ready one
            if k not in index or (not index[k]["ready"] and info["ready"]):
                index[k] = info

    return index, list(unique.values())


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


def unlock(mature_days: int = MATURE_INTERVAL_DEFAULT) -> None:
    models = ensure_unlock_fields()
    index, vocab_notes = build_vocab_index(mature_days)
    print(f"Indexed {len(index)} vocab keys ({len(vocab_notes)} notes) from {VOCAB_DECK!r}")

    updates: list[dict] = []
    script_on = 0
    for info in vocab_notes:
        if not info["mature"]:
            continue
        fmap = info["fields"]
        if SCRIPT_FIELD in fmap and fmap.get(SCRIPT_FIELD, "") != "1":
            updates.append(
                {
                    "action": "updateNoteFields",
                    "params": {
                        "note": {"id": info["noteId"], "fields": {SCRIPT_FIELD: "1"}}
                    },
                }
            )
            script_on += 1

    print(f"ScriptUnlocked newly set: {script_on}")

    if SENTENCE_MODEL not in models:
        flush_updates(updates)
        print("Sentence model not found; run with --setup and import Farsi_Sentences.txt")
        return

    sentences = fetch_notes(f'note:"{SENTENCE_MODEL}"')
    unlocked = script_unlocked = locked = skipped = 0
    missing_report: list[tuple[str, list[str]]] = []

    for note in sentences:
        reqs = parse_req_tags(note.get("tags") or [])
        fmap = field_map(note)
        if not reqs:
            skipped += 1
            continue

        ready_ok, mature_ok, missing = eval_reqs(reqs, index)
        if missing and len(missing_report) < MISSING_REPORT_LIMIT:
            missing_report.append((fmap.get("Farsi Transliteration", "")[:40], missing))

        if not ready_ok:
            locked += 1
            continue

        pending: dict[str, str] = {}
        if SENTENCE_FIELD in fmap and fmap.get(SENTENCE_FIELD, "") != "1":
            pending[SENTENCE_FIELD] = "1"
            unlocked += 1
        if (
            mature_ok
            and SENTENCE_SCRIPT_FIELD in fmap
            and fmap.get(SENTENCE_SCRIPT_FIELD, "") != "1"
        ):
            pending[SENTENCE_SCRIPT_FIELD] = "1"
            script_unlocked += 1
        if pending:
            updates.append(
                {
                    "action": "updateNoteFields",
                    "params": {"note": {"id": note["noteId"], "fields": pending}},
                }
            )

    flush_updates(updates)

    print(
        f"Sentences: translit newly unlocked={unlocked}; "
        f"script newly unlocked={script_unlocked}; still locked={locked}; no req tags={skipped}"
    )
    if missing_report:
        print("Examples with unknown req:: keys (fix tags if needed):")
        for persian, miss in missing_report:
            print(f"  {persian!r} → missing {miss}")

    print("Done. Sync Anki when ready so mobile/web get unlock fields.")


def main():
    parser = argparse.ArgumentParser(description="Farsi Anki unlock via AnkiConnect")
    parser.add_argument("--mature-days", type=int, default=MATURE_INTERVAL_DEFAULT)
    args = parser.parse_args()
    unlock(mature_days=args.mature_days)


if __name__ == "__main__":
    main()
