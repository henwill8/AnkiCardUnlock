"""AnkiConnect action that sets the order of new cards."""

import sys

from aqt import gui_hooks


def _ankiconnect():
    for mod in list(sys.modules.values()):
        ac = getattr(mod, "ac", None)
        if ac is not None and callable(getattr(ac, "resolve_action", None)):
            return ac
    return None


def _apply(legacy, params):
    ids = [int(card_id) for card_id in params.get("cards") or []]
    places = [int(place) for place in params.get("positions") or []]
    if not ids:
        return 0
    if len(ids) != len(places):
        raise Exception("cards and positions must be the same length")
    start = places[0]
    if places != list(range(start, start + len(places))):
        raise Exception("positions must be contiguous")
    service = legacy.service
    if service is None:
        raise Exception("collection is not available")
    col = service.col
    cards = []
    for cid, pos in zip(ids, places):
        card = col.get_card(cid)
        if int(card.type) != 0:
            continue
        card.due = pos
        cards.append(card)
    if not cards:
        return 0
    undo = col.add_custom_undo_entry("Reposition new cards")
    changes = col.update_cards(cards)
    col.merge_undo_entries(undo)
    service.change(changes)
    return len(cards)


def _reposition_new_cards(self, cards, positions):
    return _apply(self, {"cards": cards, "positions": positions})


def _merge_related(legacy, params):
    """Point verb cards at the base note. The card id, and its review log, stay."""
    import html

    moves = params.get("moves") or []
    note_edits = params.get("edits") or []
    delete_ids = [int(nid) for nid in (params.get("delete") or [])]
    service = legacy.service
    if service is None:
        raise Exception("collection is not available")
    col = service.col
    undo = col.add_custom_undo_entry(params.get("undo") or "Merge related verbs")
    changes = None
    cards = []
    for move in moves:
        card = col.get_card(int(move["card"]))
        card.nid = int(move["note"])
        card.ord = int(move["ord"])
        cards.append(card)
    if cards:
        changes = col.update_cards(cards)
        col.merge_undo_entries(undo)
        for move in moves:
            row = col.db.first(
                "select nid, ord from cards where id = ?",
                int(move["card"]),
            )
            if (
                row is None
                or int(row[0]) != int(move["note"])
                or int(row[1]) != int(move["ord"])
            ):
                raise Exception(f"card {move['card']} did not move")
    notes = []
    for edit in note_edits:
        note = col.get_note(int(edit["id"]))
        for name, value in (edit.get("fields") or {}).items():
            note[name] = html.unescape(value or "")
        extra = [tag for tag in (edit.get("tags") or []) if tag not in note.tags]
        if extra:
            note.tags = list(note.tags) + extra
        notes.append(note)
    if notes:
        changes = col.update_notes(notes)
        col.merge_undo_entries(undo)
    if delete_ids:
        changes = col.remove_notes(delete_ids)
        col.merge_undo_entries(undo)
    if changes is not None:
        service.change(changes)
    return {"cards": len(cards), "notes": len(notes), "deleted": len(delete_ids)}


def _merge_related_verbs(self, moves, edits, delete, undo=None):
    return _merge_related(
        self,
        {"moves": moves, "edits": edits, "delete": delete, "undo": undo},
    )


def _legacy_class(ac):
    for mod in sys.modules.values():
        if getattr(mod, "ac", None) is ac and hasattr(mod, "Legacy"):
            return mod.Legacy
    return None


def _install() -> None:
    ac = _ankiconnect()
    if ac is None:
        print("anki_unlock_reposition: AnkiConnect is not loaded")
        return
    cls = type(ac)
    if not getattr(cls, "_anki_unlock_reposition", False):
        _reposition_new_cards.api = True
        _reposition_new_cards.versions = []
        cls.repositionNewCards = _reposition_new_cards
        _merge_related_verbs.api = True
        _merge_related_verbs.versions = []
        cls.mergeRelatedVerbs = _merge_related_verbs
        cls._anki_unlock_reposition = True
    legacy_cls = _legacy_class(ac)
    if legacy_cls is None or getattr(legacy_cls.call, "_anki_unlock_reposition", False):
        return
    original = legacy_cls.call

    def call(self, name, params):
        if name == "repositionNewCards":
            return _apply(self, params)
        if name == "mergeRelatedVerbs":
            return _merge_related(self, params)
        return original(self, name, params)

    call._anki_unlock_reposition = True
    legacy_cls.call = call


gui_hooks.profile_did_open.append(_install)
