#!/usr/bin/env python3
"""Best-effort OCR extraction for the scanned JLPT vocabulary PDF.

The source PDF is image-based, so this script renders selected pages,
splits each page into left/right columns, OCRs each column with Tesseract,
and extracts candidate vocabulary headers.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = next((TOOL_ROOT / "dictionary").glob("*.pdf"), None)
TESSDATA_DIR = TOOL_ROOT / "tessdata"
TMP_DIR = TOOL_ROOT / ".ocr_tmp"


NUMBER_TOKEN = r"\d{1,2}|[oO][A-Za-z0-9]?|[iIl]\d?"


HEADER_WITH_BRACKET_RE = re.compile(
    r"""
    ^\s*
    (?:(?P<number>\d{1,2}|[oO][A-Za-z0-9]?|[iIl]\d?)\s*[|｜]\s*|[|｜]\s*)?
    \s*
    (?P<headword>[ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z][^【\[\]\n|:;。]{0,50}?)
    \s*
    [【\[](?P<bracket>[^】\]\n]{1,80})[】\]]
    """,
    re.VERBOSE,
)

HEADER_WITH_OPEN_BRACKET_RE = re.compile(
    r"""
    ^\s*
    (?:(?P<number>\d{1,2}|[oO][A-Za-z0-9]?|[iIl]\d?|[Tt][oO])\s*[|｜]\s*|[|｜]\s*)?
    \s*
    (?P<headword>[ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z][^【\[\]\n|:;。]{0,50}?)
    \s*
    [【\[](?P<bracket>[^】\]\n|]{1,80})$
    """,
    re.VERBOSE,
)

HEADER_WITHOUT_BRACKET_RE = re.compile(
    r"""
    ^\s*
    (?P<number>\d{1,2}|[oO][A-Za-z0-9]?|[iIl]\d?)\s*
    [|｜]\s*
    (?P<headword>[ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z][^\s【\[\]\n|:;。]{1,40})
    (?:\s+.*)?$
    """,
    re.VERBOSE,
)


@dataclass
class OcrColumn:
    page: int
    column: str
    text: str


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_pages(value: str) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ValueError(f"Invalid page range: {part}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def image_size(path: Path) -> tuple[int, int]:
    result = run(["magick", "identify", "-format", "%w %h", str(path)])
    width_text, height_text = result.stdout.strip().split()
    return int(width_text), int(height_text)


def is_valid_image(path: Path) -> bool:
    try:
        image_size(path)
    except (subprocess.CalledProcessError, ValueError):
        return False
    return True


def render_page(pdf_path: Path, page: int, dpi: int) -> Path:
    TMP_DIR.mkdir(exist_ok=True)
    prefix = TMP_DIR / f"page_{page:04d}_{dpi}"
    image_path = prefix.with_suffix(".png")
    if image_path.exists() and is_valid_image(image_path):
        return image_path
    if image_path.exists():
        image_path.unlink()
    run(
        [
            "pdftoppm",
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(prefix),
        ]
    )
    return image_path


def split_columns(image_path: Path, page: int) -> list[tuple[str, Path]]:
    width, height = image_size(image_path)
    midpoint = width // 2
    gutter = max(10, width // 180)
    columns = [
        ("left", 0, midpoint - gutter),
        ("right", midpoint + gutter, width - midpoint - gutter),
    ]
    output: list[tuple[str, Path]] = []
    for name, x_offset, crop_width in columns:
        column_path = TMP_DIR / f"page_{page:04d}_{name}.png"
        run(
            [
                "magick",
                str(image_path),
                "-crop",
                f"{crop_width}x{height}+{x_offset}+0",
                str(column_path),
            ]
        )
        output.append((name, column_path))
    return output


def ocr_image(image_path: Path) -> str:
    result = run(
        [
            "tesseract",
            "--tessdata-dir",
            str(TESSDATA_DIR),
            str(image_path),
            "stdout",
            "-l",
            "jpn+chi_tra",
            "--psm",
            "6",
        ]
    )
    return result.stdout


def clean_headword(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    value = value.strip(" |:;。・,，.「」『』()（）")
    return value


def normalize_number(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    if lowered == "to":
        return "10"
    if lowered == "os":
        return "08"
    if lowered.startswith("o") and lowered[1:].isdigit():
        return "0" + lowered[1:]
    if lowered.startswith("i"):
        return lowered.replace("i", "1", 1)
    return value.zfill(2) if value.isdigit() else value


def normalize_ocr_header_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[;:,.・'\"“”~j]+\s*", "", line)
    line = re.sub(r"^[^\dA-Za-zぁ-んァ-ヶー一-龯々〆ヵヶ]*[|｜]\s*", "", line)
    if re.match(r"^.{0,6}\d{1,2}\s*[|｜]", line):
        line = re.sub(r"^.*?(\d{1,2})\s*[|｜]\s*", r"\1 | ", line)
    line = re.sub(r"^[iIl]\s+(\d{1,2}\s*[|｜])", r"\1", line)
    line = re.sub(r"^[^ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z\d|｜]*[iIl][oO](\d)\s*[|｜]\s*", r"0\1 | ", line)
    line = re.sub(r"^[^ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z\d|｜]*[Tt][oO]\s*[|｜]\s*", r"10 | ", line)
    line = re.sub(r"^[^ぁ-んァ-ヶー一-龯々〆ヵヶA-Za-z\d|｜]*(\d{1,2})\s*[|｜]\s*", r"\1 | ", line)
    line = re.sub(
        rf"^[|｜]\s*({NUMBER_TOKEN})\s*[|｜]\s*",
        r"\1 | ",
        line,
    )
    line = re.sub(
        r"^[|｜]\s*[Tt][oO]\s*[|｜]\s*",
        "10 | ",
        line,
    )
    return line


def extract_candidates(columns: list[OcrColumn], level: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[int, str, str]] = set()

    for column in columns:
        lines = [line.rstrip() for line in column.text.splitlines()]
        for line_index, line in enumerate(lines):
            candidate_line = normalize_ocr_header_line(line)
            if (
                "【" in line
                and "】" not in line
                and line_index + 1 < len(lines)
                and "】" in lines[line_index + 1]
            ):
                candidate_line = candidate_line + " " + lines[line_index + 1].strip()

            bracket_matches = list(HEADER_WITH_BRACKET_RE.finditer(candidate_line))
            if not bracket_matches and "【" in candidate_line and "】" not in candidate_line:
                open_match = HEADER_WITH_OPEN_BRACKET_RE.match(candidate_line)
                bracket_matches = [open_match] if open_match else []

            for match in bracket_matches:
                headword = clean_headword(match.group("headword"))
                bracket = (match.group("bracket") or "").strip()
                if len(headword) < 2:
                    continue
                if re.fullmatch(r"[Nn]\d|道具|住家", headword):
                    continue

                key = (column.page, column.column, headword)
                if key in seen:
                    continue
                seen.add(key)

                context = " / ".join(
                    item.strip()
                    for item in lines[line_index : line_index + 3]
                    if item.strip()
                )
                rows.append(
                    {
                        "level": level,
                        "page": str(column.page),
                        "column": column.column,
                        "entry_no": normalize_number(match.group("number")),
                        "headword": headword,
                        "bracket": bracket,
                        "ocr_context": context,
                    }
                )

            if "【" not in candidate_line and "[" not in candidate_line:
                match = HEADER_WITHOUT_BRACKET_RE.match(candidate_line)
                if match:
                    headword = clean_headword(match.group("headword"))
                    entry_no = normalize_number(match.group("number"))
                    if len(headword) < 2:
                        continue
                    if re.search(r"[、，,]", headword):
                        continue
                    if re.fullmatch(r"[Nn]\d|道具|住家", headword):
                        continue
                    if (
                        entry_no.isdigit()
                        and int(entry_no) >= 50
                        and line_index >= max(0, len(lines) - 3)
                    ):
                        continue

                    key = (column.page, column.column, headword)
                    if key in seen:
                        continue
                    seen.add(key)

                    context = " / ".join(
                        item.strip()
                        for item in lines[line_index : line_index + 3]
                        if item.strip()
                    )
                    rows.append(
                        {
                            "level": level,
                            "page": str(column.page),
                            "column": column.column,
                            "entry_no": entry_no,
                            "headword": headword,
                            "bracket": "",
                            "ocr_context": context,
                        }
                    )
    return rows


def write_raw(columns: list[OcrColumn], raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for column in columns:
        path = raw_dir / f"page_{column.page:04d}_{column.column}.txt"
        path.write_text(column.text, encoding="utf-8")


def raw_column_path(raw_dir: Path, page: int, column: str) -> Path:
    return raw_dir / f"page_{page:04d}_{column}.txt"


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["level", "page", "column", "entry_no", "headword", "bracket", "ocr_context"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--pages", required=True, help="Pages like 100 or 95-100,104")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--output", type=Path, default=TOOL_ROOT / "outputs" / "jlpt_vocab_candidates.csv")
    parser.add_argument("--raw-dir", type=Path, default=TOOL_ROOT / "outputs" / "ocr_raw")
    parser.add_argument("--level", default="", help="Optional JLPT level label to write into the CSV")
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Ignore existing raw OCR text files and regenerate them.",
    )
    args = parser.parse_args()

    if args.pdf is None or not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")
    for tool in ("pdftoppm", "magick", "tesseract"):
        run(["which", tool])
    if not (TESSDATA_DIR / "jpn.traineddata").exists():
        raise SystemExit(f"Missing OCR language data: {TESSDATA_DIR / 'jpn.traineddata'}")

    pages = parse_pages(args.pages)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    columns: list[OcrColumn] = []
    for page in pages:
        print(f"OCR page {page}...", flush=True)
        rendered = render_page(args.pdf, page, args.dpi)
        for column_name, column_image in split_columns(rendered, page):
            raw_path = raw_column_path(args.raw_dir, page, column_name)
            if raw_path.exists() and not args.force_ocr:
                text = raw_path.read_text(encoding="utf-8")
            else:
                text = ocr_image(column_image)
                raw_path.write_text(text, encoding="utf-8")
            columns.append(OcrColumn(page=page, column=column_name, text=text))

    rows = extract_candidates(columns, args.level)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} candidate rows to {args.output}")
    print(f"Wrote raw OCR text to {args.raw_dir}")


if __name__ == "__main__":
    main()
