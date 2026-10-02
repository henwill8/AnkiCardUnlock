#!/usr/bin/env python3
"""Unlock Farsi script cards + sentence cards via AnkiConnect.

Also writes learned_vocab.txt for conversation practice: every vocab note whose
FA↔EN cards are no longer New, marked mature when both intervals have reached
the script bar.

Suspends a card whose front would be blank. When every template on a note is
locked, Anki still keeps one card and shows a blank front; that card is
suspended too.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

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
VOCAB_OUT = Path(__file__).resolve().parent / "learned_vocab.txt"


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


def showing_ords(fronts: list[str], fields: dict[str, str]) -> set[int]:
    return {i for i, front in enumerate(fronts) if front_text(front, fields)}


def template_gate_field(model: str, name: str, html_sides: str) -> str | None:
    lowered = name.lower()
    if model == VOCAB_MODEL:
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
    newly_on: dict[int, set[str]],
    *,
    unsuspend: bool = True,
) -> tuple[int, int, int]:
    """Suspend blank fronts. Return (suspended, unsuspended, fully locked notes).

    A locked template is suspended on its own. When no template would show
    text, Anki still keeps one card with a blank front — suspend every card
    on that note.
    """
    to_suspend: list[int] = []
    to_unsuspend: list[int] = []
    fully_locked = 0
    for note in notes:
        nid = note["noteId"]
        fmap = field_map(note)
        just_on = newly_on.get(nid, set())
        render_fields = dict(fmap)
        for field in just_on:
            render_fields[field] = "1"
        showing = showing_ords(fronts, render_fields) if fronts else set()
        note_cards = [
            cid for cid in (note.get("cards") or []) if cid in cards_by_id
        ]
        if fronts and not showing and note_cards:
            fully_locked += 1
        for cid in note_cards:
            card = cards_by_id[cid]
            ord_ = card.get("ord", 0)
            suspended = card.get("queue") == -1
            blank = bool(fronts) and ord_ not in showing
            if blank:
                if not suspended:
                    to_suspend.append(cid)
                continue
            field = ord_gates.get(ord_)
            if not field:
                continue
            unlocked = fmap.get(field, "") == "1" or field in just_on
            if unlocked:
                if unsuspend and suspended:
                    to_unsuspend.append(cid)
            elif not suspended:
                to_suspend.append(cid)

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
    return len(to_suspend), len(to_unsuspend), fully_locked


def sync_card_visibility(
    models: list[str],
    newly_on: dict[int, set[str]],
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
    for model, notes in ((VOCAB_MODEL, vocab_raw), (SENTENCE_MODEL, sentences)):
        if not notes or model not in templates:
            continue
        gates, fronts = templates[model]
        suspended_n, unsuspended_n, locked_n = apply_visibility(
            notes,
            cards_by_id,
            gates,
            fronts,
            newly_on,
            unsuspend=unsuspend,
        )
        suspended += suspended_n
        unsuspended += unsuspended_n
        fully_locked += locked_n
    print(
        f"Visibility: suspended={suspended}; unsuspended={unsuspended}; "
        f"fully locked notes={fully_locked}"
    )


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

    cards_by_id = fetch_cards_by_id(all_card_ids)

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
            "tags": note.get("tags") or [],
        }
        unique[nid] = info
        for k in keys:
            # First key wins unless replacing a not-yet-ready entry with a ready one
            if k not in index or (not index[k]["ready"] and info["ready"]):
                index[k] = info

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


def learned_row(info: dict) -> tuple[str, str, str, str, str] | None:
    """One dump row when both FA-EN cards have been studied."""
    if not info.get("ready"):
        return None
    fmap = info["fields"]
    trans_name = persian_field_name(fmap)
    translit = plain_field(fmap.get(trans_name, ""))
    if not translit:
        return None
    english = ""
    for name in ("English", "Meaning", "Gloss"):
        if name in fmap and name != trans_name:
            english = plain_field(fmap[name])
            break
    script = ""
    for name in ("Farsi", "Farsi Script", "Persian"):
        if name in fmap and name != trans_name:
            script = plain_field(fmap[name])
            break
    tags = " ".join(t.strip() for t in info.get("tags") or [] if t.strip())
    level = "mature" if info.get("mature") else "learned"
    return level, translit, english, script, tags.replace("\t", " ")


def render_learned_vocab(vocab_notes: list[dict], mature_days: int) -> str:
    rows = [row for info in vocab_notes if (row := learned_row(info))]
    rows.sort(key=lambda row: (row[1].casefold(), row[2].casefold(), row[3]))
    ready = len(rows)
    mature = sum(1 for row in rows if row[0] == "mature")
    header = (
        "# learned_vocab\n"
        "# source: anki_unlock.py\n"
        f"# mature_days: {mature_days}\n"
        f"# ready: {ready}\n"
        f"# mature: {mature}\n"
        "# columns: level, transliteration, english, script, tags\n"
        "# level mature: both FA-EN cards interval >= mature_days; script unlocked\n"
        "# level learned: both FA-EN cards are not new; script still locked\n"
        "# ~ separates formal and spoken; > separates infinitive and present stem\n"
    )
    body = "".join("\t".join(row) + "\n" for row in rows)
    return header + body


def write_learned_vocab(
    vocab_notes: list[dict], path: Path, mature_days: int
) -> tuple[int, int]:
    text = render_learned_vocab(vocab_notes, mature_days)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    ready = sum(1 for line in text.splitlines() if line and not line.startswith("#"))
    mature = sum(1 for line in text.splitlines() if line.startswith("mature\t"))
    return ready, mature


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
        sync_card_visibility(invoke("modelNames"), {}, unsuspend=False)
        print("Done.")
        return

    models = ensure_unlock_fields()
    index, vocab_notes = build_vocab_index(mature_days)
    print(f"Indexed {len(index)} vocab keys ({len(vocab_notes)} notes) from {VOCAB_DECK!r}")

    updates: list[dict] = []
    newly_on: dict[int, set[str]] = {}
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
            newly_on.setdefault(info["noteId"], set()).add(SCRIPT_FIELD)
            script_on += 1

    print(f"ScriptUnlocked newly set: {script_on}")

    sentences: list[dict] = []
    unlocked = script_unlocked = locked = skipped = 0
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
                newly_on.setdefault(note["noteId"], set()).update(pending)

    flush_updates(updates)

    if SENTENCE_MODEL in models:
        print(
            f"Sentences: translit newly unlocked={unlocked}; "
            f"script newly unlocked={script_unlocked}; still locked={locked}; no req tags={skipped}"
        )
        if missing_report:
            print("Examples with unknown req:: keys (fix tags if needed):")
            for persian, miss in missing_report:
                print(f"  {persian!r} → missing {miss}")

    sync_card_visibility(models, newly_on)

    out = Path(vocab_out) if vocab_out else VOCAB_OUT
    ready_n, mature_n = write_learned_vocab(vocab_notes, out, mature_days)
    print(f"Learned vocab: {ready_n} ready ({mature_n} mature) -> {out}")

    print("Done. Sync Anki when ready so mobile/web get unlock fields.")


def main():
    parser = argparse.ArgumentParser(description="Farsi Anki unlock via AnkiConnect")
    parser.add_argument("--mature-days", type=int, default=MATURE_INTERVAL_DEFAULT)
    parser.add_argument(
        "--suspend-locked",
        action="store_true",
        help="Suspend blank and fully locked cards without changing unlock fields",
    )
    parser.add_argument(
        "--vocab-out",
        default=str(VOCAB_OUT),
        help="Learned-vocab dump for conversation practice",
    )
    args = parser.parse_args()
    unlock(
        mature_days=args.mature_days,
        vocab_out=args.vocab_out,
        suspend_only=args.suspend_locked,
    )


if __name__ == "__main__":
    main()
