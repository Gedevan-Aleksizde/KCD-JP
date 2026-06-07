#! /usr/bin/env python3

import argparse
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("input", nargs="?", type=Path, default=Path("strip.xml"))
parser.add_argument("output", nargs="?", type=Path, default=Path("strip-output.csv"))
parser.add_argument("--keep-br", action="store_true")

ROW_PATTERN = re.compile(
    r"^<Row><Cell>(?P<text1>.*?)</Cell><Cell>(?P<text2>.*?)</Cell><Cell>(?P<text3>.*?)</Cell></Row>$"
)


def csv_field(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def html_escape_for_text(value: str) -> str:
    return value.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def normalize_text3(value: str, keep_br: bool) -> str:
    if not keep_br:
        value = value.replace("&lt;br/&gt;", "  ")

    replacements = (
        ("“", "「"),
        ("”", "」"),
        ("？", "?"),
        ("！", "!"),
        ("（", " ("),
        ("）", ") "),
        ("［", " ["),
        ("］", "] "),
        ("｛", " {"),
        ("｝", "} "),
        ("：", ":"),
        ("；", ";"),
        ("，", ","),
        ("．", "."),
    )
    for source, target in replacements:
        value = value.replace(source, target)
    return value


def main(args: argparse.Namespace) -> None:
    lines = args.input.read_text(encoding="utf-8").splitlines()

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            match = ROW_PATTERN.fullmatch(line.strip())
            if match is None:
                raise ValueError(f"invalid row format at line {line_number}: {line}")

            text1 = match.group("text1")
            text2 = html_escape_for_text(match.group("text2"))
            text3 = normalize_text3(html_escape_for_text(match.group("text3")), args.keep_br)

            handle.write(
                ",".join(
                    [
                        csv_field(text1),
                        csv_field(text2),
                        csv_field(""),
                        csv_field(""),
                        csv_field(text3),
                        "1",
                    ]
                )
                + "\n"
            )


if __name__ == "__main__":
    main(parser.parse_args())
