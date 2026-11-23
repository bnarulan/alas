import re

CHUNK_CHARS = 320
BOUNDARY = re.compile(r"""[.!?…]+[»”’"')\]]*(?:\s+|$)|\n(?:[^\S\r\n]*\r?\n)+""")
CLAUSE_END = re.compile(r"[,.;:!?…]\s+|\n+")


def sentence_ends(text: str) -> list[int]:
    ends = [match.end() for match in BOUNDARY.finditer(text)]
    if not ends or ends[-1] < len(text):
        ends.append(len(text))
    return ends


def split_passage(text: str) -> list[str]:
    """Group complete sentences and split unusually long sentences at whitespace."""
    if len(text) <= CHUNK_CHARS:
        return [text]

    chunks: list[str] = []
    pending = ""
    start = 0
    for end in sentence_ends(text):
        sentence = text[start:end]
        start = end
        if len(pending) + len(sentence) > CHUNK_CHARS and pending:
            chunks.append(pending)
            pending = ""
        while len(sentence) > CHUNK_CHARS:
            window = sentence[:CHUNK_CHARS]
            cut = max((match.end() for match in re.finditer(r"\s+", window)), default=0)
            if cut < CHUNK_CHARS // 2:
                cut = CHUNK_CHARS
            chunks.append(sentence[:cut])
            sentence = sentence[cut:]
        pending += sentence

    if pending:
        chunks.append(pending)
    return chunks


def split_for_retry(text: str) -> tuple[str, str] | None:
    """Bisect near a clause boundary while keeping the source punctuation and spacing."""
    middle = len(text) / 2
    lower, upper = len(text) // 4, len(text) * 3 // 4
    for pattern in (BOUNDARY, CLAUSE_END, re.compile(r"\s+")):
        cuts = [match.end() for match in pattern.finditer(text) if lower < match.end() < upper]
        if cuts:
            cut = min(cuts, key=lambda position: abs(position - middle))
            return text[:cut], text[cut:]
    return None
