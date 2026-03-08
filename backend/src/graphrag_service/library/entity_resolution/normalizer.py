"""Author name normalization and blocking key computation.

Handles diacritics, suffixes, CJK names, and initial extraction
for entity resolution blocking.
"""

import re
import unicodedata
from dataclasses import dataclass


# Common suffixes to strip (case-insensitive)
_SUFFIXES = re.compile(
    r"\b(jr\.?|sr\.?|ii|iii|iv|ph\.?d\.?|md|m\.?d\.?)\s*$",
    re.IGNORECASE,
)

# Patterns for detecting initials like "G." or "G.E."
_INITIAL_PATTERN = re.compile(r"^[A-Z]\.?$")


@dataclass(frozen=True)
class NameParts:
    """Parsed name components."""

    first: str
    last: str
    first_initial: str


def normalize_name(name: str) -> str:
    """Normalize an author name for comparison.

    Steps:
    1. Strip whitespace
    2. Decompose Unicode and remove combining marks (diacritics)
    3. Remove suffixes (Jr., Sr., III, Ph.D., etc.)
    4. Collapse multiple spaces
    5. Lowercase
    """
    if not name:
        return ""

    # Strip and decompose Unicode
    text = name.strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    # Remove suffixes
    text = _SUFFIXES.sub("", text).strip()

    # Remove trailing commas/periods from suffix removal
    text = text.rstrip(",").rstrip(".").strip()

    # Collapse whitespace and lowercase
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def parse_name_parts(name: str) -> NameParts:
    """Parse a name into first/last/initial parts.

    Handles:
    - "First Last" → first="first", last="last", initial="f"
    - "First Middle Last" → first="first", last="last", initial="f"
    - "Last, First" → first="first", last="last", initial="f"
    - Single name → first="", last=name, initial=""
    """
    normalized = normalize_name(name)
    if not normalized:
        return NameParts(first="", last="", first_initial="")

    # Handle "Last, First" format
    if "," in normalized:
        parts = [p.strip() for p in normalized.split(",", 1)]
        last = parts[0]
        first = parts[1] if len(parts) > 1 else ""
    else:
        tokens = normalized.split()
        if len(tokens) == 1:
            return NameParts(first="", last=tokens[0], first_initial="")
        first = tokens[0]
        last = tokens[-1]

    first_initial = first[0] if first else ""
    return NameParts(first=first, last=last, first_initial=first_initial)


def compute_blocking_key(name: str) -> str:
    """Compute a blocking key for candidate grouping.

    Format: "{last_name}_{first_initial}" (all lowercase, normalized).
    Authors with the same blocking key are compared pairwise.
    """
    parts = parse_name_parts(name)
    if not parts.last:
        return ""
    if not parts.first_initial:
        return parts.last
    return f"{parts.last}_{parts.first_initial}"
