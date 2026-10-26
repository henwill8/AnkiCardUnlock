#!/usr/bin/env python3
"""Lint a Farsi Anki notes export. Prints OK, or one error per line."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

NONSTANDARD = ("oo", "ee", "â", "ā", "ī", "ū", "ō", "ē", "'", "’")
ALLOWED_DECKS = frozenset({"Farsi", "Farsi::Queue"})


def split_rows(text: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    header: list[str] = []
    body_lines: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("#") and not body_lines:
            header.append(line)
            continue
        if line.strip():
            body_lines.append((lineno, line))
    rows: list[tuple[int, list[str]]] = []
    blob = "".join(f"{line}\n" for _, line in body_lines)
    reader = csv.reader(io.StringIO(blob), delimiter="\t", quotechar='"')
    index = 0
    for fields in reader:
        if not any(field.strip() for field in fields):
            continue
        while index < len(body_lines) and not body_lines[index][1].strip():
            index += 1
        lineno = body_lines[index][0] if index < len(body_lines) else -1
        index += 1
        rows.append((lineno, fields))
    return header, rows


def lint(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    header, rows = split_rows(text)
    errors: list[str] = []
    joined = "\n".join(header)
    widths = {len(fields) for _lineno, fields in rows}
    if not widths:
        widths = {8}
    if widths - {8, 16}:
        errors.append(f"row width must be 8 or 16, got {sorted(widths)}")
        return errors
    if len(widths) != 1:
        errors.append("mixed 8-column and 16-column rows")
        return errors
    width = widths.pop()
    for needle in (
        "#separator:tab",
        "#html:true",
        "#guid column:1",
        f"#tags column:{width}",
    ):
        if needle not in joined:
            errors.append(f"header missing {needle}")

    def check_translit(where: str, tr: str, label: str, required: bool) -> None:
        if not tr:
            if required:
                errors.append(f"{where}: {label} empty")
            return
        if tr != tr.strip() or any(ch.isupper() for ch in tr):
            errors.append(f"{where}: {label} transliteration ({tr})")
        for mark in NONSTANDARD:
            if mark in tr:
                errors.append(f"{where}: nonstandard {mark!r} in {label} ({tr})")
                break

    def check_script(where: str, script: str, label: str, required: bool) -> None:
        if script != script.strip():
            errors.append(f"{where}: leading or trailing space")
        if not script:
            if required:
                errors.append(f"{where}: {label} missing Persian letters")
            return
        if not any("\u0600" <= ch <= "\u06ff" for ch in script):
            errors.append(f"{where}: {label} missing Persian letters")

    def check_unlock(where: str, value: str, label: str) -> None:
        if value not in ("", "1"):
            errors.append(f"{where}: {label} is {value!r}")

    seen_guid: dict[str, int] = {}
    for lineno, fields in rows:
        if len(fields) != width:
            errors.append(f"L{lineno}: {len(fields)} fields, want {width}")
            continue
        guid, model, deck = fields[0], fields[1], fields[2]
        tr, _en, script, unlocked = fields[3], fields[4], fields[5], fields[6]
        tags = fields[-1]
        where = f"L{lineno}"
        verb_tr = ""
        if width == 16:
            verb_tr = fields[7]
        if not guid:
            errors.append(f"{where}: guid empty")
        elif guid in seen_guid:
            errors.append(f"{where}: duplicate guid also on L{seen_guid[guid]}")
        else:
            seen_guid[guid] = lineno
        if model != "Farsi" or deck not in ALLOWED_DECKS:
            errors.append(f"{where}: notetype/deck is {model!r}/{deck!r}")
        if tr != tr.strip() or script != script.strip():
            errors.append(f"{where}: leading or trailing space")
        check_translit(where, tr, "transliteration", not verb_tr.strip())
        check_script(where, script, "script", bool(tr.strip()))
        check_unlock(where, unlocked, "ScriptUnlocked")
        if width == 16:
            verb_tr, verb_script, verb_unlock = fields[7], fields[9], fields[10]
            verb2_tr, verb2_script, verb2_unlock = fields[11], fields[13], fields[14]
            check_translit(where, verb_tr, "verb transliteration", False)
            check_script(where, verb_script, "verb script", bool(verb_tr.strip()))
            check_unlock(where, verb_unlock, "VerbScriptUnlocked")
            check_translit(where, verb2_tr, "verb2 transliteration", False)
            check_script(where, verb2_script, "verb2 script", bool(verb2_tr.strip()))
            check_unlock(where, verb2_unlock, "Verb2ScriptUnlocked")
            if verb_tr.strip() and verb_script != verb_script.strip():
                errors.append(f"{where}: leading or trailing space")
        if not tags.strip():
            errors.append(f"{where}: tags empty")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/lint_notes.py <Farsi.txt>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    errors = lint(path)
    if errors:
        print("\n".join(errors))
        print(f"{len(errors)} errors")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
