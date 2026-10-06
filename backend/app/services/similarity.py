"""String similarity in the 0..1 range.

Uses rapidfuzz when installed (fast C++), otherwise a pure-Python fallback
built on difflib that follows the same partial-ratio algorithm.
"""
from __future__ import annotations

from difflib import SequenceMatcher

try:  # pragma: no cover - exercised implicitly when rapidfuzz is present
    from rapidfuzz import fuzz as _fuzz

    def ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return _fuzz.ratio(a, b) / 100.0

    def partial_ratio(short: str, long: str) -> float:
        if not short or not long:
            return 0.0
        return _fuzz.partial_ratio(short, long) / 100.0

    BACKEND = "rapidfuzz"
except ImportError:  # pragma: no cover
    def ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b, autojunk=False).ratio()

    def partial_ratio(short: str, long: str) -> float:
        if not short or not long:
            return 0.0
        if len(short) > len(long):
            short, long = long, short
        if short in long:
            return 1.0
        matcher = SequenceMatcher(None, short, long, autojunk=False)
        best = 0.0
        size = len(short)
        for block in matcher.get_matching_blocks():
            start = max(0, block[1] - block[0])
            window = long[start:start + size]
            score = SequenceMatcher(None, short, window, autojunk=False).ratio()
            if score > best:
                best = score
                if best >= 0.995:
                    break
        return best

    BACKEND = "difflib"
