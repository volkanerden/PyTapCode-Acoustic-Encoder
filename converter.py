"""
From terminal, run:

    python converter.py input.docx output.docx
"""

import re
import sys
import zipfile
import xml.sax.saxutils
from typing import Dict, Iterable, List, Tuple


# uppercase mapping for turkish characters
TURKISH_UPPER_MAP: Dict[str, str] = {
    "i": "İ",
    "ı": "I",
    "ğ": "Ğ",
    "ş": "Ş",
    "ö": "Ö",
    "ü": "Ü",
    "ç": "Ç",
}


def turkish_upper(ch: str) -> str:
    return TURKISH_UPPER_MAP.get(ch, ch.upper())


# 5×6 tap‑code alphabet matrix
TAP_MATRIX: List[List[str | None]] = [
    ["A", "B", "C", "Ç", "D", "E"],
    ["F", "G", "Ğ", "H", "I", "İ"],
    ["J", "K", "L", "M", "N", "O"],
    ["Ö", "P", "R", "S", "Ş", "T"],
    ["U", "Ü", "V", "Y", "Z", None], # the 30th cell is unused
]


def build_tap_map(matrix: List[List[str | None]]) -> Dict[str, Tuple[int, int]]:
    """
    character to matrix position mapping.
    rows and columns start at 1.
    If none, skip.
    """
    mapping: Dict[str, Tuple[int, int]] = {}
    for row_index, row in enumerate(matrix, start=1):
        for col_index, ch in enumerate(row, start=1):

            if ch is None:
                continue

            mapping[ch] = (row_index, col_index)
            lower = ch.lower()
            upper = ch.upper()
            mapping[lower] = (row_index, col_index)
            mapping[upper] = (row_index, col_index)
    return mapping


# Build the character → (row, col) lookup table
TAP_MAP: Dict[str, Tuple[int, int]] = build_tap_map(TAP_MATRIX)

# Punctuation removed from the source text before encoding.
# The slash character ``/`` is not included because it is used as part of the encoding format
PUNCTUATION: str = ".,;:!?-—()[]{}\"'…*%&“”‘’‹›«»—‑–‒–‖|\n\r\t\f\v"


def number_to_turkish_words(n: int) -> str:
    """
    number to word conversion
    Handles values from 0 up to billions.
    Follows Turkish numbering conventions.
    """

    if n == 0:
        return "sıfır"

    units = {
        1: "bir",
        2: "iki",
        3: "üç",
        4: "dört",
        5: "beş",
        6: "altı",
        7: "yedi",
        8: "sekiz",
        9: "dokuz",
    }
    tens_map = {
        10: "on",
        20: "yirmi",
        30: "otuz",
        40: "kırk",
        50: "elli",
        60: "altmış",
        70: "yetmiş",
        80: "seksen",
        90: "doksan",
    }

    def under_thousand(num: int) -> List[str]:
        words: List[str] = []
        hundreds = num // 100
        remainder = num % 100
        if hundreds:
            # Omit "bir" before "yüz"
            if hundreds > 1:
                words.append(units[hundreds])
            words.append("yüz")
        tens = remainder // 10 * 10
        ones = remainder % 10
        if tens:
            words.append(tens_map[tens])
        if ones:
            words.append(units[ones])
        return words

    parts: List[str] = []
    billions = n // 1_000_000_000
    n %= 1_000_000_000
    millions = n // 1_000_000
    n %= 1_000_000
    thousands = n // 1_000
    remainder = n % 1_000

    if billions:
        parts.extend(number_to_turkish_words(billions).split())
        parts.append("milyar")
    if millions:
        parts.extend(number_to_turkish_words(millions).split())
        parts.append("milyon")
    if thousands:
        # Omit "bir" before "bin"
        if thousands > 1:
            parts.extend(number_to_turkish_words(thousands).split())
        parts.append("bin")
    if remainder:
        parts.extend(under_thousand(remainder))
    return " ".join(parts)


def expand_numbers(text: str) -> str:

    def repl(match: re.Match[str]) -> str:
        number_str = match.group(0)
        try:
            value = int(number_str)
        except ValueError:
            return number_str
        return number_to_turkish_words(value)

    return re.sub(r"\d+", repl, text)


def remove_punctuation(text: str) -> str:
    translator = str.maketrans({ch: "" for ch in PUNCTUATION})
    return text.translate(translator)


def encode_char(ch: str) -> str:
    """
    Characters not found in ``TAP_MAP`` are ignored by returning an
    empty string.  Before lookup, letters are uppercased using the
    Turkish locale aware function. Whitespace characters are not
    encoded at all, they act solely as word delimiters.
    """
    if ch.isspace():
        return ""
    ch_key = turkish_upper(ch)
    pos = TAP_MAP.get(ch_key)
    if not pos:
        return ""
    row, col = pos
    return "." * row + " " + "." * col


def encode_token(token: str) -> str:
    """
    Each character in "token" is encoded individually. Empty
    strings result in an empty encoded token. The encoded token is
    constructed by joining encoded characters with single spaces.
    """
    encoded_chars: List[str] = []
    for ch in token:
        pattern = encode_char(ch)

        if pattern:
            encoded_chars.append(pattern)
    return " ".join(encoded_chars)


def encode_text_to_tokens(text: str) -> Iterable[str]:
    """Encode the full text into a sequence of encoded words.

    The cleaned input string "text" is split on whitespace into
    individual words. Each word is encoded using
    ``encode_token`` (which processes characters one by one).
    A slash is appended to the encoded representation of every word
    to mark the end. Tokens that produce no encoding are skipped.
    """

    # split on any whitespace to obtain words
    # consecutive spaces, newlines and tabs are treated as a single separator
    tokens = text.split()
    for token in tokens:
        encoded = encode_token(token)
        if encoded:
            yield f"{encoded} /"


def create_minimal_docx(output_path: str, text: str) -> None:
    """
    Constructs a minimal OpenXML package by writing three
    parts: "[Content_Types].xml", "_rels/.rels", and
    "document.xml".  The "document.xml" contains the provided
    "text" inside a single paragraph.
    """
    # XML content for [Content_Types].xml
    content_types = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default ContentType=\"application/xml\" Extension=\"xml\"/>"
        "<Default ContentType=\"application/vnd.openxmlformats-package.relationships+xml\" Extension=\"rels\"/>"
        "<Override ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\" PartName=\"/document.xml\"/>"
        "</Types>"
    )

    rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"/document.xml\"/>"
        "</Relationships>"
    )

    escaped_text = xml.sax.saxutils.escape(text)
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        "<w:body>"
        "<w:p>"
        "<w:r><w:t>" + escaped_text + "</w:t></w:r>"
        "</w:p>"
        "</w:body>"
        "</w:document>"
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("document.xml", document_xml)


def read_docx_text(input_path: str) -> str:
    # Try using python-docx if installed
    try:
        import docx  # type: ignore
        doc = docx.Document(input_path)
        return " ".join(paragraph.text for paragraph in doc.paragraphs)

    except Exception:
        # Fallback: parse the XML manually
        with zipfile.ZipFile(input_path) as z:
            candidate_parts = ["word/document.xml", "document.xml"]
            xml_data = None
            for part in candidate_parts:
                try:
                    xml_data = z.read(part)
                    break
                except KeyError:
                    continue
            if xml_data is None:
                raise FileNotFoundError(
                    "Could not find document.xml part in the .docx archive"
                )
        # Decode bytes to string
        xml_str = xml_data.decode("utf-8", errors="ignore")
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml_str, flags=re.DOTALL)
        # Replace XML character entities with their literal form
        decoded = [xml.sax.saxutils.unescape(t) for t in texts]
        return " ".join(decoded)


def process_text(text: str) -> str:
    expanded = expand_numbers(text)
    cleaned = remove_punctuation(expanded)
    encoded_tokens = list(encode_text_to_tokens(cleaned))
    return " ".join(encoded_tokens)


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: python converter.py <input.docx> <output.docx>",
            file=sys.stderr,
        )
        return 1
    input_path = argv[1]
    output_path = argv[2]
    try:
        original_text = read_docx_text(input_path)
    except Exception as exc:
        print(f"Error reading input file: {exc}", file=sys.stderr)
        return 1
    # Process the text
    encoded_text = process_text(original_text)
    try:
        create_minimal_docx(output_path, encoded_text)
    except Exception as exc:
        print(f"Error writing output file: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))