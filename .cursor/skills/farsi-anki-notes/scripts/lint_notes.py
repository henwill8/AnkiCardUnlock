#!/usr/bin/env python3
"""Lint a Farsi Anki notes export. Prints OK, or one error per line."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

NONSTANDARD = ("oo", "ee", "â", "ā", "ī", "ū", "ō", "ē", "'", "’")
RLM = "\u200f"


def period_marks_ok(text: str) -> bool:
    for index, ch in enumerate(text):
        if ch != ".":
            continue
        before = text[index - 1] if index else ""
        after = text[index + 1] if index + 1 < len(text) else ""
        if before != RLM or after != RLM:
            return False
    return True


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
    for needle in ("#separator:tab", "#html:true", "#guid column:1", "#tags column:10"):
        if needle not in joined:
            errors.append(f"header missing {needle}")

    seen_guid: dict[str, int] = {}
    for lineno, fields in rows:
        if len(fields) != 10:
            errors.append(f"L{lineno}: {len(fields)} fields, want 10")
            continue
        guid, model, deck, tr, _en, script, example, blank, unlocked, tags = fields
        where = f"L{lineno}"
        if not guid:
            errors.append(f"{where}: guid empty")
        elif guid in seen_guid:
            errors.append(f"{where}: duplicate guid also on L{seen_guid[guid]}")
        else:
            seen_guid[guid] = lineno
        if model != "Farsi" or not deck.strip():
            errors.append(f"{where}: notetype/deck is {model!r}/{deck!r}")
        if tr != tr.strip() or script != script.strip():
            errors.append(f"{where}: leading or trailing space")
        if any(ch.isupper() for ch in tr):
            errors.append(f"{where}: transliteration has uppercase ({tr})")
        for mark in NONSTANDARD:
            if mark in tr:
                errors.append(f"{where}: nonstandard {mark!r} in transliteration ({tr})")
                break
        if not any("\u0600" <= ch <= "\u06ff" for ch in script):
            errors.append(f"{where}: script missing Persian letters")
        if unlocked not in ("", "1"):
            errors.append(f"{where}: ScriptUnlocked is {unlocked!r}")
        if example != example.strip() or blank != blank.strip():
            errors.append(f"{where}: leading or trailing space in example")
        if not any("\u0600" <= ch <= "\u06ff" for ch in example):
            errors.append(f"{where}: example sentence missing Persian letters")
        if not period_marks_ok(example) or not period_marks_ok(blank):
            errors.append(f"{where}: period missing right-to-left marks")
        if "____" not in blank:
            errors.append(f"{where}: example blank missing ____")
        elif f"{RLM}____{RLM}" not in blank:
            errors.append(f"{where}: example blank underlines missing right-to-left marks")
        elif not any(
            "\u0600" <= ch <= "\u06ff" for ch in blank.replace("____", "").replace(RLM, "")
        ):
            errors.append(f"{where}: example blank leaves no words")
        else:
            rest = blank.replace("____", "")
            if any(ch.isascii() and ch.isalpha() for ch in rest):
                errors.append(f"{where}: example blank is not in Persian script")
            elif rest.strip(" \t.!?؟،؛:\"'()[]\u200f") and not any(
                "\u0600" <= ch <= "\u06ff" for ch in rest
            ):
                errors.append(f"{where}: example blank is not in Persian script")
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
