"""AnkiConnect action that sets the order of new cards and reconciles desynced cards."""

import sys
import time

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


def _repair_desynced_cards_impl(col):
    """Reconcile cards whose scheduling was rolled back or desynced behind revlog."""
    cutoff_ms = (int(time.time()) - 259200) * 1000  # last 3 days
    rows = col.db.all(
        """
        SELECT cid, count(*), max(id)
        FROM revlog
        WHERE id > ?
        GROUP BY cid
        """,
        cutoff_ms,
    )
    if not rows:
        return 0

    repaired = []
    for cid, rev_count, max_id in rows:
        try:
            card = col.get_card(cid)
        except Exception:
            continue

        last_rev = col.db.first(
            "SELECT id, ease, ivl, lastIvl, factor, type FROM revlog WHERE id = ?",
            max_id,
        )
        if not last_rev:
            continue
        rev_id, ease, ivl, last_ivl, factor, rev_type = last_rev
        rev_time = int(rev_id / 1000)

        needs_fix = False

        if ivl < 0:
            # Intraday learning step (ivl in negative seconds, e.g. -5400s = 90m)
            expected_due = rev_time + abs(ivl)
            # If card is in learning queue and due is earlier than expected due
            if card.queue == 1 and card.due < expected_due:
                card.due = expected_due
                card.type = 1
                card.queue = 1
                card.ivl = 0
                card.reps = rev_count
                needs_fix = True
            elif card.reps < rev_count:
                card.reps = rev_count
                needs_fix = True
        elif ivl > 0:
            # Graduated / Review card (ivl in positive days)
            # If card is stuck in learning queue or ivl / reps doesn't match
            if card.queue != 2 or card.type != 2 or card.ivl != ivl or card.reps < rev_count:
                card.type = 2
                card.queue = 2
                card.ivl = ivl
                card.reps = rev_count
                rev_day = int((rev_time - col.crt) / 86400)
                card.due = rev_day + ivl
                needs_fix = True

        if needs_fix:
            repaired.append(card)

    if repaired:
        undo = col.add_custom_undo_entry("Repair desynced cards")
        changes = col.update_cards(repaired)
        col.merge_undo_entries(undo)
        return len(repaired)
    return 0


def _repair_action(legacy, params):
    service = legacy.service
    if service is None or service.col is None:
        raise Exception("collection is not available")
    count = _repair_desynced_cards_impl(service.col)
    if count > 0:
        service.change(None)
    return count


def _repair_desynced_cards(self):
    return _repair_action(self, {})


_syncing_repair = False


def _on_sync_finished():
    global _syncing_repair
    if _syncing_repair:
        _syncing_repair = False
        return
    try:
        from aqt import mw
        if mw and mw.col:
            count = _repair_desynced_cards_impl(mw.col)
            if count > 0:
                print(f"anki_unlock_reposition: Reconciled {count} desynced card(s) after sync")
                _syncing_repair = True
                try:
                    mw.on_sync()
                except Exception:
                    _syncing_repair = False
    except Exception as e:
        _syncing_repair = False
        print(f"anki_unlock_reposition: error in sync reconciler: {e}")


def _on_profile_open():
    try:
        from aqt import mw
        if mw and mw.col:
            count = _repair_desynced_cards_impl(mw.col)
            if count > 0:
                print(f"anki_unlock_reposition: Reconciled {count} desynced card(s) on profile open")
    except Exception as e:
        print(f"anki_unlock_reposition: error on profile open: {e}")


def _on_reviewer_will_show_question(card):
    """Guard against presenting a learning card before its interval has actually elapsed."""
    try:
        from aqt import mw
        if not mw or not mw.col or not card:
            return
        if card.queue == 1:
            last_rev = mw.col.db.first(
                "SELECT id, ivl FROM revlog WHERE cid = ? ORDER BY id DESC LIMIT 1",
                card.id,
            )
            if last_rev:
                rev_id, ivl = last_rev
                if ivl < 0:
                    rev_time = int(rev_id / 1000)
                    expected_due = rev_time + abs(ivl)
                    now = int(time.time())
                    if now < expected_due:
                        card.due = expected_due
                        mw.col.update_cards([card])
                        # Card is not due yet; advance to next
                        if hasattr(mw, "reviewer") and hasattr(mw.reviewer, "nextCard"):
                            mw.reviewer.nextCard()
    except Exception:
        pass


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
        _repair_desynced_cards.api = True
        _repair_desynced_cards.versions = []
        cls.repairDesyncedCards = _repair_desynced_cards
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
        if name == "repairDesyncedCards":
            return _repair_action(self, params)
        return original(self, name, params)

    call._anki_unlock_reposition = True
    legacy_cls.call = call


gui_hooks.profile_did_open.append(_install)
gui_hooks.profile_did_open.append(_on_profile_open)
gui_hooks.sync_did_finish.append(_on_sync_finished)
gui_hooks.reviewer_will_show_question.append(_on_reviewer_will_show_question)
