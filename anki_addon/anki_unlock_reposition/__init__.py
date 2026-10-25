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
    out = service.col.sched.reposition_new_cards(ids, start, 1, False, False)
    service.change(out)
    return len(ids)


def _reposition_new_cards(self, cards, positions):
    return _apply(self, {"cards": cards, "positions": positions})


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
        cls._anki_unlock_reposition = True
    legacy_cls = _legacy_class(ac)
    if legacy_cls is None or getattr(legacy_cls.call, "_anki_unlock_reposition", False):
        return
    original = legacy_cls.call

    def call(self, name, params):
        if name == "repositionNewCards":
            return _apply(self, params)
        return original(self, name, params)

    call._anki_unlock_reposition = True
    legacy_cls.call = call


gui_hooks.profile_did_open.append(_install)
